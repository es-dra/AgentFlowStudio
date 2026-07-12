from __future__ import annotations

from typing import Any

from agentflow.algorithms.feedback_overlay_prompt_policy import feedback_overlay_prompt_policy
from agentflow.algorithms.model_call_context import sanitize_context_payload, sanitize_context_text


ALGORITHM_ID = "afs.request_projection.v0.1"
INPUT_CONTRACT = "model-call context, canonical brief, context bundle, provider capability constraints"
OUTPUT_CONTRACT = "provider-neutral request plan and provider-specific safe request body"
FAILURE_MODES = ("unsupported_generation_target", "missing_context_id", "unsafe_provider_request")
EVIDENCE_BOUNDARY = "request plan only; provider gate and adapter execution happen outside this algorithm"


def build_request_plan(
    *,
    model_call_context: dict[str, Any],
    canonical_brief: dict[str, Any] | None = None,
    provider_service_id: str | None = None,
) -> dict[str, Any]:
    context_id = str(model_call_context.get("context_id") or "").strip()
    if not context_id:
        raise ValueError("model_call_context requires context_id")
    generation_target = str(model_call_context.get("generation_target") or "").strip()
    refs = list((model_call_context.get("reference_context") or {}).get("reference_image_refs") or [])
    input_source = _input_source(model_call_context)
    duration_contract = _duration_contract(model_call_context)
    request_mode = _request_mode(generation_target, refs)
    prompt = _prompt_text(model_call_context, canonical_brief)
    overlay_prompt_policy = _overlay_prompt_policy(model_call_context)
    payload = {
        "artifact_type": "agentflow_model_request_plan",
        "schema_version": "afs_model_request_plan.v0.1",
        "algorithm_id": ALGORITHM_ID,
        "context_id": context_id,
        "operation_intent": model_call_context.get("operation_intent"),
        "generation_target": generation_target,
        "request_mode": request_mode,
        "input_source": input_source,
        "duration_contract": duration_contract,
        "provider_neutral": True,
        "provider_service_id": provider_service_id or "not_selected",
        "provider_request": {
            "prompt": prompt,
            "reference_image_refs": refs,
            "input_source": input_source,
            "duration_seconds": duration_contract.get("duration_seconds"),
            "context_id": context_id,
            "mode": request_mode,
        },
        "safety_boundary": {
            "no_provider_raw": True,
            "no_secret": True,
            "no_credentialed_url": True,
            "no_local_path": True,
            "no_media_bytes": True,
        },
        "trace_summary": {
            "model_call_context_algorithm_id": model_call_context.get("algorithm_id"),
            "reference_image_count": len(refs),
            "input_source_mode": input_source.get("source_mode") or "",
            "duration_seconds": duration_contract.get("duration_seconds"),
            "feedback_context_overlay_prompt_policy": overlay_prompt_policy,
            "projection_not_provider_execution": True,
        },
    }
    return sanitize_context_payload(payload)


def _request_mode(generation_target: str, refs: list[str]) -> str:
    if generation_target in {"image", "keyframe"}:
        return "i2i" if refs else "t2i"
    if generation_target == "video":
        return "i2v" if refs else "t2v"
    if generation_target == "prompt":
        return "prompt_optimize"
    if generation_target == "asset_card":
        return "visual_inspect"
    if generation_target == "revision":
        return "revision"
    raise ValueError("unsupported generation target")


def _input_source(model_call_context: dict[str, Any]) -> dict[str, Any]:
    context = model_call_context.get("reference_context") if isinstance(model_call_context, dict) else {}
    source = context.get("input_source") if isinstance(context, dict) else {}
    return source if isinstance(source, dict) else {}


def _duration_contract(model_call_context: dict[str, Any]) -> dict[str, Any]:
    context = model_call_context.get("preference_context") if isinstance(model_call_context, dict) else {}
    contract = context.get("duration_contract") if isinstance(context, dict) else {}
    return contract if isinstance(contract, dict) else {}


def _prompt_text(model_call_context: dict[str, Any], canonical_brief: dict[str, Any] | None) -> str:
    if canonical_brief:
        for key in ("canonical_prompt", "optimized_prompt", "prompt_text"):
            if canonical_brief.get(key):
                return sanitize_context_text(canonical_brief[key])
    prompt = (model_call_context.get("input_prompt") or {}).get("visible_prompt")
    return sanitize_context_text(prompt)


def _overlay_prompt_policy(model_call_context: dict[str, Any]) -> dict[str, Any]:
    feedback = model_call_context.get("feedback_context") if isinstance(model_call_context, dict) else {}
    policy = feedback.get("prompt_policy") if isinstance(feedback, dict) else {}
    if isinstance(policy, dict) and policy:
        return policy
    overlays = feedback.get("context_overlays") if isinstance(feedback, dict) else []
    return feedback_overlay_prompt_policy(context_overlays=overlays if isinstance(overlays, list) else [])


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "build_request_plan",
)
