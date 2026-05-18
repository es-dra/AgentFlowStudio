from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.highlight_artifacts import build_highlight_quality_report, is_highlight_quality_profile
from narratocut.harness.final_video_quality import build_final_video_quality_report
from narratocut.harness.quality_profiles import (
    FINAL_VIDEO_PROFILE,
    REAL_CLIP_QUALITY_PROFILES,
    SUBTITLE_BURN_PROFILE,
    SUBTITLE_EXPORT_PROFILE,
    VIDEO_REAL_CLIPS_PROFILE,
)
from narratocut.harness.real_clip_quality import (
    build_real_video_quality_report,
    build_video_real_clips_quality_report,
)
from narratocut.harness.subtitle_quality import build_subtitle_quality_report
from narratocut.harness.subtitle_burn_quality import build_subtitle_burn_quality_report
from narratocut.harness.video_artifacts import build_video_quality_report, is_video_quality_profile


def build_quality_report(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    run_manifest = _read_json(root / "run_manifest.json")
    if isinstance(run_manifest, dict):
        quality_profile = run_manifest.get("quality_profile")
        if quality_profile in REAL_CLIP_QUALITY_PROFILES:
            return build_real_video_quality_report(root, str(quality_profile))
        if quality_profile == VIDEO_REAL_CLIPS_PROFILE:
            return build_video_real_clips_quality_report(root)
        if quality_profile == FINAL_VIDEO_PROFILE:
            return build_final_video_quality_report(root)
        if quality_profile == SUBTITLE_EXPORT_PROFILE:
            return build_subtitle_quality_report(root)
        if quality_profile == SUBTITLE_BURN_PROFILE:
            return build_subtitle_burn_quality_report(root)
        if is_video_quality_profile(quality_profile):
            return build_video_quality_report(root, quality_profile)
        if is_highlight_quality_profile(quality_profile):
            return build_highlight_quality_report(root, quality_profile)

    checks: list[dict[str, Any]] = []

    hooks = _check_json_array(root, "hooks_file_exists", "hooks_non_empty", "hooks.json", checks)
    scripts = _check_json_array(root, "scripts_file_exists", "scripts_non_empty", "scripts.json", checks)
    clip_plans = _check_json_array(
        root,
        "clip_plans_file_exists",
        "clip_plans_non_empty",
        "clip_plans.json",
        checks,
    )
    _add_file_check(root / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(root / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(root / "trace.json", "trace_file_exists", checks)
    slice_manifest = _check_json_object(
        root,
        "slice_manifest_exists",
        "slice_manifest.json",
        checks,
    )
    clips_dir = root / "clips"
    _add_check(checks, "clips_dir_exists", "pass" if clips_dir.is_dir() else "fail")
    _add_mock_clip_count_check(clips_dir, slice_manifest, checks)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "hooks": len(hooks) if hooks is not None else 0,
            "scripts": len(scripts) if scripts is not None else 0,
            "clip_plans": len(clip_plans) if clip_plans is not None else 0,
        },
    }


def _check_json_array(
    root: Path,
    exists_check: str,
    non_empty_check: str,
    filename: str,
    checks: list[dict[str, Any]],
) -> list[Any] | None:
    path = root / filename
    if not _add_file_check(path, exists_check, checks):
        _add_check(checks, non_empty_check, "fail", {"count": 0})
        return None

    payload = _read_json(path)
    if not isinstance(payload, list):
        _add_check(checks, non_empty_check, "fail", {"reason": "not_json_array"})
        return None

    status = "pass" if payload else "fail"
    _add_check(checks, non_empty_check, status, {"count": len(payload)})
    return payload


def _check_json_object(
    root: Path,
    exists_check: str,
    filename: str,
    checks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    path = root / filename
    if not _add_file_check(path, exists_check, checks):
        return None

    payload = _read_json(path)
    if isinstance(payload, dict):
        return payload

    _add_check(checks, f"{exists_check}_valid_json_object", "fail")
    return None


def _add_mock_clip_count_check(
    clips_dir: Path,
    slice_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
) -> None:
    clip_count = len(list(clips_dir.glob("*.txt"))) if clips_dir.is_dir() else 0
    manifest_count = 0
    if slice_manifest is not None:
        manifest_count = int(slice_manifest.get("clip_count") or len(slice_manifest.get("items", [])))
    status = "pass" if clip_count == manifest_count and manifest_count > 0 else "fail"
    _add_check(
        checks,
        "mock_clips_count_matches_manifest",
        status,
        {"clips": clip_count, "manifest_items": manifest_count},
    )


def _add_file_check(path: Path, name: str, checks: list[dict[str, Any]]) -> bool:
    exists = path.is_file()
    _add_check(checks, name, "pass" if exists else "fail")
    return exists


def _add_check(
    checks: list[dict[str, Any]],
    name: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
