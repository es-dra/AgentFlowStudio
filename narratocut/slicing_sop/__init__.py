"""Slicing, rendering, and export SOP modules."""

from narratocut.slicing_sop.ffmpeg_probe import FFmpegInfo, check_ffmpeg_available
from narratocut.slicing_sop.mock_slicer import mock_slice_clip_plans
from narratocut.slicing_sop.planner import generate_clip_plans_from_scripts
from narratocut.slicing_sop.real_slicer import RealSlicingConfig, build_ffmpeg_slice_command

__all__ = [
    "FFmpegInfo",
    "RealSlicingConfig",
    "build_ffmpeg_slice_command",
    "check_ffmpeg_available",
    "generate_clip_plans_from_scripts",
    "mock_slice_clip_plans",
]
