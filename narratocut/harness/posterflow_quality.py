from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.harness.posterflow_quality_io import (
    REQUIRED_ARTIFACTS,
    add_json_parse_checks,
    add_jsonl_schema_checks,
    add_schema_checks,
    check_name,
    read_json_object,
    read_jsonl,
)
from narratocut.harness.posterflow_quality_feedback import build_quality_feedback_signals
from narratocut.harness.posterflow_quality_references import add_reference_checks, candidate_count
from narratocut.harness.quality_profiles import POSTERFLOW_MEMORY_DEMO_PROFILE


def posterflow_artifacts_to_inspect() -> list[str]:
    return list(REQUIRED_ARTIFACTS) + ["image_candidates/", "round_2/image_candidates/"]


def build_posterflow_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    artifacts = {name: read_json_object(run_dir / name) for name in REQUIRED_ARTIFACTS if name.endswith(".json")}
    jsonl_artifacts = {name: read_jsonl(run_dir / name) for name in REQUIRED_ARTIFACTS if name.endswith(".jsonl")}

    for artifact in REQUIRED_ARTIFACTS:
        _add_file_check(run_dir / artifact, f"posterflow_{_check_name(artifact)}_exists", checks)
    _add_check(checks, "posterflow_image_candidates_dir_exists", "pass" if (run_dir / "image_candidates").is_dir() else "fail")

    add_json_parse_checks(run_dir, checks)
    add_schema_checks(artifacts, checks)
    add_jsonl_schema_checks(jsonl_artifacts, checks)
    add_reference_checks(run_dir, artifacts, jsonl_artifacts, checks)
    _add_report_checks(run_dir, checks)

    failed = [check for check in checks if check["status"] == "fail"]
    feedback_signals = build_quality_feedback_signals(checks)
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "feedback_signals": feedback_signals,
        "warnings": [],
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "quality_profile": POSTERFLOW_MEMORY_DEMO_PROFILE,
            "candidate_count": candidate_count(artifacts.get("poster_candidates_manifest.json")),
            "memory_candidate_count": candidate_count(artifacts.get("poster_memory_candidates.json")),
            "quality_feedback_signal_count": len(feedback_signals),
        },
    }


def build_posterflow_review_section(root: str | Path) -> dict[str, Any]:
    report = build_posterflow_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "posterflow_artifacts",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_report_checks(run_dir: Path, checks: list[dict[str, Any]]) -> None:
    preview = (run_dir / "poster_preview.html").read_text(encoding="utf-8") if (run_dir / "poster_preview.html").is_file() else ""
    report = (run_dir / "poster_report.md").read_text(encoding="utf-8") if (run_dir / "poster_report.md").is_file() else ""
    _add_check(checks, "posterflow_preview_references_candidate_images", "pass" if "candidate_001.png" in preview else "fail")
    _add_check(checks, "posterflow_report_mentions_memory", "pass" if "Memory Candidates" in report else "fail")


def _add_file_check(path: Path, name: str, checks: list[dict[str, Any]]) -> None:
    _add_check(checks, name, "pass" if path.is_file() else "fail")


def _add_check(checks: list[dict[str, Any]], name: str, status: str, details: dict[str, Any] | None = None) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)


def _review_check(check: dict[str, Any]) -> dict[str, Any]:
    mapped = "passed" if check["status"] == "pass" else "failed"
    result = {"id": check["name"], "status": mapped, "message": f"{check['name']} {check['status']}"}
    if "details" in check:
        result["details"] = check["details"]
    return result


def _review_status(checks: list[dict[str, Any]]) -> str:
    return "failed" if any(check["status"] == "failed" for check in checks) else "passed"


def _check_name(filename: str) -> str:
    return check_name(filename)


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
