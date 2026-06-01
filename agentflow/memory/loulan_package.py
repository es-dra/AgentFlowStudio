from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.loulan_assets import (
    asset_inventory,
    has_asset_registry,
    legacy_asset_summary,
    legacy_character_entries,
    next_context_bundle,
    promotion_gates,
    registry_asset_entries,
    registry_asset_summary,
    registry_file,
)
from agentflow.memory.loulan_feedback_gates import feedback_loop_gates


SCHEMA_VERSION = "0.1.0"
LOULAN_PACKAGE_TYPE = "agentflow_loulan_memory_package"
UNSAFE_OUTPUT_FRAGMENTS = ("D:\\", "C:\\", "file://", "Bearer ", "signed_url", "token=", "api_key", "secret_key", ".mp4", ".mov")


def build_loulan_memory_package(project_root: str | Path, *, created_at: str) -> dict[str, Any]:
    """Build a read-only Loulan pilot package without calling providers or copying media."""
    root = Path(project_root)
    manifest = _read_json(root / "project_manifest.json")
    shots = _read_json(root / "manifests" / "shot_list.json").get("shots") or []
    rejected_refs = _relative_files(root, root / "human" / "rejected", limit=12)
    registry_mode = has_asset_registry(root)
    if registry_mode:
        registry_payload = _read_json(registry_file(root))
        asset_entries = registry_asset_entries(registry_payload)
        asset_summary = registry_asset_summary(asset_entries, rejected_refs)
        inventory = asset_inventory(asset_entries)
    else:
        character_assets = _read_json(root / "manifests" / "character_assets.json").get("assets") or []
        asset_entries = legacy_character_entries(character_assets)
        asset_summary = legacy_asset_summary(asset_entries, rejected_refs)
        inventory = _legacy_asset_inventory(asset_entries, asset_summary)
    project_summary = _project_summary(root, manifest)
    package = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": LOULAN_PACKAGE_TYPE,
        "package_id": f"{manifest.get('project_id', 'loulan')}_memory_production_package_v0",
        "created_at": created_at,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "reads_company_knowledge": False,
        "project_summary": project_summary,
        "project": project_summary,
        "shot_summary": _shot_summary(shots),
        "asset_inventory": inventory,
        "asset_summary": asset_summary,
        "memory_collections": _memory_collections(root),
        "project_audits": _project_audits(manifest),
        "provider_route_safety": _provider_route_safety(root, manifest),
        "feedback_loop_gates": feedback_loop_gates(root),
        "promotion_gates": promotion_gates(asset_entries, rejected_refs, registry_mode=registry_mode),
        "next_context_bundle_draft": next_context_bundle(asset_entries, rejected_refs, registry_mode=registry_mode),
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
            f"- Manifest reference audit: `{package['project_audits']['manifest_reference']['status']}`",
            f"- Text encoding audit: `{package['project_audits']['text_encoding']['status']}`",
            f"- Promotion gate: `{gates['overall_status']}`",
            f"- B01 feedback loop gate: `{package['feedback_loop_gates']['b01']['status']}`",
            f"- B01 decision crosswalk: `{package['feedback_loop_gates']['b01_decision_crosswalk']['status']}`",
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


def _project_audits(manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        "manifest_reference": _project_audit(manifest, "manifest_reference_audit"),
        "text_encoding": _project_audit(manifest, "text_encoding_audit"),
    }


def _project_audit(manifest: dict[str, Any], field: str) -> dict[str, str]:
    return {
        "status": str(manifest.get(f"{field}_status") or "not_provided"),
        "artifact_ref": _safe_project_ref(manifest.get(field)),
        "report_ref": _safe_project_ref(manifest.get(f"{field}_report")),
    }


def _safe_project_ref(value: Any) -> str:
    text = str(value or "")
    if text.startswith(("D:\\", "C:\\", "file://", "http://", "https://")):
        return ""
    return text.replace("\\", "/")


def _legacy_asset_inventory(entries: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_registry_ref": "manifests/character_assets.json",
        "registry_type": "loulan_character_asset_manifest",
        "total_assets": summary["total_assets"],
        "type_counts": {"character": summary["total_assets"]},
        "status_counts": summary["status_counts"],
        "missing_sha256_count": summary["missing_sha256_count"],
        "missing_ref_count": 0,
        "eligible_assets": [entry for entry in entries if entry["eligible_for_context"]][:24],
        "blocked_assets": [
            {
                "memory_ref": entry["memory_ref"],
                "asset_type": entry.get("asset_type", "character"),
                "status": entry["status"],
                "reason": "missing_sha256" if not entry["sha256_present"] else entry["status"],
            }
            for entry in entries
            if not entry["eligible_for_context"]
        ][:48],
        "assets": entries[:48],
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


def _reject_unsafe_output(package: dict[str, Any]) -> None:
    serialized = json.dumps(package, ensure_ascii=False)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_OUTPUT_FRAGMENTS):
        raise ValueError("Loulan package contains unsafe local path, media ref, provider secret, or signed URL")
