from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from narratocut.schemas import ClipPlan, ClipSegment
from narratocut.utils import write_json


REAL_SLICE_MANIFEST = "real_slice_manifest.json"

@dataclass(frozen=True)
class RealSlicingConfig:
    ffmpeg_executable: str = "ffmpeg"
    output_ext: str = ".mp4"
    overwrite: bool = True
    clips_dir: str = "clips"

    def __post_init__(self) -> None:
        if not self.ffmpeg_executable.strip():
            raise ValueError("ffmpeg_executable must not be empty.")
        if not self.output_ext.startswith("."):
            raise ValueError("output_ext must start with a dot.")
        clips_path = Path(self.clips_dir)
        if not self.clips_dir.strip() or clips_path.is_absolute() or ".." in clips_path.parts:
            raise ValueError("clips_dir must be a safe relative path.")


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


def slice_clip_plans_real(
    input_video: str | Path,
    clip_plans: list[ClipPlan],
    output_dir: str | Path,
    config: RealSlicingConfig | None = None,
) -> dict[str, Any]:
    """Execute minimal FFmpeg slicing for clip plans and write a manifest."""
    resolved_config = config or RealSlicingConfig()
    source = Path(input_video)
    root = Path(output_dir)
    clips_dir_ref = Path(resolved_config.clips_dir)
    clips_dir = root / clips_dir_ref
    clips_dir.mkdir(parents=True, exist_ok=True)

    if not source.is_file():
        manifest = _manifest(
            status="failed",
            clips=[],
            errors=[f"input_video_missing: {_display_ref(source)}"],
        )
        write_json(root / REAL_SLICE_MANIFEST, manifest)
        return manifest

    clips: list[dict[str, Any]] = []
    errors: list[str] = []
    clip_index = 1
    for plan in clip_plans:
        segments = plan.segments
        if not segments:
            error = f"clip_plan_has_no_segments: {plan.clip_plan_id}"
            errors.append(error)
            clips.append(_failed_clip(plan.clip_plan_id, "", error))
            continue

        for segment in segments:
            clip_id = f"clip_{clip_index:03d}"
            output_ref = clips_dir_ref / f"{clip_id}{resolved_config.output_ext}"
            output_path = root / output_ref
            try:
                result = _slice_segment(
                    source=source,
                    segment=segment,
                    output_path=output_path,
                    config=resolved_config,
                )
            except FileNotFoundError:
                error = f"ffmpeg_executable_not_found: {resolved_config.ffmpeg_executable}"
                errors.append(error)
                clips.append(
                    _failed_clip(
                        clip_id=clip_id,
                        clip_plan_id=plan.clip_plan_id,
                        path=_display_ref(output_ref),
                        error=error,
                    )
                )
                clip_index += 1
                continue
            except OSError as exc:
                error = f"ffmpeg_execution_failed: {exc}"
                errors.append(error)
                clips.append(
                    _failed_clip(
                        clip_id=clip_id,
                        clip_plan_id=plan.clip_plan_id,
                        path=_display_ref(output_ref),
                        error=error,
                    )
                )
                clip_index += 1
                continue
            clip = _clip_record(
                clip_id=clip_id,
                clip_plan_id=plan.clip_plan_id,
                segment=segment,
                output_ref=output_ref,
                status="succeeded" if result.returncode == 0 else "failed",
                result=result,
            )
            if result.returncode != 0:
                error = _ffmpeg_error(clip_id, result)
                clip["error"] = error
                errors.append(error)
            clips.append(clip)
            clip_index += 1

    status = _manifest_status(clips, errors)
    manifest = _manifest(
        status=status,
        clips=clips,
        errors=errors,
    )
    write_json(root / REAL_SLICE_MANIFEST, manifest)
    return manifest


def _format_seconds(value: float) -> str:
    return f"{value:g}"


def _slice_segment(
    source: Path,
    segment: ClipSegment,
    output_path: Path,
    config: RealSlicingConfig,
) -> subprocess.CompletedProcess[str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_slice_command(
        input_video=source,
        start_sec=segment.start_sec,
        duration_sec=segment.end_sec - segment.start_sec,
        output_video=output_path,
        config=config,
    )
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def _clip_record(
    clip_id: str,
    clip_plan_id: str,
    segment: ClipSegment,
    output_ref: Path,
    status: str,
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "clip_plan_id": clip_plan_id,
        "segment_id": segment.segment_id,
        "path": _display_ref(output_ref),
        "status": status,
        "start_sec": segment.start_sec,
        "end_sec": segment.end_sec,
        "duration_sec": segment.end_sec - segment.start_sec,
        "ffmpeg_command": [str(item) for item in result.args],
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _failed_clip(clip_plan_id: str, path: str, error: str, clip_id: str = "") -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "clip_plan_id": clip_plan_id,
        "path": path,
        "status": "failed",
        "error": error,
    }


def _manifest(
    status: str,
    clips: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    passed_clips = [clip for clip in clips if clip.get("status") in {"succeeded", "passed"}]
    return {
        "status": status,
        "clip_count": len(passed_clips),
        "clips": clips,
        "errors": errors,
        "manifest_path": REAL_SLICE_MANIFEST,
    }


def _manifest_status(clips: list[dict[str, Any]], errors: list[str]) -> str:
    if not errors:
        return "succeeded"
    if any(clip.get("status") in {"succeeded", "passed"} for clip in clips):
        return "partial_failed"
    return "failed"


def _ffmpeg_error(clip_id: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        return f"{clip_id}: ffmpeg_failed_exit_{result.returncode}: {detail}"
    return f"{clip_id}: ffmpeg_failed_exit_{result.returncode}"


def _display_ref(path: str | Path) -> str:
    return str(path).replace("\\", "/")
