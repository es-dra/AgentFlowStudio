from __future__ import annotations

import subprocess
from pathlib import Path

from narratocut.schemas import ClipPlan, ClipSegment
from narratocut.slicing_sop.real_slicer import RealSlicingConfig, slice_clip_plans_real


def test_slice_clip_plans_real_runs_ffmpeg_for_each_clip_plan(tmp_path, monkeypatch) -> None:
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"not a real video")
    clip_plans = [
        _clip_plan("clip_plan_a", 0, 3),
        _clip_plan("clip_plan_b", 3, 5.5),
    ]
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("narratocut.slicing_sop.real_slicer.subprocess.run", fake_run)

    manifest = slice_clip_plans_real(
        input_video=input_video,
        clip_plans=clip_plans,
        output_dir=tmp_path / "real_slices",
        config=RealSlicingConfig(ffmpeg_executable="ffmpeg-test", overwrite=False),
    )

    assert manifest["status"] == "succeeded"
    assert manifest["clip_count"] == 2
    assert manifest["errors"] == []
    assert [clip["path"] for clip in manifest["clips"]] == [
        "clips/clip_001.mp4",
        "clips/clip_002.mp4",
    ]
    assert manifest["clips"][0]["start_sec"] == 0
    assert manifest["clips"][0]["end_sec"] == 3
    assert manifest["clips"][0]["duration_sec"] == 3
    assert calls == [
        [
            "ffmpeg-test",
            "-n",
            "-ss",
            "0",
            "-i",
            str(input_video),
            "-t",
            "3",
            str(tmp_path / "real_slices" / "clips" / "clip_001.mp4"),
        ],
        [
            "ffmpeg-test",
            "-n",
            "-ss",
            "3",
            "-i",
            str(input_video),
            "-t",
            "2.5",
            str(tmp_path / "real_slices" / "clips" / "clip_002.mp4"),
        ],
    ]


def test_slice_clip_plans_real_writes_manifest(tmp_path, monkeypatch) -> None:
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"not a real video")

    def fake_run(command, capture_output, text, check):
        output_path = Path(command[-1])
        output_path.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("narratocut.slicing_sop.real_slicer.subprocess.run", fake_run)

    manifest = slice_clip_plans_real(
        input_video=input_video,
        clip_plans=[_clip_plan("clip_plan_a", 0, 1)],
        output_dir=tmp_path / "real_slices",
    )

    manifest_path = tmp_path / "real_slices" / "real_slice_manifest.json"
    assert manifest_path.is_file()
    assert manifest["manifest_path"] == "real_slice_manifest.json"


def test_slice_clip_plans_real_honors_configured_clips_dir(tmp_path, monkeypatch) -> None:
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"not a real video")

    def fake_run(command, capture_output, text, check):
        output_path = Path(command[-1])
        output_path.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("narratocut.slicing_sop.real_slicer.subprocess.run", fake_run)

    manifest = slice_clip_plans_real(
        input_video=input_video,
        clip_plans=[_clip_plan("clip_plan_a", 0, 1)],
        output_dir=tmp_path / "real_slices",
        config=RealSlicingConfig(clips_dir="custom_clips"),
    )

    assert manifest["clips"][0]["path"] == "custom_clips/clip_001.mp4"
    assert (tmp_path / "real_slices" / "custom_clips" / "clip_001.mp4").is_file()


def test_slice_clip_plans_real_reports_ffmpeg_failure(tmp_path, monkeypatch) -> None:
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"not a real video")

    def fake_run(command, capture_output, text, check):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="ffmpeg failed")

    monkeypatch.setattr("narratocut.slicing_sop.real_slicer.subprocess.run", fake_run)

    manifest = slice_clip_plans_real(
        input_video=input_video,
        clip_plans=[_clip_plan("clip_plan_a", 0, 1)],
        output_dir=tmp_path / "real_slices",
    )

    assert manifest["status"] == "failed"
    assert manifest["clip_count"] == 0
    assert manifest["clips"][0]["status"] == "failed"
    assert manifest["errors"]


def test_slice_clip_plans_real_reports_missing_input_without_subprocess(tmp_path, monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess should not be called")

    monkeypatch.setattr("narratocut.slicing_sop.real_slicer.subprocess.run", fail_if_called)

    manifest = slice_clip_plans_real(
        input_video=tmp_path / "missing.mp4",
        clip_plans=[_clip_plan("clip_plan_a", 0, 1)],
        output_dir=tmp_path / "real_slices",
    )

    assert manifest["status"] == "failed"
    assert "input_video_missing" in manifest["errors"][0]


def test_slice_clip_plans_real_reports_missing_ffmpeg(tmp_path, monkeypatch) -> None:
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"not a real video")

    def fake_run(command, capture_output, text, check):
        raise FileNotFoundError("ffmpeg missing")

    monkeypatch.setattr("narratocut.slicing_sop.real_slicer.subprocess.run", fake_run)

    manifest = slice_clip_plans_real(
        input_video=input_video,
        clip_plans=[_clip_plan("clip_plan_a", 0, 1)],
        output_dir=tmp_path / "real_slices",
        config=RealSlicingConfig(ffmpeg_executable="ffmpeg-missing"),
    )

    assert manifest["status"] == "failed"
    assert manifest["clip_count"] == 0
    assert "ffmpeg_executable_not_found" in manifest["errors"][0]


def _clip_plan(clip_plan_id: str, start: float, end: float) -> ClipPlan:
    return ClipPlan(
        clip_plan_id=clip_plan_id,
        project_id="project_demo",
        hook_id="hook_demo",
        title="Demo clip",
        cover_text="Demo",
        segments=[
            ClipSegment(
                segment_id=f"{clip_plan_id}_segment",
                source_video="source.mp4",
                start_sec=start,
                end_sec=end,
            )
        ],
    )
