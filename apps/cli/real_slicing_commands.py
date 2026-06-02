from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from apps.cli.artifact_loaders import load_clip_plans
from agentflow_studio.schemas import ClipPlan
from agentflow_studio.slicing_sop import RealSlicingConfig, slice_clip_plans_real


def slice_real_command(
    input_video: Path = typer.Option(
        ...,
        "--video",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Local input video file.",
    ),
    clip_plans_path: Path = typer.Option(
        ...,
        "--clip-plans",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to clip plans JSON.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Directory for real slice outputs.",
    ),
    ffmpeg_executable: str = typer.Option(
        "ffmpeg",
        "--ffmpeg",
        help="FFmpeg executable to use.",
    ),
    overwrite: bool = typer.Option(
        True,
        "--overwrite/--no-overwrite",
        help="Allow FFmpeg to overwrite existing output files.",
    ),
) -> None:
    """Execute minimal FFmpeg slicing from clip plans."""
    clip_plans = load_clip_plans(clip_plans_path)
    manifest = run_real_slicing_from_cli(
        input_video,
        clip_plans,
        output_dir,
        ffmpeg_executable,
        overwrite,
    )
    typer.echo("Real slicing completed")
    typer.echo(f"Status: {manifest['status']}")
    typer.echo(f"Clips: {manifest['clip_count']}")
    typer.echo(f"Output: {output_dir}")
    if manifest["status"] == "failed" and manifest["errors"]:
        typer.echo(f"Error: {manifest['errors'][0]}")
    if manifest["status"] == "failed":
        raise typer.Exit(code=1)


def run_real_slicing_from_cli(
    input_video: Path,
    clip_plans: list[ClipPlan],
    output_dir: Path,
    ffmpeg_executable: str,
    overwrite: bool,
) -> dict[str, Any]:
    return slice_clip_plans_real(
        input_video=input_video,
        clip_plans=clip_plans,
        output_dir=output_dir,
        config=RealSlicingConfig(
            ffmpeg_executable=ffmpeg_executable,
            overwrite=overwrite,
        ),
    )
