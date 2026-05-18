from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratocut.schemas import VideoMetadata
from narratocut.subtitle_burn_sop import SubtitleBurnConfig
from narratocut.utils import write_json
from narratocut.workflow_engine import load_workflow
from narratocut.workflow_engine.planner import draft_workflow_plan


WORKFLOW = Path("workflows/final_video_with_subtitles.yaml")


def test_final_video_with_subtitles_workflow_definition_is_burn_only() -> None:
    workflow = load_workflow(WORKFLOW)

    assert workflow.mode == "final_video_with_subtitles"
    assert workflow.quality_profile == "subtitle_burn"
    step_types = [step.type for step in workflow.steps]
    assert step_types == ["burn_subtitles", "probe_subtitle_burn"]
    forbidden_fragments = [
        "assemble",
        "concat",
        "transcribe",
        "bgm",
        "cover",
        "transition",
        "remote_asr",
        "openai",
        "multimodal",
    ]
    assert not any(fragment in step for step in step_types for fragment in forbidden_fragments)


def test_final_video_with_subtitles_workflow_writes_burn_artifacts(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "subtitle_burn_run"
    calls: list[list[str]] = []
    _patch_subtitle_burn_tools(monkeypatch, duration_sec=8.0, ffmpeg_calls=calls)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    for artifact in [
        "final_video_with_subtitles.mp4",
        "subtitle_burn_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]:
        assert (output_dir / artifact).is_file()

    burn_manifest = json.loads((output_dir / "subtitle_burn_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert burn_manifest["status"] == "succeeded"
    assert burn_manifest["source_video"].endswith("final_video.mp4")
    assert burn_manifest["subtitles_path"].endswith("subtitles.srt")
    assert burn_manifest["output_video"] == "final_video_with_subtitles.mp4"
    assert burn_manifest["duration_sec"] == 8.0
    assert burn_manifest["ffmpeg_command"]
    assert any("-vf" == item for item in burn_manifest["ffmpeg_command"])
    assert calls
    assert run_manifest["workflow_mode"] == "final_video_with_subtitles"
    assert run_manifest["quality_profile"] == "subtitle_burn"
    assert run_manifest["artifacts"]["subtitle_burn_manifest"] == "subtitle_burn_manifest.json"
    assert run_manifest["artifacts"]["subtitled_video"] == "final_video_with_subtitles.mp4"

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    section_names = {section["name"] for section in review["sections"]}
    assert "subtitle_burn_outputs" in section_names


def test_final_video_with_subtitles_records_failed_ffmpeg_burn(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "subtitle_burn_run"

    def failing_ffmpeg(command, capture_output, text, check):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="subtitle filter failed")

    _patch_subtitle_burn_tools(monkeypatch, duration_sec=8.0, ffmpeg_run=failing_ffmpeg)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    burn_manifest = json.loads((output_dir / "subtitle_burn_manifest.json").read_text(encoding="utf-8"))
    assert burn_manifest["status"] == "failed"
    assert burn_manifest["returncode"] == 1
    assert burn_manifest["stderr"] == "subtitle filter failed"
    assert any("subtitle filter failed" in error for error in burn_manifest["errors"])

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "fail"
    assert review["status"] == "failed"


def test_final_video_with_subtitles_records_missing_subtitle_file(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path, missing_subtitles=True)
    output_dir = tmp_path / "subtitle_burn_run"
    _patch_subtitle_burn_tools(monkeypatch, duration_sec=8.0)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    burn_manifest = json.loads((output_dir / "subtitle_burn_manifest.json").read_text(encoding="utf-8"))
    assert burn_manifest["status"] == "failed"
    assert any("subtitles_missing" in error for error in burn_manifest["errors"])
    assert not (output_dir / "final_video_with_subtitles.mp4").exists()


def test_subtitle_burn_config_rejects_unsafe_output_name() -> None:
    with pytest.raises(ValueError, match="safe relative file name"):
        SubtitleBurnConfig(output_name="../outside.mp4")


def test_subtitle_burn_inspection_uses_manifest_output_video_name(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path, output_name="captioned.mp4")
    output_dir = tmp_path / "subtitle_burn_run"
    _patch_subtitle_burn_tools(monkeypatch, duration_sec=8.0)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    inspection = inspect_run(output_dir)
    artifact_status = {artifact["path"]: artifact["status"] for artifact in inspection["artifacts"]}
    assert inspection["status"] == "pass"
    assert artifact_status["captioned.mp4"] == "found"


def test_final_video_with_subtitles_handles_relative_output_dir(tmp_path, monkeypatch) -> None:
    workflow_path = Path.cwd() / WORKFLOW
    input_path = _write_input_bundle(tmp_path)
    _patch_subtitle_burn_tools(monkeypatch, duration_sec=8.0)
    monkeypatch.chdir(tmp_path)

    status, _ = run_workflow_from_cli(
        workflow_path=workflow_path,
        input_path=input_path,
        output_dir=Path("subtitle_burn_run"),
    )

    assert status == "success"
    assert (tmp_path / "subtitle_burn_run" / "subtitle_burn_manifest.json").is_file()
    assert (tmp_path / "subtitle_burn_run" / "final_video_with_subtitles.mp4").is_file()


def test_subtitle_burn_review_fails_when_manifest_succeeds_but_output_missing(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "run",
            "workflow": "workflows/final_video_with_subtitles.yaml",
            "workflow_mode": "final_video_with_subtitles",
            "quality_profile": "subtitle_burn",
            "artifacts": {
                "subtitle_burn_manifest": "subtitle_burn_manifest.json",
                "subtitled_video": "final_video_with_subtitles.mp4",
            },
        },
    )
    write_json(run_dir / "manifest.json", {"run_id": "run", "status": "success"})
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "burn_subtitles", "status": "success"}]})
    write_json(
        run_dir / "subtitle_burn_manifest.json",
        {
            "status": "succeeded",
            "source_video": "final_video.mp4",
            "subtitles_path": "subtitles.srt",
            "output_video": "final_video_with_subtitles.mp4",
            "duration_sec": 8.0,
            "ffmpeg_command": ["ffmpeg", "-y"],
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "errors": [],
            "warnings": [],
            "manifest_path": "subtitle_burn_manifest.json",
        },
    )

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "fail"
    assert review["status"] == "failed"
    subtitle_section = next(section for section in review["sections"] if section["name"] == "subtitle_burn_outputs")
    failed_ids = {check["id"] for check in subtitle_section["checks"] if check["status"] == "failed"}
    assert "subtitle_burn_output_file_exists" in failed_ids


def test_draft_workflow_plan_lists_subtitle_burn_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path=WORKFLOW,
        input_path="examples/demo_subtitles/final_video_with_subtitles_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == ["burn_subtitles", "probe_subtitle_burn"]
    expected = plan["artifacts"]["expected"]
    assert "subtitle_burn_manifest.json" in expected
    assert "final_video_with_subtitles.mp4" in expected


def _write_input_bundle(
    tmp_path: Path,
    *,
    missing_subtitles: bool = False,
    output_name: str = "final_video_with_subtitles.mp4",
) -> Path:
    final_video = tmp_path / "final_video.mp4"
    final_video.write_bytes(b"fake final video")
    subtitles = tmp_path / "subtitles.srt"
    if not missing_subtitles:
        subtitles.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello\n", encoding="utf-8")
    input_path = tmp_path / "final_video_with_subtitles_input.json"
    write_json(
        input_path,
        {
            "final_video_path": str(final_video),
            "subtitles_path": str(subtitles),
            "output_name": output_name,
        },
    )
    return input_path


def _patch_subtitle_burn_tools(
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
        output_path.write_bytes(b"fake subtitled video")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("narratocut.workflow_engine.subtitle_burn_nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr("narratocut.workflow_engine.subtitle_burn_nodes.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.harness.subtitle_burn_quality.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.subtitle_burn_sop.burn.subprocess.run", ffmpeg_run or fake_run)
