from __future__ import annotations

import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.schemas import ClipPlan, HighlightPlan, ROISettings, Transcript, VideoMetadata
from narratocut.slicing_sop import validate_clip_plan
from narratocut.workflow_engine import load_workflow


VIDEO_TO_HIGHLIGHT_CLIP_PLAN_REAL_ASR_WORKFLOW = Path("workflows/video_to_highlight_clip_plan_real_asr.yaml")


def test_video_to_highlight_clip_plan_real_asr_workflow_definition_composes_real_asr_with_phase10() -> None:
    workflow = load_workflow(VIDEO_TO_HIGHLIGHT_CLIP_PLAN_REAL_ASR_WORKFLOW)

    assert workflow.mode == "video_to_highlight_clip_plan_real_asr"
    assert workflow.quality_profile == "real_asr_highlight_clip_plan"
    assert [step.type for step in workflow.steps] == [
        "load_video",
        "extract_audio",
        "transcribe_audio_openai_compatible",
        "write_transcript",
        "load_roi_config",
        "detect_highlights",
        "rank_highlights_by_roi",
        "generate_clip_plan_from_highlights",
        "write_highlight_plan",
        "write_clip_plan",
    ]
    assert "transcribe_audio_mock" not in {step.type for step in workflow.steps}
    assert "real_slice_video" not in {step.type for step in workflow.steps}


def test_video_to_highlight_clip_plan_real_asr_workflow_writes_transcript_highlight_and_clip_plan(
    tmp_path,
    monkeypatch,
) -> None:
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")
    roi_path = tmp_path / "roi_config.json"
    roi_path.write_text(json.dumps(_roi_payload()), encoding="utf-8")
    input_path = tmp_path / "video_to_highlight_clip_plan_real_asr_input.json"
    input_path.write_text(
        json.dumps(
            {
                "video_path": str(source_video),
                "audio_extraction_mode": "mock",
                "asr_base_url": "https://example.test/v1",
                "asr_model": "fake-asr",
                "asr_api_key": "fake-key",
                "roi_config_path": str(roi_path),
                "language": "en",
                "max_highlights": 3,
            }
        ),
        encoding="utf-8",
    )

    def fake_transcribe(self, audio_artifact, *, language=None):
        return Transcript.model_validate(_transcript_payload(source_video=audio_artifact.source_video))

    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_ASR", "true")
    monkeypatch.setattr(
        "narratocut.workflow_engine.transcription_nodes.OpenAICompatibleASRProvider.transcribe",
        fake_transcribe,
    )
    output_dir = tmp_path / "run"

    status, _ = run_workflow_from_cli(
        workflow_path=VIDEO_TO_HIGHLIGHT_CLIP_PLAN_REAL_ASR_WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    assert (output_dir / "audio_manifest.json").is_file()
    assert (output_dir / "transcript.json").is_file()
    assert (output_dir / "highlight_plan.json").is_file()
    assert (output_dir / "clip_plan.json").is_file()
    assert not (output_dir / "real_slice_manifest.json").exists()
    assert not (output_dir / "clips").exists()

    transcript = Transcript.model_validate(json.loads((output_dir / "transcript.json").read_text(encoding="utf-8")))
    highlight_plan = HighlightPlan.model_validate(
        json.loads((output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    )
    clip_plan = ClipPlan.model_validate(json.loads((output_dir / "clip_plan.json").read_text(encoding="utf-8")))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert transcript.metadata["asr_provider"] == "openai_compatible"
    assert highlight_plan.input_mode == "timestamped_transcript"
    assert all("ranking_factors" in highlight.metadata for highlight in highlight_plan.highlights)
    assert all(highlight.source_segment_ids for highlight in highlight_plan.highlights)
    assert len(clip_plan.segments) == len(highlight_plan.highlights)
    assert clip_plan.segments[0].metadata["highlight_id"] == highlight_plan.highlights[0].highlight_id
    assert clip_plan.segments[0].metadata["source_segment_ids"]
    assert clip_plan.segments[0].metadata["ranking_factors"]["final_score"] >= 0
    assert run_manifest["workflow_mode"] == "video_to_highlight_clip_plan_real_asr"
    assert run_manifest["quality_profile"] == "real_asr_highlight_clip_plan"
    assert run_manifest["artifacts"]["transcript"] == "transcript.json"
    assert run_manifest["artifacts"]["highlight_plan"] == "highlight_plan.json"
    assert run_manifest["artifacts"]["clip_plan"] == "clip_plan.json"

    report = validate_clip_plan(
        clip_plan,
        ROISettings.model_validate(_roi_payload()),
        VideoMetadata(
            file_path=str(source_video),
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


def test_video_to_highlight_clip_plan_real_asr_workflow_fails_without_remote_asr_opt_in(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_ASR", raising=False)
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")
    roi_path = tmp_path / "roi_config.json"
    roi_path.write_text(json.dumps(_roi_payload()), encoding="utf-8")
    input_path = tmp_path / "video_to_highlight_clip_plan_real_asr_input.json"
    input_path.write_text(
        json.dumps(
            {
                "video_path": str(source_video),
                "audio_extraction_mode": "mock",
                "asr_base_url": "https://example.test/v1",
                "asr_model": "fake-asr",
                "asr_api_key": "fake-key",
                "roi_config_path": str(roi_path),
                "max_highlights": 3,
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "run"

    status, _ = run_workflow_from_cli(
        workflow_path=VIDEO_TO_HIGHLIGHT_CLIP_PLAN_REAL_ASR_WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert status == "failed"
    assert "NARRATOCUT_ALLOW_REMOTE_ASR" in manifest["error"]
    assert (output_dir / "audio_manifest.json").is_file()
    assert not (output_dir / "transcript.json").exists()
    assert not (output_dir / "highlight_plan.json").exists()
    assert not (output_dir / "clip_plan.json").exists()


def _transcript_payload(*, source_video: str) -> dict[str, object]:
    return {
        "transcript_id": "real_asr_highlight_transcript",
        "source_video": source_video,
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
                "text": "Once the transcript is stable, highlight detection and clip planning can reuse existing workflow contracts.",
                "speaker": "speaker_1",
                "confidence": 0.97,
                "metadata": {},
            },
            {
                "segment_id": "seg_003",
                "start_time": 8.0,
                "end_time": 12.0,
                "text": "Validate the story before spending time on real slicing, subtitles, or final assembly.",
                "speaker": "speaker_1",
                "confidence": 0.96,
                "metadata": {},
            },
        ],
        "metadata": {
            "asr_provider": "openai_compatible",
        },
    }


def _roi_payload() -> dict[str, object]:
    return {
        "target_platform": "douyin",
        "target_audience": "product builders",
        "content_goal": "increase_completion_rate",
        "min_clip_duration": 1,
        "max_clip_duration": 30,
        "target_clip_count": 3,
        "min_clip_count": 1,
        "max_clip_count": 5,
        "risk_tolerance": "low",
        "priority": ["hook_strength", "clarity", "watch_completion"],
        "validation_policy": "advisory",
    }
