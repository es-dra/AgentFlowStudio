from __future__ import annotations

from typing import Any


DEFAULT_MAX_ADJUSTMENT_SEC = 0.4
DEFAULT_MIN_CONFIDENCE = 0.5


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


def apply_audio_boundary_refinement(
    *,
    start_sec: float,
    end_sec: float,
    source_start_sec: float,
    source_end_sec: float,
    boundary_index: list[dict[str, Any]],
    min_duration_sec: float | None,
    max_duration_sec: float | None,
    max_adjustment_sec: float = DEFAULT_MAX_ADJUSTMENT_SEC,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> dict[str, Any]:
    original_start = round(start_sec, 6)
    original_end = round(end_sec, 6)
    unchanged = {"start_sec": original_start, "end_sec": original_end, "evidence": {}}
    if not boundary_index or max_adjustment_sec <= 0:
        return unchanged

    start = _eligible_boundary(
        _nearest_boundary(start_sec, boundary_index),
        source_start_sec=source_start_sec,
        source_end_sec=source_end_sec,
        max_adjustment_sec=max_adjustment_sec,
        min_confidence=min_confidence,
    )
    end = _eligible_boundary(
        _nearest_boundary(end_sec, boundary_index),
        source_start_sec=source_start_sec,
        source_end_sec=source_end_sec,
        max_adjustment_sec=max_adjustment_sec,
        min_confidence=min_confidence,
    )
    for start_candidate, end_candidate, applied in (
        (start, end, ["start", "end"]),
        (start, None, ["start"]),
        (None, end, ["end"]),
    ):
        refined_start = round(float(start_candidate["time_sec"]), 6) if start_candidate else original_start
        refined_end = round(float(end_candidate["time_sec"]), 6) if end_candidate else original_end
        if not _duration_allowed(
            refined_start,
            refined_end,
            min_duration_sec=min_duration_sec,
            max_duration_sec=max_duration_sec,
        ):
            continue
        applied = [
            key
            for key in applied
            if (key == "start" and start_candidate and refined_start != original_start)
            or (key == "end" and end_candidate and refined_end != original_end)
        ]
        if not applied or (refined_start == original_start and refined_end == original_end):
            continue
        return {
            "start_sec": refined_start,
            "end_sec": refined_end,
            "evidence": {
                "audio_boundary_refinement": {
                    "strategy": "audio_boundary_refined",
                    "original_start_sec": original_start,
                    "original_end_sec": original_end,
                    "refined_start_sec": refined_start,
                    "refined_end_sec": refined_end,
                    "applied": applied,
                    "max_adjustment_sec": max_adjustment_sec,
                    "min_confidence": min_confidence,
                }
            },
        }
    return unchanged


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


def _eligible_boundary(
    boundary: dict[str, Any] | None,
    *,
    source_start_sec: float,
    source_end_sec: float,
    max_adjustment_sec: float,
    min_confidence: float,
) -> dict[str, Any] | None:
    if boundary is None:
        return None
    time_sec = float(boundary["time_sec"])
    if time_sec < source_start_sec or time_sec > source_end_sec:
        return None
    if float(boundary["confidence"]) < min_confidence:
        return None
    if float(boundary["distance_sec"]) > max_adjustment_sec:
        return None
    return boundary


def _duration_allowed(
    start_sec: float,
    end_sec: float,
    *,
    min_duration_sec: float | None,
    max_duration_sec: float | None,
) -> bool:
    duration = round(end_sec - start_sec, 6)
    if duration <= 0:
        return False
    if min_duration_sec is not None and duration < min_duration_sec:
        return False
    if max_duration_sec is not None and duration > max_duration_sec:
        return False
    return True


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
