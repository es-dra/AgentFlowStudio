from __future__ import annotations

from pathlib import Path

from agentflow_studio.package_sop import write_package_report
from agentflow_studio.utils import write_json


def test_package_report_documents_elastic_clip_boundary_evidence(tmp_path: Path) -> None:
    run_dir = _write_base_package_run(tmp_path, final_duration=18.0)
    _write_clip_plan(run_dir, start_sec=0.0, end_sec=4.4, candidate_id="cand_001")
    _write_score_report(
        run_dir,
        {
            "candidate_id": "cand_001",
            "decision": "selected",
            "total_score": 0.82,
            "reasons": ["strong_hook", "duration_fit"],
            "source_candidate": {
                "evidence": {
                    "boundary_strategy": "elastic_duration_split",
                    "target_duration_sec": 5.0,
                    "source_window_start_sec": 0.0,
                    "source_window_end_sec": 13.2,
                }
            },
        },
    )

    write_package_report(run_dir)

    report_text = (run_dir / "package_report.md").read_text(encoding="utf-8")
    assert "- Boundary: elastic_duration_split" in report_text
    assert "- Target duration: 5.00s" in report_text
    assert "- Source window: 0.00s - 13.20s" in report_text


def test_package_report_documents_native_clip_boundary_when_no_split_evidence(tmp_path: Path) -> None:
    run_dir = _write_base_package_run(tmp_path, final_duration=4.8)
    _write_clip_plan(run_dir, start_sec=3.0, end_sec=7.8, candidate_id="cand_001")
    _write_score_report(
        run_dir,
        {
            "candidate_id": "cand_001",
            "decision": "selected",
            "total_score": 0.78,
            "reasons": ["duration_fit"],
            "source_candidate": {"source": "transcript_window", "evidence": {"window_size": 1}},
        },
    )

    write_package_report(run_dir)

    report_text = (run_dir / "package_report.md").read_text(encoding="utf-8")
    assert "- Boundary: native_transcript_window" in report_text
    assert "- Target duration: not applicable" in report_text
    assert "- Source window: 3.00s - 7.80s" in report_text


def test_package_report_documents_audio_boundary_evidence(tmp_path: Path) -> None:
    run_dir = _write_base_package_run(tmp_path, final_duration=4.8)
    _write_clip_plan(run_dir, start_sec=2.2, end_sec=5.9, candidate_id="cand_001")
    _write_score_report(
        run_dir,
        {
            "candidate_id": "cand_001",
            "decision": "selected",
            "total_score": 0.77,
            "reasons": ["duration_fit"],
            "source_candidate": {
                "evidence": {
                    "audio_boundary": {
                        "source": "boundary_signal_manifest.json",
                        "start": {
                            "time_sec": 2.0,
                            "kind": "silence_end",
                            "confidence": 0.93,
                            "distance_sec": 0.2,
                        },
                        "end": {
                            "time_sec": 6.0,
                            "kind": "silence_start",
                            "confidence": 0.88,
                            "distance_sec": 0.1,
                        },
                    }
                }
            },
        },
    )

    write_package_report(run_dir)

    report_text = (run_dir / "package_report.md").read_text(encoding="utf-8")
    assert (
        "- Audio boundary: start 2.00s silence_end (0.20s away, conf 0.93); "
        "end 6.00s silence_start (0.10s away, conf 0.88)"
    ) in report_text


def test_package_report_marks_distant_audio_boundary_as_not_nearby(tmp_path: Path) -> None:
    run_dir = _write_base_package_run(tmp_path, final_duration=4.8)
    _write_clip_plan(run_dir, start_sec=2.2, end_sec=5.9, candidate_id="cand_001")
    _write_score_report(
        run_dir,
        {
            "candidate_id": "cand_001",
            "decision": "selected",
            "total_score": 0.77,
            "reasons": ["duration_fit"],
            "source_candidate": {
                "evidence": {
                    "audio_boundary": {
                        "source": "boundary_signal_manifest.json",
                        "start": {
                            "time_sec": 31.0,
                            "kind": "silence_start",
                            "confidence": 0.99,
                            "distance_sec": 28.8,
                        },
                        "end": {
                            "time_sec": 31.0,
                            "kind": "silence_start",
                            "confidence": 0.99,
                            "distance_sec": 25.1,
                        },
                    }
                }
            },
        },
    )

    write_package_report(run_dir)

    report_text = (run_dir / "package_report.md").read_text(encoding="utf-8")
    assert "- Audio boundary: not nearby" in report_text
    assert "28.80s away" not in report_text


def test_package_report_documents_audio_boundary_refinement(tmp_path: Path) -> None:
    run_dir = _write_base_package_run(tmp_path, final_duration=4.1)
    _write_clip_plan(run_dir, start_sec=2.0, end_sec=6.1, candidate_id="cand_001")
    _write_score_report(
        run_dir,
        {
            "candidate_id": "cand_001",
            "decision": "selected",
            "total_score": 0.79,
            "reasons": ["duration_fit"],
            "source_candidate": {
                "evidence": {
                    "boundary_strategy": "audio_boundary_refined",
                    "base_boundary_strategy": "elastic_duration_split",
                    "audio_boundary_refinement": {
                        "strategy": "audio_boundary_refined",
                        "original_start_sec": 1.8,
                        "original_end_sec": 6.3,
                        "refined_start_sec": 2.0,
                        "refined_end_sec": 6.1,
                        "applied": ["start", "end"],
                        "max_adjustment_sec": 0.4,
                        "min_confidence": 0.5,
                    },
                }
            },
        },
    )

    write_package_report(run_dir)

    report_text = (run_dir / "package_report.md").read_text(encoding="utf-8")
    assert "- Boundary: audio_boundary_refined" in report_text
    assert "- Base boundary: elastic_duration_split" in report_text
    assert "- Audio refinement: 1.80s - 6.30s -> 2.00s - 6.10s (start, end)" in report_text


def test_package_report_summarizes_selection_diagnostics(tmp_path: Path) -> None:
    run_dir = _write_base_package_run(tmp_path, final_duration=18.0)
    _write_clip_plan(run_dir, start_sec=0.0, end_sec=4.4, candidate_id="cand_001")
    _write_score_report(
        run_dir,
        {
            "candidate_id": "cand_001",
            "decision": "selected",
            "total_score": 0.42,
            "reasons": ["duration_fit"],
            "source_candidate": {"source": "transcript_window", "evidence": {"window_size": 1}},
        },
    )
    write_json(
        run_dir / "selection_diagnostics.json",
        {
            "schema_version": "0.1",
            "status": "succeeded",
            "candidate_count": 4,
            "selected_count": 1,
            "selected_score_range": {"min": 0.42, "max": 0.42},
            "score_gaps": {"best_rejected_gap_to_selected_floor": -0.01},
            "near_misses": [{"candidate_id": "cand_002", "selection_score": 0.41, "rejection_reasons": ["selection_limit"]}],
            "rejection_reason_counts": {"selection_limit": 2},
            "boundary_strategy_counts": {"native_transcript_window": 4},
            "selected_position_counts": {"early": 1},
            "warnings": [{"code": "near_miss_rejected", "message": "A rejected candidate was close to the selected floor."}],
        },
    )

    write_package_report(run_dir)

    report_text = (run_dir / "package_report.md").read_text(encoding="utf-8")
    assert "## Selection Diagnostics" in report_text
    assert "- Candidates: 4 total, 1 selected" in report_text
    assert "- Selected score range: 0.420 - 0.420" in report_text
    assert "- Top near miss: `cand_002` score 0.410 (selection_limit)" in report_text
    assert "- Warnings: near_miss_rejected" in report_text


def _write_base_package_run(tmp_path: Path, *, final_duration: float) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    final_video = tmp_path / "final_video.mp4"
    final_video.write_bytes(b"fake final video")
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "run",
            "workflow": "workflows/final_video_package.yaml",
            "workflow_mode": "final_video_package",
            "quality_profile": "finished_package",
            "artifacts": {"finished_package_manifest": "finished_package_manifest.json"},
        },
    )
    write_json(run_dir / "final_video_manifest.json", {"status": "succeeded", "duration_sec": final_duration})
    write_json(
        run_dir / "finished_package_manifest.json",
        {
            "schema_version": "0.1",
            "status": "succeeded",
            "package_id": "pkg",
            "primary_video": {"role": "final_video", "path": str(final_video), "required": True, "exists": True},
            "assets": [{"role": "final_video", "path": str(final_video), "required": True, "exists": True}],
            "errors": [],
            "warnings": [],
            "manifest_path": "finished_package_manifest.json",
        },
    )
    return run_dir


def _write_clip_plan(run_dir: Path, *, start_sec: float, end_sec: float, candidate_id: str) -> None:
    write_json(
        run_dir / "clip_plan.json",
        {
            "segments": [
                {
                    "segment_id": "seg_001",
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "text": "Selected short transcript window.",
                    "metadata": {"candidate_id": candidate_id},
                }
            ]
        },
    )


def _write_score_report(run_dir: Path, candidate: dict[str, object]) -> None:
    write_json(run_dir / "highlight_score_report.json", {"candidates": [candidate]})
