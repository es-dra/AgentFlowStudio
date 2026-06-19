from __future__ import annotations

from typing import Any

from agentflow.algorithms.provider_gate_manifest import (
    strip_image_edit_language as algorithm_strip_image_edit_language,
    video_provider_prompt as algorithm_video_provider_prompt,
)
from apps.api.runtime_models import VideoGenerationRequest


def video_provider_prompt(request: VideoGenerationRequest, context_bundle: dict[str, Any] | None) -> str:
    return algorithm_video_provider_prompt(
        prompt_text=request.prompt_text,
        optimized_prompt=request.optimized_prompt,
        duration_sec=request.duration_sec,
        motion=request.motion,
        last_frame_image_asset_id=request.last_frame_image_asset_id,
        context_bundle=context_bundle,
    )


def strip_image_edit_language(value: str) -> str:
    return algorithm_strip_image_edit_language(value)
