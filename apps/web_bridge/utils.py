from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def display_ref(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def duration_ms(started_at: Any, ended_at: Any) -> int | None:
    if started_at is None or ended_at is None:
        return None
    return max(0, round((ended_at - started_at).total_seconds() * 1000))


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def safe_stem(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value).strip("_") or "workflow"


def value_from(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key)
    return str(value) if value is not None else default
