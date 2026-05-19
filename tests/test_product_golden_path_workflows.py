from __future__ import annotations

import json
import subprocess
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratocut.schemas import Transcript, VideoMetadata
from narratocut.utils import write_json
from narratocut.workflow_engine import load_workflow


VIDEO_WORKFLOW = Path("workflows/video_to_finished_package_real_asr.yaml")
SCRIPT_WORKFLOW = Path("workflows/video_script_to_finished_package_real_asr.yaml")


def test_video_to_finished_package_real_asr_workflow_definition() -> None:
    workflow = load_workflow(VIDEO_WORKFLOW)

    assert workflow.mode == "video_to_finished_package_real_asr"
    assert workflow.quality_profile == "finished_package"
    assert workflow.metadata["kind"] == "product"
    assert workflow.metadata["status"] == "optional"
    step_types = [step.type for step in workflow.steps]
    assert step_types == [
        "load_video",
        "extract_audio",
        "analyze_audio_boundary_signals",
        "transcribe_audio_openai_compatible",
        "write_transcript",
        "load_roi_config",
        "generate_candidate_windows",
        "score_candidate_windows",
        "write_highlight_score_report",
        "write_selection_diagnostics",
        "write_highlight_plan",
        "generate_clip_plan_from_highlights",
        "write_clip_plan",
        "probe_video_metadata",
        "validate_clip_plan",
        "real_slice_video",
        "generate_assembly_plan",
        "concat_clips",
        "probe_final_video",
        "write_clip_timeline_subtitles",
        "mix_bgm",
        "probe_bgm_mix",
        "write_finished_package",
        "write_package_report",
    ]
    assert "multimodal" not in " ".join(step_types)


def test_video_to_finished_package_real_asr_workflow_runs_product_path(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "run"
    _patch_real_tools(monkeypatch)
    _patch_real_asr(monkeypatch, source_video=str(tmp_path / "input.mp4"))

    status, _ = run_workflow_from_cli(VIDEO_WORKFLOW, input_path, output_dir)

    assert status == "success"
    _assert_product_outputs(output_dir)
    highlight_plan = json.loads((output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    clip_plan = json.loads((output_dir / "clip_plan.json").read_text(encoding="utf-8"))
    subtitle_manifest = json.loads((output_dir / "subtitle_manifest.json").read_text(encoding="utf-8"))
    package = json.loads((output_dir / "finished_package_manifest.json").read_text(encoding="utf-8"))
    package_report = (output_dir / "package_report.md").read_text(encoding="utf-8")

    assert len(highlight_plan["highlights"]) >= 2
    assert highlight_plan["metadata"]["source"] == "candidate_scoring"
    assert len(clip_plan["segments"]) >= 2
    assert all(segment["end_sec"] - segment["start_sec"] <= 8.0 for segment in clip_plan["segments"])
    assert all(segment["metadata"].get("candidate_id") for segment in clip_plan["segments"])
    assert all(segment["metadata"].get("scorer") == "deterministic_viral_scorer_v0" for segment in clip_plan["segments"])
    assert subtitle_manifest["timeline"] == "final_video"
    assert subtitle_manifest["duration_sec"] <= 30.0
    assert package["evidence"]["real_slice_manifest"].endswith("real_slice_manifest.json")
    assert package["evidence"]["subtitle_manifest"].endswith("subtitle_manifest.json")
    assert (output_dir / "selection_diagnostics.json").is_file()
    assert "## Selected Clips" in package_report
    assert "## Selection Diagnostics" in package_report
    assert "Candidate ID" in package_report

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    assert _product_warnings(inspection).isdisjoint(_six_quality_warnings())


def test_video_script_to_finished_package_real_asr_workflow_runs_alignment_path(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path, with_script=True)
    output_dir = tmp_path / "script_run"
    _patch_real_tools(monkeypatch)
    _patch_real_asr(monkeypatch, source_video=str(tmp_path / "input.mp4"))

    status, _ = run_workflow_from_cli(SCRIPT_WORKFLOW, input_path, output_dir)

    assert status == "success"
    _assert_product_outputs(output_dir)
    alignment = json.loads((output_dir / "script_highlight_alignment.json").read_text(encoding="utf-8"))
    highlight_plan = json.loads((output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    clip_plan = json.loads((output_dir / "clip_plan.json").read_text(encoding="utf-8"))

    assert alignment["aligned_count"] >= 2
    assert alignment["skipped_count"] == 0
    assert highlight_plan["input_mode"] == "timestamped_transcript"
    assert highlight_plan["metadata"]["source"] == "candidate_scoring"
    assert (output_dir / "highlight_score_report.json").is_file()
    assert any(highlight["metadata"].get("script_alignment") for highlight in highlight_plan["highlights"])
    assert all(segment["metadata"].get("highlight_id") for segment in clip_plan["segments"])
    assert all(segment["end_sec"] - segment["start_sec"] <= 8.0 for segment in clip_plan["segments"])

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    assert _product_warnings(inspection).isdisjoint(_six_quality_warnings())


def _assert_product_outputs(output_dir: Path) -> None:
    for artifact in [
        "audio_manifest.json",
        "boundary_signal_manifest.json",
        "transcript.json",
        "candidate_windows.json",
        "highlight_score_report.json",
        "selection_diagnostics.json",
        "highlight_plan.json",
        "clip_plan.json",
        "clip_plan_validation.json",
        "real_slice_manifest.json",
        "assembly_plan.json",
        "final_video_manifest.json",
        "final_video.mp4",
        "subtitles.srt",
        "subtitle_manifest.json",
        "final_video_with_bgm.mp4",
        "audio_mix_manifest.json",
        "finished_package_manifest.json",
        "package_report.md",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]:
        assert (output_dir / artifact).is_file(), artifact
    assert (output_dir / "clips" / "clip_001.mp4").is_file()
    assert (output_dir / "clips" / "clip_002.mp4").is_file()


def _write_input_bundle(tmp_path: Path, *, with_script: bool = False) -> Path:
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake video")
    bgm = tmp_path / "bgm.mp3"
    bgm.write_bytes(b"verified bgm")
    bgm_metadata = tmp_path / "bgm.metadata.json"
    write_json(
        bgm_metadata,
        {
            "quality_verified": True,
            "verification_method": "manual_local_review",
            "license": "local_test_asset",
        },
    )
    roi = tmp_path / "roi_config.json"
    write_json(roi, _roi_payload())
    payload = {
        "video_path": str(video),
        "source_video": str(video),
        "audio_extraction_mode": "mock",
        "asr_base_url": "https://example.test/v1",
        "asr_model": "fake-asr",
        "asr_api_key": "fake-key",
        "roi_config_path": str(roi),
        "language": "en",
        "max_highlights": 3,
        "max_clips": 3,
        "bgm_path": str(bgm),
        "bgm_metadata_path": str(bgm_metadata),
        "output_clips_dir": "clips",
    }
    if with_script:
        script = tmp_path / "script.txt"
        script.write_text(
            "The real bottleneck is choosing what to cut.\nValidate the story before final assembly.",
            encoding="utf-8",
        )
        payload["script_path"] = str(script)
        payload["alignment_min_confidence"] = 0.25
    input_path = tmp_path / ("script_input.json" if with_script else "input.json")
    write_json(input_path, payload)
    return input_path


def _patch_real_asr(monkeypatch, *, source_video: str) -> None:
    def fake_transcribe(self, audio_artifact, *, language=None):  # noqa: ANN001, ANN202
        return Transcript.model_validate(_transcript_payload(source_video=source_video))

    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_ASR", "true")
    monkeypatch.setattr(
        "narratocut.workflow_engine.transcription_nodes.OpenAICompatibleASRProvider.transcribe",
        fake_transcribe,
    )


def _patch_real_tools(monkeypatch) -> None:
    def fake_probe(video_path, ffprobe_executable="ffprobe", timeout_sec=30):  # noqa: ANN001, ANN202
        path_text = str(video_path)
        duration = 4.0 if "clip_" in path_text else 8.0 if "final_video" in path_text else 40.0
        return VideoMetadata(
            file_path=str(video_path),
            duration_sec=duration,
            width=1080,
            height=1920,
            codec="h264",
            fps=30,
            bitrate=1000,
            probe_status="succeeded",
        )

    def fake_tool_check(executable="ffmpeg"):  # noqa: ANN001, ANN202
        from narratocut.slicing_sop.ffmpeg_probe import FFmpegInfo

        return FFmpegInfo(available=True, executable=str(executable), version="test", raw_output="test", error=None)

    def fake_run(command, capture_output, text, check):  # noqa: ANN001, ANN202
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake media")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("narratocut.workflow_engine.nodes.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.workflow_engine.nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr("narratocut.workflow_engine.assembly_nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr("narratocut.workflow_engine.assembly_nodes.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.workflow_engine.bgm_nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr("narratocut.workflow_engine.bgm_nodes.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.harness.real_clip_quality.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.harness.final_video_quality.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.harness.bgm_quality.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.slicing_sop.real_slicer.subprocess.run", fake_run)
    monkeypatch.setattr("narratocut.assembly_sop.concat.subprocess.run", fake_run)
    monkeypatch.setattr("narratocut.bgm_sop.mix.subprocess.run", fake_run)


def _transcript_payload(*, source_video: str) -> dict[str, object]:
    return {
        "transcript_id": "product_asr_transcript",
        "source_video": source_video,
        "language": "en",
        "duration": 30.0,
        "segments": [
            {"segment_id": "seg_001", "start_time": 0.0, "end_time": 4.0, "text": "Opening context that should not dominate the edit."},
            {"segment_id": "seg_002", "start_time": 6.0, "end_time": 10.0, "text": "The real bottleneck is choosing what to cut."},
            {"segment_id": "seg_003", "start_time": 14.0, "end_time": 18.0, "text": "Middle explanation can be skipped for a tighter promo."},
            {"segment_id": "seg_004", "start_time": 20.0, "end_time": 24.0, "text": "Validate the story before final assembly."},
            {"segment_id": "seg_005", "start_time": 26.0, "end_time": 30.0, "text": "A clear call to action closes the short video."},
        ],
        "metadata": {"asr_provider": "openai_compatible"},
    }


def _roi_payload() -> dict[str, object]:
    return {
        "target_platform": "douyin",
        "target_audience": "product builders",
        "content_goal": "increase_completion_rate",
        "min_clip_duration": 1,
        "max_clip_duration": 30,
        "target_clip_count": 3,
        "min_clip_count": 2,
        "max_clip_count": 5,
        "risk_tolerance": "low",
        "priority": ["hook_strength", "clarity", "watch_completion"],
        "validation_policy": "advisory",
    }


def _product_warnings(inspection: dict[str, object]) -> set[str]:
    report = inspection["quality_report"]
    assert isinstance(report, dict)
    return set(report.get("warnings", []))


def _six_quality_warnings() -> set[str]:
    return {
        "product_quality_warning: single_clip_only",
        "product_quality_warning: clip_starts_at_zero_only",
        "product_quality_warning: no_highlight_evidence",
        "product_quality_warning: subtitle_source_video_missing",
        "product_quality_warning: subtitle_duration_exceeds_primary_video",
        "product_quality_warning: bgm_quality_unverified",
    }
