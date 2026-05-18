from __future__ import annotations

import json
import subprocess
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratocut.schemas import ClipPlan, HighlightPlan, Transcript, VideoMetadata
from narratocut.utils import write_json
from narratocut.workflow_engine import load_workflow


WORKFLOW = Path("workflows/video_to_real_clips.yaml")


def test_video_to_real_clips_workflow_definition_composes_planning_and_real_slicing() -> None:
    workflow = load_workflow(WORKFLOW)

    assert workflow.mode == "video_to_real_clips"
    assert workflow.quality_profile == "video_real_clips"
    step_types = [step.type for step in workflow.steps]
    assert step_types == [
        "load_video",
        "extract_audio",
        "transcribe_audio_mock",
        "write_transcript",
        "load_roi_config",
        "detect_highlights",
        "rank_highlights_by_roi",
        "generate_clip_plan_from_highlights",
        "write_highlight_plan",
        "write_clip_plan",
        "probe_video_metadata",
        "validate_clip_plan",
        "real_slice_video",
    ]
    forbidden_fragments = ["assemble", "concat", "subtitle", "bgm", "remote_asr", "openai", "multimodal"]
    assert not any(fragment in step for step in step_types for fragment in forbidden_fragments)


def test_video_to_real_clips_workflow_writes_planning_and_real_clip_artifacts(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "run"
    calls: list[list[str]] = []
    _patch_real_tools(monkeypatch, duration_sec=30.0, ffmpeg_calls=calls)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    for artifact in [
        "audio_manifest.json",
        "audio/audio.wav",
        "transcript.json",
        "highlight_plan.json",
        "clip_plan.json",
        "video_metadata.json",
        "clip_plan_validation.json",
        "real_slice_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]:
        assert (output_dir / artifact).is_file()
    assert (output_dir / "clips" / "clip_001.mp4").is_file()

    transcript = Transcript.model_validate(json.loads((output_dir / "transcript.json").read_text(encoding="utf-8")))
    highlight_plan = HighlightPlan.model_validate(
        json.loads((output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    )
    clip_plan = ClipPlan.model_validate(json.loads((output_dir / "clip_plan.json").read_text(encoding="utf-8")))
    slice_manifest = json.loads((output_dir / "real_slice_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert transcript.source_video == str(tmp_path / "input.mp4")
    assert highlight_plan.input_mode == "timestamped_transcript"
    assert len(clip_plan.segments) == len(highlight_plan.highlights)
    assert slice_manifest["status"] == "succeeded"
    assert slice_manifest["clip_count"] == len(clip_plan.segments)
    assert slice_manifest["clips_dir"] == "clips"
    assert all(clip["ffmpeg_command"] for clip in slice_manifest["clips"])
    assert calls
    assert run_manifest["workflow_mode"] == "video_to_real_clips"
    assert run_manifest["quality_profile"] == "video_real_clips"

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "pass"
    artifact_statuses = {item["path"]: item["status"] for item in inspection["artifacts"]}
    assert artifact_statuses["transcript.json"] == "found"
    assert artifact_statuses["highlight_plan.json"] == "found"
    assert artifact_statuses["clip_plan.json"] == "found"
    assert artifact_statuses["real_slice_manifest.json"] == "found"
    assert artifact_statuses["clips/"] == "found"
    assert inspection["quality_report"]["summary"]["quality_profile"] == "video_real_clips"
    assert inspection["quality_report"]["summary"]["real_clips"]["clips"] == len(clip_plan.segments)
    assert review["status"] == "passed"
    section_names = {section["name"] for section in review["sections"]}
    assert {"video_artifacts", "highlight_artifacts", "real_video_outputs"}.issubset(section_names)


def _write_input_bundle(tmp_path: Path) -> Path:
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake video")
    fixture_path = tmp_path / "transcript_fixture.json"
    write_json(fixture_path, _transcript_payload())
    roi_path = tmp_path / "roi_config.json"
    write_json(roi_path, _roi_payload())
    input_path = tmp_path / "video_to_real_clips_input.json"
    write_json(
        input_path,
        {
            "video_path": str(video),
            "asr_fixture_path": str(fixture_path),
            "roi_config_path": str(roi_path),
            "audio_extraction_mode": "mock",
            "input_mode": "timestamped_transcript",
            "language": "en",
            "max_highlights": 2,
            "output_clips_dir": "clips",
        },
    )
    return input_path


def _transcript_payload() -> dict[str, object]:
    return {
        "transcript_id": "demo_video_real_clips_transcript",
        "source_video": None,
        "language": "en",
        "duration": 12.0,
        "segments": [
            {
                "segment_id": "seg_001",
                "start_time": 0.0,
                "end_time": 4.0,
                "text": "Most teams chase automation first, but the real bottleneck is choosing what to cut.",
                "speaker": "speaker_1",
                "confidence": 0.98,
                "metadata": {},
            },
            {
                "segment_id": "seg_002",
                "start_time": 4.0,
                "end_time": 8.0,
                "text": "Once the transcript is stable, clip planning can drive real slicing safely.",
                "speaker": "speaker_1",
                "confidence": 0.97,
                "metadata": {},
            },
            {
                "segment_id": "seg_003",
                "start_time": 8.0,
                "end_time": 12.0,
                "text": "This phase proves the composition without final assembly, subtitles, or BGM.",
                "speaker": "speaker_1",
                "confidence": 0.96,
                "metadata": {},
            },
        ],
        "metadata": {},
    }


def _roi_payload() -> dict[str, object]:
    return {
        "target_platform": "douyin",
        "target_audience": "product builders",
        "content_goal": "increase_completion_rate",
        "min_clip_duration": 1,
        "max_clip_duration": 30,
        "target_clip_count": 2,
        "min_clip_count": 1,
        "max_clip_count": 3,
        "risk_tolerance": "low",
        "priority": ["hook_strength", "clarity", "watch_completion"],
        "validation_policy": "advisory",
    }


def _patch_real_tools(monkeypatch, *, duration_sec: float, ffmpeg_calls: list[list[str]]) -> None:
    def fake_probe(video_path, ffprobe_executable="ffprobe", timeout_sec=30):  # noqa: ANN001, ANN202
        path_text = str(video_path)
        probed_duration = 4.0 if "clip_" in path_text else duration_sec
        return VideoMetadata(
            file_path=str(video_path),
            duration_sec=probed_duration,
            width=1080,
            height=1920,
            codec="h264",
            fps=30,
            bitrate=1000,
            probe_status="succeeded",
        )

    def fake_tool_check(executable="ffmpeg"):  # noqa: ANN001, ANN202
        from narratocut.slicing_sop.ffmpeg_probe import FFmpegInfo

        return FFmpegInfo(
            available=True,
            executable=str(executable),
            version="ffmpeg-test",
            raw_output="ffmpeg-test",
            error=None,
        )

    def fake_run(command, capture_output, text, check):  # noqa: ANN001, ANN202
        ffmpeg_calls.append(command)
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("narratocut.workflow_engine.nodes.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.harness.real_clip_quality.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.workflow_engine.nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr("narratocut.slicing_sop.real_slicer.subprocess.run", fake_run)
