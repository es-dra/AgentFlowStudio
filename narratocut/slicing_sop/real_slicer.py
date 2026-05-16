from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RealSlicingConfig:
    ffmpeg_executable: str = "ffmpeg"
    output_ext: str = ".mp4"
    overwrite: bool = True

    def __post_init__(self) -> None:
        if not self.ffmpeg_executable.strip():
            raise ValueError("ffmpeg_executable must not be empty.")
        if not self.output_ext.startswith("."):
            raise ValueError("output_ext must start with a dot.")


def build_ffmpeg_slice_command(
    input_video: str | Path,
    start_sec: float,
    duration_sec: float,
    output_video: str | Path,
    config: RealSlicingConfig | None = None,
) -> list[str]:
    """Build a minimal FFmpeg slice command without executing it."""
    if start_sec < 0:
        raise ValueError("start_sec must be greater than or equal to 0.")
    if duration_sec <= 0:
        raise ValueError("duration_sec must be greater than 0.")

    resolved_config = config or RealSlicingConfig()
    overwrite_flag = "-y" if resolved_config.overwrite else "-n"

    return [
        resolved_config.ffmpeg_executable,
        overwrite_flag,
        "-ss",
        _format_seconds(start_sec),
        "-i",
        str(Path(input_video)),
        "-t",
        _format_seconds(duration_sec),
        str(Path(output_video)),
    ]


def _format_seconds(value: float) -> str:
    return f"{value:g}"
