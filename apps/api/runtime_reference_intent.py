from __future__ import annotations

from typing import Any


ORIGINALIZE_REFERENCE_MODE = "originalize_ip_safe"
LOCALIZED_REFERENCE_MODE = "localized_edit"

_ORIGINALIZE_MODE_VALUES = {
    "originalize",
    "originalize_ip_safe",
    "reference_guided_original_rebirth",
    "original_rebirth",
    "ip_safe_rebirth",
    "ip_risk_reduction",
    "inspiration_reference",
    "style_reference_only",
    "原创重生",
    "降ip风险",
    "降低ip风险",
    "去ip",
    "灵感参考",
}

_LOCALIZED_MODE_VALUES = {
    "localized_edit",
    "partial_revision",
    "image_guided_partial_revision",
    "text_only_revision",
    "局部修改",
    "局部修订",
}

_ORIGINALIZE_TERMS = (
    "原创重生",
    "降ip",
    "降低ip",
    "降低 IP",
    "去ip",
    "避开ip",
    "不要像原角色",
    "不要复制",
    "重新设计",
    "原创资产",
    "灵感参考",
    "只参考风格",
    "originalize",
    "ip safe",
    "copyright safe",
    "inspiration only",
    "do not copy",
    "redesign",
)

_LOCALIZED_TERMS = (
    "局部",
    "只改",
    "仅改",
    "保持",
    "不变",
    "preserve",
    "keep",
    "only",
    "localized",
    "partial",
)


def normalize_reference_transform_mode(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    compact = text.replace(" ", "").replace("-", "_").casefold()
    if compact in {item.replace(" ", "").replace("-", "_").casefold() for item in _ORIGINALIZE_MODE_VALUES}:
        return ORIGINALIZE_REFERENCE_MODE
    if compact in {item.replace(" ", "").replace("-", "_").casefold() for item in _LOCALIZED_MODE_VALUES}:
        return LOCALIZED_REFERENCE_MODE
    lowered = text.casefold()
    if any(term.casefold() in lowered for term in _ORIGINALIZE_TERMS):
        return ORIGINALIZE_REFERENCE_MODE
    if any(term.casefold() in lowered for term in _LOCALIZED_TERMS):
        return LOCALIZED_REFERENCE_MODE
    return ""


def reference_transform_mode_from_params(params: dict[str, Any] | None) -> str:
    data = params if isinstance(params, dict) else {}
    for key in (
        "reference_transform_mode",
        "referenceTransformMode",
        "asset_reference_mode",
        "assetReferenceMode",
        "prompt_reference_mode",
    ):
        mode = normalize_reference_transform_mode(data.get(key))
        if mode:
            return mode
    revision = data.get("asset_card_revision") if isinstance(data.get("asset_card_revision"), dict) else {}
    return normalize_reference_transform_mode(revision.get("mode"))


def reference_transform_mode_for_request(request: Any) -> str:
    params = getattr(request, "node_parameters", None)
    mode = reference_transform_mode_from_params(params if isinstance(params, dict) else {})
    if mode:
        return mode
    prompt = f"{getattr(request, 'prompt_text', '')} {getattr(request, 'optimized_prompt', '')}"
    return normalize_reference_transform_mode(prompt)


def is_originalize_reference_mode(value: Any) -> bool:
    return normalize_reference_transform_mode(value) == ORIGINALIZE_REFERENCE_MODE


def is_originalize_reference_request(request: Any) -> bool:
    return reference_transform_mode_for_request(request) == ORIGINALIZE_REFERENCE_MODE


def originalize_reference_policy(reference_count: int = 0) -> str:
    prefix = f"Connected reference images: {reference_count}. " if reference_count else ""
    return (
        f"{prefix}Originality-safe reference transformation: use reference images as inspiration and visual evidence only, "
        "not as identity, layout, pose, costume, logo, or exact proportion anchors. Extract high-level concept, broad shape language, "
        "material mood, palette relationship, and functional intent; redesign the subject into a new production-safe asset with new identity, "
        "face/head details, costume system, distinctive markings, and composition. Avoid copying recognizable IP, trademark, logo, exact outfit, "
        "signature silhouette, weapon design, or iconic scene composition."
    )


def prompt_mentions_originalize(value: str) -> bool:
    text = str(value or "")
    return normalize_reference_transform_mode(text) == ORIGINALIZE_REFERENCE_MODE


__all__ = (
    "LOCALIZED_REFERENCE_MODE",
    "ORIGINALIZE_REFERENCE_MODE",
    "is_originalize_reference_mode",
    "is_originalize_reference_request",
    "normalize_reference_transform_mode",
    "originalize_reference_policy",
    "prompt_mentions_originalize",
    "reference_transform_mode_for_request",
    "reference_transform_mode_from_params",
)
