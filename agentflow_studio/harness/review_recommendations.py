from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow_studio.harness.quality_profiles import REAL_CLIP_QUALITY_PROFILES, VIDEO_REAL_CLIPS_PROFILE


def build_review_recommendations(
    root: Path,
    run_manifest: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
) -> list[str]:
    if not run_manifest or run_manifest.get("quality_profile") not in REAL_CLIP_QUALITY_PROFILES | {VIDEO_REAL_CLIPS_PROFILE}:
        return []

    recommendation_set: list[str] = []
    real_manifest = _load_json_object(root / "real_slice_manifest.json")
    validation = _load_json_object(root / "clip_plan_validation.json")
    metadata = _load_json_object(root / "video_metadata.json")
    all_errors = " ".join(
        str(item)
        for source in [
            quality_report.get("errors", []) if quality_report else [],
            real_manifest.get("errors", []) if real_manifest else [],
            validation.get("hard_errors", []) if validation else [],
            metadata.get("errors", []) if metadata else [],
        ]
        for item in source
    )
    reason = str(real_manifest.get("reason") if real_manifest else "")

    if "ffmpeg_unavailable" in all_errors or "ffmpeg_unavailable" in reason:
        recommendation_set.append("Install FFmpeg or set NCUT_FFMPEG_PATH to a valid ffmpeg executable.")
    if "ffprobe" in all_errors or "video_duration_unavailable" in all_errors:
        recommendation_set.append("Install FFprobe or set NCUT_FFPROBE_PATH so video duration can be validated.")
    if "segment_exceeds_video_duration" in all_errors:
        recommendation_set.append("Adjust the ClipPlan segment end times so they stay within video duration.")
    if "unsafe_output_name" in all_errors:
        recommendation_set.append("Use a plain output file name without directories or path traversal.")
    if "clip_plan_validation_failed" in reason:
        recommendation_set.append("Review clip_plan_validation.json before rerunning real slicing.")
    return recommendation_set


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
