from __future__ import annotations

import json
import subprocess
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratocut.schemas import VideoMetadata
from narratocut.utils import write_json
from narratocut.workflow_engine import load_workflow


WORKFLOW = Path("workflows/clips_to_final_video.yaml")


def test_clips_to_final_video_workflow_definition_is_assembly_only() -> None:
    workflow = load_workflow(WORKFLOW)

    assert workflow.mode == "clips_to_final_video"
    assert workflow.quality_profile == "final_video"
    step_types = [step.type for step in workflow.steps]
    assert step_types == [
        "load_real_slice_manifest",
        "generate_assembly_plan",
        "concat_clips",
        "probe_final_video",
    ]
    forbidden_fragments = ["subtitle", "bgm", "cover", "remote_asr", "openai", "multimodal"]
    assert not any(fragment in step for step in step_types for fragment in forbidden_fragments)


def test_clips_to_final_video_workflow_writes_final_video_artifacts(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "assembly_run"
    calls: list[list[str]] = []
    _patch_assembly_tools(monkeypatch, duration_sec=8.0, ffmpeg_calls=calls)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    for artifact in [
        "real_slice_manifest.json",
        "assembly_plan.json",
        "concat_list.txt",
        "final_video.mp4",
        "final_video_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]:
        assert (output_dir / artifact).is_file()

    assembly_plan = json.loads((output_dir / "assembly_plan.json").read_text(encoding="utf-8"))
    final_manifest = json.loads((output_dir / "final_video_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert assembly_plan["output_name"] == "final_video.mp4"
    assert assembly_plan["target_duration_sec"] == 8.0
    assert [clip["path"] for clip in assembly_plan["clips"]] == ["clips/clip_001.mp4", "clips/clip_002.mp4"]
    assert final_manifest["status"] == "succeeded"
    assert final_manifest["final_video"] == "final_video.mp4"
    assert final_manifest["duration_sec"] == 8.0
    assert final_manifest["input_clip_count"] == 2
    assert final_manifest["ffmpeg_command"]
    assert calls
    assert run_manifest["workflow_mode"] == "clips_to_final_video"
    assert run_manifest["quality_profile"] == "final_video"

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    section_names = {section["name"] for section in review["sections"]}
    assert "final_video_outputs" in section_names


def test_clips_to_final_video_records_missing_input_clip(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path, missing_clip=True)
    output_dir = tmp_path / "assembly_run"
    _patch_assembly_tools(monkeypatch, duration_sec=4.0)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    final_manifest = json.loads((output_dir / "final_video_manifest.json").read_text(encoding="utf-8"))
    assert final_manifest["status"] == "failed"
    assert any("input_clip_missing" in error for error in final_manifest["errors"])

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "fail"
    assert review["status"] == "failed"


def test_clips_to_final_video_rejects_unsafe_input_clip_path(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path, clip_path="../outside.mp4")
    output_dir = tmp_path / "assembly_run"
    _patch_assembly_tools(monkeypatch, duration_sec=4.0)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    final_manifest = json.loads((output_dir / "final_video_manifest.json").read_text(encoding="utf-8"))
    assert final_manifest["status"] == "failed"
    assert any("unsafe_clip_path" in error for error in final_manifest["errors"])


def test_clips_to_final_video_records_failed_ffmpeg_concat(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "assembly_run"

    def failing_ffmpeg(command, capture_output, text, check):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="concat failed")

    _patch_assembly_tools(monkeypatch, duration_sec=8.0, ffmpeg_run=failing_ffmpeg)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    final_manifest = json.loads((output_dir / "final_video_manifest.json").read_text(encoding="utf-8"))
    assert final_manifest["status"] == "failed"
    assert final_manifest["returncode"] == 1
    assert any("concat failed" in error for error in final_manifest["errors"])


def test_clips_to_final_video_review_uses_manifest_final_video_name(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path, output_name="assembled.mp4")
    output_dir = tmp_path / "assembly_run"
    _patch_assembly_tools(monkeypatch, duration_sec=8.0)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    inspect_run(output_dir)
    review = review_run(output_dir)
    assert review["status"] == "passed"
    final_section = next(section for section in review["sections"] if section["name"] == "final_video_outputs")
    final_video_check = next(check for check in final_section["checks"] if check["id"] == "artifact_final_video_exists")
    assert final_video_check["status"] == "passed"
    assert final_video_check["details"]["path"] == "assembled.mp4"


def test_final_video_quality_classifies_known_ffmpeg_stderr_warnings(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "assembly_run"

    def warning_ffmpeg(command, capture_output, text, check):  # noqa: ANN001, ANN202
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake final video")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="",
            stderr="Non-monotonic DTS; previous: 177145, current: 176400",
        )

    _patch_assembly_tools(monkeypatch, duration_sec=8.0, ffmpeg_run=warning_ffmpeg)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    inspection = inspect_run(output_dir)
    assert inspection["status"] == "pass"
    quality_report = inspection["quality_report"]
    warning_check = next(check for check in quality_report["checks"] if check["name"] == "final_video_ffmpeg_warnings")
    assert warning_check["status"] == "warning"
    assert warning_check["details"]["warnings"][0]["code"] == "non_monotonic_dts"
    assert "final_video_ffmpeg_warning: non_monotonic_dts" in quality_report["warnings"]

    review = review_run(output_dir)
    assert review["status"] == "warning"


def test_final_video_quality_fails_when_video_stream_missing(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "assembly_run"
    _patch_assembly_tools(monkeypatch, duration_sec=8.0, probe_status="failed", probe_errors=["video_stream_missing"])

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    inspection = inspect_run(output_dir)
    assert inspection["status"] == "fail"
    quality_report = inspection["quality_report"]
    failed_checks = {check["name"] for check in quality_report["checks"] if check["status"] == "fail"}
    assert "final_video_stream_present" in failed_checks
    assert "final_video_stream_missing: final_video.mp4" in quality_report["errors"]


def _write_input_bundle(
    tmp_path: Path,
    *,
    missing_clip: bool = False,
    clip_path: str = "clips/clip_001.mp4",
    output_name: str = "final_video.mp4",
) -> Path:
    source_run = tmp_path / "source_run"
    clips_dir = source_run / "clips"
    clips_dir.mkdir(parents=True)
    (clips_dir / "clip_001.mp4").write_bytes(b"fake clip 1")
    if not missing_clip:
        (clips_dir / "clip_002.mp4").write_bytes(b"fake clip 2")
    write_json(
        source_run / "real_slice_manifest.json",
        {
            "status": "succeeded",
            "source_video": "data/raw/demo_real_video/input.mp4",
            "clips_dir": "clips",
            "clip_count": 2,
            "clips": [
                {
                    "clip_id": "clip_001",
                    "status": "succeeded",
                    "path": clip_path,
                    "start_sec": 0.0,
                    "end_sec": 4.0,
                    "duration_sec": 4.0,
                },
                {
                    "clip_id": "clip_002",
                    "status": "succeeded",
                    "path": "clips/clip_002.mp4",
                    "start_sec": 4.0,
                    "end_sec": 8.0,
                    "duration_sec": 4.0,
                },
            ],
            "errors": [],
        },
    )
    input_path = tmp_path / "clips_to_final_video_input.json"
    write_json(
        input_path,
        {
            "real_slice_manifest_path": str(source_run / "real_slice_manifest.json"),
            "output_name": output_name,
        },
    )
    return input_path


def _patch_assembly_tools(
    monkeypatch,
    *,
    duration_sec: float,
    probe_status: str = "succeeded",
    probe_errors: list[str] | None = None,
    ffmpeg_calls: list[list[str]] | None = None,
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
            probe_status=probe_status,
            errors=probe_errors or [],
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
        if ffmpeg_calls is not None:
            ffmpeg_calls.append(command)
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake final video")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("narratocut.workflow_engine.assembly_nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr("narratocut.workflow_engine.assembly_nodes.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.harness.final_video_quality.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.assembly_sop.concat.subprocess.run", ffmpeg_run or fake_run)
