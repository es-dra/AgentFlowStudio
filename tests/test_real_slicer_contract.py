from __future__ import annotations

from pathlib import Path

import pytest

from agentflow_studio.slicing_sop.real_slicer import RealSlicingConfig, build_ffmpeg_slice_command


def test_build_ffmpeg_slice_command_uses_minimal_contract() -> None:
    command = build_ffmpeg_slice_command(
        input_video=Path("input.mp4"),
        start_sec=1.5,
        duration_sec=12.25,
        output_video=Path("out") / "clip.mp4",
        config=RealSlicingConfig(ffmpeg_executable="ffmpeg-test", overwrite=True),
    )

    assert command == [
        "ffmpeg-test",
        "-y",
        "-ss",
        "1.5",
        "-i",
        str(Path("input.mp4")),
        "-t",
        "12.25",
        str(Path("out") / "clip.mp4"),
    ]


def test_build_ffmpeg_slice_command_can_disable_overwrite() -> None:
    command = build_ffmpeg_slice_command(
        "input.mp4",
        0,
        5,
        "clip.mp4",
        RealSlicingConfig(overwrite=False),
    )

    assert command[1] == "-n"


def test_build_ffmpeg_slice_command_rejects_negative_start() -> None:
    with pytest.raises(ValueError, match="start_sec"):
        build_ffmpeg_slice_command("input.mp4", -0.1, 5, "clip.mp4")


def test_build_ffmpeg_slice_command_rejects_non_positive_duration() -> None:
    with pytest.raises(ValueError, match="duration_sec"):
        build_ffmpeg_slice_command("input.mp4", 0, 0, "clip.mp4")


def test_real_slicing_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="ffmpeg_executable"):
        RealSlicingConfig(ffmpeg_executable="")
    with pytest.raises(ValueError, match="output_ext"):
        RealSlicingConfig(output_ext="mp4")
