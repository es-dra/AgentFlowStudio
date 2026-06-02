from __future__ import annotations

import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.schemas import Transcript
from agentflow_studio.workflow_engine import load_workflow


VIDEO_TO_TRANSCRIPT_WORKFLOW = Path("workflows/video_to_transcript.yaml")


def test_video_to_transcript_workflow_definition_stays_narrow() -> None:
    workflow = load_workflow(VIDEO_TO_TRANSCRIPT_WORKFLOW)

    assert workflow.mode == "video_to_transcript"
    assert workflow.quality_profile == "mock_asr_transcript"
    assert [step.type for step in workflow.steps] == [
        "load_video",
        "extract_audio",
        "transcribe_audio_mock",
        "write_transcript",
    ]
    assert "detect_highlights" not in {step.type for step in workflow.steps}
    assert "generate_clip_plan_from_highlights" not in {step.type for step in workflow.steps}


def test_video_to_transcript_workflow_writes_transcript_only(tmp_path) -> None:
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")
    fixture_path = tmp_path / "transcript_fixture.json"
    fixture_path.write_text(json.dumps(_transcript_payload()), encoding="utf-8")
    input_path = tmp_path / "video_to_transcript_input.json"
    input_path.write_text(
        json.dumps(
            {
                "video_path": str(source_video),
                "asr_fixture_path": str(fixture_path),
                "audio_extraction_mode": "mock",
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "run"

    status, _ = run_workflow_from_cli(
        workflow_path=VIDEO_TO_TRANSCRIPT_WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    assert (output_dir / "audio_manifest.json").is_file()
    assert (output_dir / "audio" / "audio.wav").is_file()
    assert (output_dir / "transcript.json").is_file()
    assert not (output_dir / "highlight_plan.json").exists()
    assert not (output_dir / "clip_plan.json").exists()

    transcript = Transcript.model_validate(json.loads((output_dir / "transcript.json").read_text(encoding="utf-8")))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert transcript.source_video == str(source_video)
    assert transcript.metadata["asr_provider"] == "mock"
    assert transcript.metadata["audio_path"] == "audio/audio.wav"
    assert run_manifest["workflow_mode"] == "video_to_transcript"
    assert run_manifest["quality_profile"] == "mock_asr_transcript"
    assert run_manifest["artifacts"]["audio_manifest"] == "audio_manifest.json"
    assert run_manifest["artifacts"]["transcript"] == "transcript.json"
    assert "highlight_plan" not in run_manifest["artifacts"]
    assert "clip_plan" not in run_manifest["artifacts"]


def _transcript_payload() -> dict[str, object]:
    return {
        "transcript_id": "demo_video_transcript",
        "source_video": None,
        "language": "en",
        "duration": 7.0,
        "segments": [
            {
                "segment_id": "seg_001",
                "start_time": 0.0,
                "end_time": 3.5,
                "text": "A real product workflow should expose every intermediate artifact.",
                "speaker": "speaker_1",
                "confidence": 0.98,
                "metadata": {},
            },
            {
                "segment_id": "seg_002",
                "start_time": 3.5,
                "end_time": 7.0,
                "text": "The transcript is the bridge between video input and highlight planning.",
                "speaker": "speaker_1",
                "confidence": 0.97,
                "metadata": {},
            },
        ],
        "metadata": {},
    }
