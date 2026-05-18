from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from narratocut.utils import write_json


AUDIO_MIX_MANIFEST = "audio_mix_manifest.json"
BGM_VIDEO = "final_video_with_bgm.mp4"


@dataclass(frozen=True)
class BGMMixConfig:
    ffmpeg_executable: str = "ffmpeg"
    output_name: str = BGM_VIDEO
    bgm_volume: float = 0.2
    original_audio_volume: float = 1.0
    overwrite: bool = True

    def __post_init__(self) -> None:
        if not self.ffmpeg_executable.strip():
            raise ValueError("ffmpeg_executable must not be empty.")
        output_path = Path(self.output_name)
        if not self.output_name.strip() or output_path.is_absolute() or ".." in output_path.parts:
            raise ValueError("output_name must be a safe relative file name.")
        if output_path.name != self.output_name:
            raise ValueError("output_name must not include directories.")
        if self.bgm_volume < 0:
            raise ValueError("bgm_volume must be greater than or equal to 0.")
        if self.original_audio_volume < 0:
            raise ValueError("original_audio_volume must be greater than or equal to 0.")


def mix_bgm_into_video(
    *,
    source_video: str | Path,
    bgm_audio: str | Path,
    output_dir: str | Path,
    config: BGMMixConfig | None = None,
) -> dict[str, Any]:
    resolved_config = config or BGMMixConfig()
    video_path = Path(source_video)
    bgm_path = Path(bgm_audio)
    root = Path(output_dir)
    output_ref = resolved_config.output_name
    output_path = root / output_ref

    if not video_path.is_file():
        manifest = _manifest(
            "failed",
            source_video=video_path,
            bgm_path=bgm_path,
            output_video=output_ref,
            config=resolved_config,
            errors=[f"source_video_missing: {_display_ref(video_path)}"],
        )
        return _write_manifest(root, manifest)
    if not bgm_path.is_file():
        manifest = _manifest(
            "failed",
            source_video=video_path,
            bgm_path=bgm_path,
            output_video=output_ref,
            config=resolved_config,
            errors=[f"bgm_missing: {_display_ref(bgm_path)}"],
        )
        return _write_manifest(root, manifest)

    command = build_ffmpeg_bgm_mix_command(video_path, bgm_path, output_path, resolved_config)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            bgm_path=bgm_path,
            output_video=output_ref,
            config=resolved_config,
            errors=[f"ffmpeg_executable_not_found: {resolved_config.ffmpeg_executable}"],
            command=command,
        )
        return _write_manifest(root, manifest)
    except OSError as exc:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            bgm_path=bgm_path,
            output_video=output_ref,
            config=resolved_config,
            errors=[f"ffmpeg_execution_failed: {exc}"],
            command=command,
        )
        return _write_manifest(root, manifest)

    if result.returncode != 0:
        manifest = _manifest(
            "failed",
            source_video=video_path,
            bgm_path=bgm_path,
            output_video=output_ref,
            config=resolved_config,
            errors=[_ffmpeg_error(result)],
            command=command,
            result=result,
        )
        return _write_manifest(root, manifest)

    if not output_path.is_file():
        manifest = _manifest(
            "failed",
            source_video=video_path,
            bgm_path=bgm_path,
            output_video=output_ref,
            config=resolved_config,
            errors=[f"bgm_mix_output_missing: {_display_ref(output_ref)}"],
            command=command,
            result=result,
        )
        return _write_manifest(root, manifest)

    manifest = _manifest(
        "succeeded",
        source_video=video_path,
        bgm_path=bgm_path,
        output_video=output_ref,
        config=resolved_config,
        command=command,
        result=result,
    )
    return _write_manifest(root, manifest)


def build_ffmpeg_bgm_mix_command(
    source_video: str | Path,
    bgm_audio: str | Path,
    output_video: str | Path,
    config: BGMMixConfig | None = None,
) -> list[str]:
    resolved_config = config or BGMMixConfig()
    overwrite_flag = "-y" if resolved_config.overwrite else "-n"
    filter_complex = (
        f"[0:a]volume={resolved_config.original_audio_volume:g}[a0];"
        f"[1:a]volume={resolved_config.bgm_volume:g}[a1];"
        "[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]"
    )
    return [
        resolved_config.ffmpeg_executable,
        overwrite_flag,
        "-i",
        str(Path(source_video)),
        "-stream_loop",
        "-1",
        "-i",
        str(Path(bgm_audio)),
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(Path(output_video)),
    ]


def _manifest(
    status: str,
    *,
    source_video: str | Path,
    bgm_path: str | Path,
    output_video: str,
    config: BGMMixConfig,
    errors: list[str] | None = None,
    command: list[str] | None = None,
    result: subprocess.CompletedProcess[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "source_video": _display_ref(source_video),
        "bgm_path": _display_ref(bgm_path),
        "output_video": _display_ref(output_video),
        "bgm_volume": config.bgm_volume,
        "original_audio_volume": config.original_audio_volume,
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
        "manifest_path": AUDIO_MIX_MANIFEST,
    }


def _write_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    write_json(root / AUDIO_MIX_MANIFEST, manifest)
    return manifest


def _ffmpeg_error(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        return f"ffmpeg_bgm_mix_failed_exit_{result.returncode}: {detail}"
    return f"ffmpeg_bgm_mix_failed_exit_{result.returncode}"


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
