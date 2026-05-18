from __future__ import annotations

from narratocut.harness import real_clip_quality
from narratocut.harness.quality_checks import build_quality_report
from narratocut.schemas import VideoMetadata
from narratocut.utils import write_json


def test_real_video_quality_profile_reports_failed_slice_manifest(tmp_path) -> None:
    run_dir = tmp_path / "real_run"
    run_dir.mkdir()
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "real_run",
            "workflow": "workflows/real_video_roi_to_clips.yaml",
            "workflow_mode": "real_video",
            "quality_profile": "real_video",
            "artifacts": {
                "video_metadata": "video_metadata.json",
                "clip_plan_validation": "clip_plan_validation.json",
                "real_slice_manifest": "real_slice_manifest.json",
                "clips": "clips",
            },
        },
    )
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "real_slice_video"}]})
    write_json(run_dir / "manifest.json", {"status": "failed"})
    write_json(run_dir / "video_metadata.json", {"probe_status": "failed", "errors": ["ffprobe_unavailable"]})
    write_json(
        run_dir / "clip_plan_validation.json",
        {"status": "failed", "hard_errors": [{"code": "ffmpeg_unavailable"}], "warnings": [], "checks": []},
    )
    write_json(
        run_dir / "real_slice_manifest.json",
        {"status": "failed", "reason": "ffmpeg_unavailable", "clips": [], "errors": ["ffmpeg_unavailable"]},
    )

    report = build_quality_report(run_dir)

    assert report["status"] == "fail"
    checks = {check["name"]: check for check in report["checks"]}
    assert checks["real_slice_manifest_status"]["status"] == "fail"
    assert any("ffmpeg_unavailable" in error for error in report["errors"])


def test_real_video_quality_profile_checks_clip_duration_when_ffprobe_available(
    tmp_path,
    monkeypatch,
) -> None:
    run_dir = tmp_path / "real_run"
    clips_dir = run_dir / "clips"
    clips_dir.mkdir(parents=True)
    (clips_dir / "clip_001.mp4").write_bytes(b"fake-video")
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "real_run",
            "workflow": "workflows/real_video_roi_to_clips.yaml",
            "workflow_mode": "real_video",
            "quality_profile": "real_video",
            "artifacts": {
                "video_metadata": "video_metadata.json",
                "clip_plan_validation": "clip_plan_validation.json",
                "real_slice_manifest": "real_slice_manifest.json",
                "clips": "clips",
            },
        },
    )
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "real_slice_video"}]})
    write_json(run_dir / "manifest.json", {"status": "success"})
    write_json(run_dir / "video_metadata.json", {"probe_status": "succeeded", "duration_sec": 10})
    write_json(run_dir / "clip_plan_validation.json", {"status": "passed", "hard_errors": [], "warnings": []})
    write_json(
        run_dir / "real_slice_manifest.json",
        {
            "status": "succeeded",
            "clips": [
                {
                    "clip_id": "clip_001",
                    "status": "succeeded",
                    "path": "clips/clip_001.mp4",
                    "duration_sec": 2.0,
                }
            ],
            "errors": [],
        },
    )

    def fake_probe(video_path, ffprobe_executable="ffprobe", timeout_sec=30):  # noqa: ANN001, ANN202
        return VideoMetadata(
            file_path=str(video_path),
            duration_sec=2.1,
            probe_status="succeeded",
        )

    monkeypatch.setattr(real_clip_quality, "probe_video_metadata", fake_probe)

    report = build_quality_report(run_dir)

    checks = [check for check in report["checks"] if check["name"] == "real_clip_duration_tolerance"]
    assert report["status"] == "pass"
    assert checks
    assert checks[0]["status"] == "pass"
