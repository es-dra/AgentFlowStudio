from __future__ import annotations

import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.schemas import HighlightPlan
from narratocut.utils import write_json
from narratocut.workflow_engine import load_workflow


OCR_WORKFLOW = Path("workflows/video_subtitle_ocr_to_highlight_plan.yaml")


def test_video_subtitle_ocr_to_highlight_plan_workflow_definition() -> None:
    workflow = load_workflow(OCR_WORKFLOW)

    assert workflow.mode == "ocr_candidate_scoring"
    assert workflow.quality_profile == "candidate_scoring"
    assert [step.type for step in workflow.steps] == [
        "load_video",
        "build_ocr_transcript",
        "write_ocr_transcript",
        "generate_candidate_windows",
        "score_candidate_windows",
        "write_highlight_score_report",
        "write_selection_diagnostics",
        "write_highlight_plan",
    ]


def test_video_subtitle_ocr_to_highlight_plan_workflow_writes_scored_outputs(tmp_path) -> None:
    output_dir = tmp_path / "ocr_scoring"
    video_path = tmp_path / "source.mp4"
    video_path.write_text("placeholder video path for workflow input validation", encoding="utf-8")
    frames_path = tmp_path / "ocr_frames.json"
    write_json(
        frames_path,
        {
            "frames": [
                {"time_sec": 1.0, "text": "90% of creators cut the wrong part", "confidence": 0.91},
                {"time_sec": 1.5, "text": "90% of creators cut the wrong part", "confidence": 0.9},
                {"time_sec": 2.0, "text": "but the real problem is the opening hook", "confidence": 0.87},
                {"time_sec": 4.0, "text": "therefore choose the reversal first", "confidence": 0.88},
            ]
        },
    )
    input_path = tmp_path / "input.json"
    write_json(
        input_path,
        {
            "video_path": str(video_path),
            "ocr_frames_path": str(frames_path),
            "language": "en",
            "frame_interval_sec": 0.5,
            "dedupe_similarity": 0.85,
            "merge_gap_sec": 0.8,
            "min_text_chars": 3,
            "max_window_size": 2,
            "min_duration_sec": 1,
            "max_duration_sec": 12,
            "max_selected": 2,
            "max_overlap_ratio": 0.4,
        },
    )

    status, _ = run_workflow_from_cli(
        workflow_path=OCR_WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    transcript = json.loads((output_dir / "ocr_transcript.json").read_text(encoding="utf-8"))
    candidates = json.loads((output_dir / "candidate_windows.json").read_text(encoding="utf-8"))
    score_report = json.loads((output_dir / "highlight_score_report.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((output_dir / "selection_diagnostics.json").read_text(encoding="utf-8"))
    highlight_plan = HighlightPlan.model_validate(
        json.loads((output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    )

    assert transcript["metadata"]["content_channel"] == "ocr_subtitle"
    assert candidates["content_channel"] == "ocr_subtitle"
    assert score_report["selected_count"] >= 1
    assert diagnostics["status"] == "succeeded"
    assert diagnostics["candidate_count"] == score_report["candidate_count"]
    assert highlight_plan.highlights
    assert highlight_plan.highlights[0].metadata["candidate_id"]
    inspection = __import__("narratocut.harness.inspection", fromlist=["inspect_run"]).inspect_run(output_dir)
    review = __import__("narratocut.harness.reviewer", fromlist=["review_run"]).review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
