from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.quality_profiles import FINISHED_PACKAGE_PROFILE
from narratocut.harness.short_clip_quality import add_short_clip_product_checks


def package_artifacts_to_inspect() -> list[str]:
    return [
        "finished_package_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]


def build_package_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    package = _check_json_object(run_dir, "finished_package_manifest_exists", "finished_package_manifest.json", checks)
    _add_package_checks(run_dir, package, checks, errors)
    _add_product_quality_checks(run_dir, package, checks, warnings)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": warnings,
        "errors": errors + [_check_error(check) for check in failed if _check_error(check) not in errors],
        "summary": {
            "quality_profile": FINISHED_PACKAGE_PROFILE,
            "package_id": package.get("package_id") if package else None,
            "asset_count": len(package.get("assets", [])) if package else 0,
        },
    }


def build_package_review_section(root: str | Path) -> dict[str, Any]:
    report = build_package_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "finished_package_outputs",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_package_checks(
    root: Path,
    package: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if package is None:
        return
    status = str(package.get("status") or "")
    _add_check(checks, "finished_package_manifest_status", "pass" if status == "succeeded" else "fail", {"status": status})
    errors.extend(str(error) for error in package.get("errors", []) if error)
    assets = package.get("assets")
    if not isinstance(assets, list) or not assets:
        _add_check(checks, "finished_package_assets_non_empty", "fail", {"count": 0})
        return
    _add_check(checks, "finished_package_assets_non_empty", "pass", {"count": len(assets)})
    for asset in assets:
        if isinstance(asset, dict):
            _add_asset_check(root, asset, checks, errors)


def _add_product_quality_checks(
    root: Path,
    package: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    if package is None:
        return
    evidence = package.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    if not evidence:
        return
    primary_duration = _primary_video_duration(root, package, evidence)
    _add_slice_quality_checks(root, evidence, checks, warnings)
    add_short_clip_product_checks(
        primary_duration=primary_duration,
        clip_plan=_load_evidence_json(root, evidence, "clip_plan"),
        checks=checks,
        warnings=warnings,
        add_warning=_add_warning,
    )
    _add_subtitle_quality_checks(root, evidence, primary_duration, checks, warnings)
    _add_bgm_quality_checks(root, evidence, checks, warnings)


def _add_slice_quality_checks(
    root: Path,
    evidence: dict[str, Any],
    checks: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    real_slice = _load_evidence_json(root, evidence, "real_slice_manifest")
    clip_plan = _load_evidence_json(root, evidence, "clip_plan")
    if real_slice is None:
        _add_warning(checks, warnings, "product_quality_slice_evidence_missing", {})
        return

    clips = real_slice.get("clips")
    inferred_clip_count = len(clips) if isinstance(clips, list) else 0
    clip_count = int(real_slice.get("clip_count") or inferred_clip_count)
    if clip_count <= 1:
        _add_warning(checks, warnings, "product_quality_single_clip_only", {"clip_count": clip_count})

    if isinstance(clips, list) and clips and all(_optional_float(clip.get("start_sec")) == 0.0 for clip in clips if isinstance(clip, dict)):
        _add_warning(checks, warnings, "product_quality_clip_starts_at_zero_only", {"clip_count": len(clips)})

    if not _has_highlight_evidence(clip_plan):
        _add_warning(checks, warnings, "product_quality_no_highlight_evidence", {})


def _add_subtitle_quality_checks(
    root: Path,
    evidence: dict[str, Any],
    primary_duration: float | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    subtitle_manifest = _load_evidence_json(root, evidence, "subtitle_manifest")
    if subtitle_manifest is None:
        _add_warning(checks, warnings, "product_quality_subtitle_evidence_missing", {})
        return
    if not subtitle_manifest.get("source_video"):
        _add_warning(checks, warnings, "product_quality_subtitle_source_video_missing", {})
    if subtitle_manifest.get("timeline") != "final_video":
        _add_warning(
            checks,
            warnings,
            "product_quality_subtitle_timeline_not_final_video",
            {"timeline": subtitle_manifest.get("timeline")},
        )
    subtitle_duration = _optional_float(subtitle_manifest.get("duration_sec"))
    if primary_duration is not None and subtitle_duration is not None and subtitle_duration > primary_duration + 0.5:
        _add_warning(
            checks,
            warnings,
            "product_quality_subtitle_duration_exceeds_primary_video",
            {"subtitle_duration_sec": subtitle_duration, "primary_duration_sec": primary_duration},
        )


def _add_bgm_quality_checks(
    root: Path,
    evidence: dict[str, Any],
    checks: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    audio_mix_manifest = _load_evidence_json(root, evidence, "audio_mix_manifest")
    if audio_mix_manifest is None:
        _add_warning(checks, warnings, "product_quality_bgm_evidence_missing", {})
        return
    if not audio_mix_manifest.get("quality_verified"):
        _add_warning(
            checks,
            warnings,
            "product_quality_bgm_quality_unverified",
            {"bgm_path": audio_mix_manifest.get("bgm_path")},
        )


def _add_asset_check(
    root: Path,
    asset: dict[str, Any],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    role = _safe_check_fragment(str(asset.get("role") or "asset"))
    path = str(asset.get("path") or "")
    exists = _asset_path(root, path).is_file()
    status = "pass" if _is_safe_path(path) and exists else "fail"
    _add_check(
        checks,
        f"finished_package_asset_{role}_exists",
        status,
        {"path": path, "required": bool(asset.get("required"))},
    )
    if status == "fail":
        errors.append(f"finished_package_asset_missing: {role}")


def _primary_video_duration(root: Path, package: dict[str, Any], evidence: dict[str, Any]) -> float | None:
    final_video_manifest = _load_evidence_json(root, evidence, "final_video_manifest")
    if final_video_manifest is not None:
        duration = _optional_float(final_video_manifest.get("duration_sec"))
        if duration is not None:
            return duration
    primary = package.get("primary_video")
    if not isinstance(primary, dict):
        return None
    return _optional_float(primary.get("duration_sec"))


def _load_evidence_json(root: Path, evidence: dict[str, Any], key: str) -> dict[str, Any] | None:
    ref = evidence.get(key)
    if not isinstance(ref, str) or not ref:
        return None
    path = _asset_path(root, ref)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _has_highlight_evidence(clip_plan: dict[str, Any] | None) -> bool:
    if not isinstance(clip_plan, dict):
        return False
    segments = clip_plan.get("segments")
    if not isinstance(segments, list):
        return False
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        metadata = segment.get("metadata")
        if isinstance(metadata, dict) and (
            metadata.get("highlight_id")
            or metadata.get("source_segment_ids")
            or metadata.get("ranking_factors")
        ):
            return True
    return False


def _add_warning(
    checks: list[dict[str, Any]],
    warnings: list[str],
    name: str,
    details: dict[str, Any],
) -> None:
    _add_check(checks, name, "warning", details)
    warnings.append(f"product_quality_warning: {name.removeprefix('product_quality_')}")


def _check_json_object(
    root: Path,
    exists_check: str,
    filename: str,
    checks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    path = root / filename
    if not _add_file_check(path, exists_check, checks):
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _add_check(checks, f"{exists_check}_valid_json_object", "fail")
        return None
    if isinstance(payload, dict):
        return payload
    _add_check(checks, f"{exists_check}_valid_json_object", "fail")
    return None


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


def _is_safe_path(ref: str) -> bool:
    return bool(ref) and ".." not in Path(ref).parts


def _asset_path(root: Path, ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute() or path.is_file():
        return path
    return root / path


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_check_fragment(value: str) -> str:
    return "".join(char if char.isalnum() or char == "_" else "_" for char in value)


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


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
