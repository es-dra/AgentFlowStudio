from __future__ import annotations

from pathlib import Path

from narratocut.package_sop import write_package_report
from narratocut.utils import write_json


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
