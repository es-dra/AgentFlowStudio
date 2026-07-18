from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

from apps.api.runtime_external_video_models import ExternalVideoJobRequest
from apps.api.runtime_store import RuntimeStore


def external_video_media_path(store: RuntimeStore, project_id: str, job_id: str) -> Path | None:
    path = (store.run_dir(project_id, job_id) / "media" / "final-video.bin").resolve()
    root = store.run_dir(project_id, job_id).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.is_file() else None


def create_replay_video(output_dir: Path, request: ExternalVideoJobRequest) -> Path:
    media_dir = output_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / "final-video.bin"
    duration = max(1, min(int(request.duration_sec), 12))
    width, height = dimensions(request.aspect_ratio)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={width}x{height}:rate=24:duration={duration}",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            str(target),
        ]
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            return target
        except (subprocess.SubprocessError, OSError):
            pass
    target.write_bytes(b"AFS external video replay fixture")
    return target


def download_external_video(url: str, output_dir: Path) -> Path:
    media_dir = output_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / "final-video.bin"
    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
        response.raise_for_status()
        total = 0
        with target.open("wb") as handle:
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                total += len(chunk)
                if total > 250 * 1024 * 1024:
                    raise ValueError("external video exceeded the 250 MB download limit")
                handle.write(chunk)
    if target.stat().st_size <= 0:
        raise ValueError("external video download was empty")
    return target


def output_summary(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"byte_count": path.stat().st_size, "sha256": digest}


def dimensions(aspect_ratio: str) -> tuple[int, int]:
    if str(aspect_ratio).strip() == "16:9":
        return 640, 360
    if str(aspect_ratio).strip() == "1:1":
        return 480, 480
    return 360, 640


__all__ = (
    "create_replay_video",
    "download_external_video",
    "external_video_media_path",
    "output_summary",
)
