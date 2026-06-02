from __future__ import annotations

import json
import subprocess
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.harness.inspection import inspect_run
from agentflow_studio.harness.reviewer import review_run
from agentflow_studio.schemas import ClipPlan, ClipSegment, VideoMetadata
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine import load_workflow


WORKFLOW = Path("workflows/clip_plan_to_real_clips.yaml")


def test_clip_plan_to_real_clips_workflow_definition_is_execution_only() -> None:
    workflow = load_workflow(WORKFLOW)

    assert workflow.mode == "clip_plan_to_real_clips"
    assert workflow.quality_profile == "real_clips"
    step_types = [step.type for step in workflow.steps]
    assert step_types == [
        "load_video",
        "load_clip_plan",
        "probe_video_metadata",
        "validate_clip_plan",
        "real_slice_video",
    ]
    forbidden_fragments = [
        "assemble",
        "concat",
        "subtitle",
        "bgm",
        "remote_asr",
        "openai",
        "multimodal",
    ]
    assert not any(fragment in step for step in step_types for fragment in forbidden_fragments)


def test_clip_plan_to_real_clips_workflow_writes_real_clip_artifacts(tmp_path, monkeypatch) -> None:
    video, clip_plan_path, input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "run"
    calls: list[list[str]] = []

    _patch_real_tools(
        monkeypatch,
        duration_sec=20.0,
        ffmpeg_available=True,
        ffmpeg_calls=calls,
        write_clip_files=True,
    )

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    assert (output_dir / "video_metadata.json").is_file()
    assert (output_dir / "clip_plan_validation.json").is_file()
    assert (output_dir / "real_slice_manifest.json").is_file()
    assert (output_dir / "clips" / "clip_001.mp4").is_file()
    assert (output_dir / "clips" / "clip_002.mp4").is_file()
    assert (output_dir / "manifest.json").is_file()
    assert (output_dir / "run_manifest.json").is_file()
    assert (output_dir / "trace.json").is_file()

    manifest = json.loads((output_dir / "real_slice_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "succeeded"
    assert manifest["source_video"] == str(video)
    assert manifest["clip_plan_path"] == str(clip_plan_path)
    assert manifest["clips_dir"] == "clips"
    assert manifest["clip_count"] == 2
    assert [clip["path"] for clip in manifest["clips"]] == [
        "clips/clip_001.mp4",
        "clips/clip_002.mp4",
    ]
    assert all(not Path(clip["path"]).is_absolute() for clip in manifest["clips"])
    assert all(clip["ffmpeg_command"] for clip in manifest["clips"])
    assert all(clip["returncode"] == 0 for clip in manifest["clips"])
    assert calls

    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert run_manifest["workflow_mode"] == "clip_plan_to_real_clips"
    assert run_manifest["quality_profile"] == "real_clips"
    assert run_manifest["artifacts"]["video_metadata"] == "video_metadata.json"
    assert run_manifest["artifacts"]["clip_plan_validation"] == "clip_plan_validation.json"
    assert run_manifest["artifacts"]["real_slice_manifest"] == "real_slice_manifest.json"
    assert run_manifest["artifacts"]["clips"] == "clips"


def test_clip_plan_to_real_clips_skips_slicing_when_validation_fails(tmp_path, monkeypatch) -> None:
    _, _, input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "run"

    def fail_if_called(*args, **kwargs):  # noqa: ANN001, ANN202
        raise AssertionError("real slicing should not execute when validation fails")

    _patch_real_tools(
        monkeypatch,
        duration_sec=6.0,
        ffmpeg_available=True,
        ffmpeg_run=fail_if_called,
    )

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    validation = json.loads((output_dir / "clip_plan_validation.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "real_slice_manifest.json").read_text(encoding="utf-8"))
    assert validation["status"] == "failed"
    assert any(error["code"] == "segment_exceeds_video_duration" for error in validation["hard_errors"])
    assert manifest["status"] == "skipped"
    assert manifest["reason"] == "clip_plan_validation_failed"


def test_clip_plan_to_real_clips_records_failed_ffmpeg_clip(tmp_path, monkeypatch) -> None:
    _, _, input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "run"

    def failing_ffmpeg(command, capture_output, text, check):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="ffmpeg failed")

    _patch_real_tools(
        monkeypatch,
        duration_sec=20.0,
        ffmpeg_available=True,
        ffmpeg_run=failing_ffmpeg,
    )

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    manifest = json.loads((output_dir / "real_slice_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["clip_count"] == 0
    assert all(clip["status"] == "failed" for clip in manifest["clips"])
    assert all(clip["returncode"] == 1 for clip in manifest["clips"])
    assert any("ffmpeg failed" in error for error in manifest["errors"])


def test_real_clips_review_flags_missing_declared_clip_file(tmp_path) -> None:
    run_dir = tmp_path / "real_clips_run"
    run_dir.mkdir()
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "real_clips_run",
            "workflow": "workflows/clip_plan_to_real_clips.yaml",
            "workflow_mode": "clip_plan_to_real_clips",
            "quality_profile": "real_clips",
            "artifacts": {
                "video_metadata": "video_metadata.json",
                "clip_plan_validation": "clip_plan_validation.json",
                "real_slice_manifest": "real_slice_manifest.json",
                "clips": "clips",
            },
        },
    )
    write_json(run_dir / "manifest.json", {"status": "success"})
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "real_slice_video"}]})
    write_json(run_dir / "video_metadata.json", {"probe_status": "succeeded", "duration_sec": 20})
    write_json(run_dir / "clip_plan_validation.json", {"status": "passed", "hard_errors": [], "warnings": []})
    write_json(
        run_dir / "real_slice_manifest.json",
        {
            "status": "succeeded",
            "clips_dir": "clips",
            "clips": [
                {
                    "clip_id": "clip_001",
                    "status": "succeeded",
                    "path": "clips/clip_001.mp4",
                    "duration_sec": 3,
                }
            ],
            "errors": [],
        },
    )

    inspection = inspect_run(run_dir)
    report = review_run(run_dir)

    assert inspection["status"] == "fail"
    assert report["status"] == "failed"
    assert any(
        check["id"] == "quality_report_passed" and check["status"] == "failed"
        for section in report["sections"]
        for check in section["checks"]
    )


def _write_input_bundle(tmp_path: Path) -> tuple[Path, Path, Path]:
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake video")
    clip_plan_path = tmp_path / "clip_plan.json"
    write_json(clip_plan_path, _clip_plan())
    input_path = tmp_path / "input.json"
    write_json(
        input_path,
        {
            "video_path": str(video),
            "clip_plan_path": str(clip_plan_path),
            "output_clips_dir": "clips",
        },
    )
    return video, clip_plan_path, input_path


def _clip_plan() -> ClipPlan:
    return ClipPlan(
        clip_plan_id="clip_plan_phase_12_1",
        project_id="phase_12_1",
        hook_id="hook_demo",
        title="Phase 12.1 demo",
        cover_text="Demo",
        output_name="clip_demo.mp4",
        segments=[
            ClipSegment(
                segment_id="seg_001",
                source_video="input.mp4",
                start_sec=0,
                end_sec=3,
            ),
            ClipSegment(
                segment_id="seg_002",
                source_video="input.mp4",
                start_sec=3,
                end_sec=8,
            ),
        ],
    )


def _patch_real_tools(
    monkeypatch,
    *,
    duration_sec: float,
    ffmpeg_available: bool,
    ffmpeg_calls: list[list[str]] | None = None,
    write_clip_files: bool = False,
    ffmpeg_run=None,
) -> None:
    def fake_probe(video_path, ffprobe_executable="ffprobe", timeout_sec=30):  # noqa: ANN001, ANN202
        return VideoMetadata(
            file_path=str(video_path),
            duration_sec=duration_sec,
            width=1080,
            height=1920,
            codec="h264",
            fps=30,
            bitrate=1000,
            probe_status="succeeded",
        )

    def fake_tool_check(executable="ffmpeg"):  # noqa: ANN001, ANN202
        from agentflow_studio.slicing_sop.ffmpeg_probe import FFmpegInfo

        return FFmpegInfo(
            available=ffmpeg_available,
            executable=str(executable),
            version="ffmpeg-test" if ffmpeg_available else None,
            raw_output="ffmpeg-test" if ffmpeg_available else None,
            error=None if ffmpeg_available else "ffmpeg_unavailable",
        )

    def fake_run(command, capture_output, text, check):  # noqa: ANN001, ANN202
        if ffmpeg_calls is not None:
            ffmpeg_calls.append(command)
        if write_clip_files:
            output_path = Path(command[-1])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("agentflow_studio.workflow_engine.nodes.probe_video_metadata", fake_probe)
    monkeypatch.setattr("agentflow_studio.workflow_engine.nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr(
        "agentflow_studio.slicing_sop.real_slicer.subprocess.run",
        ffmpeg_run or fake_run,
    )
