from __future__ import annotations

import json
from typing import Any


CONTROL_EVENT_FORBIDDEN_PRIVATE_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "data/processed/runs",
    "data/raw/",
    ".mp4",
    ".mov",
    "api_key",
    "access_token",
    "refresh_token",
    "secret_key",
    "client_secret",
    "authorization:",
    "bearer ",
    "cookie=",
    "signed_url",
)


def reject_unsafe_markers(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    markers = tuple(fragment.lower() for fragment in CONTROL_EVENT_FORBIDDEN_PRIVATE_FRAGMENTS) + (
        "provider_raw",
        "raw_provider_response",
        "signed url",
        "generated_media_bytes",
        "data:image/",
    )
    for marker in markers:
        if marker and marker in serialized:
            raise ValueError("control event/register contains unsafe marker")


def required_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"missing required object: {field}")
    return value


def required_text(payload: dict[str, Any], field: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ValueError(f"missing required field: {field}")
    return value


__all__ = ("reject_unsafe_markers", "required_dict", "required_text")
