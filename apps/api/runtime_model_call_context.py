from __future__ import annotations

from typing import Any

from agentflow.algorithms.model_call_context import build_model_call_context


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
        user_preferences={
            "duration_sec": request.duration_sec,
            "motion": request.motion,
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio,
        },
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
        upstream_refs=_image_refs(request.base_video_job_id, request.base_video_artifact_id, request.parent_revision_job_id),
        user_preferences={
            "duration_sec": request.duration_sec,
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio,
            "motion": request.motion,
            "provider_capability_mode": request.provider_capability_mode,
            "preserve_policy": request.preserve_policy,
        },
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


__all__ = (
    "keyframe_model_call_context",
    "prompt_optimization_model_call_context",
    "revision_model_call_context",
    "video_generation_model_call_context",
    "visual_inspect_model_call_context",
)
