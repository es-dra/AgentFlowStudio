"""Slicing, rendering, and export SOP modules."""

from narratocut.slicing_sop.ffmpeg_probe import (
    FFmpegInfo,
    MediaToolPaths,
    MediaToolsInfo,
    check_ffmpeg_available,
    check_media_tools,
    resolve_media_tool_paths,
)
from narratocut.slicing_sop.clip_validation import validate_clip_plan
from narratocut.slicing_sop.mock_slicer import mock_slice_clip_plans
from narratocut.slicing_sop.planner import generate_clip_plans_from_scripts
from narratocut.slicing_sop.real_slicer import (
    RealSlicingConfig,
    build_ffmpeg_slice_command,
    slice_clip_plans_real,
)
from narratocut.slicing_sop.video_metadata import probe_video_metadata

__all__ = [
    "FFmpegInfo",
    "MediaToolPaths",
    "MediaToolsInfo",
    "RealSlicingConfig",
    "build_ffmpeg_slice_command",
    "check_ffmpeg_available",
    "check_media_tools",
    "generate_clip_plans_from_scripts",
    "mock_slice_clip_plans",
    "probe_video_metadata",
    "resolve_media_tool_paths",
    "slice_clip_plans_real",
    "validate_clip_plan",
]
