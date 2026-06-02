from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FFmpegInfo:
    available: bool
    executable: str | None
    version: str | None
    raw_output: str | None
    error: str | None


@dataclass(frozen=True)
class MediaToolPaths:
    ffmpeg: str
    ffprobe: str


@dataclass(frozen=True)
class MediaToolsInfo:
    status: str
    ffmpeg: FFmpegInfo
    ffprobe: FFmpegInfo

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "ffmpeg_available": self.ffmpeg.available,
            "ffprobe_available": self.ffprobe.available,
            "ffmpeg_executable": self.ffmpeg.executable,
            "ffprobe_executable": self.ffprobe.executable,
            "ffmpeg_version": self.ffmpeg.version,
            "ffprobe_version": self.ffprobe.version,
            "warnings": self.warnings,
        }

    @property
    def warnings(self) -> list[str]:
        warnings: list[str] = []
        if self.ffmpeg.error:
            warnings.append(self.ffmpeg.error)
        if self.ffprobe.error:
            warnings.append(self.ffprobe.error)
        return warnings


def resolve_media_tool_paths(
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
    config_path: str | Path | None = None,
) -> MediaToolPaths:
    config = _load_config(config_path)
    return MediaToolPaths(
        ffmpeg=_first_non_empty(
            ffmpeg,
            _env("NCUT_FFMPEG_PATH"),
            config.get("ffmpeg_path"),
            "ffmpeg",
        ),
        ffprobe=_first_non_empty(
            ffprobe,
            _env("NCUT_FFPROBE_PATH"),
            config.get("ffprobe_path"),
            "ffprobe",
        ),
    )


def check_media_tools(
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
    config_path: str | Path | None = None,
) -> MediaToolsInfo:
    paths = resolve_media_tool_paths(ffmpeg=ffmpeg, ffprobe=ffprobe, config_path=config_path)
    ffmpeg_info = check_ffmpeg_available(paths.ffmpeg)
    ffprobe_info = _check_executable(paths.ffprobe, "FFprobe")
    status = "ready" if ffmpeg_info.available and ffprobe_info.available else "unavailable"
    return MediaToolsInfo(status=status, ffmpeg=ffmpeg_info, ffprobe=ffprobe_info)


def check_ffmpeg_available(executable: str = "ffmpeg") -> FFmpegInfo:
    """Probe whether an FFmpeg executable is callable without requiring it."""
    return _check_executable(executable, "FFmpeg")


def _check_executable(executable: str, label: str) -> FFmpegInfo:
    try:
        result = subprocess.run(
            [executable, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError:
        return FFmpegInfo(
            available=False,
            executable=executable,
            version=None,
            raw_output=None,
            error=f"{label} executable not found: {executable}",
        )
    except subprocess.TimeoutExpired:
        return FFmpegInfo(
            available=False,
            executable=executable,
            version=None,
            raw_output=None,
            error=f"{label} check timed out after 5 seconds: {executable}",
        )
    except OSError as exc:
        return FFmpegInfo(
            available=False,
            executable=executable,
            version=None,
            raw_output=None,
            error=f"{label} check failed: {exc}",
        )

    raw_output = _combined_output(result.stdout, result.stderr)
    if result.returncode != 0:
        return FFmpegInfo(
            available=False,
            executable=executable,
            version=None,
            raw_output=raw_output,
            error=f"{executable} -version failed with exit code {result.returncode}",
        )

    return FFmpegInfo(
        available=True,
        executable=executable,
        version=_extract_version(raw_output),
        raw_output=raw_output,
        error=None,
    )


def _combined_output(stdout: str | None, stderr: str | None) -> str:
    return "\n".join(part for part in [stdout or "", stderr or ""] if part).strip()


def _extract_version(raw_output: str) -> str | None:
    for line in raw_output.splitlines():
        text = line.strip()
        if text:
            return text
    return None


def _load_config(config_path: str | Path | None) -> dict[str, str | None]:
    path = Path(config_path) if config_path is not None else Path("configs/ffmpeg.yaml")
    if not path.is_file():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {
        "ffmpeg_path": _optional_str(payload.get("ffmpeg_path")),
        "ffprobe_path": _optional_str(payload.get("ffprobe_path")),
    }


def _env(name: str) -> str | None:
    import os

    return _optional_str(os.environ.get(name))


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    raise ValueError("at least one executable value is required")


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
