from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from narratocut.schemas import VideoMetadata


def probe_video_metadata(
    video_path: str | Path,
    ffprobe_executable: str = "ffprobe",
    timeout_sec: int = 30,
) -> VideoMetadata:
    source = Path(video_path)
    if not source.is_file():
        return VideoMetadata(
            file_path=_display_ref(source),
            probe_status="missing",
            errors=[f"input_video_missing: {_display_ref(source)}"],
        )

    command = [
        ffprobe_executable,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(source),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except FileNotFoundError:
        return _failed_metadata(source, f"ffprobe_unavailable: {ffprobe_executable}")
    except subprocess.TimeoutExpired:
        return _failed_metadata(source, f"ffprobe_timeout: {timeout_sec}s")
    except OSError as exc:
        return _failed_metadata(source, f"ffprobe_failed: {exc}")

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        return _failed_metadata(source, f"ffprobe_exit_{result.returncode}{suffix}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return _failed_metadata(source, f"ffprobe_invalid_json: {exc}")

    return parse_ffprobe_video_metadata(source, payload)


def parse_ffprobe_video_metadata(
    video_path: str | Path,
    payload: dict[str, Any],
) -> VideoMetadata:
    video_stream = _first_video_stream(payload)
    format_info = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    duration = _optional_float(format_info.get("duration"))
    bitrate = _optional_int(format_info.get("bit_rate"))

    if video_stream is None:
        return VideoMetadata(
            file_path=_display_ref(video_path),
            duration_sec=duration,
            bitrate=bitrate,
            probe_status="failed",
            errors=["video_stream_missing"],
        )

    return VideoMetadata(
        file_path=_display_ref(video_path),
        duration_sec=duration,
        width=_optional_int(video_stream.get("width")),
        height=_optional_int(video_stream.get("height")),
        codec=_optional_str(video_stream.get("codec_name")),
        fps=_parse_rate(video_stream.get("r_frame_rate")),
        bitrate=bitrate,
        probe_status="succeeded",
    )


def _first_video_stream(payload: dict[str, Any]) -> dict[str, Any] | None:
    streams = payload.get("streams")
    if not isinstance(streams, list):
        return None
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == "video":
            return stream
    return None


def _failed_metadata(path: Path, error: str) -> VideoMetadata:
    return VideoMetadata(
        file_path=_display_ref(path),
        probe_status="failed",
        errors=[error],
    )


def _parse_rate(value: object) -> float | None:
    if not isinstance(value, str) or not value or value == "0/0":
        return None
    if "/" not in value:
        return _optional_float(value)
    numerator, denominator = value.split("/", 1)
    top = _optional_float(numerator)
    bottom = _optional_float(denominator)
    if top is None or bottom in (None, 0):
        return None
    return top / bottom


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _display_ref(path: str | Path) -> str:
    return str(path).replace("\\", "/")
