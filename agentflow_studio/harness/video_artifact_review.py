from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.harness.quality_profiles import VIDEO_REAL_CLIPS_PROFILE
from agentflow_studio.harness.video_artifacts import (
    MOCK_ASR_TRANSCRIPT_PROFILE,
    REAL_ASR_PROFILES,
    build_video_quality_report,
    is_video_highlight_quality_profile,
)


def build_video_review_section(root: str | Path, run_manifest: dict[str, Any] | None) -> dict[str, Any]:
    profile = str(run_manifest.get("quality_profile") if run_manifest else "")
    report = build_video_quality_report(root, profile)
    video_check_names = _video_review_check_names(profile)
    checks = [
        _review_check(check)
        for check in report["checks"]
        if check["name"] in video_check_names
    ]
    return {
        "name": "video_artifacts",
        "status": _review_status(checks),
        "checks": checks,
    }


def _video_review_check_names(profile: str) -> set[str]:
    names = {
        "audio_manifest_exists",
        "audio_manifest_status_valid",
        "audio_manifest_execution_consistent",
        "audio_artifact_exists",
        "transcript_exists",
        "transcript_schema_valid",
        "transcript_segments_non_empty",
        "transcript_segment_time_ranges_valid",
        "transcript_segments_monotonic",
        "transcript_segment_text_non_empty",
        "transcript_provider_metadata_present",
    }
    if profile in {MOCK_ASR_TRANSCRIPT_PROFILE, "video_highlight_clip_plan", VIDEO_REAL_CLIPS_PROFILE}:
        names.add("mock_asr_provider_marked")
    if profile in REAL_ASR_PROFILES:
        names.update({"real_asr_provider_marked", "api_secret_values_not_recorded"})
    if is_video_highlight_quality_profile(profile):
        names.update({"highlight_source_segments_exist_in_transcript", "clip_source_segments_exist_in_transcript"})
    return names


def _review_check(check: dict[str, Any]) -> dict[str, Any]:
    status = check["status"]
    mapped = "passed" if status == "pass" else "warning" if status == "warning" else "failed"
    result = {"id": check["name"], "status": mapped, "message": f"{check['name']} {status}"}
    if "details" in check:
        result["details"] = check["details"]
    return result


def _review_status(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "failed" for check in checks):
        return "failed"
    if any(check["status"] == "warning" for check in checks):
        return "warning"
    return "passed"
