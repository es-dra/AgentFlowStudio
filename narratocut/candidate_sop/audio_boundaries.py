from __future__ import annotations

from typing import Any


def build_boundary_index(boundary_signal_manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(boundary_signal_manifest, dict) or boundary_signal_manifest.get("status") != "succeeded":
        return []
    manifest_path = str(boundary_signal_manifest.get("manifest_path") or "boundary_signal_manifest.json")
    points = boundary_signal_manifest.get("boundary_points")
    if not isinstance(points, list):
        return []
    indexed: list[dict[str, Any]] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        time_sec = _optional_float(point.get("time_sec"))
        if time_sec is None:
            continue
        indexed.append(
            {
                "time_sec": time_sec,
                "kind": str(point.get("kind") or "boundary"),
                "confidence": _optional_float(point.get("confidence")) or 0.0,
                "source": manifest_path,
            }
        )
    return indexed


def nearest_audio_boundary_evidence(
    *,
    start_sec: float,
    end_sec: float,
    boundary_index: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not boundary_index:
        return None
    start = _nearest_boundary(start_sec, boundary_index)
    end = _nearest_boundary(end_sec, boundary_index)
    if start is None and end is None:
        return None
    source = (start or end or {}).get("source") or "boundary_signal_manifest.json"
    return {
        "source": source,
        "start": start,
        "end": end,
    }


def _nearest_boundary(target_sec: float, boundary_index: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not boundary_index:
        return None
    nearest = min(boundary_index, key=lambda point: abs(float(point["time_sec"]) - target_sec))
    return {
        "time_sec": round(float(nearest["time_sec"]), 6),
        "kind": str(nearest["kind"]),
        "confidence": round(float(nearest["confidence"]), 6),
        "distance_sec": round(abs(float(nearest["time_sec"]) - target_sec), 6),
    }


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
