from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agentflow_studio.harness.highlight_artifacts import (
    HIGHLIGHT_CLIP_PLAN_PROFILE,
    build_highlight_quality_report,
)
from agentflow_studio.harness.quality_profiles import VIDEO_REAL_CLIPS_PROFILE
from agentflow_studio.harness.video_artifact_checks import (
    all_clip_source_ids_known,
    all_source_ids_known,
    audio_execution_is_consistent,
    segment_time_range_valid,
    segments_monotonic,
    text_non_empty,
    transcript_provider,
    transcript_schema_valid,
    transcript_segment_ids,
)
from agentflow_studio.harness.video_artifact_summaries import (
    audio_summary,
    clip_plan_summary,
    highlight_plan_summary,
    transcript_summary,
)


MOCK_ASR_TRANSCRIPT_PROFILE = "mock_asr_transcript"
REAL_ASR_TRANSCRIPT_PROFILE = "real_asr_transcript"
VIDEO_HIGHLIGHT_CLIP_PLAN_PROFILE = "video_highlight_clip_plan"
REAL_ASR_HIGHLIGHT_CLIP_PLAN_PROFILE = "real_asr_highlight_clip_plan"
VIDEO_TRANSCRIPT_PROFILES = {MOCK_ASR_TRANSCRIPT_PROFILE, REAL_ASR_TRANSCRIPT_PROFILE}
VIDEO_HIGHLIGHT_PROFILES = {
    VIDEO_HIGHLIGHT_CLIP_PLAN_PROFILE,
    REAL_ASR_HIGHLIGHT_CLIP_PLAN_PROFILE,
    VIDEO_REAL_CLIPS_PROFILE,
}
VIDEO_QUALITY_PROFILES = VIDEO_TRANSCRIPT_PROFILES | VIDEO_HIGHLIGHT_PROFILES
REAL_ASR_PROFILES = {REAL_ASR_TRANSCRIPT_PROFILE, REAL_ASR_HIGHLIGHT_CLIP_PLAN_PROFILE}
SECRET_SCAN_FILES = ["manifest.json", "run_manifest.json", "trace.json", "quality_report.json", "transcript.json", "audio_manifest.json"]
SECRET_VALUE_RE = re.compile(r"(^|[^A-Za-z0-9])sk-[A-Za-z0-9][A-Za-z0-9._-]{6,}")


def is_video_quality_profile(value: object) -> bool:
    return str(value or "") in VIDEO_QUALITY_PROFILES


def is_video_highlight_quality_profile(value: object) -> bool:
    return str(value or "") in VIDEO_HIGHLIGHT_PROFILES


def video_artifacts_to_inspect(quality_profile: object) -> list[str]:
    artifacts = [
        "audio_manifest.json",
        "audio/audio.wav",
        "transcript.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]
    if is_video_highlight_quality_profile(quality_profile):
        artifacts.insert(3, "highlight_plan.json")
        artifacts.insert(4, "clip_plan.json")
    if str(quality_profile or "") == VIDEO_REAL_CLIPS_PROFILE:
        artifacts.extend(["video_metadata.json", "clip_plan_validation.json", "real_slice_manifest.json", "clips/"])
    return artifacts


def build_video_quality_report(root: str | Path, quality_profile: object) -> dict[str, Any]:
    run_dir = Path(root)
    profile = str(quality_profile or "")
    audio_manifest = _read_json_object(run_dir / "audio_manifest.json")
    transcript = _read_json_object(run_dir / "transcript.json")
    highlight_plan = _read_json_object(run_dir / "highlight_plan.json")
    clip_plan = _read_json_object(run_dir / "clip_plan.json")

    checks: list[dict[str, Any]] = []
    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    _add_audio_checks(run_dir, audio_manifest, checks)
    _add_transcript_checks(run_dir, transcript, profile, checks)

    if is_video_highlight_quality_profile(profile):
        highlight_report = build_highlight_quality_report(run_dir, HIGHLIGHT_CLIP_PLAN_PROFILE)
        checks.extend(highlight_report["checks"])
        _add_source_segment_reference_checks(transcript, highlight_plan, clip_plan, checks)

    if profile in REAL_ASR_PROFILES:
        _add_secret_scan_check(run_dir, checks)

    failed = [check for check in checks if check["status"] == "fail"]
    warnings = [check["name"] for check in checks if check["status"] == "warning"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": warnings,
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "quality_profile": profile,
            "audio_manifest": audio_summary(audio_manifest),
            "transcript": transcript_summary(transcript),
            "highlight_plan": highlight_plan_summary(highlight_plan),
            "clip_plan": clip_plan_summary(clip_plan),
        },
    }


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


def _add_audio_checks(root: Path, audio_manifest: dict[str, Any] | None, checks: list[dict[str, Any]]) -> None:
    _add_file_check(root / "audio_manifest.json", "audio_manifest_exists", checks)
    _add_check(checks, "audio_manifest_json_object", "pass" if audio_manifest is not None else "fail")
    if audio_manifest is None:
        _add_check(checks, "audio_manifest_status_valid", "fail")
        _add_check(checks, "audio_manifest_execution_consistent", "fail")
        return

    status = str(audio_manifest.get("status") or "")
    extraction_mode = str(audio_manifest.get("extraction_mode") or "")
    metadata = audio_manifest.get("metadata") if isinstance(audio_manifest.get("metadata"), dict) else {}
    executed = metadata.get("executed")
    command = metadata.get("ffmpeg_command")
    audio_ref = str(audio_manifest.get("audio_path") or "")

    _add_check(
        checks,
        "audio_manifest_status_valid",
        "pass" if status in {"mocked", "succeeded"} else "fail",
        {"status": status, "extraction_mode": extraction_mode},
    )
    _add_check(
        checks,
        "audio_manifest_execution_consistent",
        "pass" if audio_execution_is_consistent(extraction_mode, status, executed, command) else "fail",
        {"executed": executed, "ffmpeg_command_count": len(command) if isinstance(command, list) else None},
    )
    if audio_ref:
        _add_check(checks, "audio_artifact_exists", "pass" if (root / audio_ref).is_file() else "fail", {"path": audio_ref})
    else:
        _add_check(checks, "audio_artifact_exists", "fail", {"path": audio_ref})


def _add_transcript_checks(
    root: Path,
    transcript: dict[str, Any] | None,
    profile: str,
    checks: list[dict[str, Any]],
) -> None:
    _add_file_check(root / "transcript.json", "transcript_exists", checks)
    _add_check(checks, "transcript_json_object", "pass" if transcript is not None else "fail")
    if transcript is None:
        for name in _transcript_dependent_checks(profile):
            _add_check(checks, name, "fail")
        return

    schema_valid = transcript_schema_valid(transcript)
    segments = transcript.get("segments") if isinstance(transcript.get("segments"), list) else []
    provider = transcript_provider(transcript)
    _add_check(checks, "transcript_schema_valid", "pass" if schema_valid else "fail")
    _add_check(checks, "transcript_segments_non_empty", "pass" if segments else "fail", {"count": len(segments)})
    _add_check(
        checks,
        "transcript_segment_time_ranges_valid",
        "pass" if segments and all(segment_time_range_valid(item) for item in segments) else "fail",
    )
    _add_check(
        checks,
        "transcript_segments_monotonic",
        "pass" if segments and segments_monotonic(segments) else "fail",
    )
    _add_check(
        checks,
        "transcript_segment_text_non_empty",
        "pass" if segments and all(text_non_empty(item.get("text")) for item in segments if isinstance(item, dict)) else "fail",
    )
    _add_check(
        checks,
        "transcript_provider_metadata_present",
        "pass" if text_non_empty(provider) else "fail",
        {"provider": provider},
    )
    if profile in {MOCK_ASR_TRANSCRIPT_PROFILE, VIDEO_HIGHLIGHT_CLIP_PLAN_PROFILE, VIDEO_REAL_CLIPS_PROFILE}:
        _add_check(checks, "mock_asr_provider_marked", "pass" if provider == "mock" else "fail", {"provider": provider})
    if profile in REAL_ASR_PROFILES:
        _add_check(
            checks,
            "real_asr_provider_marked",
            "pass" if provider == "openai_compatible" else "fail",
            {"provider": provider},
        )


def _add_source_segment_reference_checks(
    transcript: dict[str, Any] | None,
    highlight_plan: dict[str, Any] | None,
    clip_plan: dict[str, Any] | None,
    checks: list[dict[str, Any]],
) -> None:
    transcript_ids = transcript_segment_ids(transcript)
    highlights = highlight_plan.get("highlights") if isinstance(highlight_plan, dict) else None
    highlight_list = highlights if isinstance(highlights, list) else []
    segments = clip_plan.get("segments") if isinstance(clip_plan, dict) else None
    segment_list = segments if isinstance(segments, list) else []
    _add_check(
        checks,
        "highlight_source_segments_exist_in_transcript",
        "pass" if highlight_list and all_source_ids_known(highlight_list, transcript_ids) else "fail",
        {"transcript_segment_count": len(transcript_ids)},
    )
    _add_check(
        checks,
        "clip_source_segments_exist_in_transcript",
        "pass" if segment_list and all_clip_source_ids_known(segment_list, transcript_ids) else "fail",
        {"transcript_segment_count": len(transcript_ids)},
    )


def _add_secret_scan_check(root: Path, checks: list[dict[str, Any]]) -> None:
    findings: list[str] = []
    for name in SECRET_SCAN_FILES:
        path = root / name
        if path.is_file() and SECRET_VALUE_RE.search(path.read_text(encoding="utf-8", errors="replace")):
            findings.append(name)
    _add_check(
        checks,
        "api_secret_values_not_recorded",
        "pass" if not findings else "fail",
        {"files": findings},
    )


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
    if profile in {MOCK_ASR_TRANSCRIPT_PROFILE, VIDEO_HIGHLIGHT_CLIP_PLAN_PROFILE, VIDEO_REAL_CLIPS_PROFILE}:
        names.add("mock_asr_provider_marked")
    if profile in REAL_ASR_PROFILES:
        names.update({"real_asr_provider_marked", "api_secret_values_not_recorded"})
    if is_video_highlight_quality_profile(profile):
        names.update({"highlight_source_segments_exist_in_transcript", "clip_source_segments_exist_in_transcript"})
    return names


def _transcript_dependent_checks(profile: str) -> list[str]:
    names = [
        "transcript_schema_valid",
        "transcript_segments_non_empty",
        "transcript_segment_time_ranges_valid",
        "transcript_segments_monotonic",
        "transcript_segment_text_non_empty",
        "transcript_provider_metadata_present",
    ]
    if profile in {MOCK_ASR_TRANSCRIPT_PROFILE, VIDEO_HIGHLIGHT_CLIP_PLAN_PROFILE, VIDEO_REAL_CLIPS_PROFILE}:
        names.append("mock_asr_provider_marked")
    if profile in REAL_ASR_PROFILES:
        names.append("real_asr_provider_marked")
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


def _add_file_check(path: Path, name: str, checks: list[dict[str, Any]]) -> None:
    _add_check(checks, name, "pass" if path.is_file() else "fail")


def _add_check(checks: list[dict[str, Any]], name: str, status: str, details: dict[str, Any] | None = None) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
