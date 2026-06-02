from __future__ import annotations

import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.harness.inspection import inspect_run
from agentflow_studio.harness.reviewer import review_run
from agentflow_studio.subtitle_sop import build_subtitle_export, transcript_to_srt
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine import load_workflow


WORKFLOW = Path("workflows/transcript_to_subtitles.yaml")


def test_transcript_to_subtitles_workflow_definition_is_export_only() -> None:
    workflow = load_workflow(WORKFLOW)

    assert workflow.mode == "transcript_to_subtitles"
    assert workflow.quality_profile == "subtitle_export"
    step_types = [step.type for step in workflow.steps]
    assert step_types == ["load_transcript", "write_subtitles"]
    forbidden_fragments = [
        "assemble",
        "concat",
        "burn",
        "ffmpeg",
        "bgm",
        "cover",
        "transition",
        "remote_asr",
        "openai",
        "multimodal",
    ]
    assert not any(fragment in step for step in step_types for fragment in forbidden_fragments)


def test_srt_export_formats_transcript_timestamps() -> None:
    transcript = _transcript_payload()

    srt = transcript_to_srt(transcript)
    export = build_subtitle_export(transcript, subtitle_path="subtitles.srt")

    assert "1\n00:00:01,234 --> 00:00:04,500\nOpen with a concrete problem." in srt
    assert "2\n00:00:04,500 --> 00:01:02,006\nShow the turnaround." in srt
    assert export.manifest.status == "succeeded"
    assert export.manifest.subtitle_path == "subtitles.srt"
    assert export.manifest.segment_count == 2
    assert [cue.segment_id for cue in export.manifest.cues] == ["seg_001", "seg_002"]


def test_transcript_to_subtitles_workflow_writes_subtitle_artifacts(tmp_path) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "subtitle_run"

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    for artifact in [
        "subtitles.srt",
        "subtitle_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]:
        assert (output_dir / artifact).is_file()

    subtitle_manifest = json.loads((output_dir / "subtitle_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    srt = (output_dir / "subtitles.srt").read_text(encoding="utf-8")

    assert subtitle_manifest["status"] == "succeeded"
    assert subtitle_manifest["format"] == "srt"
    assert subtitle_manifest["subtitle_path"] == "subtitles.srt"
    assert subtitle_manifest["source_transcript_id"] == "demo_subtitle_transcript"
    assert subtitle_manifest["segment_count"] == 2
    assert "00:00:01,234 --> 00:00:04,500" in srt
    assert run_manifest["workflow_mode"] == "transcript_to_subtitles"
    assert run_manifest["quality_profile"] == "subtitle_export"

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    section_names = {section["name"] for section in review["sections"]}
    assert "subtitle_outputs" in section_names


def test_transcript_to_subtitles_records_non_monotonic_segments(tmp_path) -> None:
    input_path = _write_input_bundle(tmp_path, transcript=_non_monotonic_transcript_payload())
    output_dir = tmp_path / "subtitle_run"

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    subtitle_manifest = json.loads((output_dir / "subtitle_manifest.json").read_text(encoding="utf-8"))
    assert subtitle_manifest["status"] == "failed"
    assert "subtitle_segments_not_monotonic" in subtitle_manifest["errors"]
    assert not (output_dir / "subtitles.srt").exists()

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "fail"
    assert review["status"] == "failed"


def test_subtitle_review_fails_when_manifest_succeeds_but_srt_missing(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "run",
            "workflow": "workflows/transcript_to_subtitles.yaml",
            "workflow_mode": "transcript_to_subtitles",
            "quality_profile": "subtitle_export",
            "artifacts": {
                "subtitle_manifest": "subtitle_manifest.json",
                "subtitles": "subtitles.srt",
            },
        },
    )
    write_json(run_dir / "manifest.json", {"run_id": "run", "status": "success"})
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "write_subtitles", "status": "success"}]})
    write_json(
        run_dir / "subtitle_manifest.json",
        {
            "status": "succeeded",
            "format": "srt",
            "subtitle_path": "subtitles.srt",
            "source_transcript_id": "demo_subtitle_transcript",
            "source_video": None,
            "language": "en",
            "segment_count": 1,
            "duration_sec": 1.0,
            "cues": [
                {
                    "index": 1,
                    "segment_id": "seg_001",
                    "start_time": 0.0,
                    "end_time": 1.0,
                    "start_timestamp": "00:00:00,000",
                    "end_timestamp": "00:00:01,000",
                    "text": "Missing SRT file.",
                }
            ],
            "errors": [],
            "warnings": [],
            "manifest_path": "subtitle_manifest.json",
        },
    )

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "fail"
    assert review["status"] == "failed"
    subtitle_section = next(section for section in review["sections"] if section["name"] == "subtitle_outputs")
    failed_ids = {check["id"] for check in subtitle_section["checks"] if check["status"] == "failed"}
    assert "subtitle_file_exists" in failed_ids


def _write_input_bundle(tmp_path: Path, transcript: dict | None = None) -> Path:
    transcript_path = tmp_path / "transcript.json"
    write_json(transcript_path, transcript or _transcript_payload())
    input_path = tmp_path / "transcript_to_subtitles_input.json"
    write_json(input_path, {"transcript_path": str(transcript_path)})
    return input_path


def _transcript_payload() -> dict:
    return {
        "transcript_id": "demo_subtitle_transcript",
        "source_video": "data/raw/demo.mp4",
        "language": "en",
        "duration": 62.006,
        "segments": [
            {
                "segment_id": "seg_001",
                "start_time": 1.234,
                "end_time": 4.5,
                "text": "Open with a concrete problem.",
            },
            {
                "segment_id": "seg_002",
                "start_time": 4.5,
                "end_time": 62.006,
                "text": "Show the turnaround.",
            },
        ],
        "metadata": {},
    }


def _non_monotonic_transcript_payload() -> dict:
    payload = _transcript_payload()
    payload["segments"][1]["start_time"] = 3.0
    payload["segments"][1]["end_time"] = 5.0
    return payload
