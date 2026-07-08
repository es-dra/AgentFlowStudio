from __future__ import annotations

from typing import Any

from agentflow.algorithms.model_call_context import build_model_call_context
from apps.api.runtime_video_contract import video_duration_contract, video_input_source_contract


def public_model_call_context_summary(
    context: dict[str, Any],
    *,
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sources = _safe_dict(context.get("context_sources"))
    asset_context = _safe_dict(context.get("asset_context"))
    reference_context = _safe_dict(context.get("reference_context"))
    provider_constraints = _safe_dict(context.get("provider_constraints"))
    trace_summary = _safe_dict(context.get("trace_summary"))
    safety_boundary = _safe_dict(context.get("safety_boundary"))
    summary = {
        "context_id": str(context.get("context_id") or ""),
        "schema_version": str(context.get("schema_version") or ""),
        "operation_intent": str(context.get("operation_intent") or ""),
        "generation_target": str(context.get("generation_target") or ""),
        "context_sources": {
            "context_bundle_present": bool(sources.get("context_bundle_present")),
            "included_asset_count": _safe_int(sources.get("included_asset_count")),
            "excluded_asset_count": _safe_int(sources.get("excluded_asset_count")),
            "feedback_context_overlay_count": _safe_int(sources.get("feedback_context_overlay_count")),
            "upstream_ref_count": _safe_int(sources.get("upstream_ref_count")),
        },
        "asset_context": {
            "context_eligible_asset_count": len(_safe_list(asset_context.get("context_eligible_asset_ids"))),
            "draft_assets_enter_context": bool(asset_context.get("draft_assets_enter_context")),
        },
        "reference_context": {
            "reference_image_count": _safe_int(reference_context.get("reference_image_count")),
        },
        "provider_constraints": {
            "capability": str(provider_constraints.get("capability") or ""),
            "provider_gate": str(provider_constraints.get("provider_gate") or provider_constraints.get("required_gate") or ""),
        },
        "trace_summary": {
            "warning_ids": _safe_ref_list(trace_summary.get("warning_ids") or []),
            "feedback_context_overlay_ids": _safe_ref_list(trace_summary.get("feedback_context_overlay_ids") or []),
        },
        "safety_boundary": {
            "no_secrets": bool(safety_boundary.get("no_secrets")),
            "no_provider_raw": bool(safety_boundary.get("no_provider_raw")),
            "no_credentialed_url": bool(safety_boundary.get("no_credentialed_url")),
            "no_local_path": bool(safety_boundary.get("no_local_path")),
            "no_media_bytes": bool(safety_boundary.get("no_media_bytes")),
            "feedback_is_not_memory": bool(safety_boundary.get("feedback_is_not_memory")),
            "draft_assets_are_not_context_truth": bool(safety_boundary.get("draft_assets_are_not_context_truth")),
        },
        "non_claims": [
            "not_provider_execution",
            "not_generated_media_qa",
            "not_human_acceptance",
            "not_public_readiness",
        ],
    }
    if artifact:
        summary["artifact"] = {
            "artifact_id": str(artifact.get("artifact_id") or ""),
            "artifact_type": str(artifact.get("artifact_type") or ""),
            "filename": str(artifact.get("filename") or ""),
            "role": str(artifact.get("role") or ""),
            "media_type": str(artifact.get("media_type") or ""),
        }
    return summary


def prompt_optimization_model_call_context(
    *,
    project_id: str,
    request: Any,
    assembly: dict[str, Any],
    context_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    return build_model_call_context(
        project_id=project_id,
        node_ref={"node_id": request.node_id or "", "node_type": request.node_type},
        operation_intent="prompt_optimize",
        generation_target="prompt",
        input_prompt=request.prompt_text,
        context_bundle=context_bundle,
        fixed_assets=_included_assets(context_bundle),
        reference_image_refs=list(getattr(request, "asset_refs", []) or []),
        user_preferences={"style": request.style, "target_platform": request.target_platform},
        expert_rule_ids=[
            *_rule_ids(assembly.get("knowledge_rules") or []),
            *_director_scenario_ids(assembly.get("director_scenario") or {}),
        ],
        provider_constraints={"capability": "llm", "provider_gate": "AFS_ALLOW_REMOTE_LLM"},
    )


def keyframe_model_call_context(
    *,
    project_id: str,
    request: Any,
    context_bundle: dict[str, Any] | None,
    provider_constraints: dict[str, Any],
) -> dict[str, Any]:
    return build_model_call_context(
        project_id=project_id,
        node_ref={"node_id": request.node_id or "", "node_type": "image"},
        operation_intent="image_generate",
        generation_target="image",
        input_prompt=request.optimized_prompt or request.prompt_text,
        context_bundle=context_bundle,
        fixed_assets=_included_assets(context_bundle),
        reference_image_refs=list(getattr(request, "asset_refs", []) or []),
        user_preferences={"style": request.style, "target_platform": request.target_platform},
        provider_constraints=provider_constraints,
    )


def video_generation_model_call_context(
    *,
    project_id: str,
    request: Any,
    context_bundle: dict[str, Any] | None,
    provider_constraints: dict[str, Any],
) -> dict[str, Any]:
    return build_model_call_context(
        project_id=project_id,
        node_ref={"node_id": request.node_id or "", "node_type": "video"},
        operation_intent="video_generate",
        generation_target="video",
        input_prompt=request.optimized_prompt or request.prompt_text,
        context_bundle=context_bundle,
        fixed_assets=_included_assets(context_bundle),
        reference_image_refs=_image_refs(
            getattr(request, "first_frame_image_asset_id", None),
            getattr(request, "last_frame_image_asset_id", None),
        ),
        input_source=video_input_source_contract(request),
        user_preferences={
            "duration_sec": request.duration_sec,
            "duration_contract": video_duration_contract(request.duration_sec),
            "motion": request.motion,
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio,
        },
        duration_contract=video_duration_contract(request.duration_sec),
        provider_constraints=provider_constraints,
    )


def visual_inspect_model_call_context(
    *,
    project_id: str,
    request: Any,
    provider_constraints: dict[str, Any],
) -> dict[str, Any]:
    image_refs = [
        *list(getattr(request, "source_image_asset_refs", []) or []),
        *list(getattr(request, "sampled_image_asset_refs", []) or []),
    ]
    video_ref = getattr(request, "source_video_artifact_id", None)
    return build_model_call_context(
        project_id=project_id,
        node_ref={"node_id": request.node_id or "", "node_type": "asset_card"},
        operation_intent="visual_inspect",
        generation_target="asset_card",
        input_prompt=request.prompt_text,
        reference_image_refs=_image_refs(*image_refs),
        upstream_refs=_image_refs(video_ref),
        user_preferences={
            "asset_type": request.asset_type,
            "vision_output_policy": "draft_asset_card_only",
        },
        provider_constraints=provider_constraints,
    )


def revision_model_call_context(
    *,
    project_id: str,
    request: Any,
    revision_control: dict[str, Any],
    provider_constraints: dict[str, Any],
) -> dict[str, Any]:
    return build_model_call_context(
        project_id=project_id,
        node_ref={"node_id": request.node_id or "", "node_type": "video"},
        operation_intent="revision",
        generation_target="revision",
        input_prompt=request.revision_intent,
        reference_image_refs=_image_refs(request.first_frame_image_asset_id, request.last_frame_image_asset_id),
        input_source=video_input_source_contract(request),
        upstream_refs=_image_refs(request.base_video_job_id, request.base_video_artifact_id, request.parent_revision_job_id),
        user_preferences={
            "duration_sec": request.duration_sec,
            "duration_contract": video_duration_contract(request.duration_sec),
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio,
            "motion": request.motion,
            "provider_capability_mode": request.provider_capability_mode,
            "preserve_policy": request.preserve_policy,
        },
        duration_contract=video_duration_contract(request.duration_sec),
        provider_constraints=provider_constraints,
        feedback_events=[
            {
                "kind": "video_revision_request",
                "note": request.revision_intent,
                "summary": request.revision_intent,
            }
        ],
        revision_control=revision_control,
    )


def _included_assets(context_bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not context_bundle:
        return []
    return [item for item in (context_bundle.get("included_assets") or []) if isinstance(item, dict)]


def _image_refs(*values: Any) -> list[str]:
    refs: list[str] = []
    for value in values:
        ref = str(value or "").strip()
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _rule_ids(rules: list[dict[str, Any]]) -> list[str]:
    return [str(rule.get("rule_id") or "").strip() for rule in rules if rule.get("rule_id")]


def _director_scenario_ids(context: dict[str, Any]) -> list[str]:
    packs = context.get("selected_packs") if isinstance(context, dict) else []
    return [
        "director_scenario:" + str(pack.get("scenario_id") or "").strip()
        for pack in (packs if isinstance(packs, list) else [])
        if isinstance(pack, dict) and pack.get("scenario_id")
    ]


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_ref_list(values: Any) -> list[str]:
    refs: list[str] = []
    for value in _safe_list(values):
        ref = str(value or "").strip()
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


__all__ = (
    "keyframe_model_call_context",
    "prompt_optimization_model_call_context",
    "public_model_call_context_summary",
    "revision_model_call_context",
    "video_generation_model_call_context",
    "visual_inspect_model_call_context",
)
