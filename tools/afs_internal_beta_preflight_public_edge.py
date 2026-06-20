from __future__ import annotations

from typing import Any

from tools.afs_public_edge_preflight import DEFAULT_PUBLIC_URL, run_public_edge_preflight


def default_public_studio_url(base_url: str) -> str:
    value = str(base_url or "").strip().rstrip("/")
    if not value:
        return DEFAULT_PUBLIC_URL
    if value.endswith("/studio"):
        return value + "/"
    return value + "/studio/"


def collect_public_edge_status(
    *,
    base_url: str,
    public_url: str = "",
    server: str = "",
    check_runtime_health: bool = False,
) -> dict[str, Any]:
    try:
        return run_public_edge_preflight(
            public_url=public_url.strip() or default_public_studio_url(base_url),
            server=server,
            check_runtime_health=check_runtime_health,
        )
    except Exception as exc:  # pragma: no cover - deployed network failures are environment-dependent.
        return {
            "artifact_type": "afs_public_edge_preflight_report",
            "schema_version": "0.1.0",
            "status": "needs_attention",
            "provider_calls_started": False,
            "writes_company_kb": False,
            "writes_long_term_memory": False,
            "summary": {
                "public_edge_http_status": 0,
                "edge_basic_auth": False,
                "runtime_status": "",
                "error_class": exc.__class__.__name__,
            },
            "checks": [],
        }


def safe_public_edge_status(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    return {
        "artifact_type": "afs_public_edge_preflight_report",
        "schema_version": str(value.get("schema_version") or "0.1.0"),
        "status": str(value.get("status") or "needs_attention"),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "writes_company_kb": bool(value.get("writes_company_kb")),
        "writes_long_term_memory": bool(value.get("writes_long_term_memory")),
        "summary": _safe_public_edge_summary(value.get("summary")),
    }


def _safe_public_edge_summary(value: Any) -> dict[str, bool | int | str]:
    if not isinstance(value, dict):
        value = {}
    return {
        "public_edge_http_status": int(value.get("public_edge_http_status") or 0),
        "edge_basic_auth": bool(value.get("edge_basic_auth")),
        "runtime_status": str(value.get("runtime_status") or ""),
    }
