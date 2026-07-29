from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.afs_readiness_claims import safe_readiness_projection
from tools.afs_three_end_status import run_three_end_status


def collect_three_end_status(*, repo_root: Path, server: str = "") -> dict[str, Any]:
    try:
        return run_three_end_status(repo_root=repo_root, server=server)
    except RuntimeError:
        return {
            "artifact_type": "afs_three_end_status_report",
            "schema_version": "0.1.0",
            "status": "needs_attention",
            "provider_calls_started": False,
            "writes_company_kb": False,
            "writes_long_term_memory": False,
            "summary": {
                "checked_end_count": 0,
                "aligned_end_count": 0,
                "dirty_end_count": 0,
                "runtime_status": "",
            },
            "ends": {},
            "runtime_health": {},
        }


def safe_three_end_status(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    health = value.get("runtime_health") if isinstance(value.get("runtime_health"), dict) else {}
    return {
        "artifact_type": "afs_three_end_status_report",
        "schema_version": str(value.get("schema_version") or "0.1.0"),
        "status": str(value.get("status") or "needs_attention"),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "writes_company_kb": bool(value.get("writes_company_kb")),
        "writes_long_term_memory": bool(value.get("writes_long_term_memory")),
        "summary": _safe_three_end_summary(value.get("summary")),
        "ends": _safe_three_end_snapshots(value.get("ends")),
        "runtime_health": _safe_runtime_health(health),
        "readiness_claims": _safe_readiness_claims(value.get("readiness_claims")),
    }


def _safe_three_end_summary(value: Any) -> dict[str, int | str]:
    if not isinstance(value, dict):
        value = {}
    return {
        "checked_end_count": int(value.get("checked_end_count") or 0),
        "aligned_end_count": int(value.get("aligned_end_count") or 0),
        "dirty_end_count": int(value.get("dirty_end_count") or 0),
        "runtime_status": str(value.get("runtime_status") or ""),
    }


def _safe_three_end_snapshots(value: Any) -> dict[str, dict[str, bool | str]]:
    if not isinstance(value, dict):
        return {}
    safe: dict[str, dict[str, bool | str]] = {}
    allowed_labels = {"local", "server_home", "server_opt"}
    for key, snapshot in value.items():
        label = str(key)
        if label not in allowed_labels or not isinstance(snapshot, dict):
            continue
        safe[label] = {
            "label": str(snapshot.get("label") or label),
            "branch_status": str(snapshot.get("branch_status") or ""),
            "head": str(snapshot.get("head") or ""),
            "origin_head": str(snapshot.get("origin_head") or ""),
            "dirty": bool(snapshot.get("dirty")),
            "aligned_with_origin": bool(snapshot.get("aligned_with_origin")),
        }
    return safe


def _safe_runtime_health(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "service": str(payload.get("service") or ""),
        "status": str(payload.get("status") or ""),
        "service_version": str(payload.get("service_version") or ""),
        "schema_version": str(payload.get("schema_version") or ""),
        "runtime_root_persisted": bool(payload.get("runtime_root_persisted")),
        "auth_required": bool(payload.get("auth_required")),
        "studio_static": _safe_studio_static(payload.get("studio_static")),
        "provider_gates": _safe_provider_gates(payload.get("provider_gates")),
        "readiness": safe_readiness_projection(payload.get("readiness")),
    }


def _safe_studio_static(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    safe: dict[str, Any] = {
        "mounted": bool(value.get("mounted")),
        "root_exists": bool(value.get("root_exists")),
        "index_exists": bool(value.get("index_exists")),
        "assets_dir_exists": bool(value.get("assets_dir_exists")),
        "entry_js_exists": bool(value.get("entry_js_exists")),
        "status": str(value.get("status") or "missing"),
        "route": str(value.get("route") or ""),
        "role": str(value.get("role") or ""),
    }
    if isinstance(value.get("legacy"), dict):
        safe["legacy"] = _safe_studio_static(value.get("legacy"))
    if isinstance(value.get("studio_next"), dict):
        safe["studio_next"] = _safe_studio_static(value.get("studio_next"))
    return safe


def _safe_provider_gates(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    allowed = {"llm", "image", "video", "vision", "asr", "external_download"}
    return {str(key): bool(val) for key, val in value.items() if str(key) in allowed}
def _safe_readiness_claims(value: Any) -> dict[str, bool | str]:
    if not isinstance(value, dict):
        value = {}
    return {
        "repo_ends_aligned": bool(value.get("repo_ends_aligned")),
        "runtime_service_ready": bool(value.get("runtime_service_ready")),
        "runtime_three_end_alignment_evidence": bool(value.get("runtime_three_end_alignment_evidence")),
        "runtime_loaded_code_freshness_claim": str(value.get("runtime_loaded_code_freshness_claim") or "not_claimed"),
        "acceptance_ready": bool(value.get("acceptance_ready")),
        "human_creative_acceptance": bool(value.get("human_creative_acceptance")),
        "product_readiness": bool(value.get("product_readiness")),
    }
