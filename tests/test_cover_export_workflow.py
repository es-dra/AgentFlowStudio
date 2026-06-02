from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.harness.inspection import inspect_run
from agentflow_studio.harness.reviewer import review_run
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine import load_workflow
from agentflow_studio.workflow_engine.planner import draft_workflow_plan


WORKFLOW = Path("workflows/final_video_to_cover.yaml")


def test_final_video_to_cover_workflow_definition_is_cover_only() -> None:
    workflow = load_workflow(WORKFLOW)

    assert workflow.mode == "final_video_to_cover"
    assert workflow.quality_profile == "cover_export"
    step_types = [step.type for step in workflow.steps]
    assert step_types == ["export_cover"]
    forbidden_fragments = [
        "assemble",
        "concat",
        "subtitle",
        "bgm",
        "transition",
        "remote_asr",
        "openai",
        "multimodal",
    ]
    assert not any(fragment in step for step in step_types for fragment in forbidden_fragments)


def test_final_video_to_cover_workflow_writes_cover_artifacts(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "cover_run"
    calls: list[list[str]] = []
    _patch_cover_export_tools(monkeypatch, ffmpeg_calls=calls)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    for artifact in [
        "cover.jpg",
        "cover_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]:
        assert (output_dir / artifact).is_file()

    cover_manifest = json.loads((output_dir / "cover_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert cover_manifest["status"] == "succeeded"
    assert cover_manifest["source_video"].endswith("final_video.mp4")
    assert cover_manifest["cover_path"] == "cover.jpg"
    assert cover_manifest["cover_time_sec"] == 1.0
    assert cover_manifest["returncode"] == 0
    assert cover_manifest["ffmpeg_command"]
    assert "-frames:v" in cover_manifest["ffmpeg_command"]
    assert "cover.jpg" in str(calls[0][-1])
    assert run_manifest["workflow_mode"] == "final_video_to_cover"
    assert run_manifest["quality_profile"] == "cover_export"
    assert run_manifest["artifacts"]["cover_manifest"] == "cover_manifest.json"
    assert run_manifest["artifacts"]["cover_image"] == "cover.jpg"

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    assert "cover_export_outputs" in {section["name"] for section in review["sections"]}


def test_final_video_to_cover_records_missing_source_video(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path, missing_video=True)
    output_dir = tmp_path / "cover_run"
    _patch_cover_export_tools(monkeypatch)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    cover_manifest = json.loads((output_dir / "cover_manifest.json").read_text(encoding="utf-8"))
    assert cover_manifest["status"] == "failed"
    assert any("source_video_missing" in error for error in cover_manifest["errors"])
    assert not (output_dir / "cover.jpg").exists()


def test_final_video_to_cover_records_failed_ffmpeg_export(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "cover_run"

    def failing_ffmpeg(command, capture_output, text, check):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="frame extraction failed")

    _patch_cover_export_tools(monkeypatch, ffmpeg_run=failing_ffmpeg)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    cover_manifest = json.loads((output_dir / "cover_manifest.json").read_text(encoding="utf-8"))
    assert cover_manifest["status"] == "failed"
    assert cover_manifest["returncode"] == 1
    assert cover_manifest["stderr"] == "frame extraction failed"
    assert any("frame extraction failed" in error for error in cover_manifest["errors"])

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "fail"
    assert review["status"] == "failed"


def test_cover_export_config_rejects_unsafe_output_name() -> None:
    from agentflow_studio.cover_sop import CoverExportConfig

    with pytest.raises(ValueError, match="safe relative file name"):
        CoverExportConfig(output_name="../outside.jpg")


def test_cover_export_command_marks_single_image_output() -> None:
    from agentflow_studio.cover_sop import CoverExportConfig, build_ffmpeg_cover_export_command

    command = build_ffmpeg_cover_export_command(
        source_video="final_video.mp4",
        output_image="cover.jpg",
        config=CoverExportConfig(cover_time_sec=1.0),
    )

    assert command[command.index("-update") + 1] == "1"
    assert "-frames:v" in command


def test_cover_export_review_fails_when_manifest_succeeds_but_cover_missing(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "run",
            "workflow": "workflows/final_video_to_cover.yaml",
            "workflow_mode": "final_video_to_cover",
            "quality_profile": "cover_export",
            "artifacts": {
                "cover_manifest": "cover_manifest.json",
                "cover_image": "cover.jpg",
            },
        },
    )
    write_json(run_dir / "manifest.json", {"run_id": "run", "status": "success"})
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "export_cover", "status": "success"}]})
    write_json(
        run_dir / "cover_manifest.json",
        {
            "status": "succeeded",
            "source_video": "final_video.mp4",
            "cover_path": "cover.jpg",
            "cover_time_sec": 1.0,
            "ffmpeg_command": ["ffmpeg", "-y"],
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "errors": [],
            "warnings": [],
            "manifest_path": "cover_manifest.json",
        },
    )

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "fail"
    assert review["status"] == "failed"
    cover_section = next(section for section in review["sections"] if section["name"] == "cover_export_outputs")
    failed_ids = {check["id"] for check in cover_section["checks"] if check["status"] == "failed"}
    assert "cover_image_file_exists" in failed_ids


def test_draft_workflow_plan_lists_cover_export_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path=WORKFLOW,
        input_path="examples/demo_cover/final_video_to_cover_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == ["export_cover"]
    expected = plan["artifacts"]["expected"]
    assert "cover_manifest.json" in expected
    assert "cover.jpg" in expected


def _write_input_bundle(
    tmp_path: Path,
    *,
    missing_video: bool = False,
    output_name: str = "cover.jpg",
) -> Path:
    final_video = tmp_path / "final_video.mp4"
    if not missing_video:
        final_video.write_bytes(b"fake final video")
    input_path = tmp_path / "final_video_to_cover_input.json"
    write_json(
        input_path,
        {
            "final_video_path": str(final_video),
            "cover_time_sec": 1.0,
            "output_name": output_name,
        },
    )
    return input_path


def _patch_cover_export_tools(
    monkeypatch,
    *,
    ffmpeg_calls: list[list[str]] | None = None,
    ffmpeg_run=None,
) -> None:
    def fake_tool_check(executable="ffmpeg"):  # noqa: ANN001, ANN202
        from agentflow_studio.slicing_sop.ffmpeg_probe import FFmpegInfo

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
        output_path.write_bytes(b"fake cover")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("agentflow_studio.workflow_engine.cover_nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr("agentflow_studio.cover_sop.export.subprocess.run", ffmpeg_run or fake_run)
