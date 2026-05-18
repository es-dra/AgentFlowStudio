from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from narratocut.utils import write_json


SUBTITLE_BURN_MANIFEST = "subtitle_burn_manifest.json"
SUBTITLED_VIDEO = "final_video_with_subtitles.mp4"


@dataclass(frozen=True)
class SubtitleBurnConfig:
    ffmpeg_executable: str = "ffmpeg"
    output_name: str = SUBTITLED_VIDEO
    overwrite: bool = True

    def __post_init__(self) -> None:
        if not self.ffmpeg_executable.strip():
            raise ValueError("ffmpeg_executable must not be empty.")
        output_path = Path(self.output_name)
        if not self.output_name.strip() or output_path.is_absolute() or ".." in output_path.parts:
            raise ValueError("output_name must be a safe relative file name.")
        if output_path.name != self.output_name:
            raise ValueError("output_name must not include directories.")


def burn_subtitles_into_video(
    *,
    source_video: str | Path,
    subtitles_path: str | Path,
    output_dir: str | Path,
    config: SubtitleBurnConfig | None = None,
) -> dict[str, Any]:
    resolved_config = config or SubtitleBurnConfig()
    video_path = Path(source_video)
    subtitle_path = Path(subtitles_path)
    root = Path(output_dir)
    output_ref = resolved_config.output_name
    output_path = root / output_ref

    if not video_path.is_file():
        manifest = _manifest(
            "failed",
            source_video=video_path,
            subtitles_path=subtitle_path,
            output_video=output_ref,
            errors=[f"source_video_missing: {_display_ref(video_path)}"],
        )
        return _write_manifest(root, manifest)
    if not subtitle_path.is_file():
        manifest = _manifest(
            "failed",
            source_video=video_path,
            subtitles_path=subtitle_path,
            output_video=output_ref,
            errors=[f"subtitles_missing: {_display_ref(subtitle_path)}"],
        )
        return _write_manifest(root, manifest)

    command = build_ffmpeg_subtitle_burn_command(video_path, subtitle_path, output_path, resolved_config)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            subtitles_path=subtitle_path,
            output_video=output_ref,
            errors=[f"ffmpeg_executable_not_found: {resolved_config.ffmpeg_executable}"],
            command=command,
        )
        return _write_manifest(root, manifest)
    except OSError as exc:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            subtitles_path=subtitle_path,
            output_video=output_ref,
            errors=[f"ffmpeg_execution_failed: {exc}"],
            command=command,
        )
        return _write_manifest(root, manifest)

    if result.returncode != 0:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            subtitles_path=subtitle_path,
            output_video=output_ref,
            errors=[_ffmpeg_error(result)],
            command=command,
            result=result,
        )
        return _write_manifest(root, manifest)

    manifest = _manifest(
        "succeeded",
        source_video=video_path,
        subtitles_path=subtitle_path,
        output_video=output_ref,
        command=command,
        result=result,
    )
    return _write_manifest(root, manifest)


def build_ffmpeg_subtitle_burn_command(
    source_video: str | Path,
    subtitles_path: str | Path,
    output_video: str | Path,
    config: SubtitleBurnConfig | None = None,
) -> list[str]:
    resolved_config = config or SubtitleBurnConfig()
    overwrite_flag = "-y" if resolved_config.overwrite else "-n"
    return [
        resolved_config.ffmpeg_executable,
        overwrite_flag,
        "-i",
        str(Path(source_video)),
        "-vf",
        f"subtitles=filename='{_escape_subtitle_filter_path(Path(subtitles_path))}'",
        "-c:a",
        "copy",
        str(Path(output_video)),
    ]


def _manifest(
    status: str,
    *,
    source_video: str | Path,
    subtitles_path: str | Path,
    output_video: str,
    errors: list[str] | None = None,
    command: list[str] | None = None,
    result: subprocess.CompletedProcess[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "source_video": _display_ref(source_video),
        "subtitles_path": _display_ref(subtitles_path),
        "output_video": _display_ref(output_video),
        "duration_sec": None,
        "width": None,
        "height": None,
        "codec": None,
        "ffmpeg_command": [str(item) for item in command] if command else [],
        "returncode": result.returncode if result else None,
        "stdout": result.stdout if result else "",
        "stderr": result.stderr if result else "",
        "errors": errors or [],
        "warnings": [],
        "manifest_path": SUBTITLE_BURN_MANIFEST,
    }


def _write_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    write_json(root / SUBTITLE_BURN_MANIFEST, manifest)
    return manifest


def _ffmpeg_error(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        return f"ffmpeg_subtitle_burn_failed_exit_{result.returncode}: {detail}"
    return f"ffmpeg_subtitle_burn_failed_exit_{result.returncode}"


def _escape_subtitle_filter_path(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    return value.replace(":", r"\:").replace("'", r"\'")


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
