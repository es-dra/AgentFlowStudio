from __future__ import annotations

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.schemas import ClipPlan, ClipSegment, ROISettings
from agentflow_studio.utils import write_json


def test_real_video_workflow_writes_reviewable_failure_artifacts_when_ffprobe_is_missing(
    tmp_path,
    monkeypatch,
) -> None:
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake video")
    roi_path = tmp_path / "roi_config.json"
    clip_plan_path = tmp_path / "clip_plan.json"
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "run"
    write_json(roi_path, _roi())
    write_json(clip_plan_path, _clip_plan())
    write_json(
        input_path,
        {
            "project": {"project_id": "demo_real_video", "name": "Demo"},
            "video": {"path": str(video)},
            "roi": {"path": str(roi_path)},
            "clip_plan": {"path": str(clip_plan_path)},
            "output": {"clips_dir": "clips"},
        },
    )

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("missing tool")

    monkeypatch.setattr("agentflow_studio.slicing_sop.video_metadata.subprocess.run", fake_run)
    monkeypatch.setattr("agentflow_studio.slicing_sop.ffmpeg_probe.subprocess.run", fake_run)

    status, _ = run_workflow_from_cli(
        workflow_path="workflows/real_video_roi_to_clips.yaml",
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    assert (output_dir / "run_manifest.json").is_file()
    assert (output_dir / "trace.json").is_file()
    assert (output_dir / "video_metadata.json").is_file()
    assert (output_dir / "clip_plan_validation.json").is_file()
    assert (output_dir / "real_slice_manifest.json").is_file()
    manifest = (output_dir / "real_slice_manifest.json").read_text(encoding="utf-8")
    assert "clip_plan_validation_failed" in manifest


def _roi() -> ROISettings:
    return ROISettings(
        target_platform="douyin",
        target_audience="college students",
        content_goal="increase_completion_rate",
        min_clip_duration=8,
        max_clip_duration=30,
        target_clip_count=1,
        min_clip_count=1,
        max_clip_count=3,
        risk_tolerance="low",
        priority=["hook_strength"],
    )


def _clip_plan() -> ClipPlan:
    return ClipPlan(
        clip_plan_id="clip_plan_demo",
        project_id="demo_real_video",
        hook_id="hook_demo",
        title="Demo",
        cover_text="Demo",
        output_name="clip_demo.mp4",
        segments=[
            ClipSegment(
                segment_id="seg_001",
                source_video="input.mp4",
                start_sec=0,
                end_sec=10,
            )
        ],
    )
