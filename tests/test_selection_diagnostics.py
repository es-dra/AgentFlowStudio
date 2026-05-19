from __future__ import annotations

from narratocut.candidate_sop import build_selection_diagnostics


def test_selection_diagnostics_flags_near_miss_and_rejection_pressure() -> None:
    score_report = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source": "phase14_2c_candidate_scoring",
        "candidate_count": 5,
        "selected_count": 2,
        "candidates": [
            _candidate("cand_001", "selected", 0.44, 0.44, 0.0, 5.0, ["strong_hook"], []),
            _candidate("cand_002", "selected", 0.40, 0.40, 20.0, 25.0, ["duration_fit"], []),
            _candidate("cand_003", "rejected", 0.42, 0.42, 40.0, 45.0, ["strong_hook"], ["selection_limit"]),
            _candidate("cand_004", "rejected", 0.39, 0.39, 20.5, 25.5, [], ["overlap"]),
            _candidate("cand_005", "rejected", 0.18, 0.18, 21.0, 26.0, [], ["duplicate_source_window"]),
        ],
    }

    diagnostics = build_selection_diagnostics(score_report)

    assert diagnostics["status"] == "succeeded"
    assert diagnostics["candidate_count"] == 5
    assert diagnostics["selected_count"] == 2
    assert diagnostics["rejection_reason_counts"] == {
        "selection_limit": 1,
        "overlap": 1,
        "duplicate_source_window": 1,
    }
    assert diagnostics["selected_score_range"] == {"min": 0.4, "max": 0.44}
    assert diagnostics["score_gaps"]["best_rejected_gap_to_selected_floor"] == -0.02
    assert [item["candidate_id"] for item in diagnostics["near_misses"]] == ["cand_003", "cand_004"]
    assert "near_miss_rejected" in _warning_codes(diagnostics)
    assert "duplicate_source_window_pressure" in _warning_codes(diagnostics)


def test_selection_diagnostics_summarizes_boundary_and_position_distribution() -> None:
    score_report = {
        "schema_version": "0.1",
        "status": "succeeded",
        "candidate_count": 4,
        "selected_count": 3,
        "candidates": [
            _candidate("cand_001", "selected", 0.3, 0.3, 0.0, 5.0, [], [], boundary_strategy="audio_boundary_refined"),
            _candidate("cand_002", "selected", 0.29, 0.29, 5.5, 10.5, [], [], boundary_strategy="audio_boundary_refined"),
            _candidate("cand_003", "selected", 0.28, 0.28, 9.0, 14.0, [], [], boundary_strategy="elastic_duration_split"),
            _candidate("cand_004", "rejected", 0.15, 0.15, 50.0, 55.0, [], ["selection_limit"], boundary_strategy="native_transcript_window"),
        ],
    }

    diagnostics = build_selection_diagnostics(score_report)

    assert diagnostics["boundary_strategy_counts"] == {
        "audio_boundary_refined": 2,
        "elastic_duration_split": 1,
        "native_transcript_window": 1,
    }
    assert diagnostics["selected_position_counts"] == {"early": 3}
    assert "selection_clustered" in _warning_codes(diagnostics)
    assert "few_strong_hooks" in _warning_codes(diagnostics)


def _candidate(
    candidate_id: str,
    decision: str,
    total_score: float,
    selection_score: float,
    start_sec: float,
    end_sec: float,
    reasons: list[str],
    rejection_reasons: list[str],
    *,
    boundary_strategy: str = "elastic_duration_split",
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "decision": decision,
        "total_score": total_score,
        "selection_score": selection_score,
        "start_sec": start_sec,
        "end_sec": end_sec,
        "duration_sec": end_sec - start_sec,
        "text": f"{candidate_id} text",
        "reasons": reasons,
        "rejection_reasons": rejection_reasons,
        "score_breakdown": {
            "hook_strength": 0.7 if "strong_hook" in reasons else 0.1,
            "on_screen_hook_strength": 0.0,
        },
        "source_candidate": {
            "evidence": {
                "boundary_strategy": boundary_strategy,
            }
        },
    }


def _warning_codes(diagnostics: dict[str, object]) -> set[str]:
    warnings = diagnostics["warnings"]
    assert isinstance(warnings, list)
    return {str(item["code"]) for item in warnings if isinstance(item, dict)}
