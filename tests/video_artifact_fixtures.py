from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.utils import write_json


def write_video_transcript_input(tmp_path: Path) -> Path:
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")
    fixture_path = tmp_path / "transcript_fixture.json"
    fixture_path.write_text(json.dumps(base_transcript(provider="mock")), encoding="utf-8")
    input_path = tmp_path / "video_to_transcript_input.json"
    input_path.write_text(
        json.dumps(
            {
                "video_path": str(source_video),
                "asr_fixture_path": str(fixture_path),
                "audio_extraction_mode": "mock",
            }
        ),
        encoding="utf-8",
    )
    return input_path


def write_video_highlight_input(tmp_path: Path) -> Path:
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")
    fixture_path = tmp_path / "transcript_fixture.json"
    fixture_path.write_text(json.dumps(base_transcript(provider="mock")), encoding="utf-8")
    roi_path = tmp_path / "roi_config.json"
    roi_path.write_text(json.dumps(roi_payload()), encoding="utf-8")
    input_path = tmp_path / "video_to_highlight_clip_plan_input.json"
    input_path.write_text(
        json.dumps(
            {
                "video_path": str(source_video),
                "asr_fixture_path": str(fixture_path),
                "roi_config_path": str(roi_path),
                "audio_extraction_mode": "mock",
                "input_mode": "timestamped_transcript",
                "max_highlights": 3,
            }
        ),
        encoding="utf-8",
    )
    return input_path


def write_video_run(
    run_dir: Path,
    *,
    quality_profile: str,
    transcript: dict[str, Any],
    highlight_plan: dict[str, Any] | None = None,
    clip_plan: dict[str, Any] | None = None,
) -> Path:
    run_dir.mkdir(parents=True)
    audio_dir = run_dir / "audio"
    audio_dir.mkdir()
    (audio_dir / "audio.wav").write_text("mock audio", encoding="utf-8")
    artifacts = _artifacts(highlight_plan=highlight_plan, clip_plan=clip_plan)
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": run_dir.name,
            "workflow": "workflows/video_to_transcript.yaml",
            "workflow_mode": quality_profile,
            "quality_profile": quality_profile,
            "artifacts": artifacts,
        },
    )
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "write_transcript", "status": "success"}]})
    write_json(run_dir / "manifest.json", {"status": "success"})
    write_json(run_dir / "audio_manifest.json", audio_manifest(audio_dir))
    write_json(run_dir / "transcript.json", transcript)
    if highlight_plan is not None:
        write_json(run_dir / "highlight_plan.json", highlight_plan)
    if clip_plan is not None:
        write_json(run_dir / "clip_plan.json", clip_plan)
    return run_dir


def base_transcript(*, provider: str) -> dict[str, Any]:
    return {
        "transcript_id": "video_transcript",
        "source_video": "input.mp4",
        "language": "en",
        "duration": 12.0,
        "segments": [
            _segment("seg_001", 0.0, 4.0, "Most teams chase automation first, but the real bottleneck is choosing what to cut."),
            _segment("seg_002", 4.0, 8.0, "A stable transcript lets highlight detection reuse existing workflow contracts."),
            _segment("seg_003", 8.0, 12.0, "Validate the story before spending time on real slicing or final assembly."),
        ],
        "metadata": {
            "asr_provider": provider,
            "audio_path": "audio/audio.wav",
            "transcript_source": "fixture",
        },
    }


def base_highlight_plan(*, source_segment_ids: list[str]) -> dict[str, Any]:
    return {
        "plan_id": "highlight_plan_video",
        "input_mode": "timestamped_transcript",
        "source_id": "video_transcript",
        "highlights": [
            {
                "highlight_id": "hl_001",
                "source_type": "transcript",
                "highlight_type": "hook",
                "title": "Hook",
                "text": "Most teams chase automation first.",
                "reason": "Strong opening contrast.",
                "score": 0.8,
                "confidence": 0.9,
                "roi_tags": ["hook_strength"],
                "source_segment_ids": source_segment_ids,
                "start_time": 0.0,
                "end_time": 4.0,
                "suggested_duration": 4.0,
                "metadata": {"ranking_factors": {"final_score": 0.88}},
            }
        ],
        "summary": "test plan",
        "warnings": [],
        "metadata": {},
        "created_at": "2026-05-18T00:00:00Z",
    }


def base_clip_plan(*, source_segment_ids: list[str]) -> dict[str, Any]:
    return {
        "clip_plan_id": "clip_plan_highlight_plan_video",
        "project_id": "video_transcript",
        "hook_id": "hl_001",
        "script_id": None,
        "duration_sec": 4.0,
        "title": "Hook",
        "cover_text": "Most teams chase automation first.",
        "segments": [
            {
                "segment_id": "clip_plan_seg_001",
                "source_video": "input.mp4",
                "start_sec": 0.0,
                "end_sec": 4.0,
                "text": "Most teams chase automation first.",
                "metadata": {
                    "highlight_id": "hl_001",
                    "source_segment_ids": source_segment_ids,
                    "ranking_factors": {"final_score": 0.88},
                },
            }
        ],
        "voiceover_text": None,
        "cta_text": None,
        "output_name": "clip_plan.mp4",
        "metadata": {"source": "phase10_highlight_clip_plan_generator"},
        "created_at": "2026-05-18T00:00:00Z",
    }


def roi_payload() -> dict[str, object]:
    return {
        "target_platform": "douyin",
        "target_audience": "product builders",
        "content_goal": "increase_completion_rate",
        "min_clip_duration": 1,
        "max_clip_duration": 30,
        "target_clip_count": 3,
        "min_clip_count": 1,
        "max_clip_count": 5,
        "risk_tolerance": "low",
        "priority": ["hook_strength", "clarity", "watch_completion"],
        "validation_policy": "advisory",
    }


def audio_manifest(audio_dir: Path) -> dict[str, Any]:
    return {
        "source_video": "input.mp4",
        "audio_path": "audio/audio.wav",
        "status": "mocked",
        "extraction_mode": "mock",
        "sample_rate": 16000,
        "channels": 1,
        "codec": "pcm_s16le",
        "manifest_path": "audio_manifest.json",
        "error": None,
        "metadata": {
            "executed": False,
            "ffmpeg_command": [],
            "absolute_audio_path": str(audio_dir / "audio.wav"),
        },
    }


def _artifacts(
    *,
    highlight_plan: dict[str, Any] | None,
    clip_plan: dict[str, Any] | None,
) -> dict[str, str]:
    artifacts = {
        "audio_manifest": "audio_manifest.json",
        "audio": "audio/audio.wav",
        "transcript": "transcript.json",
        "manifest": "manifest.json",
    }
    if highlight_plan is not None:
        artifacts["highlight_plan"] = "highlight_plan.json"
    if clip_plan is not None:
        artifacts["clip_plan"] = "clip_plan.json"
    return artifacts


def _segment(segment_id: str, start: float, end: float, text: str) -> dict[str, Any]:
    return {
        "segment_id": segment_id,
        "start_time": start,
        "end_time": end,
        "text": text,
        "speaker": "speaker_1",
        "confidence": 0.97,
        "metadata": {},
    }
