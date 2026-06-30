from __future__ import annotations

from typing import Any


ALGORITHM_ID = "afs.generation_bridge.v0.1"
INPUT_CONTRACT = "keyframe request, model call context, model request plan, provider gate, safe manifest"
OUTPUT_CONTRACT = "safe local deterministic generation bridge without provider raw response or media bytes"
FAILURE_MODES = ("missing_model_context", "unsafe_bridge_payload", "provider_claim_without_gate", "media_bytes_leak")
EVIDENCE_BOUNDARY = "local deterministic bridge only; not provider smoke, generated media, human acceptance, or business validation"

BRIDGE_STAGE = "keyframe_local_deterministic_bridge"
NON_CLAIMS = [
    "not generated media",
    "not provider smoke when provider_calls_started is false",
    "not human acceptance",
    "not business validation",
    "not durable memory promotion",
]


def build_keyframe_generation_bridge(
    *,
    project_id: str,
    node_id: str | None,
    status: str,
    provider_gate: dict[str, Any],
    provider_calls_started: bool,
    requested_candidate_count: int,
    reference_image_count: int,
    seed: int | None,
    blocks: list[dict[str, Any]],
    context_bundle: dict[str, Any] | None,
    model_call_context: dict[str, Any],
    model_request_plan: dict[str, Any],
) -> dict[str, Any]:
    generation_state = "blocked_before_provider" if not provider_calls_started else "provider_path_started"
    planned_outputs = [
        {
            "candidate_id": f"planned_candidate_{index:03d}",
            "artifact_state": "planned",
            "media_bytes_available": False,
            "preview_available": False,
            "requires_provider_gate": True,
        }
        for index in range(1, _candidate_count(requested_candidate_count) + 1)
    ]
    return {
        "artifact_type": "agentflow_generation_bridge",
        "schema_version": "0.1.0",
        "algorithm_id": ALGORITHM_ID,
        "bridge_stage": BRIDGE_STAGE,
        "summary": {
            "project_id": project_id,
            "node_id": node_id or "",
            "requested_capability": "image_keyframe",
            "generation_state": generation_state,
            "provider_calls_started": provider_calls_started,
            "provider_smoked": False,
            "human_accepted": False,
            "business_validated": False,
            "bridge_media_generated": False,
            "planned_candidate_count": len(planned_outputs),
        },
        "request_evidence": {
            "model_call_context_id": str(model_call_context.get("context_id") or ""),
            "model_request_plan_ref": "model_request_plan.json",
            "keyframe_request_plan_ref": "keyframe_request_plan.json",
            "safe_manifest_ref": "keyframe_generation_safe_manifest.json",
            "seed": seed,
        },
        "context_evidence": _context_evidence(context_bundle, reference_image_count),
        "provider_evidence": {
            "provider_gate": _safe_provider_gate(provider_gate),
            "provider_calls_started": provider_calls_started,
            "provider_smoked": False,
            "raw_provider_response_stored": False,
            "generated_media_bytes_stored": False,
            "external_private_link_stored": False,
            "blocks": _safe_blocks(blocks),
        },
        "planned_outputs": planned_outputs,
        "model_request_evidence": {
            "plan_artifact_type": str(model_request_plan.get("artifact_type") or ""),
            "requested_modality": str(model_request_plan.get("requested_modality") or ""),
            "provider_service_id": str(model_request_plan.get("provider_service_id") or ""),
        },
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }


def _context_evidence(context_bundle: dict[str, Any] | None, reference_image_count: int) -> dict[str, Any]:
    if not isinstance(context_bundle, dict):
        return {
            "context_bundle_present": False,
            "included_asset_count": 0,
            "reference_image_count": reference_image_count,
            "subject_reference_asset_id": None,
        }
    return {
        "context_bundle_present": True,
        "mode": str(context_bundle.get("mode") or ""),
        "included_asset_count": len(_list(context_bundle.get("included_assets"))),
        "reference_image_count": reference_image_count,
        "subject_reference_asset_id": context_bundle.get("subject_reference_asset_id"),
        "draft_assets_rejected": bool((context_bundle.get("trace_summary") or {}).get("draft_assets_rejected"))
        if isinstance(context_bundle.get("trace_summary"), dict)
        else False,
    }


def _safe_provider_gate(provider_gate: dict[str, Any]) -> dict[str, str]:
    return {
        "capability": str(provider_gate.get("capability") or ""),
        "env": str(provider_gate.get("env") or ""),
        "status": str(provider_gate.get("status") or ""),
    }


def _safe_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "block_id": str(block.get("block_id") or ""),
            "reason": str(block.get("reason") or "")[:240],
            "required_gate": str(block.get("required_gate") or ""),
        }
        for block in blocks
        if isinstance(block, dict)
    ]


def _candidate_count(value: int) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(count, 4))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "ALGORITHM_ID",
    "BRIDGE_STAGE",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "NON_CLAIMS",
    "OUTPUT_CONTRACT",
    "build_keyframe_generation_bridge",
)
