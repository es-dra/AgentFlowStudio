from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.video_pipeline import SCHEMA_VERSION, build_memory_video_pipeline_plan


REVIEW_TYPE = "agentflow_memory_video_pipeline_review"
ARTIFACT_MANIFEST_TYPE = "agentflow_memory_video_pipeline_artifact_manifest"
UNSAFE_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "file://",
    "data:image/",
    "Bearer ",
    "signed_url",
    "signature=",
    "token=",
    "api_key",
    "secret_key",
    "https://",
    "http://",
)


def build_memory_video_pipeline_review(
    protocol: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Build a no-call review artifact from explicit I2V manifest references."""
    plan = build_memory_video_pipeline_plan(protocol)
    _validate_artifact_manifest(artifact_manifest)
    artifacts = [_load_artifact(item) for item in artifact_manifest["artifacts"]]
    _validate_expected_lanes(plan, artifacts)
    lane_counts = Counter(item["lane_id"] for item in artifacts)
    run_ids = sorted({item["run_id"] for item in artifacts})
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": REVIEW_TYPE,
        "protocol_id": plan["protocol_id"],
        "provider_calls_started_by_review": False,
        "writes_long_term_memory": False,
        "review_inputs": {
            "artifact_manifest_type": artifact_manifest["artifact_type"],
            "run_ids": run_ids,
            "artifact_count": len(artifacts),
        },
        "lane_parity": _lane_parity(plan, artifacts),
        "video_artifacts": [_safe_video_artifact(item) for item in artifacts],
        "review_rubric": protocol["review_rubric"],
        "storyboard": protocol["storyboard"],
        "cross_run_stability": {
            "status": "ready_for_human_visual_review" if len(run_ids) > 1 else "not_available_single_run",
            "run_count": len(run_ids),
            "lane_repeat_counts": dict(sorted(lane_counts.items())),
            "review_fields": [
                "shot_structure_consistency",
                "identity_anchor_retention",
                "wardrobe_anchor_retention",
                "scene_anchor_retention",
                "occlusion_recovery_repeatability",
                "motion_physics_repeatability",
            ],
            "machine_judgement": "not_performed",
        },
        "claim_boundaries": {
            "structure_verification": "review_artifact_built",
            "runtime_verification": "manifest_status_only",
            "human_acceptance": "not_reviewed",
            "business_validation": "not_validated",
            "quality_improvement_claim": "not_claimed",
            "durable_memory_runtime": "not_implemented",
        },
    }


def write_memory_video_pipeline_review(review: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(output_root / "memory_video_pipeline_review.json", review),
    ]
    report_path = output_root / "memory_video_pipeline_review.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_memory_video_pipeline_review_report(review), encoding="utf-8")
    paths.append(report_path)
    return paths


def render_memory_video_pipeline_review_report(review: dict[str, Any]) -> str:
    lane_lines = "\n".join(
        f"- {lane}: {count} run(s)"
        for lane, count in review["cross_run_stability"]["lane_repeat_counts"].items()
    )
    return "\n".join(
        [
            "# Memory Video Pipeline Review",
            "",
            f"- Protocol: `{review['protocol_id']}`",
            "- Provider calls: not started by review",
            "- Runtime verification: manifest status only",
            "- Human acceptance: not reviewed",
            "- Business validation: not validated",
            "- Quality improvement claim: not claimed",
            "- Durable Memory runtime: not implemented",
            "",
            "## Cross-Run Inputs",
            "",
            f"- Runs reviewed: {review['cross_run_stability']['run_count']}",
            lane_lines,
            "",
        ]
    )


def _validate_artifact_manifest(artifact_manifest: dict[str, Any]) -> None:
    if artifact_manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("memory video artifact manifest schema_version must be 0.1.0")
    if artifact_manifest.get("artifact_type") != ARTIFACT_MANIFEST_TYPE:
        raise ValueError(f"memory video artifact manifest artifact_type must be {ARTIFACT_MANIFEST_TYPE}")
    artifacts = artifact_manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("memory video artifact manifest requires artifacts")


def _load_artifact(item: dict[str, Any]) -> dict[str, Any]:
    run_id = str(item.get("run_id") or "")
    lane_id = str(item.get("lane_id") or "")
    manifest_path = Path(str(item.get("i2v_manifest_path") or ""))
    if not run_id or not lane_id or not manifest_path.is_file():
        raise ValueError("artifact entries require run_id, lane_id, and readable i2v_manifest_path")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _reject_unsafe_refs(manifest)
    output = _single_output(manifest)
    return {
        "run_id": run_id,
        "lane_id": lane_id,
        "status": manifest.get("status"),
        "provider": manifest.get("provider"),
        "api_family": manifest.get("api_family"),
        "model": manifest.get("model"),
        "task_status": manifest.get("task", {}).get("task_status"),
        "source_image_sha256": manifest.get("input_image", {}).get("sha256"),
        "output": output,
    }


def _reject_unsafe_refs(value: Any) -> None:
    serialized = str(value)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_FRAGMENTS):
        raise ValueError("memory video review input contains unsafe provider URL, local path, secret, or signed media reference")


def _single_output(manifest: dict[str, Any]) -> dict[str, Any]:
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list) or len(outputs) != 1:
        raise ValueError("I2V manifest must contain exactly one output")
    output = outputs[0]
    if output.get("provider_url_persisted") is not False:
        raise ValueError("I2V manifest must not persist provider URLs")
    return {
        "candidate_id": output.get("candidate_id"),
        "video_ref": output.get("video_path"),
        "byte_count": output.get("byte_count"),
        "sha256": output.get("sha256"),
        "content_type": output.get("content_type"),
    }


def _validate_expected_lanes(plan: dict[str, Any], artifacts: list[dict[str, Any]]) -> None:
    expected = {lane["lane_id"] for lane in plan["lane_plans"]}
    by_run: dict[str, set[str]] = defaultdict(set)
    for item in artifacts:
        if item["lane_id"] not in expected:
            raise ValueError(f"unexpected lane artifact: {item['lane_id']}")
        by_run[item["run_id"]].add(item["lane_id"])
    missing = {
        run_id: sorted(expected - lanes)
        for run_id, lanes in by_run.items()
        if lanes != expected
    }
    if missing:
        raise ValueError(f"missing lane artifacts: {missing}")


def _lane_parity(plan: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, bool]:
    source_hashes = {item["source_image_sha256"] for item in artifacts}
    return {
        **plan["lane_parity"],
        "expected_lanes_present": True,
        "same_source_image_sha256": len(source_hashes) == 1,
        "all_manifests_succeeded": all(item["status"] == "succeeded" for item in artifacts),
    }


def _safe_video_artifact(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": item["run_id"],
        "lane_id": item["lane_id"],
        "status": item["status"],
        "task_status": item["task_status"],
        "provider": item["provider"],
        "api_family": item["api_family"],
        "model": item["model"],
        "source_image_sha256": item["source_image_sha256"],
        "output": item["output"],
    }
