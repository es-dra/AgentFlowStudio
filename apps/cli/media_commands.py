from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from agentflow_studio.slicing_sop import check_ffmpeg_available, check_media_tools


def ffmpeg_check_command(
    executable: str = typer.Option(
        "ffmpeg",
        "--executable",
        "-e",
        help="FFmpeg executable to probe.",
    ),
    ffmpeg_executable: Optional[str] = typer.Option(
        None,
        "--ffmpeg",
        help="FFmpeg executable path. Overrides --executable when set.",
    ),
    ffprobe_executable: Optional[str] = typer.Option(
        None,
        "--ffprobe",
        help="FFprobe executable path.",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Optional FFmpeg config YAML.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Write structured JSON status.",
    ),
) -> None:
    """Check whether FFmpeg is callable on this machine."""
    ffmpeg_value = ffmpeg_executable or executable
    if json_output or ffprobe_executable or config_path:
        tools = check_media_tools(
            ffmpeg=ffmpeg_value,
            ffprobe=ffprobe_executable,
            config_path=config_path,
        )
        if json_output:
            typer.echo(json.dumps(tools.to_dict(), ensure_ascii=False, indent=2))
            return
        if tools.status == "ready":
            typer.echo("FFmpeg and FFprobe available")
            return
        typer.echo("; ".join(tools.warnings))
        return

    info = check_ffmpeg_available(ffmpeg_value)
    if info.available:
        version = info.version or "unknown version"
        typer.echo(f"FFmpeg available: {info.executable} ({version})")
        return

    typer.echo(f"FFmpeg unavailable: {info.error}")
