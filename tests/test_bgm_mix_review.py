from __future__ import annotations

from pathlib import Path

from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratocut.schemas import VideoMetadata
from narratocut.utils import write_json


def test_bgm_mix_review_fails_when_manifest_succeeds_but_output_missing(tmp_path) -> None:
    run_dir = _write_manifest_run(tmp_path)

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "fail"
    assert review["status"] == "failed"
    bgm_section = next(section for section in review["sections"] if section["name"] == "bgm_mix_outputs")
    failed_ids = {check["id"] for check in bgm_section["checks"] if check["status"] == "failed"}
    assert "bgm_mix_output_file_exists" in failed_ids


def test_bgm_mix_review_warns_on_known_ffmpeg_warning(tmp_path) -> None:
    run_dir = _write_manifest_run(
        tmp_path,
        stderr="Non-monotonic DTS in output stream 0:0",
    )
    (run_dir / "final_video_with_bgm.mp4").write_bytes(b"fake bgm video")

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "pass"
    assert review["status"] == "warning"
    bgm_section = next(section for section in review["sections"] if section["name"] == "bgm_mix_outputs")
    warning_ids = {check["id"] for check in bgm_section["checks"] if check["status"] == "warning"}
    assert "bgm_mix_ffmpeg_warnings" in warning_ids


def test_bgm_mix_review_warns_on_duration_drift(tmp_path, monkeypatch) -> None:
    run_dir = _write_manifest_run(tmp_path, duration_sec=8.0)
    (run_dir / "final_video_with_bgm.mp4").write_bytes(b"fake bgm video")

    def fake_probe(video_path, ffprobe_executable="ffprobe", timeout_sec=30):  # noqa: ANN001, ANN202
        return VideoMetadata(
            file_path=str(video_path),
            duration_sec=11.5,
            width=1080,
            height=1920,
            codec="h264",
            fps=30,
            bitrate=1000,
            probe_status="succeeded",
            errors=[],
        )

    monkeypatch.setattr("narratocut.harness.bgm_quality.probe_video_metadata", fake_probe)

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "pass"
    assert review["status"] == "warning"
    bgm_section = next(section for section in review["sections"] if section["name"] == "bgm_mix_outputs")
    warning_ids = {check["id"] for check in bgm_section["checks"] if check["status"] == "warning"}
    assert "bgm_mix_duration_tolerance" in warning_ids


def _write_manifest_run(
    tmp_path: Path,
    *,
    stderr: str = "",
    duration_sec: float = 8.0,
) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "run",
            "workflow": "workflows/final_video_with_bgm.yaml",
            "workflow_mode": "final_video_with_bgm",
            "quality_profile": "bgm_mix",
            "artifacts": {
                "audio_mix_manifest": "audio_mix_manifest.json",
                "bgm_video": "final_video_with_bgm.mp4",
            },
        },
    )
    write_json(run_dir / "manifest.json", {"run_id": "run", "status": "success"})
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "mix_bgm", "status": "success"}]})
    write_json(
        run_dir / "audio_mix_manifest.json",
        {
            "status": "succeeded",
            "source_video": "final_video.mp4",
            "bgm_path": "bgm.mp3",
            "output_video": "final_video_with_bgm.mp4",
            "bgm_volume": 0.2,
            "original_audio_volume": 1.0,
            "duration_sec": duration_sec,
            "ffmpeg_command": ["ffmpeg", "-y"],
            "returncode": 0,
            "stdout": "",
            "stderr": stderr,
            "errors": [],
            "warnings": [],
            "manifest_path": "audio_mix_manifest.json",
        },
    )
    return run_dir
