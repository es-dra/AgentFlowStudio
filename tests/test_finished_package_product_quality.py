from __future__ import annotations

import json
from pathlib import Path

from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratocut.utils import write_json


def test_finished_package_quality_warns_for_demo_smoke_quality_gaps(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    final_video = tmp_path / "final_video.mp4"
    subtitled_video = tmp_path / "final_video_with_subtitles.mp4"
    bgm_video = tmp_path / "final_video_with_bgm.mp4"
    cover = tmp_path / "cover.jpg"
    review = tmp_path / "review_report.json"
    for path in [final_video, subtitled_video, bgm_video, cover]:
        path.write_bytes(b"fake media")
    write_json(review, {"status": "passed"})
    real_slice = _write_real_slice_manifest(tmp_path)
    clip_plan = _write_clip_plan_without_highlight_evidence(tmp_path)
    subtitle_manifest = _write_unmatched_subtitle_manifest(tmp_path)
    audio_mix_manifest = _write_unverified_audio_mix_manifest(tmp_path)
    final_video_manifest = _write_final_video_manifest(tmp_path, final_video)
    _write_package_run_manifest(run_dir)
    write_json(run_dir / "manifest.json", {"run_id": "run", "status": "success"})
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "write_finished_package", "status": "success"}]})
    write_json(
        run_dir / "finished_package_manifest.json",
        {
            "schema_version": "0.1",
            "status": "succeeded",
            "package_id": "pkg",
            "primary_video": {"role": "final_video", "path": str(final_video), "required": True, "exists": True},
            "assets": [
                {"role": "final_video", "path": str(final_video), "required": True, "exists": True},
                {"role": "subtitled_video", "path": str(subtitled_video), "required": False, "exists": True},
                {"role": "bgm_video", "path": str(bgm_video), "required": False, "exists": True},
                {"role": "cover_image", "path": str(cover), "required": False, "exists": True},
                {"role": "review_report", "path": str(review), "required": False, "exists": True},
            ],
            "evidence": {
                "real_slice_manifest": str(real_slice),
                "clip_plan": str(clip_plan),
                "subtitle_manifest": str(subtitle_manifest),
                "audio_mix_manifest": str(audio_mix_manifest),
                "final_video_manifest": str(final_video_manifest),
            },
            "errors": [],
            "warnings": [],
            "manifest_path": "finished_package_manifest.json",
        },
    )

    inspection = inspect_run(run_dir)
    review_report = review_run(run_dir)

    assert inspection["status"] == "pass"
    assert review_report["status"] == "warning"
    warnings = set(inspection["quality_report"]["warnings"])
    assert {
        "product_quality_warning: single_clip_only",
        "product_quality_warning: clip_starts_at_zero_only",
        "product_quality_warning: no_highlight_evidence",
        "product_quality_warning: subtitle_source_video_missing",
        "product_quality_warning: subtitle_duration_exceeds_primary_video",
        "product_quality_warning: bgm_quality_unverified",
    } <= warnings
    package_section = next(section for section in review_report["sections"] if section["name"] == "finished_package_outputs")
    warning_ids = {check["id"] for check in package_section["checks"] if check["status"] == "warning"}
    assert "product_quality_single_clip_only" in warning_ids
    assert "product_quality_subtitle_source_video_missing" in warning_ids


def _write_real_slice_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "real_slice_manifest.json"
    write_json(
        path,
        {
            "status": "succeeded",
            "clip_count": 1,
            "clips": [{"clip_id": "clip_001", "start_sec": 0.0, "end_sec": 10.0}],
        },
    )
    return path


def _write_clip_plan_without_highlight_evidence(tmp_path: Path) -> Path:
    path = tmp_path / "clip_plan.json"
    write_json(
        path,
        {
            "segments": [
                {
                    "segment_id": "seg_001",
                    "start_sec": 0.0,
                    "end_sec": 10.0,
                    "metadata": {},
                }
            ]
        },
    )
    return path


def _write_unmatched_subtitle_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "subtitle_manifest.json"
    write_json(path, {"status": "succeeded", "source_video": None, "duration_sec": 12.4})
    return path


def _write_unverified_audio_mix_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "audio_mix_manifest.json"
    write_json(
        path,
        {
            "status": "succeeded",
            "bgm_path": "data/raw/demo_bgm/bgm.wav",
            "duration_sec": 10.0,
        },
    )
    return path


def _write_final_video_manifest(tmp_path: Path, final_video: Path) -> Path:
    path = tmp_path / "final_video_manifest.json"
    write_json(path, {"status": "succeeded", "final_video": str(final_video), "duration_sec": 10.0})
    return path


def _write_package_run_manifest(run_dir: Path) -> None:
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "run",
            "workflow": "workflows/final_video_package.yaml",
            "workflow_mode": "final_video_package",
            "quality_profile": "finished_package",
            "artifacts": {
                "finished_package_manifest": "finished_package_manifest.json",
            },
        },
    )
