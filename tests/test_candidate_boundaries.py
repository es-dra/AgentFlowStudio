from __future__ import annotations

from narratocut.candidate_sop.audio_boundaries import apply_audio_boundary_refinement
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


def test_audio_boundary_refinement_moves_to_nearby_confident_boundaries() -> None:
    result = apply_audio_boundary_refinement(
        start_sec=1.8,
        end_sec=6.3,
        source_start_sec=1.5,
        source_end_sec=6.5,
        boundary_index=[
            {"time_sec": 2.0, "kind": "silence_end", "confidence": 0.93, "source": "boundary_signal_manifest.json"},
            {"time_sec": 6.1, "kind": "silence_start", "confidence": 0.88, "source": "boundary_signal_manifest.json"},
        ],
        min_duration_sec=4.0,
        max_duration_sec=6.0,
        max_adjustment_sec=0.4,
        min_confidence=0.5,
    )

    assert result["start_sec"] == 2.0
    assert result["end_sec"] == 6.1
    assert result["evidence"]["audio_boundary_refinement"] == {
        "strategy": "audio_boundary_refined",
        "original_start_sec": 1.8,
        "original_end_sec": 6.3,
        "refined_start_sec": 2.0,
        "refined_end_sec": 6.1,
        "applied": ["start", "end"],
        "max_adjustment_sec": 0.4,
        "min_confidence": 0.5,
    }


def test_audio_boundary_refinement_refuses_duration_violating_adjustment() -> None:
    result = apply_audio_boundary_refinement(
        start_sec=1.8,
        end_sec=5.9,
        source_start_sec=1.5,
        source_end_sec=6.2,
        boundary_index=[
            {"time_sec": 2.2, "kind": "silence_end", "confidence": 0.9, "source": "boundary_signal_manifest.json"},
            {"time_sec": 5.7, "kind": "silence_start", "confidence": 0.9, "source": "boundary_signal_manifest.json"},
        ],
        min_duration_sec=4.0,
        max_duration_sec=6.0,
        max_adjustment_sec=0.5,
        min_confidence=0.5,
    )

    assert result["start_sec"] == 1.8
    assert result["end_sec"] == 5.9
    assert "audio_boundary_refinement" not in result["evidence"]


def test_audio_boundary_refinement_ignores_low_confidence_or_distant_boundaries() -> None:
    result = apply_audio_boundary_refinement(
        start_sec=1.8,
        end_sec=6.1,
        source_start_sec=1.5,
        source_end_sec=6.4,
        boundary_index=[
            {"time_sec": 2.0, "kind": "silence_end", "confidence": 0.4, "source": "boundary_signal_manifest.json"},
            {"time_sec": 5.3, "kind": "silence_start", "confidence": 0.9, "source": "boundary_signal_manifest.json"},
        ],
        min_duration_sec=4.0,
        max_duration_sec=6.0,
        max_adjustment_sec=0.4,
        min_confidence=0.5,
    )

    assert result["start_sec"] == 1.8
    assert result["end_sec"] == 6.1
    assert "audio_boundary_refinement" not in result["evidence"]
