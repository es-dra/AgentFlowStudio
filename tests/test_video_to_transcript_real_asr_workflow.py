from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.audio_sop import AudioArtifact
from narratocut.schemas import Transcript
from narratocut.workflow_engine import load_workflow
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.workflow_engine.transcription_nodes import transcribe_audio_openai_compatible_node


VIDEO_TO_TRANSCRIPT_REAL_ASR_WORKFLOW = Path("workflows/video_to_transcript_real_asr.yaml")


def test_video_to_transcript_real_asr_workflow_definition_is_explicit_remote_asr_path() -> None:
    workflow = load_workflow(VIDEO_TO_TRANSCRIPT_REAL_ASR_WORKFLOW)

    assert workflow.mode == "video_to_transcript_real_asr"
    assert workflow.quality_profile == "real_asr_transcript"
    assert [step.type for step in workflow.steps] == [
        "load_video",
        "extract_audio",
        "transcribe_audio_openai_compatible",
        "write_transcript",
    ]
    assert "transcribe_audio_mock" not in {step.type for step in workflow.steps}
    assert "detect_highlights" not in {step.type for step in workflow.steps}


def test_transcribe_audio_openai_compatible_node_requires_remote_asr_opt_in(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_ASR", raising=False)
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav")
    context = WorkflowContext(
        run_id="test",
        workflow_name="test",
        output_dir=tmp_path / "run",
        inputs={
            "asr_base_url": "https://example.test/v1",
            "asr_model": "fake-asr",
            "asr_api_key": "fake-key",
        },
        state={
            "audio_artifact": AudioArtifact(
                source_video="input.mp4",
                audio_path="audio/audio.wav",
                status="succeeded",
                extraction_mode="ffmpeg",
                sample_rate=16000,
                channels=1,
                codec="pcm_s16le",
                metadata={"absolute_audio_path": str(audio_path)},
            )
        },
    )
    step = WorkflowStepDefinition(
        id="transcribe_audio_openai_compatible",
        type="transcribe_audio_openai_compatible",
        inputs={
            "base_url": "asr_base_url",
            "model": "asr_model",
            "api_key": "asr_api_key",
        },
    )

    with pytest.raises(ValueError, match="NARRATOCUT_ALLOW_REMOTE_ASR"):
        transcribe_audio_openai_compatible_node(step, context)


def test_video_to_transcript_real_asr_workflow_writes_transcript_with_provider_patch(tmp_path, monkeypatch) -> None:
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")
    input_path = tmp_path / "video_to_transcript_real_asr_input.json"
    input_path.write_text(
        json.dumps(
            {
                "video_path": str(source_video),
                "audio_extraction_mode": "mock",
                "asr_base_url": "https://example.test/v1",
                "asr_model": "fake-asr",
                "asr_api_key": "fake-key",
                "language": "en",
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
        workflow_path=VIDEO_TO_TRANSCRIPT_REAL_ASR_WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    assert (output_dir / "audio_manifest.json").is_file()
    assert (output_dir / "transcript.json").is_file()
    assert not (output_dir / "highlight_plan.json").exists()
    assert not (output_dir / "clip_plan.json").exists()

    transcript = Transcript.model_validate(json.loads((output_dir / "transcript.json").read_text(encoding="utf-8")))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert transcript.source_video == str(source_video)
    assert transcript.metadata["asr_provider"] == "openai_compatible"
    assert run_manifest["workflow_mode"] == "video_to_transcript_real_asr"
    assert run_manifest["quality_profile"] == "real_asr_transcript"
    assert run_manifest["artifacts"]["transcript"] == "transcript.json"


def _transcript_payload(*, source_video: str) -> dict[str, object]:
    return {
        "transcript_id": "real_asr_test_transcript",
        "source_video": source_video,
        "language": "en",
        "duration": 4.0,
        "segments": [
            {
                "segment_id": "seg_001",
                "start_time": 0.0,
                "end_time": 4.0,
                "text": "A real ASR workflow should still produce the same transcript contract.",
                "speaker": "speaker_1",
                "confidence": 0.95,
                "metadata": {},
            }
        ],
        "metadata": {
            "asr_provider": "openai_compatible",
        },
    }
