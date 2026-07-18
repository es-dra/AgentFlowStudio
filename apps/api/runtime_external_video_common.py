from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.api.runtime_store import read_json
from apps.api.runtime_video_constants import REMOTE_TRUE_VALUES, REMOTE_VIDEO_ENV, VIDEO_NON_CLAIMS
from apps.api.runtime_video_manifest import write_json_checked


EXTERNAL_DOWNLOAD_ENV = "AFS_ALLOW_EXTERNAL_DOWNLOAD"
EXTERNAL_VIDEO_ACTION = "external_video_generation"
EXTERNAL_VIDEO_NON_CLAIMS = [
    *VIDEO_NON_CLAIMS,
    "external engine orchestration only",
    "not generated-media QA",
    "not provider smoke unless explicitly run",
]
LIBTV_ACCESS_KEY_ENV = "LIBTV_ACCESS_KEY"
LIBTV_BASE_URL_ENV = "LIBTV_OPENAPI_BASE_URL"
LIBTV_BASE_URL_ENVS = (LIBTV_BASE_URL_ENV, "OPENAPI_IM_BASE", "IM_BASE_URL")
DEFAULT_LIBTV_BASE_URL = "https://im.liblib.tv"
PUBLIC_PREVIEW_MIME = "video/mp4"
SAFE_OUTPUT_ID = "final_video"


def external_download_gate() -> dict[str, str]:
    status = "ready_not_run" if os.environ.get(EXTERNAL_DOWNLOAD_ENV, "").strip().lower() in REMOTE_TRUE_VALUES else "blocked"
    return {"capability": "external_download", "env": EXTERNAL_DOWNLOAD_ENV, "status": status}


def block(block_id: str, reason: str, *, required_gate: str = "") -> dict[str, str]:
    payload = {"block_id": block_id, "reason": safe_text(reason, 180)}
    if required_gate:
        payload["required_gate"] = required_gate
    return payload


def safe_provider_error(error: Exception) -> str:
    text = str(error)
    lowered = text.lower()
    if any(fragment in lowered for fragment in ("api", "key", "secret", "token", "authorization", "bearer", "cookie")):
        return "External video provider configuration is not ready."
    return safe_text(text, 180)


def safe_provider_id(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip())[:160]


def safe_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    text = re.sub(r"https?://\S+", "[url omitted]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?i)\b[a-z]:\\\S+|/(?:home|users|tmp|var|opt|mnt)/\S+", "[path omitted]", text)
    text = re.sub(r"(?i)\.(mp4|mov|webm)\b", "[video]", text)
    text = re.sub(r"(?i)\b(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|secret[_ -]?key|client[_ -]?secret)\b", "[credential]", text)
    return text[:limit]


def write_task_state(output_dir: Path, state: dict[str, Any]) -> None:
    write_json_checked(output_dir / "external_video_task_state.json", state)


def load_task_state(output_dir: Path) -> dict[str, Any]:
    return read_json(output_dir / "external_video_task_state.json")


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = (
    "DEFAULT_LIBTV_BASE_URL",
    "EXTERNAL_DOWNLOAD_ENV",
    "EXTERNAL_VIDEO_ACTION",
    "EXTERNAL_VIDEO_NON_CLAIMS",
    "LIBTV_ACCESS_KEY_ENV",
    "LIBTV_BASE_URL_ENVS",
    "LIBTV_BASE_URL_ENV",
    "PUBLIC_PREVIEW_MIME",
    "REMOTE_VIDEO_ENV",
    "SAFE_OUTPUT_ID",
    "block",
    "external_download_gate",
    "load_task_state",
    "parse_time",
    "safe_provider_error",
    "safe_provider_id",
    "safe_text",
    "utc_now",
    "write_task_state",
)
