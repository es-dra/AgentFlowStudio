from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentflow_studio.utils import write_json


ASSEMBLY_PLAN = "assembly_plan.json"
CONCAT_LIST = "concat_list.txt"
FINAL_VIDEO = "final_video.mp4"
FINAL_VIDEO_MANIFEST = "final_video_manifest.json"


@dataclass(frozen=True)
class AssemblyConfig:
    ffmpeg_executable: str = "ffmpeg"
    output_name: str = FINAL_VIDEO
    overwrite: bool = True

    def __post_init__(self) -> None:
        if not self.ffmpeg_executable.strip():
            raise ValueError("ffmpeg_executable must not be empty.")
        output_path = Path(self.output_name)
        if not self.output_name.strip() or output_path.is_absolute() or ".." in output_path.parts:
            raise ValueError("output_name must be a safe relative file name.")
        if output_path.name != self.output_name:
            raise ValueError("output_name must not include directories.")


def build_assembly_plan(
    real_slice_manifest: dict[str, Any],
    *,
    source_manifest_path: str | Path,
    output_name: str = FINAL_VIDEO,
) -> dict[str, Any]:
    clips = [
        _plan_clip(clip)
        for clip in real_slice_manifest.get("clips", [])
        if isinstance(clip, dict) and clip.get("status") in {"succeeded", "passed"}
    ]
    return {
        "schema_version": "0.1",
        "source_manifest_path": _display_ref(source_manifest_path),
        "source_video": real_slice_manifest.get("source_video"),
        "output_name": output_name,
        "target_duration_sec": sum(float(clip.get("duration_sec") or 0) for clip in clips),
        "clip_count": len(clips),
        "clips": clips,
        "assembly_options": {
            "method": "ffmpeg_concat_demuxer",
        },
    }


def concat_clips(
    assembly_plan: dict[str, Any],
    *,
    source_run_dir: str | Path,
    output_dir: str | Path,
    config: AssemblyConfig | None = None,
) -> dict[str, Any]:
    resolved_config = config or AssemblyConfig(output_name=str(assembly_plan.get("output_name") or FINAL_VIDEO))
    source_root = Path(source_run_dir)
    root = Path(output_dir)
    output_ref = resolved_config.output_name
    final_video_path = root / output_ref

    clips = assembly_plan.get("clips")
    if not isinstance(clips, list) or not clips:
        manifest = _manifest("failed", output_ref, assembly_plan, errors=["assembly_plan_has_no_clips"])
        return _write_manifest(root, manifest)

    unsafe = [str(clip.get("path") or "") for clip in clips if not _is_safe_relative_path(str(clip.get("path") or ""))]
    if unsafe:
        manifest = _manifest(
            "failed",
            output_ref,
            assembly_plan,
            errors=[f"unsafe_clip_path: {path}" for path in unsafe],
        )
        return _write_manifest(root, manifest)

    missing = [
        str(clip.get("path") or "")
        for clip in clips
        if not (source_root / str(clip.get("path") or "")).is_file()
    ]
    if missing:
        manifest = _manifest(
            "failed",
            output_ref,
            assembly_plan,
            errors=[f"input_clip_missing: {path}" for path in missing],
        )
        return _write_manifest(root, manifest)

    concat_list = root / CONCAT_LIST
    _write_concat_list(concat_list, source_root, clips)
    command = build_ffmpeg_concat_command(concat_list, final_video_path, resolved_config)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        manifest = _manifest(
            "failed",
            output_ref,
            assembly_plan,
            errors=[f"ffmpeg_executable_not_found: {resolved_config.ffmpeg_executable}"],
            command=command,
        )
        return _write_manifest(root, manifest)
    except OSError as exc:
        manifest = _manifest(
            "failed",
            output_ref,
            assembly_plan,
            errors=[f"ffmpeg_execution_failed: {exc}"],
            command=command,
        )
        return _write_manifest(root, manifest)

    if result.returncode != 0:
        manifest = _manifest(
            "failed",
            output_ref,
            assembly_plan,
            errors=[_ffmpeg_error(result)],
            command=command,
            result=result,
        )
        return _write_manifest(root, manifest)

    manifest = _manifest("succeeded", output_ref, assembly_plan, command=command, result=result)
    return _write_manifest(root, manifest)


def build_ffmpeg_concat_command(
    concat_list: str | Path,
    output_video: str | Path,
    config: AssemblyConfig | None = None,
) -> list[str]:
    resolved_config = config or AssemblyConfig()
    overwrite_flag = "-y" if resolved_config.overwrite else "-n"
    return [
        resolved_config.ffmpeg_executable,
        overwrite_flag,
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(Path(concat_list)),
        "-c",
        "copy",
        str(Path(output_video)),
    ]


def _plan_clip(clip: dict[str, Any]) -> dict[str, Any]:
    return {
        "clip_id": clip.get("clip_id"),
        "source_clip_id": clip.get("clip_id"),
        "path": _display_ref(str(clip.get("path") or "")),
        "start_sec": clip.get("start_sec"),
        "end_sec": clip.get("end_sec"),
        "duration_sec": clip.get("duration_sec"),
    }


def _write_concat_list(path: Path, source_root: Path, clips: list[dict[str, Any]]) -> None:
    lines = []
    for clip in clips:
        clip_path = (source_root / str(clip.get("path") or "")).resolve()
        lines.append(f"file '{_escape_concat_path(clip_path)}'")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return bool(value.strip()) and not path.is_absolute() and ".." not in path.parts


def _manifest(
    status: str,
    final_video: str,
    assembly_plan: dict[str, Any],
    *,
    errors: list[str] | None = None,
    command: list[str] | None = None,
    result: subprocess.CompletedProcess[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "final_video": _display_ref(final_video),
        "input_clip_count": int(assembly_plan.get("clip_count") or 0),
        "input_clips": [clip.get("path") for clip in assembly_plan.get("clips", []) if isinstance(clip, dict)],
        "duration_sec": assembly_plan.get("target_duration_sec"),
        "ffmpeg_command": [str(item) for item in command] if command else [],
        "returncode": result.returncode if result else None,
        "stdout": result.stdout if result else "",
        "stderr": result.stderr if result else "",
        "errors": errors or [],
        "warnings": [],
        "manifest_path": FINAL_VIDEO_MANIFEST,
    }


def _write_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    write_json(root / FINAL_VIDEO_MANIFEST, manifest)
    return manifest


def _ffmpeg_error(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        return f"ffmpeg_concat_failed_exit_{result.returncode}: {detail}"
    return f"ffmpeg_concat_failed_exit_{result.returncode}"


def _escape_concat_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", r"'\''")


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
