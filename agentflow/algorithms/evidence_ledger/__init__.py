from __future__ import annotations

from typing import Any


ALGORITHM_ID = "afs.evidence_ledger.v0.1"
INPUT_CONTRACT = "storyboard safe manifest, candidate asset graph, auto-binding graph, quality report, production graph, asset-card candidates"
OUTPUT_CONTRACT = "safe evidence ledger with artifact roles, evidence states, provider boundary, and non-claims"
FAILURE_MODES = ("missing_safe_manifest", "missing_artifact_role", "unsafe_evidence_field", "claim_state_collapse")
EVIDENCE_BOUNDARY = "structure and runtime evidence only; no provider smoke, human acceptance, or business validation claim"

LEDGER_STAGE = "storyboard_to_asset_candidate"
NON_CLAIMS = [
    "not generated media",
    "not fixed asset memory",
    "not provider smoke when provider_calls_started is false",
    "not human acceptance",
    "not business validation",
    "not durable memory promotion",
]


def build_storyboard_evidence_ledger(
    *,
    project_id: str,
    script_node_id: str | None,
    provider_gate: dict[str, Any],
    provider_calls_started: bool,
    safe_manifest: dict[str, Any],
    asset_graph: dict[str, Any],
    content_quality_report: dict[str, Any],
    production_graph: dict[str, Any],
    asset_card_candidates: dict[str, Any],
    asset_auto_binding_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding_graph = asset_auto_binding_graph if isinstance(asset_auto_binding_graph, dict) else {}
    evidence_items = [
        _item(
            "storyboard_breakdown_request_plan",
            "agentflow_storyboard_breakdown_request_plan",
            "planned",
            "not_applicable",
            {"provider_gate_status": str(provider_gate.get("status") or "")},
        ),
        _item(
            "storyboard_breakdown_safe_artifact",
            "agentflow_storyboard_breakdown_safe_artifact",
            "structure_verified",
            "needs_human_review_before_asset_identification",
            {"shot_count": _int(safe_manifest.get("shot_count"))},
        ),
        _item(
            "storyboard_breakdown_safe_manifest",
            "agentflow_storyboard_breakdown_safe_manifest",
            "runtime_verified",
            "not_applicable",
            {
                "raw_provider_response_stored": False,
                "generated_media_bytes_stored": False,
            },
        ),
        _item(
            "asset_graph",
            "agentflow_storyboard_asset_graph",
            "structure_verified_needs_human_review",
            "candidate_review_required",
            {
                "candidate_asset_count": _int(asset_graph.get("asset_count")),
                "unsupported_addition_count": len(_list(asset_graph.get("unsupported_additions"))),
            },
        ),
        _item(
            "asset_auto_binding_graph",
            "agentflow_asset_auto_binding_graph",
            "structure_verified_fail_closed",
            "binding_review_available",
            {
                "established_binding_count": _int(_summary(binding_graph).get("established_binding_count")),
                "blocked_candidate_count": _int(_summary(binding_graph).get("blocked_candidate_count")),
                "writes_fixed_asset": False,
            },
        ),
        _item(
            "content_quality_report",
            "agentflow_content_quality_report",
            _quality_status(content_quality_report),
            "needs_human_review",
            {
                "failed_check_count": _int(_summary(content_quality_report).get("failed_check_count")),
                "check_count": _int(_summary(content_quality_report).get("check_count")),
            },
        ),
        _item(
            "production_graph_snapshot",
            "agentflow_production_graph_snapshot",
            "structure_verified_needs_human_review",
            "candidate_review_required",
            {
                "node_count": _int(_summary(production_graph).get("node_count")),
                "relationship_count": _int(_summary(production_graph).get("relationship_count")),
            },
        ),
        _item(
            "asset_card_candidates",
            "agentflow_asset_card_candidate_set",
            "candidate_needs_human_confirmation",
            "needs_human_confirmation",
            {
                "candidate_count": _int(_summary(asset_card_candidates).get("candidate_count")),
                "writes_fixed_asset": False,
            },
        ),
    ]
    asset_types = sorted(
        {
            str(asset.get("asset_type") or "")
            for asset in _list(asset_graph.get("assets"))
            if isinstance(asset, dict) and str(asset.get("asset_type") or "")
        }
    )
    return {
        "artifact_type": "agentflow_evidence_ledger",
        "schema_version": "0.1.0",
        "algorithm_id": ALGORITHM_ID,
        "ledger_stage": LEDGER_STAGE,
        "summary": {
            "project_id": project_id,
            "script_node_id": script_node_id or "",
            "evidence_state": _ledger_state(content_quality_report),
            "entry_count": len(evidence_items),
            "provider_calls_started": provider_calls_started,
            "provider_smoked": False,
            "human_review_needed": True,
            "human_accepted": False,
            "business_validated": False,
        },
        "evidence_items": evidence_items,
        "asset_evidence": {
            "candidate_asset_count": _int(asset_graph.get("asset_count")),
            "asset_types": asset_types,
            "asset_card_candidate_count": _int(_summary(asset_card_candidates).get("candidate_count")),
            "fixed_asset_writes": False,
            "requires_human_confirmation": True,
        },
        "provider_evidence": {
            "provider_gate": _safe_provider_gate(provider_gate),
            "provider_calls_started": provider_calls_started,
            "provider_smoked": False,
            "raw_provider_response_stored": False,
            "generated_media_bytes_stored": False,
            "external_private_link_stored": False,
        },
        "trace_policy": {
            "run_trace_written_after_safe_artifacts": True,
            "run_trace_references_evidence_ledger_role": True,
        },
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }


def _item(
    artifact_role: str,
    artifact_type: str,
    evidence_state: str,
    review_state: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_role": artifact_role,
        "artifact_type": artifact_type,
        "evidence_state": evidence_state,
        "review_state": review_state,
        "safe_payload": True,
        "summary": summary,
    }


def _ledger_state(content_quality_report: dict[str, Any]) -> str:
    status = _quality_status(content_quality_report)
    if status.startswith("failed"):
        return "structure_failed_needs_repair"
    return "structure_verified_needs_human_review"


def _quality_status(content_quality_report: dict[str, Any]) -> str:
    return str(_summary(content_quality_report).get("status") or "structure_verified_needs_human_review")


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary") if isinstance(payload, dict) else {}
    return value if isinstance(value, dict) else {}


def _safe_provider_gate(provider_gate: dict[str, Any]) -> dict[str, str]:
    return {
        "capability": str(provider_gate.get("capability") or ""),
        "env": str(provider_gate.get("env") or ""),
        "status": str(provider_gate.get("status") or ""),
    }


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "LEDGER_STAGE",
    "NON_CLAIMS",
    "OUTPUT_CONTRACT",
    "build_storyboard_evidence_ledger",
)
