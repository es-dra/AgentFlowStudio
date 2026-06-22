from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any


def now_epoch() -> float:
    return time.time()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_from_epoch(value: Any) -> str | None:
    seconds = _float_or_none(value)
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def epoch_from_iso(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def elapsed_seconds(start: Any, end: Any | None = None) -> int | None:
    start_seconds = _epoch_seconds(start)
    if start_seconds is None:
        return None
    end_seconds = _epoch_seconds(end) if end is not None else now_epoch()
    if end_seconds is None:
        return None
    return max(0, int(round(end_seconds - start_seconds)))


def compact_timing(
    *,
    created_at: Any = None,
    started_at: Any = None,
    completed_at: Any = None,
) -> dict[str, Any]:
    timing: dict[str, Any] = {}
    created_epoch = _epoch_seconds(created_at)
    started_epoch = _epoch_seconds(started_at)
    completed_epoch = _epoch_seconds(completed_at)
    if created_epoch is not None:
        timing["created_at"] = iso_from_epoch(created_epoch)
        timing["elapsed_sec"] = elapsed_seconds(created_epoch, completed_epoch)
    if started_epoch is not None:
        timing["started_at"] = iso_from_epoch(started_epoch)
        timing["running_sec"] = elapsed_seconds(started_epoch, completed_epoch)
        if created_epoch is not None:
            timing["queued_sec"] = elapsed_seconds(created_epoch, started_epoch)
    if completed_epoch is not None:
        timing["completed_at"] = iso_from_epoch(completed_epoch)
    return {key: value for key, value in timing.items() if value is not None}


def _epoch_seconds(value: Any) -> float | None:
    if value is None:
        return None
    direct = _float_or_none(value)
    if direct is not None:
        return direct
    return epoch_from_iso(value)


def _float_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


__all__ = ("compact_timing", "elapsed_seconds", "epoch_from_iso", "iso_from_epoch", "now_epoch", "now_iso")
