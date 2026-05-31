from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from narratocut.utils import write_json


SCHEMA_VERSION = "0.1.0"
LOULAN_PACKAGE_TYPE = "agentflow_loulan_memory_package"
ELIGIBLE_STATUSES = frozenset({"approved", "promoted", "merged"})
BLOCKED_STATUSES = frozenset({"candidate", "candidate_pending_human_review", "needs_repair", "rejected", "expired"})
UNSAFE_OUTPUT_FRAGMENTS = ("D:\\", "C:\\", "file://", "Bearer ", "signed_url", "token=", "api_key", "secret_key", ".mp4", ".mov")


def build_loulan_memory_package(project_root: str | Path, *, created_at: str) -> dict[str, Any]:
    """Build a read-only Loulan pilot package without calling providers or copying media."""
    root = Path(project_root)
    manifest = _read_json(root / "project_manifest.json")
    shots = _read_json(root / "manifests" / "shot_list.json").get("shots") or []
    character_assets = _read_json(root / "manifests" / "character_assets.json").get("assets") or []
    asset_entries = [_asset_entry(asset) for asset in character_assets]
    rejected_refs = _relative_files(root, root / "human" / "rejected", limit=12)
    package = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": LOULAN_PACKAGE_TYPE,
        "package_id": f"{manifest.get('project_id', 'loulan')}_memory_production_package_v0",
        "created_at": created_at,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "reads_company_knowledge": False,
        "project": _project_summary(root, manifest),
        "shot_summary": _shot_summary(shots),
        "asset_summary": _asset_summary(asset_entries, rejected_refs),
        "memory_collections": _memory_collections(root),
        "provider_route_safety": _provider_route_safety(root, manifest),
        "promotion_gates": _promotion_gates(asset_entries, rejected_refs),
        "next_context_bundle_draft": _next_context_bundle_draft(asset_entries, rejected_refs),
        "canvas_nodes": _canvas_nodes(asset_entries, rejected_refs),
        "api_workbench_skeleton": _api_workbench_skeleton(),
        "claim_boundaries": _claim_boundaries(),
    }
    _reject_unsafe_output(package)
    return package


def write_loulan_memory_package(package: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "loulan_memory_package.json", package)
    report_path = output_root / "loulan_memory_package.md"
    report_path.write_text(render_loulan_memory_package_report(package), encoding="utf-8")
    return [json_path, report_path]


def render_loulan_memory_package_report(package: dict[str, Any]) -> str:
    gates = package["promotion_gates"]
    safety = package["provider_route_safety"]
    return "\n".join(
        [
            "# Loulan Memory Package",
            "",
            f"- Project: `{package['project']['title']}`",
            f"- Package: `{package['package_id']}`",
            "- Provider calls: not started",
            "- durable Memory runtime: not implemented",
            "- Company memory write: not performed",
            f"- Image route: `{safety['image_generation']}`",
            f"- Promotion gate: `{gates['overall_status']}`",
            f"- Eligible memory refs: {len(package['next_context_bundle_draft']['eligible_memory_refs'])}",
            f"- Blocked memory refs: {len(package['next_context_bundle_draft']['blocked_memory_refs'])}",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required Loulan file: {path.name}") from exc


def _project_summary(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(manifest.get("project_id") or "loulan_scene_assets"),
        "title": str(manifest.get("title") or "Loulan Scene Assets"),
        "source_root_label": root.name,
        "target_format": str(manifest.get("target_format") or "unknown"),
        "current_phase": str(manifest.get("current_phase") or "unknown"),
        "claim_level": str(manifest.get("current_claim_level") or "not_reviewed"),
        "video_generation_status": str(manifest.get("video_generation_status") or "unknown"),
    }


def _shot_summary(shots: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(shot.get("quality_status") or "planned") for shot in shots)
    return {
        "total_shots": len(shots),
        "status_counts": dict(sorted(statuses.items())),
        "sample_shots": [
            {
                "shot_id": str(shot.get("shot_id") or ""),
                "generation_block": shot.get("generation_block"),
                "scene": str(shot.get("scene") or ""),
                "status": str(shot.get("quality_status") or "planned"),
            }
            for shot in shots[:8]
        ],
    }


def _asset_entry(asset: dict[str, Any]) -> dict[str, Any]:
    status = _normalize_status(asset.get("status"))
    sha = str(asset.get("sha256") or "")
    ref = f"character:{asset.get('asset_id') or 'unknown'}"
    return {
        "memory_ref": ref,
        "asset_id": str(asset.get("asset_id") or ""),
        "label": _asset_label(asset),
        "character": str(asset.get("character") or ""),
        "phase": str(asset.get("phase") or ""),
        "status": status,
        "sha256": sha,
        "sha256_present": bool(sha),
        "output_ref": _safe_relative_text(asset.get("output_path")),
        "asset_card_ref": _safe_relative_text(asset.get("asset_card")),
        "review_card_ref": _safe_relative_text(asset.get("review_card")),
        "eligible_for_context": status in ELIGIBLE_STATUSES and bool(sha),
    }


def _asset_label(asset: dict[str, Any]) -> str:
    character = str(asset.get("character") or asset.get("asset_id") or "asset")
    phase = str(asset.get("phase") or "").replace("_", " ")
    return f"{character} {phase}".strip()


def _asset_summary(entries: list[dict[str, Any]], rejected_refs: list[str]) -> dict[str, Any]:
    statuses = Counter(entry["status"] for entry in entries)
    return {
        "total_assets": len(entries),
        "status_counts": dict(sorted(statuses.items())),
        "missing_sha256_count": sum(1 for entry in entries if not entry["sha256_present"]),
        "rejected_asset_count": len(rejected_refs),
        "assets": entries[:16],
        "rejected_asset_refs": rejected_refs,
    }


def _memory_collections(root: Path) -> list[dict[str, Any]]:
    return [
        _collection(root, "character_memory", "asset_library/characters", "character assets"),
        _collection(root, "director_feedback", "asset_library/director_notes", "director feedback"),
        _collection(root, "motion_intent", "asset_library/motion_intent", "motion intent"),
        _collection(root, "review_cards", "reviews", "human review evidence"),
        _collection(root, "provider_run_ledgers", "runs", "provider run ledgers"),
    ]


def _collection(root: Path, collection_id: str, relative_dir: str, label: str) -> dict[str, Any]:
    files = _relative_files(root, root / relative_dir, limit=8)
    return {
        "collection_id": collection_id,
        "label": label,
        "status": "available" if files else "missing",
        "sample_refs": files,
        "auto_promotes_memory": False,
    }


def _provider_route_safety(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    requested = str(manifest.get("image_model_requested") or "").lower()
    route_failure_doc = (root / "docs" / "image2_route_failure_and_workbench_plan_v0.md").exists()
    unsafe_builtin = "built-in" in requested or "chatgpt image2" in requested or route_failure_doc
    video_status = str(manifest.get("video_generation_status") or "")
    return {
        "image_generation": "blocked_until_api_workbench" if unsafe_builtin else "dry_run_only",
        "video_generation": "deferred_until_keyframe_approval" if "deferred" in video_status else "dry_run_only",
        "unsafe_builtin_image_route_detected": unsafe_builtin,
        "request_preview_only": True,
        "capability_gates_required": ["image", "video"],
    }


def _promotion_gates(entries: list[dict[str, Any]], rejected_refs: list[str]) -> dict[str, Any]:
    blocking = []
    for entry in entries:
        if entry["status"] in BLOCKED_STATUSES or not entry["sha256_present"]:
            reason = "missing_sha256" if not entry["sha256_present"] else entry["status"]
            blocking.append({"memory_ref": entry["memory_ref"], "reason": reason})
    blocking.extend({"memory_ref": ref, "reason": "rejected_asset"} for ref in rejected_refs)
    return {
        "overall_status": "blocked" if blocking else "ready",
        "blocking_refs": blocking,
        "promotion_modes": ["promote", "merge", "reject", "expire"],
        "requires_human_review": True,
        "writes_long_term_memory": False,
    }


def _next_context_bundle_draft(entries: list[dict[str, Any]], rejected_refs: list[str]) -> dict[str, Any]:
    eligible = [entry["memory_ref"] for entry in entries if entry["eligible_for_context"]]
    blocked = [entry["memory_ref"] for entry in entries if not entry["eligible_for_context"]]
    blocked.extend(rejected_refs)
    return {
        "status": "promotion_decision_required",
        "eligible_memory_refs": eligible,
        "blocked_memory_refs": blocked,
        "projection_mode": "file_protocol_only",
        "writes_long_term_memory": False,
    }


def _canvas_nodes(entries: list[dict[str, Any]], rejected_refs: list[str]) -> list[dict[str, str]]:
    blocked = any(not entry["eligible_for_context"] for entry in entries) or bool(rejected_refs)
    return [
        {"id": "project", "label": "Project", "status": "planned"},
        {"id": "shots", "label": "Shots", "status": "review ready"},
        {"id": "assets", "label": "Assets", "status": "blocked" if blocked else "review ready"},
        {"id": "memory-loaded", "label": "Memory Loaded", "status": "promotion decision required"},
        {"id": "baseline-plan", "label": "Baseline Plan", "status": "planned"},
        {"id": "memory-backed-plan", "label": "Memory-backed Plan", "status": "planned"},
        {"id": "review", "label": "Review", "status": "planned"},
        {"id": "feedback", "label": "Feedback", "status": "planned"},
        {"id": "next-pass", "label": "Next Pass", "status": "blocked" if blocked else "planned"},
    ]


def _api_workbench_skeleton() -> dict[str, str]:
    return {
        "asset_resolver": "planned",
        "reference_pack_builder": "planned",
        "prompt_compiler": "planned",
        "request_manifest": "planned",
        "response_ledger": "planned",
        "qa_gate": "planned",
        "promotion_gate": "planned",
        "live_provider_calls": "blocked_by_default",
    }


def _claim_boundaries() -> dict[str, str]:
    return {
        "structure_verification": "package_contract_only",
        "runtime_verification": "not_run",
        "human_acceptance": "not_acceptance",
        "business_validation": "not_validated",
        "provider_smoke": "not_run",
        "durable_memory_runtime": "not_implemented",
    }


def _relative_files(root: Path, directory: Path, *, limit: int) -> list[str]:
    if not directory.exists():
        return []
    refs: list[str] = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        ref = path.relative_to(root).as_posix()
        if not ref.lower().endswith((".mp4", ".mov")):
            refs.append(ref)
        if len(refs) >= limit:
            break
    return refs


def _normalize_status(value: Any) -> str:
    status = str(value or "candidate").strip().lower()
    return status or "candidate"


def _safe_relative_text(value: Any) -> str:
    text = str(value or "")
    return "" if text.startswith(("D:\\", "C:\\", "file://")) else text.replace("\\", "/")


def _reject_unsafe_output(package: dict[str, Any]) -> None:
    serialized = json.dumps(package, ensure_ascii=False)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_OUTPUT_FRAGMENTS):
        raise ValueError("Loulan package contains unsafe local path, media ref, provider secret, or signed URL")
