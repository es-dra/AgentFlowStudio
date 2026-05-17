from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app
from narratocut.utils import write_json


def test_slice_real_command_writes_real_slice_manifest(tmp_path, monkeypatch) -> None:
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"not a real video")
    clip_plans_path = tmp_path / "clip_plans.json"
    output_dir = tmp_path / "real_slicing_demo"
    write_json(clip_plans_path, [_clip_plan_payload()])

    def fake_slice_clip_plans_real(input_video, clip_plans, output_dir, config):
        return {
            "status": "passed",
            "clip_count": len(clip_plans),
            "clips": [
                {
                    "clip_id": "clip_001",
                    "path": "clips/clip_001.mp4",
                    "status": "passed",
                    "start_sec": 0,
                    "end_sec": 1,
                    "duration_sec": 1,
                }
            ],
            "errors": [],
            "manifest_path": "real_slice_manifest.json",
        }

    monkeypatch.setattr(
        "apps.cli.real_slicing_commands.slice_clip_plans_real",
        fake_slice_clip_plans_real,
    )

    result = CliRunner().invoke(
        app,
        [
            "slice-real",
            "--video",
            str(input_video),
            "--clip-plans",
            str(clip_plans_path),
            "--output",
            str(output_dir),
            "--ffmpeg",
            "ffmpeg-test",
            "--no-overwrite",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Real slicing completed" in result.output
    assert "Status: passed" in result.output
    assert "Clips: 1" in result.output
    assert f"Output: {output_dir}" in result.output


def test_slice_real_command_returns_failure_for_failed_manifest(tmp_path, monkeypatch) -> None:
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"not a real video")
    clip_plans_path = tmp_path / "clip_plans.json"
    write_json(clip_plans_path, [_clip_plan_payload()])

    def fake_slice_clip_plans_real(input_video, clip_plans, output_dir, config):
        return {
            "status": "failed",
            "clip_count": 0,
            "clips": [],
            "errors": ["ffmpeg_unavailable"],
            "manifest_path": "real_slice_manifest.json",
        }

    monkeypatch.setattr(
        "apps.cli.real_slicing_commands.slice_clip_plans_real",
        fake_slice_clip_plans_real,
    )

    result = CliRunner().invoke(
        app,
        [
            "slice-real",
            "--video",
            str(input_video),
            "--clip-plans",
            str(clip_plans_path),
            "--output",
            str(tmp_path / "real_slicing_demo"),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "Status: failed" in result.output
    assert "Error: ffmpeg_unavailable" in result.output


def _clip_plan_payload() -> dict[str, object]:
    return {
        "clip_plan_id": "clip_plan_demo",
        "project_id": "project_demo",
        "hook_id": "hook_demo",
        "title": "Demo clip",
        "cover_text": "Demo",
        "segments": [
            {
                "segment_id": "segment_demo",
                "source_video": "source.mp4",
                "start_sec": 0,
                "end_sec": 1,
            }
        ],
    }
