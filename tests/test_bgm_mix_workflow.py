from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratocut.schemas import VideoMetadata
from narratocut.utils import write_json
from narratocut.workflow_engine import load_workflow
from narratocut.workflow_engine.planner import draft_workflow_plan


WORKFLOW = Path("workflows/final_video_with_bgm.yaml")


def test_final_video_with_bgm_workflow_definition_is_bgm_only() -> None:
    workflow = load_workflow(WORKFLOW)

    assert workflow.mode == "final_video_with_bgm"
    assert workflow.quality_profile == "bgm_mix"
    step_types = [step.type for step in workflow.steps]
    assert step_types == ["mix_bgm", "probe_bgm_mix"]
    forbidden_fragments = [
        "assemble",
        "concat",
        "subtitle",
        "cover",
        "transition",
        "remote_asr",
        "openai",
        "multimodal",
    ]
    assert not any(fragment in step for step in step_types for fragment in forbidden_fragments)


def test_final_video_with_bgm_workflow_writes_mix_artifacts(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "bgm_mix_run"
    calls: list[list[str]] = []
    _patch_bgm_mix_tools(monkeypatch, duration_sec=8.0, ffmpeg_calls=calls)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    for artifact in [
        "final_video_with_bgm.mp4",
        "audio_mix_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]:
        assert (output_dir / artifact).is_file()

    mix_manifest = json.loads((output_dir / "audio_mix_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert mix_manifest["status"] == "succeeded"
    assert mix_manifest["source_video"].endswith("final_video.mp4")
    assert mix_manifest["bgm_path"].endswith("bgm.mp3")
    assert mix_manifest["output_video"] == "final_video_with_bgm.mp4"
    assert mix_manifest["bgm_volume"] == 0.2
    assert mix_manifest["original_audio_volume"] == 1.0
    assert mix_manifest["duration_sec"] == 8.0
    assert mix_manifest["ffmpeg_command"]
    assert "-filter_complex" in mix_manifest["ffmpeg_command"]
    assert calls
    assert run_manifest["workflow_mode"] == "final_video_with_bgm"
    assert run_manifest["quality_profile"] == "bgm_mix"
    assert run_manifest["artifacts"]["audio_mix_manifest"] == "audio_mix_manifest.json"
    assert run_manifest["artifacts"]["bgm_video"] == "final_video_with_bgm.mp4"

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    assert "bgm_mix_outputs" in {section["name"] for section in review["sections"]}


def test_final_video_with_bgm_records_missing_bgm_file(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path, missing_bgm=True)
    output_dir = tmp_path / "bgm_mix_run"
    _patch_bgm_mix_tools(monkeypatch, duration_sec=8.0)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    mix_manifest = json.loads((output_dir / "audio_mix_manifest.json").read_text(encoding="utf-8"))
    assert mix_manifest["status"] == "failed"
    assert any("bgm_missing" in error for error in mix_manifest["errors"])
    assert not (output_dir / "final_video_with_bgm.mp4").exists()


def test_final_video_with_bgm_records_failed_ffmpeg_mix(tmp_path, monkeypatch) -> None:
    input_path = _write_input_bundle(tmp_path)
    output_dir = tmp_path / "bgm_mix_run"

    def failing_ffmpeg(command, capture_output, text, check):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="audio mix failed")

    _patch_bgm_mix_tools(monkeypatch, duration_sec=8.0, ffmpeg_run=failing_ffmpeg)

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    mix_manifest = json.loads((output_dir / "audio_mix_manifest.json").read_text(encoding="utf-8"))
    assert mix_manifest["status"] == "failed"
    assert mix_manifest["returncode"] == 1
    assert mix_manifest["stderr"] == "audio mix failed"
    assert any("audio mix failed" in error for error in mix_manifest["errors"])

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    assert inspection["status"] == "fail"
    assert review["status"] == "failed"


def test_bgm_mix_config_rejects_unsafe_output_name() -> None:
    from narratocut.bgm_sop import BGMMixConfig

    with pytest.raises(ValueError, match="safe relative file name"):
        BGMMixConfig(output_name="../outside.mp4")


def test_bgm_mix_config_rejects_volume_above_one() -> None:
    from narratocut.bgm_sop import BGMMixConfig

    with pytest.raises(ValueError, match="between 0 and 1"):
        BGMMixConfig(bgm_volume=1.5)

    with pytest.raises(ValueError, match="between 0 and 1"):
        BGMMixConfig(original_audio_volume=1.5)


def test_bgm_mix_command_loops_bgm_and_maps_video() -> None:
    from narratocut.bgm_sop import BGMMixConfig, build_ffmpeg_bgm_mix_command

    command = build_ffmpeg_bgm_mix_command(
        source_video="final_video.mp4",
        bgm_audio="bgm.mp3",
        output_video="final_video_with_bgm.mp4",
        config=BGMMixConfig(),
    )

    assert command[command.index("-stream_loop") + 1] == "-1"
    assert command[command.index("-map") + 1] == "0:v:0"
    assert "-filter_complex" in command
    assert "-shortest" in command


def test_bgm_mix_command_supports_bgm_only_strategy_for_silent_video() -> None:
    from narratocut.bgm_sop import BGMMixConfig, build_ffmpeg_bgm_mix_command

    command = build_ffmpeg_bgm_mix_command(
        source_video="silent_final_video.mp4",
        bgm_audio="bgm.mp3",
        output_video="final_video_with_bgm.mp4",
        config=BGMMixConfig(mix_strategy="bgm_only"),
    )

    assert "0:a" not in " ".join(command)
    assert command[command.index("-map") + 1] == "0:v:0"
    assert "[aout]" in command


def test_draft_workflow_plan_lists_bgm_mix_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path=WORKFLOW,
        input_path="examples/demo_bgm/final_video_with_bgm_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == ["mix_bgm", "probe_bgm_mix"]
    expected = plan["artifacts"]["expected"]
    assert "audio_mix_manifest.json" in expected
    assert "final_video_with_bgm.mp4" in expected


def _write_input_bundle(
    tmp_path: Path,
    *,
    missing_video: bool = False,
    missing_bgm: bool = False,
    output_name: str = "final_video_with_bgm.mp4",
) -> Path:
    final_video = tmp_path / "final_video.mp4"
    if not missing_video:
        final_video.write_bytes(b"fake final video")
    bgm = tmp_path / "bgm.mp3"
    if not missing_bgm:
        bgm.write_bytes(b"fake bgm")
    input_path = tmp_path / "final_video_with_bgm_input.json"
    write_json(
        input_path,
        {
            "final_video_path": str(final_video),
            "bgm_path": str(bgm),
            "bgm_volume": 0.2,
            "original_audio_volume": 1.0,
            "output_name": output_name,
        },
    )
    return input_path


def _patch_bgm_mix_tools(
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
        output_path.write_bytes(b"fake bgm video")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("narratocut.workflow_engine.bgm_nodes.check_ffmpeg_available", fake_tool_check)
    monkeypatch.setattr("narratocut.workflow_engine.bgm_nodes.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.harness.bgm_quality.probe_video_metadata", fake_probe)
    monkeypatch.setattr("narratocut.bgm_sop.mix.subprocess.run", ffmpeg_run or fake_run)
