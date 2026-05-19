from __future__ import annotations

import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.schemas import Transcript
from narratocut.workflow_engine import load_workflow

from tests.test_product_golden_path_workflows import (
    _assert_product_outputs,
    _patch_real_tools,
    _product_warnings,
    _six_quality_warnings,
    _write_input_bundle,
)


VIDEO_LOCAL_WORKFLOW = Path("workflows/video_to_finished_package_local_asr.yaml")
SCRIPT_LOCAL_WORKFLOW = Path("workflows/video_script_to_finished_package_local_asr.yaml")


def test_video_to_finished_package_local_asr_workflow_definition() -> None:
    workflow = load_workflow(VIDEO_LOCAL_WORKFLOW)

    assert workflow.mode == "video_to_finished_package_local_asr"
    assert workflow.quality_profile == "finished_package"
    step_types = [step.type for step in workflow.steps]
    assert step_types[:4] == [
        "load_video",
        "extract_audio",
        "transcribe_audio_faster_whisper",
        "write_transcript",
    ]
    assert "transcribe_audio_openai_compatible" not in step_types


def test_video_script_to_finished_package_local_asr_workflow_definition() -> None:
    workflow = load_workflow(SCRIPT_LOCAL_WORKFLOW)

    assert workflow.mode == "video_script_to_finished_package_local_asr"
    step_types = [step.type for step in workflow.steps]
    assert step_types[:4] == [
        "load_video",
        "extract_audio",
        "transcribe_audio_faster_whisper",
        "write_transcript",
    ]
    assert "align_script_highlights_to_transcript" in step_types
    assert "transcribe_audio_openai_compatible" not in step_types


def test_video_to_finished_package_local_asr_workflow_runs_product_path(tmp_path, monkeypatch) -> None:
    input_path = _write_local_input_bundle(tmp_path)
    output_dir = tmp_path / "run"
    _patch_real_tools(monkeypatch)
    _patch_local_asr(monkeypatch, source_video=str(tmp_path / "input.mp4"))

    status, _ = run_workflow_from_cli(VIDEO_LOCAL_WORKFLOW, input_path, output_dir)

    assert status == "success"
    _assert_product_outputs(output_dir)
    transcript = json.loads((output_dir / "transcript.json").read_text(encoding="utf-8"))
    highlight_plan = json.loads((output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    clip_plan = json.loads((output_dir / "clip_plan.json").read_text(encoding="utf-8"))
    assert transcript["metadata"]["asr_provider"] == "faster_whisper"
    assert highlight_plan["metadata"]["source"] == "candidate_scoring"
    assert all(segment["end_sec"] - segment["start_sec"] <= 8.0 for segment in clip_plan["segments"])
    assert all(segment["metadata"].get("candidate_id") for segment in clip_plan["segments"])
    inspection = __import__("narratocut.harness.inspection", fromlist=["inspect_run"]).inspect_run(output_dir)
    review = __import__("narratocut.harness.reviewer", fromlist=["review_run"]).review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    assert _product_warnings(inspection).isdisjoint(_six_quality_warnings())


def _write_local_input_bundle(tmp_path: Path, *, with_script: bool = False) -> Path:
    input_path = _write_input_bundle(tmp_path, with_script=with_script)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    for key in ["asr_base_url", "asr_api_key", "asr_api_key_env", "asr_timeout_sec"]:
        payload.pop(key, None)
    payload["asr_model"] = "tiny"
    payload["asr_device"] = "cpu"
    payload["asr_compute_type"] = "int8"
    payload["asr_beam_size"] = 1
    payload["asr_vad_filter"] = False
    input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return input_path


def _patch_local_asr(monkeypatch, *, source_video: str) -> None:
    def fake_transcribe(self, audio_artifact, *, language=None):  # noqa: ANN001, ANN202
        return Transcript.model_validate(
            {
                "transcript_id": "local_asr_test_transcript",
                "source_video": source_video,
                "language": language or "en",
                "duration": 30.0,
                "segments": [
                    {"segment_id": "seg_001", "start_time": 0.0, "end_time": 4.0, "text": "Opening context that should not dominate the edit."},
                    {"segment_id": "seg_002", "start_time": 6.0, "end_time": 10.0, "text": "The real bottleneck is choosing what to cut."},
                    {"segment_id": "seg_003", "start_time": 14.0, "end_time": 18.0, "text": "Middle explanation can be skipped for a tighter promo."},
                    {"segment_id": "seg_004", "start_time": 20.0, "end_time": 24.0, "text": "Validate the story before final assembly."},
                    {"segment_id": "seg_005", "start_time": 26.0, "end_time": 30.0, "text": "A clear call to action closes the short video."},
                ],
                "metadata": {"asr_provider": "faster_whisper"},
            }
        )

    monkeypatch.setattr(
        "narratocut.workflow_engine.transcription_nodes.FasterWhisperASRProvider.transcribe",
        fake_transcribe,
    )
