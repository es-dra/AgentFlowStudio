from __future__ import annotations

import re
from typing import Any

from agentflow.algorithms.provider_gate_manifest import (
    strip_image_edit_language as algorithm_strip_image_edit_language,
    video_generation_plan as algorithm_video_generation_plan,
    video_provider_prompt as algorithm_video_provider_prompt,
)
from apps.api.runtime_models import VideoGenerationRequest


_ABSTRACT_VIDEO_MARKERS = (
    "abstract",
    "geometric",
    "storyboard card",
    "timeline block",
    "canvas node",
    "unbranded panel",
    "blank label",
    "safe abstract",
)

_CHARACTER_VIDEO_MARKERS = (
    "actor",
    "body",
    "character",
    "clothing",
    "face",
    "hairstyle",
    "human",
    "person",
    "portrait",
    "wardrobe",
    "\u4eba\u7269",
    "\u89d2\u8272",
    "\u4eba\u50cf",
    "\u9762\u90e8",
    "\u670d\u88c5",
)

_NEGATIVE_SAFETY_PATTERNS = (
    r"\bno\s+(?:people|persons|humans?|human figures?|faces?|text|logos?|watermarks?|brands?)\b",
    r"\bwithout\s+(?:people|persons|humans?|human figures?|faces?|text|logos?|watermarks?|brands?)\b",
    r"\bavoid\s+[^.;,\n]*(?:people|persons|humans?|faces?|text|logos?|watermarks?|brands?)[^.;,\n]*",
    r"\bdo not\s+[^.;,\n]*(?:people|persons|humans?|faces?|text|logos?|watermarks?|brands?)[^.;,\n]*",
)


def video_provider_prompt(
    request: VideoGenerationRequest,
    context_bundle: dict[str, Any] | None,
    *,
    limit: int = 4000,
) -> str:
    if _uses_abstract_provider_prompt(request, context_bundle):
        return _abstract_provider_prompt(request, limit=limit)
    return algorithm_video_provider_prompt(
        prompt_text=request.prompt_text,
        optimized_prompt=request.optimized_prompt,
        duration_sec=request.duration_sec,
        motion=request.motion,
        last_frame_image_asset_id=request.last_frame_image_asset_id,
        context_bundle=context_bundle,
        context_subgraph=request.context_subgraph,
        limit=limit,
    )


def video_generation_plan(request: VideoGenerationRequest, context_bundle: dict[str, Any] | None) -> dict[str, Any]:
    return algorithm_video_generation_plan(
        prompt_text=request.prompt_text,
        optimized_prompt=request.optimized_prompt,
        duration_sec=request.duration_sec,
        motion=request.motion,
        last_frame_image_asset_id=request.last_frame_image_asset_id,
        context_bundle=context_bundle,
        context_subgraph=request.context_subgraph,
    )


def strip_image_edit_language(value: str) -> str:
    return algorithm_strip_image_edit_language(value)


def _uses_abstract_provider_prompt(request: VideoGenerationRequest, context_bundle: dict[str, Any] | None) -> bool:
    source = " ".join(
        part
        for part in (
            request.prompt_text,
            request.optimized_prompt or "",
            request.motion or "",
            _context_text(context_bundle),
        )
        if str(part or "").strip()
    ).lower()
    has_abstract_marker = any(marker in source for marker in _ABSTRACT_VIDEO_MARKERS)
    has_character_marker = _has_character_marker(source)
    explicit_no_human = bool(re.search(r"\b(?:no|without)\s+(?:people|persons|humans?|human figures?|faces?)\b", source))
    return has_abstract_marker and (explicit_no_human or not has_character_marker)


def _abstract_provider_prompt(request: VideoGenerationRequest, *, limit: int) -> str:
    base = _sanitize_abstract_prompt(strip_image_edit_language(request.optimized_prompt or request.prompt_text))
    motion = _sanitize_abstract_prompt(strip_image_edit_language(request.motion or "gentle geometric motion"))
    duration = str(request.duration_sec)
    parts = [
        base,
        f"Video task: create one continuous {duration}s image-to-video clip from the first frame.",
        "Preserve the first-frame layout, color palette, geometric shapes, lighting, and composition.",
        f"Motion: {motion}.",
        "Temporal plan:",
        "- 0.0s-2.0s: hold the initial layout and soft lighting.",
        f"- 2.0s-{duration}s: apply gentle drift to cards, timeline blocks, canvas nodes, and light movement.",
        f"- End at {duration}s: settle into a stable final frame with the same visual structure.",
    ]
    return "\n".join(part for part in parts if part.strip())[:limit]


def _sanitize_abstract_prompt(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\binterface\b", "workspace layout", text, flags=re.IGNORECASE)
    for pattern in _NEGATIVE_SAFETY_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.;")
    return text


def _context_text(context_bundle: dict[str, Any] | None) -> str:
    if not isinstance(context_bundle, dict):
        return ""
    text_channel = context_bundle.get("text_channel")
    if not isinstance(text_channel, dict):
        return ""
    return " ".join(str(text_channel.get(key) or "") for key in sorted(text_channel))


def _has_character_marker(source: str) -> bool:
    for marker in _CHARACTER_VIDEO_MARKERS:
        if marker.isascii():
            if re.search(rf"\b{re.escape(marker)}s?\b", source):
                return True
            continue
        if marker in source:
            return True
    return False


__all__ = ("strip_image_edit_language", "video_generation_plan", "video_provider_prompt")
