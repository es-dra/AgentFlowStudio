from __future__ import annotations

from typing import Any, Callable

from apps.api import runtime_studio_state_param_values as param_values
from apps.api.runtime_studio_generation_state import SAFE_GENERATION_PARAM_KEYS, sanitize_generation_param
from apps.api.runtime_studio_state_context import sanitize_context_bundle
from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]
PreviewUrlSanitizer = Callable[..., str]

SAFE_NODE_PARAM_KEYS = (
    "model", "spec", "camera", "motion", "styleRef", "attachments", "directorSetup", "directorRef",
    "isReference", "intent", "uploads", "previewAspectRatio", "visualAssets", "visual_asset_ids",
    "firstFrameImageAssetId", "lastFrameImageAssetId", "lastVideoJobId", "lastVideoPreviewUrl",
    *SAFE_GENERATION_PARAM_KEYS,
    "quotaOverrideConfirmed", "lastContextBundle", "nodeRole", "sourceTextNodeId", "scriptSegmentIndex",
    "structuredShot", "shotAssetRefs", "assetPrepState", "asset_prep", "assetCardDraft",
    "storyboardBreakdown", "storyboardBreakdownState", "scriptExpansionState", "keyframeLayer",
    "lastKeyframeJobId", "lastKeyframeCompletedJobId", "lastOptimizedPromptPlain",
    "promptOptimizationState", "lastVisualAssetWarnings", "temporaryAssetExclusions",
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
    if key in {"assetPrepState", "asset_prep", "storyboardBreakdownState", "scriptExpansionState", "promptOptimizationState"}:
        return param_values.safe_object(value, text=text, number=number, max_items=32)
    if key == "storyboardBreakdown":
        return param_values.storyboard_breakdown(value, text=text, number=number)
    if key == "keyframeLayer":
        return param_values.keyframe_layer(value, text=text)
    if key == "lastVisualAssetWarnings":
        return param_values.warnings(value, text=text)
    if key == "temporaryAssetExclusions":
        return param_values.asset_exclusions(value, text=text)
    if key == "scriptSegmentIndex":
        return int(max(0, min(9999, number(value, 0))))
    if key in {"nodeRole", "sourceTextNodeId", "directorRef"}:
        return text(value, "", 120)
    if key == "lastOptimizedPromptPlain":
        return text(value, "", 4000)
    return value


__all__ = ("SAFE_NODE_PARAM_KEYS", "sanitize_node_params")
