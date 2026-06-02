from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentflow_studio.utils import write_json


COVER_MANIFEST = "cover_manifest.json"
COVER_IMAGE = "cover.jpg"


@dataclass(frozen=True)
class CoverExportConfig:
    ffmpeg_executable: str = "ffmpeg"
    output_name: str = COVER_IMAGE
    cover_time_sec: float = 1.0
    overwrite: bool = True
    quality: int = 2

    def __post_init__(self) -> None:
        if not self.ffmpeg_executable.strip():
            raise ValueError("ffmpeg_executable must not be empty.")
        output_path = Path(self.output_name)
        if not self.output_name.strip() or output_path.is_absolute() or ".." in output_path.parts:
            raise ValueError("output_name must be a safe relative file name.")
        if output_path.name != self.output_name:
            raise ValueError("output_name must not include directories.")
        if self.cover_time_sec < 0:
            raise ValueError("cover_time_sec must be greater than or equal to 0.")
        if self.quality < 1:
            raise ValueError("quality must be greater than or equal to 1.")


def export_cover_from_video(
    *,
    source_video: str | Path,
    output_dir: str | Path,
    config: CoverExportConfig | None = None,
) -> dict[str, Any]:
    resolved_config = config or CoverExportConfig()
    video_path = Path(source_video)
    root = Path(output_dir)
    output_ref = resolved_config.output_name
    output_path = root / output_ref

    if not video_path.is_file():
        manifest = _manifest(
            "failed",
            source_video=video_path,
            cover_path=output_ref,
            cover_time_sec=resolved_config.cover_time_sec,
            errors=[f"source_video_missing: {_display_ref(video_path)}"],
        )
        return _write_manifest(root, manifest)

    command = build_ffmpeg_cover_export_command(video_path, output_path, resolved_config)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            cover_path=output_ref,
            cover_time_sec=resolved_config.cover_time_sec,
            errors=[f"ffmpeg_executable_not_found: {resolved_config.ffmpeg_executable}"],
            command=command,
        )
        return _write_manifest(root, manifest)
    except OSError as exc:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            cover_path=output_ref,
            cover_time_sec=resolved_config.cover_time_sec,
            errors=[f"ffmpeg_execution_failed: {exc}"],
            command=command,
        )
        return _write_manifest(root, manifest)

    if result.returncode != 0:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            cover_path=output_ref,
            cover_time_sec=resolved_config.cover_time_sec,
            errors=[_ffmpeg_error(result)],
            command=command,
            result=result,
        )
        return _write_manifest(root, manifest)

    if not output_path.is_file():
        manifest = _manifest(
            "failed",
            source_video=video_path,
            cover_path=output_ref,
            cover_time_sec=resolved_config.cover_time_sec,
            errors=[f"cover_output_missing: {_display_ref(output_ref)}"],
            command=command,
            result=result,
        )
        return _write_manifest(root, manifest)

    manifest = _manifest(
        "succeeded",
        source_video=video_path,
        cover_path=output_ref,
        cover_time_sec=resolved_config.cover_time_sec,
        command=command,
        result=result,
    )
    return _write_manifest(root, manifest)


def build_ffmpeg_cover_export_command(
    source_video: str | Path,
    output_image: str | Path,
    config: CoverExportConfig | None = None,
) -> list[str]:
    resolved_config = config or CoverExportConfig()
    overwrite_flag = "-y" if resolved_config.overwrite else "-n"
    return [
        resolved_config.ffmpeg_executable,
        overwrite_flag,
        "-ss",
        f"{resolved_config.cover_time_sec:g}",
        "-i",
        str(Path(source_video)),
        "-frames:v",
        "1",
        "-update",
        "1",
        "-q:v",
        str(resolved_config.quality),
        str(Path(output_image)),
    ]


def _manifest(
    status: str,
    *,
    source_video: str | Path,
    cover_path: str,
    cover_time_sec: float,
    errors: list[str] | None = None,
    command: list[str] | None = None,
    result: subprocess.CompletedProcess[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "source_video": _display_ref(source_video),
        "cover_path": _display_ref(cover_path),
        "cover_time_sec": cover_time_sec,
        "ffmpeg_command": [str(item) for item in command] if command else [],
        "returncode": result.returncode if result else None,
        "stdout": result.stdout if result else "",
        "stderr": result.stderr if result else "",
        "errors": errors or [],
        "warnings": [],
        "manifest_path": COVER_MANIFEST,
    }


def _write_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    write_json(root / COVER_MANIFEST, manifest)
    return manifest


def _ffmpeg_error(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        return f"ffmpeg_cover_export_failed_exit_{result.returncode}: {detail}"
    return f"ffmpeg_cover_export_failed_exit_{result.returncode}"


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
