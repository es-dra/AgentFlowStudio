from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_store import safe_id


LOCAL_PATH_PATTERN = re.compile(r"([a-zA-Z]:\\|/Users/|/home/|data/processed/runs)")
SAFE_PREVIEW_URL_PATTERN = re.compile(
    r"^/projects/([a-zA-Z0-9_.-]+)/(?:"
    r"image-assets/[a-zA-Z0-9_.-]+/preview|"
    r"keyframe-generations/[a-zA-Z0-9_.-]+/candidates/[a-zA-Z0-9_.-]+/preview|"
    r"video-generations/[a-zA-Z0-9_.-]+/candidates/[a-zA-Z0-9_.-]+/preview"
    r")$"
)


def safe_preview_url(value: Any, *, project_id: str | None = None) -> str:
    if value in {None, ""}:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    match = SAFE_PREVIEW_URL_PATTERN.fullmatch(text)
    if not match:
        raise ValueError("studio state previewUrl must be a safe Runtime preview route")
    if project_id is not None and match.group(1) != safe_id(project_id):
        raise ValueError("studio state previewUrl must belong to the current project")
    return text


def safe_node_preview_url(value: Any, *, node_type: str, project_id: str | None = None) -> str:
    text = safe_preview_url(value, project_id=project_id)
    if not text:
        return ""
    if node_type == "video" and "/video-generations/" not in text:
        return ""
    return text


__all__ = ("LOCAL_PATH_PATTERN", "safe_node_preview_url", "safe_preview_url")
