from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.api.runtime_store import safe_id
from apps.api.runtime_video_constants import SAFE_CANDIDATE_ID, VIDEO_SUFFIX_TYPES


def safe_outputs(output_dir: Path, raw: dict[str, Any]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for index, item in enumerate(raw.get("outputs") or [], start=1):
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("candidate_id") or f"candidate_{index:03d}")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            continue
        path = (output_dir / str(item.get("video_path") or "")).resolve()
        try:
            path.relative_to(output_dir.resolve())
        except ValueError:
            continue
        if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIX_TYPES:
            continue
        outputs.append(
            {
                "candidate_id": candidate_id,
                "byte_count": item.get("byte_count") or path.stat().st_size,
                "sha256": item.get("sha256"),
                "provider_url_persisted": False,
            }
        )
    if outputs:
        return outputs
    candidate_dir = output_dir / "video_candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    fake_path = candidate_dir / "candidate_001.mp4"
    if not fake_path.exists():
        fake_path.write_bytes(b"AFS fake async video candidate")
    return [
        {
            "candidate_id": "candidate_001",
            "byte_count": fake_path.stat().st_size,
            "sha256": None,
            "provider_url_persisted": False,
        }
    ]


def candidate_previews(project_id: str, job_id: str, outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for item in outputs:
        candidate_id = str(item.get("candidate_id") or "")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            continue
        previews.append(
            {
                "candidate_id": candidate_id,
                "preview_url": (
                    f"/projects/{safe_id(project_id)}/video-generations/"
                    f"{safe_id(job_id)}/candidates/{candidate_id}/preview"
                ),
                "byte_count": item.get("byte_count"),
                "sha256": item.get("sha256"),
            }
        )
    return previews


def candidate_file(output_dir: Path, candidate_id: str) -> Path | None:
    video_dir = (output_dir / "video_candidates").resolve()
    root = output_dir.resolve()
    try:
        video_dir.relative_to(root)
    except ValueError:
        return None
    for suffix in VIDEO_SUFFIX_TYPES:
        path = (video_dir / f"{candidate_id}{suffix}").resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.exists() and path.is_file():
            return path
    return None
