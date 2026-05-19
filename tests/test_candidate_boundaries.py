from __future__ import annotations

from narratocut.candidate_sop.boundaries import elastic_time_windows


def test_elastic_time_windows_balances_long_source_window() -> None:
    windows = elastic_time_windows(
        0.0,
        13.2,
        min_duration_sec=4.0,
        max_duration_sec=6.0,
        target_window_sec=5.0,
    )

    assert windows == [
        (0.0, 4.4, "elastic_duration_split"),
        (4.4, 8.8, "elastic_duration_split"),
        (8.8, 13.2, "elastic_duration_split"),
    ]


def test_elastic_time_windows_trims_unsplittable_overlong_source_window() -> None:
    windows = elastic_time_windows(
        0.0,
        7.2,
        min_duration_sec=4.0,
        max_duration_sec=6.0,
        target_window_sec=5.0,
    )

    assert windows == [(0.0, 5.0, "elastic_duration_trim")]
