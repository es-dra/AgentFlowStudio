from __future__ import annotations

from typing import Any, Callable

from apps.api import runtime_studio_state_param_values as param_values
from apps.api.runtime_studio_generation_state import SAFE_GENERATION_PARAM_KEYS, sanitize_generation_param
from apps.api.runtime_studio_state_context import sanitize_context_bundle
from apps.api.runtime_studio_state_feedback_overlay import sanitize_feedback_overlay_decisions
from apps.api.runtime_studio_state_human_gate import sanitize_human_gate_decisions
from apps.api.runtime_studio_state_keyframe_local_edit import (
    sanitize_keyframe_local_edit_draft,
    sanitize_local_edit_availability,
)
from apps.api.runtime_studio_state_quality_feedback import sanitize_quality_feedback_candidates
from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]
PreviewUrlSanitizer = Callable[..., str]

SAFE_NODE_PARAM_KEYS = (
    "model", "spec", "camera", "motion", "styleRef", "attachments", "directorSetup", "directorRef",
    "isReference", "intent", "uploads", "previewAspectRatio", "visualAssets", "visual_asset_ids",
    "firstFrameImageAssetId", "lastFrameImageAssetId", "lastVideoJobId", "lastVideoPreviewUrl",
    "videoInputSource",
    *SAFE_GENERATION_PARAM_KEYS,
    "quotaOverrideConfirmed", "lastContextBundle", "nodeRole", "sourceTextNodeId", "scriptSegmentIndex",
    "structuredShot", "shotAssetRefs", "assetPrepState", "asset_prep", "assetCardDraft",
    "assetCardRevision",
    "assetAutoBindingGraph", "asset_auto_binding_graph", "nodeReferenceStack", "node_reference_stack",
    "storyboardBreakdown", "storyboardBreakdownState", "scriptExpansionState", "keyframeLayer",
    "keyframeConstraints", "keyframeLocalEditDraft", "local_edit_availability",
    "lastKeyframeJobId", "lastKeyframeCompletedJobId", "lastOptimizedPromptPlain",
    "promptOptimizationState", "lastVisualAssetWarnings", "temporaryAssetExclusions",
    "humanGateDecisions", "feedbackOverlayDecisions", "qualityFeedbackCandidates",
)


def sanitize_node_params(
    value: dict[str, Any],
    *,
    project_id: str | None,
    text: TextSanitizer,
    number: NumberSanitizer,
    preview_url: PreviewUrlSanitizer,
) -> dict[str, Any]:
    safe_params: dict[str, Any] = {}
    for key in SAFE_NODE_PARAM_KEYS:
        if key not in value:
            continue
        sanitized = _sanitize_param(key, value[key], project_id=project_id, text=text, number=number, preview_url=preview_url)
        if sanitized not in (None, "", [], {}):
            safe_params[key] = sanitized
    return safe_params


def _sanitize_param(
    key: str,
    value: Any,
    *,
    project_id: str | None,
    text: TextSanitizer,
    number: NumberSanitizer,
    preview_url: PreviewUrlSanitizer,
) -> Any:
    if key == "uploads":
        return param_values.uploads(value, project_id=project_id, preview_url=preview_url, text=text, number=number)
    if key in {"firstFrameImageAssetId", "lastFrameImageAssetId", "lastVideoJobId", "lastKeyframeJobId", "lastKeyframeCompletedJobId"}:
        return safe_id(text(value, "", 120))
    if key == "lastVideoPreviewUrl":
        return preview_url(value, project_id=project_id)
    if key == "videoInputSource":
        return _video_input_source(value, text=text)
    if key in SAFE_GENERATION_PARAM_KEYS:
        return sanitize_generation_param(key, value, project_id=project_id, preview_url=preview_url, text=text, number=number)
    if key == "quotaOverrideConfirmed":
        return bool(value)
    if key == "lastContextBundle":
        return sanitize_context_bundle(value)
    if key == "visualAssets":
        return param_values.visual_assets(value, project_id=project_id, preview_url=preview_url, text=text)
    if key == "visual_asset_ids":
        return param_values.text_list(value, text=text, max_items=24, max_length=120, safe=True)
    if key == "structuredShot":
        return param_values.structured_shot(value, text=text, number=number)
    if key == "shotAssetRefs":
        return param_values.asset_refs(value, text=text)
    if key == "assetCardDraft":
        return param_values.asset_card_draft(value, text=text)
    if key == "assetCardRevision":
        return param_values.asset_card_revision(value, text=text)
    if key in {"assetPrepState", "asset_prep", "storyboardBreakdownState", "scriptExpansionState", "promptOptimizationState"}:
        return param_values.safe_object(value, text=text, number=number, max_items=32)
    if key == "storyboardBreakdown":
        return param_values.storyboard_breakdown(value, text=text, number=number)
    if key in {"assetAutoBindingGraph", "asset_auto_binding_graph"}:
        return param_values.asset_auto_binding_graph(value, text=text, number=number)
    if key in {"nodeReferenceStack", "node_reference_stack"}:
        return param_values.node_reference_stack(value, text=text, number=number)
    if key == "keyframeLayer":
        return param_values.keyframe_layer(value, text=text)
    if key == "keyframeConstraints":
        return param_values.keyframe_constraints(value, text=text, number=number)
    if key == "keyframeLocalEditDraft":
        return sanitize_keyframe_local_edit_draft(value, text=text, number=number)
    if key == "local_edit_availability":
        return sanitize_local_edit_availability(value, text=text)
    if key == "lastVisualAssetWarnings":
        return param_values.warnings(value, text=text)
    if key == "temporaryAssetExclusions":
        return param_values.asset_exclusions(value, text=text)
    if key == "humanGateDecisions":
        return sanitize_human_gate_decisions(value, text=text)
    if key == "feedbackOverlayDecisions":
        return sanitize_feedback_overlay_decisions(value, text=text)
    if key == "qualityFeedbackCandidates":
        return sanitize_quality_feedback_candidates(value, text=text)
    if key == "scriptSegmentIndex":
        return int(max(0, min(9999, number(value, 0))))
    if key in {"nodeRole", "sourceTextNodeId", "directorRef"}:
        return text(value, "", 120)
    if key == "lastOptimizedPromptPlain":
        return text(value, "", 4000)
    return value


def _video_input_source(value: Any, *, text: TextSanitizer) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    source_mode = text(value.get("source_mode"), "", 80)
    if source_mode not in {
        "uploaded_image",
        "upstream_uploaded_image",
        "upstream_generated_image",
        "visual_asset_reference",
        "explicit_first_frame_selection",
    }:
        source_mode = "explicit_first_frame_selection"
    result = {
        "source_mode": source_mode,
        "source_asset_id": safe_id(text(value.get("source_asset_id"), "", 120)),
        "source_node_id": safe_id(text(value.get("source_node_id"), "", 120)),
        "source_job_id": safe_id(text(value.get("source_job_id"), "", 120)),
        "visual_asset_id": safe_id(text(value.get("visual_asset_id"), "", 120)),
        "role": "first_frame",
    }
    return {key: item for key, item in result.items() if item}


__all__ = ("SAFE_NODE_PARAM_KEYS", "sanitize_node_params")
