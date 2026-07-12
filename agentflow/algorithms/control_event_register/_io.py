from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._validation import validate_active_pending_register, validate_control_event


def load_control_event_log(path: str | Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError(f"control event line {line_number} must be a JSON object")
        validate_control_event(event)
        events.append(event)
    return events


def append_control_event(path: str | Path, event: dict[str, Any]) -> None:
    validate_control_event(event)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def load_materialized_control_register(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("control register fixture must be a JSON object")
    validate_active_pending_register(payload)
    return payload


def write_materialized_control_register(path: str | Path, register: dict[str, Any]) -> None:
    validate_active_pending_register(register)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(register, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = (
    "append_control_event",
    "load_control_event_log",
    "load_materialized_control_register",
    "write_materialized_control_register",
)
