from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tools.afs_internal_beta_acceptance_client import HttpAcceptanceClient
from tools.afs_internal_beta_acceptance_errors import AcceptanceConfigurationError
from tools.afs_internal_beta_preflight_public_edge import collect_public_edge_status, safe_public_edge_status
from tools.afs_internal_beta_preflight_three_end import collect_three_end_status, safe_three_end_status
from tools.afs_readiness_claims import safe_readiness_projection

HTTP_PREFLIGHT_NON_CLAIMS = ["HTTP preflight only", "not provider smoke", "not generated-media QA", "not human creative acceptance", "not product or business readiness", "not public or legal readiness", "not CompanyOS promotion"]


def run_http_preflight(
    *,
    base_url: str,
    report_path: Path | None = None,
    include_three_end_status: bool = False,
    three_end_repo_root: Path | None = None,
    three_end_server: str = "",
    include_public_edge_status: bool = False,
    public_edge_url: str = "",
    public_edge_server: str = "",
    public_edge_check_runtime_health: bool = False,
    http_client_factory: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    if not base_url.strip():
        raise AcceptanceConfigurationError("HTTP preflight requires a Runtime base URL.")
    factory = http_client_factory or HttpAcceptanceClient
    client = factory(base_url.strip())
    try:
        three_end_status = None
        if include_three_end_status:
            three_end_status = collect_three_end_status(
                repo_root=three_end_repo_root or Path("."),
                server=three_end_server,
            )
        public_edge_status = None
        if include_public_edge_status:
            public_edge_status = collect_public_edge_status(
                base_url=base_url,
                public_url=public_edge_url,
                server=public_edge_server,
                check_runtime_health=public_edge_check_runtime_health,
            )
        report = _build_http_preflight_report(client, three_end_status=three_end_status, public_edge_status=public_edge_status)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _build_http_preflight_report(client, *, three_end_status: dict[str, Any] | None = None, public_edge_status: dict[str, Any] | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    health_status = 0
    health: dict[str, Any] = {}
    auth_status = 0
    auth_payload: dict[str, Any] = {}
    try:
        health_response = client.get("/health")
        health_status = int(getattr(health_response, "status_code", 0))
        health = _safe_json_object(health_response)
    except Exception as exc:  # pragma: no cover - exercised by deployed smoke more than unit tests.
        _add_preflight_check(checks, "runtime_health", "failed", {"http_status": 0, "error_class": exc.__class__.__name__})
    else:
        _add_preflight_check(
            checks,
            "runtime_health",
            "passed" if health_status == 200 and health.get("status") == "ready" else "failed",
            {
                "http_status": health_status,
                "runtime_status": health.get("status"),
                "runtime_root_persisted": bool(health.get("runtime_root_persisted")),
            },
        )
    try:
        auth_response = client.get("/auth/status")
        auth_status = int(getattr(auth_response, "status_code", 0))
        auth_payload = _safe_json_object(auth_response)
    except Exception as exc:  # pragma: no cover - exercised by deployed smoke more than unit tests.
        _add_preflight_check(checks, "auth_surface", "failed", {"http_status": 0, "error_class": exc.__class__.__name__})
    else:
        _add_preflight_check(
            checks,
            "auth_surface",
            "passed" if auth_status == 200 and auth_payload.get("auth_required") is True else "failed",
            {
                "http_status": auth_status,
                "auth_required": auth_payload.get("auth_required"),
                "invite_registration_available": auth_payload.get("invite_registration_available"),
            },
        )
    studio_static = health.get("studio_static") if isinstance(health, dict) else {}
    _add_preflight_check(
        checks,
        "studio_static",
        "passed" if isinstance(studio_static, dict) and studio_static.get("status") == "ready" else "failed",
        _safe_studio_static(studio_static),
    )
    provider_gates = _safe_provider_gates(health.get("provider_gates") if isinstance(health, dict) else {})
    _add_preflight_check(
        checks,
        "provider_gate_projection",
        "passed" if "video" in provider_gates else "failed",
        {"provider_gates": provider_gates, "provider_calls_started": False},
    )
    safe_three_end = safe_three_end_status(three_end_status) if three_end_status is not None else None
    if safe_three_end is not None:
        summary = safe_three_end.get("summary", {})
        _add_preflight_check(
            checks,
            "three_end_status",
            "passed" if safe_three_end.get("status") == "aligned" else "failed",
            {
                "status": str(safe_three_end.get("status") or ""),
                "checked_end_count": int(summary.get("checked_end_count") or 0),
                "aligned_end_count": int(summary.get("aligned_end_count") or 0),
                "dirty_end_count": int(summary.get("dirty_end_count") or 0),
                "runtime_status": str(summary.get("runtime_status") or ""),
            },
        )
    safe_public_edge = safe_public_edge_status(public_edge_status) if public_edge_status is not None else None
    if safe_public_edge is not None:
        summary = safe_public_edge.get("summary", {})
        _add_preflight_check(
            checks,
            "public_edge_auth",
            "passed" if safe_public_edge.get("status") == "ready_for_public_auth" else "failed",
            {"status": str(safe_public_edge.get("status") or ""), "public_edge_http_status": int(summary.get("public_edge_http_status") or 0), "edge_basic_auth": bool(summary.get("edge_basic_auth")), "runtime_status": str(summary.get("runtime_status") or ""), "auth_required": bool(summary.get("auth_required")), "acceptance_ready": bool(summary.get("acceptance_ready"))},
        )
    failed_count = sum(1 for item in checks if item["status"] == "failed")
    passed_count = sum(1 for item in checks if item["status"] == "passed")
    report = {
        "artifact_type": "afs_internal_beta_acceptance_preflight_report",
        "schema_version": "0.1.0",
        "mode": "deployed_http_preflight",
        "status": "ready_for_http_acceptance" if failed_count == 0 else "needs_attention",
        "provider_calls_started": False,
        "requires_invite_codes": bool(auth_payload.get("invite_registration_available") or health.get("auth_required")),
        "human_acceptance_claim": "not_claimed",
        "product_readiness_claim": "not_claimed",
        "business_validation_claim": "not_claimed",
        "readiness_claims": {
            "http_preflight_ready": failed_count == 0,
            "service_ready": health.get("status") == "ready",
            "auth_required": bool(health.get("auth_required")),
            "public_edge_auth_ready": bool(safe_public_edge.get("readiness_boundary", {}).get("public_edge_auth_ready")) if safe_public_edge is not None else False,
            "runtime_three_end_alignment_evidence": bool(safe_three_end and safe_three_end.get("status") == "aligned"),
            "runtime_loaded_code_freshness_claim": "not_claimed",
            "acceptance_ready": False,
            "human_creative_acceptance": False,
            "product_readiness": False,
        },
        "non_claims": list(HTTP_PREFLIGHT_NON_CLAIMS),
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "summary": {"passed_check_count": passed_count, "failed_check_count": failed_count},
        "safe_health": _safe_health(health),
        "checks": checks,
    }
    if safe_three_end is not None:
        report["three_end_status"] = safe_three_end
    if safe_public_edge is not None:
        report["public_edge_status"] = safe_public_edge
    return report


def _add_preflight_check(checks: list[dict[str, Any]], check_id: str, status: str, evidence: dict[str, Any]) -> None:
    checks.append({"check_id": check_id, "status": status, "provider_calls_started": False, "evidence": evidence})


def _safe_json_object(response) -> dict[str, Any]:
    try:
        value = response.json()
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _safe_health(health: dict[str, Any]) -> dict[str, Any]:
    return {
        "service": str(health.get("service") or ""),
        "status": str(health.get("status") or ""),
        "service_version": str(health.get("service_version") or ""),
        "schema_version": str(health.get("schema_version") or ""),
        "runtime_root_persisted": bool(health.get("runtime_root_persisted")),
        "auth_required": bool(health.get("auth_required")),
        "studio_static": _safe_studio_static(health.get("studio_static")),
        "provider_gates": _safe_provider_gates(health.get("provider_gates")),
        "readiness": safe_readiness_projection(health.get("readiness")),
    }


def _safe_studio_static(value: Any) -> dict[str, Any]:
    value = value if isinstance(value, dict) else {}
    safe: dict[str, Any] = {
        key: bool(value.get(key)) for key in ("mounted", "root_exists", "index_exists", "assets_dir_exists", "entry_js_exists")
    }
    safe.update(
        status=str(value.get("status") or "missing"), route=str(value.get("route") or ""), role=str(value.get("role") or "")
    )
    for key in ("legacy", "studio_next"):
        if isinstance(value.get(key), dict):
            safe[key] = _safe_studio_static(value.get(key))
    return safe


def _safe_provider_gates(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    allowed = {"llm", "image", "video", "audio", "vision", "asr", "external_download"}
    return {str(key): bool(val) for key, val in value.items() if str(key) in allowed}
