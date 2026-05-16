from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class FFmpegInfo:
    available: bool
    executable: str | None
    version: str | None
    raw_output: str | None
    error: str | None


def check_ffmpeg_available(executable: str = "ffmpeg") -> FFmpegInfo:
    """Probe whether an FFmpeg executable is callable without requiring it."""
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
            error=f"FFmpeg executable not found: {executable}",
        )
    except subprocess.TimeoutExpired:
        return FFmpegInfo(
            available=False,
            executable=executable,
            version=None,
            raw_output=None,
            error=f"FFmpeg check timed out after 5 seconds: {executable}",
        )
    except OSError as exc:
        return FFmpegInfo(
            available=False,
            executable=executable,
            version=None,
            raw_output=None,
            error=f"FFmpeg check failed: {exc}",
        )

    raw_output = _combined_output(result.stdout, result.stderr)
    if result.returncode != 0:
        return FFmpegInfo(
            available=False,
            executable=executable,
            version=None,
            raw_output=raw_output,
            error=f"ffmpeg -version failed with exit code {result.returncode}",
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
