from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_store import read_json


def public_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "user_id": str(user.get("user_id", "")),
        "email": str(user.get("email", "")),
        "display_name": str(user.get("display_name", "")),
    }


def read_or_default(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        write_json(path, default)
        return dict(default)
    try:
        payload = read_json(path)
    except (ValueError, OSError):
        payload = dict(default)
    for key, value in default.items():
        payload.setdefault(key, value)
    return payload


__all__ = ("public_user", "read_or_default")
