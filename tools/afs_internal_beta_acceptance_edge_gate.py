from __future__ import annotations

from typing import Any

from tools.afs_internal_beta_preflight_public_edge import collect_public_edge_status, safe_public_edge_status


def collect_public_edge_acceptance_gate(
    *,
    enabled: bool,
    base_url: str,
    public_url: str = "",
    server: str = "",
    check_runtime_health: bool = False,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not enabled:
        return None, None
    public_edge = safe_public_edge_status(collect_public_edge_status(
        base_url=base_url,
        public_url=public_url,
        server=server,
        check_runtime_health=check_runtime_health,
    ))
    if public_edge["status"] == "ready_for_public_auth":
        return public_edge, None
    return public_edge, public_edge_gate_report(public_edge)


def public_edge_gate_report(public_edge: dict[str, Any]) -> dict[str, Any]:
    summary = public_edge.get("summary", {})
    return {
        "artifact_type": "afs_internal_beta_acceptance_edge_gate_report",
        "schema_version": "0.1.0",
        "status": "public_edge_not_ready",
        "summary": {
            "public_edge_status": str(public_edge.get("status") or ""),
            "public_edge_http_status": int(summary.get("public_edge_http_status") or 0),
            "edge_basic_auth": bool(summary.get("edge_basic_auth")),
            "runtime_status": str(summary.get("runtime_status") or ""),
        },
        "public_edge_status": public_edge,
        "provider_calls_started": False,
        "human_acceptance_claim": "not_claimed",
        "business_validation_claim": "not_claimed",
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "non_claims": [
            "public edge gate only",
            "not invite-login verification",
            "not runtime acceptance",
            "not live provider smoke",
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
        "next_actions": [
            "Remove or intentionally keep the external Nginx Basic Auth layer.",
            "Rerun deployed HTTP acceptance after public edge status is ready_for_public_auth.",
        ],
    }
