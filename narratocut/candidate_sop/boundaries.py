from __future__ import annotations

import math


BoundaryWindow = tuple[float, float, str]


def elastic_time_windows(
    start_sec: float,
    end_sec: float,
    *,
    min_duration_sec: float | None,
    max_duration_sec: float,
    target_window_sec: float | None,
) -> list[BoundaryWindow]:
    total_duration = round(end_sec - start_sec, 6)
    if total_duration <= 0:
        return []
    if total_duration <= max_duration_sec:
        if min_duration_sec is None or total_duration >= min_duration_sec:
            return [(round(start_sec, 6), round(end_sec, 6), "elastic_duration_split")]
        return []

    target = min(target_window_sec or max_duration_sec, max_duration_sec)
    min_duration = min_duration_sec or 0.0
    if min_duration > 0 and total_duration < min_duration * 2:
        trimmed_end = round(min(start_sec + target, end_sec), 6)
        return [(round(start_sec, 6), trimmed_end, "elastic_duration_trim")]

    count = _window_count_for_duration(
        total_duration,
        min_duration_sec=min_duration,
        max_duration_sec=max_duration_sec,
        target_window_sec=target,
    )
    duration = total_duration / count
    windows: list[BoundaryWindow] = []
    for index in range(count):
        window_start = round(start_sec + duration * index, 6)
        window_end = round(start_sec + duration * (index + 1), 6)
        if index == count - 1:
            window_end = round(end_sec, 6)
        windows.append((window_start, window_end, "elastic_duration_split"))
    return windows


def _window_count_for_duration(
    duration_sec: float,
    *,
    min_duration_sec: float,
    max_duration_sec: float,
    target_window_sec: float,
) -> int:
    min_count = max(1, math.ceil(duration_sec / max_duration_sec))
    max_count = max(min_count, math.floor(duration_sec / min_duration_sec)) if min_duration_sec > 0 else min_count
    best_count = min_count
    best_distance = float("inf")
    for count in range(min_count, max_count + 1):
        candidate_duration = duration_sec / count
        if min_duration_sec > 0 and candidate_duration < min_duration_sec:
            continue
        if candidate_duration > max_duration_sec:
            continue
        distance = abs(candidate_duration - target_window_sec)
        if distance < best_distance:
            best_distance = distance
            best_count = count
    return best_count
