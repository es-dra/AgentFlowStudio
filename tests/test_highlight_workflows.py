from __future__ import annotations

import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.schemas import ClipPlan, HighlightPlan, ROISettings, VideoMetadata
from agentflow_studio.slicing_sop import validate_clip_plan
from agentflow_studio.workflow_engine import load_workflow


SCRIPT_WORKFLOW = Path("workflows/script_to_highlight_plan.yaml")
TRANSCRIPT_WORKFLOW = Path("workflows/transcript_to_highlight_clip_plan.yaml")
CANDIDATE_WORKFLOW = Path("workflows/transcript_to_candidate_windows.yaml")


def test_highlight_workflow_definitions_keep_script_and_transcript_boundaries() -> None:
    script = load_workflow(SCRIPT_WORKFLOW)
    transcript = load_workflow(TRANSCRIPT_WORKFLOW)

    assert script.mode == "highlight_detection"
    assert script.quality_profile == "highlight_plan"
    assert [step.type for step in script.steps] == [
        "load_roi_config",
        "load_script",
        "detect_highlights",
        "rank_highlights_by_roi",
        "write_highlight_plan",
    ]
    assert "generate_clip_plan_from_highlights" not in {step.type for step in script.steps}
    assert "write_clip_plan" not in {step.type for step in script.steps}

    assert transcript.mode == "highlight_to_clip_plan"
    assert transcript.quality_profile == "highlight_clip_plan"
    assert [step.type for step in transcript.steps] == [
        "load_roi_config",
        "load_transcript",
        "detect_highlights",
        "rank_highlights_by_roi",
        "generate_clip_plan_from_highlights",
        "write_highlight_plan",
        "write_clip_plan",
    ]


def test_transcript_to_candidate_windows_workflow_definition() -> None:
    workflow = load_workflow(CANDIDATE_WORKFLOW)

    assert workflow.mode == "candidate_windows"
    assert workflow.quality_profile == "candidate_windows"
    assert [step.type for step in workflow.steps] == [
        "load_transcript",
        "generate_candidate_windows",
    ]


def test_transcript_to_candidate_windows_workflow_writes_candidate_manifest(tmp_path) -> None:
    output_dir = tmp_path / "candidate_windows"

    status, _ = run_workflow_from_cli(
        workflow_path=CANDIDATE_WORKFLOW,
        input_path=Path("examples/demo_highlight/transcript_candidate_windows_input.example.json"),
        output_dir=output_dir,
    )

    assert status == "success"
    manifest = json.loads((output_dir / "candidate_windows.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "succeeded"
    assert manifest["candidate_count"] >= 1
    assert manifest["candidates"][0]["segment_ids"]
    assert run_manifest["workflow_mode"] == "candidate_windows"
    assert run_manifest["quality_profile"] == "candidate_windows"
    assert run_manifest["artifacts"]["candidate_windows"] == "candidate_windows.json"


def test_script_highlight_workflow_writes_ranked_highlight_plan_only(tmp_path) -> None:
    output_dir = tmp_path / "demo_highlight_script"

    status, _ = run_workflow_from_cli(
        workflow_path=SCRIPT_WORKFLOW,
        input_path=Path("examples/demo_highlight/script_input.example.json"),
        output_dir=output_dir,
    )

    assert status == "success"
    assert (output_dir / "highlight_plan.json").is_file()
    assert not (output_dir / "clip_plan.json").exists()

    highlight_plan = HighlightPlan.model_validate(
        json.loads((output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    )
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert highlight_plan.input_mode == "script_only"
    assert all(highlight.start_time is None for highlight in highlight_plan.highlights)
    assert all("ranking_factors" in highlight.metadata for highlight in highlight_plan.highlights)
    assert run_manifest["workflow_mode"] == "highlight_detection"
    assert run_manifest["quality_profile"] == "highlight_plan"
    assert run_manifest["artifacts"]["highlight_plan"] == "highlight_plan.json"
    assert "clip_plan" not in run_manifest["artifacts"]


def test_transcript_highlight_workflow_writes_highlight_plan_and_clip_plan(tmp_path) -> None:
    output_dir = tmp_path / "demo_highlight_transcript"

    status, _ = run_workflow_from_cli(
        workflow_path=TRANSCRIPT_WORKFLOW,
        input_path=Path("examples/demo_highlight/transcript_input.example.json"),
        output_dir=output_dir,
    )

    assert status == "success"
    highlight_plan = HighlightPlan.model_validate(
        json.loads((output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    )
    clip_plan = ClipPlan.model_validate(
        json.loads((output_dir / "clip_plan.json").read_text(encoding="utf-8"))
    )
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert highlight_plan.input_mode == "timestamped_transcript"
    assert all("ranking_factors" in highlight.metadata for highlight in highlight_plan.highlights)
    assert len(clip_plan.segments) == len(highlight_plan.highlights)
    assert clip_plan.segments[0].metadata["highlight_id"] == highlight_plan.highlights[0].highlight_id
    assert clip_plan.segments[0].metadata["ranking_factors"]["final_score"] >= 0
    assert run_manifest["workflow_mode"] == "highlight_to_clip_plan"
    assert run_manifest["quality_profile"] == "highlight_clip_plan"
    assert run_manifest["artifacts"]["highlight_plan"] == "highlight_plan.json"
    assert run_manifest["artifacts"]["clip_plan"] == "clip_plan.json"


def test_transcript_workflow_clip_plan_can_pass_phase9_validation(tmp_path) -> None:
    output_dir = tmp_path / "demo_highlight_transcript"
    status, _ = run_workflow_from_cli(
        workflow_path=TRANSCRIPT_WORKFLOW,
        input_path=Path("examples/demo_highlight/transcript_input.example.json"),
        output_dir=output_dir,
    )
    assert status == "success"
    clip_plan = ClipPlan.model_validate(
        json.loads((output_dir / "clip_plan.json").read_text(encoding="utf-8"))
    )

    report = validate_clip_plan(
        clip_plan,
        ROISettings(
            target_platform="douyin",
            target_audience="product builders",
            content_goal="increase_completion_rate",
            min_clip_duration=1,
            max_clip_duration=30,
        ),
        VideoMetadata(
            file_path="input.mp4",
            duration_sec=120,
            width=1080,
            height=1920,
            codec="h264",
            fps=30,
            bitrate=1000,
            probe_status="succeeded",
        ),
        ffmpeg_available=True,
    )

    assert report.status == "passed"
