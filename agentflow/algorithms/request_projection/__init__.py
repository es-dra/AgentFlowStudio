from __future__ import annotations

from typing import Any

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
    request_mode = _request_mode(generation_target, refs)
    prompt = _prompt_text(model_call_context, canonical_brief)
    payload = {
        "artifact_type": "agentflow_model_request_plan",
        "schema_version": "afs_model_request_plan.v0.1",
        "algorithm_id": ALGORITHM_ID,
        "context_id": context_id,
        "operation_intent": model_call_context.get("operation_intent"),
        "generation_target": generation_target,
        "request_mode": request_mode,
        "provider_neutral": True,
        "provider_service_id": provider_service_id or "not_selected",
        "provider_request": {
            "prompt": prompt,
            "reference_image_refs": refs,
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


def _prompt_text(model_call_context: dict[str, Any], canonical_brief: dict[str, Any] | None) -> str:
    if canonical_brief:
        for key in ("canonical_prompt", "optimized_prompt", "prompt_text"):
            if canonical_brief.get(key):
                return sanitize_context_text(canonical_brief[key])
    prompt = (model_call_context.get("input_prompt") or {}).get("visible_prompt")
    return sanitize_context_text(prompt)


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "build_request_plan",
)
