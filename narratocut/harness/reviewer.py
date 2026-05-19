from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.highlight_artifacts import (
    build_highlight_review_section,
    is_highlight_quality_profile,
)
from narratocut.harness.bgm_quality import build_bgm_review_section
from narratocut.harness.candidate_quality import build_candidate_review_section
from narratocut.harness.candidate_scoring_quality import build_candidate_scoring_review_section
from narratocut.harness.cover_quality import build_cover_review_section
from narratocut.harness.package_quality import build_package_review_section
from narratocut.harness.quality_profiles import (
    COVER_EXPORT_PROFILE,
    BGM_MIX_PROFILE,
    CANDIDATE_WINDOWS_PROFILE,
    CANDIDATE_SCORING_PROFILE,
    FINISHED_PACKAGE_PROFILE,
    FINAL_VIDEO_PROFILE,
    REAL_CLIP_QUALITY_PROFILES,
    SUBTITLE_BURN_PROFILE,
    SUBTITLE_EXPORT_PROFILE,
    VIDEO_REAL_CLIPS_PROFILE,
)
from narratocut.harness.review_checks import build_quality_report_check
from narratocut.harness.subtitle_burn_quality import build_subtitle_burn_review_section
from narratocut.harness.subtitle_quality import build_subtitle_review_section
from narratocut.harness.video_artifacts import (
    build_video_review_section,
    is_video_highlight_quality_profile,
    is_video_quality_profile,
)
from narratocut.utils import write_json


SCHEMA_VERSION = "0.1"
PASSED = "passed"
WARNING = "warning"
FAILED = "failed"


def review_run(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    run_manifest = _load_json_object(root / "run_manifest.json")
    trace = _load_json_object(root / "trace.json")
    quality_report = _load_json_object(root / "quality_report.json")

    sections = [
        _run_contract_section(root, run_manifest, trace, quality_report),
        _workflow_outputs_section(root, run_manifest),
    ]
    if run_manifest and run_manifest.get("quality_profile") in REAL_CLIP_QUALITY_PROFILES | {VIDEO_REAL_CLIPS_PROFILE}:
        sections.append(_real_video_section(root))
    if run_manifest and run_manifest.get("quality_profile") == FINAL_VIDEO_PROFILE:
        sections.append(_final_video_section(root))
    if run_manifest and run_manifest.get("quality_profile") == SUBTITLE_EXPORT_PROFILE:
        sections.append(build_subtitle_review_section(root))
    if run_manifest and run_manifest.get("quality_profile") == SUBTITLE_BURN_PROFILE:
        sections.append(build_subtitle_burn_review_section(root))
    if run_manifest and run_manifest.get("quality_profile") == COVER_EXPORT_PROFILE:
        sections.append(build_cover_review_section(root))
    if run_manifest and run_manifest.get("quality_profile") == BGM_MIX_PROFILE:
        sections.append(build_bgm_review_section(root))
    if run_manifest and run_manifest.get("quality_profile") == FINISHED_PACKAGE_PROFILE:
        sections.append(build_package_review_section(root))
    if run_manifest and run_manifest.get("quality_profile") == CANDIDATE_WINDOWS_PROFILE:
        sections.append(build_candidate_review_section(root))
    if run_manifest and run_manifest.get("quality_profile") == CANDIDATE_SCORING_PROFILE:
        sections.append(build_candidate_scoring_review_section(root))
    if run_manifest and is_video_quality_profile(run_manifest.get("quality_profile")):
        sections.append(build_video_review_section(root, run_manifest))
    if run_manifest and is_video_highlight_quality_profile(run_manifest.get("quality_profile")):
        highlight_manifest = dict(run_manifest)
        highlight_manifest["quality_profile"] = "highlight_clip_plan"
        sections.append(build_highlight_review_section(root, highlight_manifest))
    if run_manifest and is_highlight_quality_profile(run_manifest.get("quality_profile")):
        sections.append(build_highlight_review_section(root, run_manifest))
    summary = _summarize_sections(sections)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": _run_id(root, run_manifest),
        "status": _status_from_summary(summary),
        "summary": summary,
        "inputs": {
            "run_dir": _display_ref(root),
            "manifest": "run_manifest.json",
            "trace": "trace.json",
            "quality_report": "quality_report.json",
        },
        "sections": sections,
        "recommendations": _recommendations(root, run_manifest, quality_report),
    }


def write_review_report(
    run_dir: str | Path,
    report: dict[str, Any] | None = None,
) -> Path:
    root = Path(run_dir)
    review_report = report if report is not None else review_run(root)
    return write_json(root / "review_report.json", review_report)


def _run_contract_section(
    root: Path,
    run_manifest: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
) -> dict[str, Any]:
    checks = [
        _file_check(root / "run_manifest.json", "manifest_exists", "run_manifest.json exists"),
        _file_check(root / "trace.json", "trace_exists", "trace.json exists"),
        _file_check(
            root / "quality_report.json",
            "quality_report_exists",
            "quality_report.json exists",
        ),
        _trace_steps_check(trace),
        build_quality_report_check(quality_report),
    ]
    return _section("run_contract", checks)


def _workflow_outputs_section(
    root: Path,
    run_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    artifacts = run_manifest.get("artifacts") if run_manifest else None
    if not isinstance(artifacts, dict):
        return _section(
            "workflow_outputs",
            [
                _check(
                    "artifacts_declared",
                    FAILED,
                    "run_manifest.json declares workflow artifacts",
                )
            ],
        )

    checks: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for name, ref in artifacts.items():
        if not isinstance(ref, str) or not ref:
            checks.append(_check(f"artifact_{name}_declared", FAILED, f"{name} artifact is declared"))
            continue

        normalized_ref = _display_ref(ref)
        if normalized_ref in seen_paths:
            continue
        seen_paths.add(normalized_ref)
        checks.append(_artifact_check(root, name, ref))

    return _section("workflow_outputs", checks)


def _real_video_section(root: Path) -> dict[str, Any]:
    checks = [
        _artifact_check(root, "video_metadata", "video_metadata.json"),
        _artifact_check(root, "clip_plan_validation", "clip_plan_validation.json"),
        _artifact_check(root, "real_slice_manifest", "real_slice_manifest.json"),
    ]
    return _section("real_video_outputs", checks)


def _final_video_section(root: Path) -> dict[str, Any]:
    final_manifest = _load_json_object(root / "final_video_manifest.json")
    final_video = "final_video.mp4"
    if final_manifest and isinstance(final_manifest.get("final_video"), str) and final_manifest["final_video"]:
        final_video = str(final_manifest["final_video"])
    checks = [
        _artifact_check(root, "assembly_plan", "assembly_plan.json"),
        _artifact_check(root, "concat_list", "concat_list.txt"),
        _artifact_check(root, "final_video_manifest", "final_video_manifest.json"),
        _artifact_check(root, "final_video", final_video),
    ]
    return _section("final_video_outputs", checks)


def _file_check(path: Path, check_id: str, message: str) -> dict[str, Any]:
    return _check(check_id, PASSED if path.is_file() else FAILED, message)


def _trace_steps_check(trace: dict[str, Any] | None) -> dict[str, Any]:
    steps = trace.get("steps") if trace else None
    status = PASSED if isinstance(steps, list) and len(steps) > 0 else FAILED
    return _check(
        "trace_steps_non_empty",
        status,
        "trace.json contains at least one workflow step",
        {"count": len(steps) if isinstance(steps, list) else 0},
    )


def _artifact_check(root: Path, name: str, ref: str) -> dict[str, Any]:
    artifact_path = root / ref.rstrip("/")
    exists = artifact_path.is_dir() if ref.endswith("/") else artifact_path.exists()
    return _check(
        f"artifact_{name}_exists",
        PASSED if exists else FAILED,
        f"{_display_ref(ref)} exists",
        {"path": _display_ref(ref)},
    )


def _section(name: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "status": _status_from_checks(checks),
        "checks": checks,
    }


def _check(
    check_id: str,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    check: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if details is not None:
        check["details"] = details
    return check


def _summarize_sections(sections: list[dict[str, Any]]) -> dict[str, int]:
    checks = [check for section in sections for check in section["checks"]]
    failed = sum(1 for check in checks if check["status"] == FAILED)
    warnings = sum(1 for check in checks if check["status"] == WARNING)
    passed = sum(1 for check in checks if check["status"] == PASSED)
    return {
        "total_checks": len(checks),
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
    }


def _status_from_summary(summary: dict[str, int]) -> str:
    if summary["failed"] > 0:
        return FAILED
    if summary["warnings"] > 0:
        return WARNING
    return PASSED


def _status_from_checks(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == FAILED for check in checks):
        return FAILED
    if any(check["status"] == WARNING for check in checks):
        return WARNING
    return PASSED


def _run_id(root: Path, run_manifest: dict[str, Any] | None) -> str:
    if run_manifest and run_manifest.get("run_id"):
        return str(run_manifest["run_id"])
    return root.name


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _recommendations(
    root: Path,
    run_manifest: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
) -> list[str]:
    if not run_manifest or run_manifest.get("quality_profile") not in REAL_CLIP_QUALITY_PROFILES | {VIDEO_REAL_CLIPS_PROFILE}:
        return []

    recommendation_set: list[str] = []
    real_manifest = _load_json_object(root / "real_slice_manifest.json")
    validation = _load_json_object(root / "clip_plan_validation.json")
    metadata = _load_json_object(root / "video_metadata.json")
    all_errors = " ".join(
        str(item)
        for source in [
            quality_report.get("errors", []) if quality_report else [],
            real_manifest.get("errors", []) if real_manifest else [],
            validation.get("hard_errors", []) if validation else [],
            metadata.get("errors", []) if metadata else [],
        ]
        for item in source
    )
    reason = str(real_manifest.get("reason") if real_manifest else "")

    if "ffmpeg_unavailable" in all_errors or "ffmpeg_unavailable" in reason:
        recommendation_set.append("Install FFmpeg or set NCUT_FFMPEG_PATH to a valid ffmpeg executable.")
    if "ffprobe" in all_errors or "video_duration_unavailable" in all_errors:
        recommendation_set.append("Install FFprobe or set NCUT_FFPROBE_PATH so video duration can be validated.")
    if "segment_exceeds_video_duration" in all_errors:
        recommendation_set.append("Adjust the ClipPlan segment end times so they stay within video duration.")
    if "unsafe_output_name" in all_errors:
        recommendation_set.append("Use a plain output file name without directories or path traversal.")
    if "clip_plan_validation_failed" in reason:
        recommendation_set.append("Review clip_plan_validation.json before rerunning real slicing.")
    return recommendation_set


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
