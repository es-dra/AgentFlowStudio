from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from agentflow_studio.utils import write_json


DELIVERY_READINESS_JSON = "delivery_readiness.json"
DELIVERY_READINESS_MD = "delivery_readiness.md"
SCHEMA_VERSION = "0.1"

PASS = "pass"
WARNING = "warning"
FAIL = "fail"


def build_delivery_readiness(run_dirs: Iterable[str | Path]) -> dict[str, Any]:
    runs = [_run_readiness(Path(run_dir)) for run_dir in run_dirs]
    summary = {
        "total_runs": len(runs),
        "passed": sum(1 for run in runs if run["status"] == PASS),
        "warning": sum(1 for run in runs if run["status"] == WARNING),
        "failed": sum(1 for run in runs if run["status"] == FAIL),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": _overall_status(summary),
        "summary": summary,
        "runs": runs,
    }


def write_delivery_readiness(
    run_dirs: Iterable[str | Path],
    output_dir: str | Path,
) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    report = build_delivery_readiness(run_dirs)
    json_path = write_json(root / DELIVERY_READINESS_JSON, report)
    markdown_path = root / DELIVERY_READINESS_MD
    markdown_path.write_text(build_delivery_readiness_markdown(report), encoding="utf-8")
    return {
        "json_path": json_path,
        "markdown_path": markdown_path,
    }


def build_delivery_readiness_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    lines = [
        "# AgentFlow Studio Delivery Readiness",
        "",
        "## Summary",
        f"- Overall status: {report.get('status', 'unknown')}",
        f"- Runs: {summary.get('total_runs', 0)} total, "
        f"{summary.get('passed', 0)} passed, "
        f"{summary.get('warning', 0)} warning, "
        f"{summary.get('failed', 0)} failed",
        "",
        "## Runs",
    ]
    runs = report.get("runs")
    if not isinstance(runs, list) or not runs:
        lines.append("- No runs provided.")
        return "\n".join(lines).rstrip() + "\n"

    for run in runs:
        if not isinstance(run, dict):
            continue
        lines.extend(
            [
                f"### {run.get('run_id', 'unknown')}",
                f"- Status: {run.get('status', 'unknown')}",
                f"- Mode: {run.get('mode', 'unknown')}",
                f"- Run dir: `{run.get('run_dir', 'unknown')}`",
                f"- Workflow: `{run.get('workflow', 'unknown')}`",
                f"- Package: `{run.get('package_id', 'unknown')}`",
                f"- Candidates: {run.get('candidate_count', 0)} total, {run.get('selected_count', 0)} selected",
            ]
        )
        failures = run.get("failures")
        warnings = run.get("warnings")
        if isinstance(failures, list) and failures:
            lines.append("- Failures:")
            lines.extend(f"  - {failure}" for failure in failures)
        if isinstance(warnings, list) and warnings:
            lines.append("- Warnings:")
            lines.extend(f"  - {warning}" for warning in warnings)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _run_readiness(run_dir: Path) -> dict[str, Any]:
    run_manifest = _load_json_object(run_dir / "run_manifest.json")
    package = _load_json_object(run_dir / "finished_package_manifest.json")
    quality = _load_json_object(run_dir / "quality_report.json")
    review = _load_json_object(run_dir / "review_report.json")
    diagnostics = _load_json_object(run_dir / "selection_diagnostics.json")
    score_report = _load_json_object(run_dir / "highlight_score_report.json")

    failures = _required_file_failures(run_dir)
    warnings: list[str] = []
    failures.extend(_package_failures(package))
    failures.extend(_quality_failures(quality))
    failures.extend(_review_failures(review))
    failures.extend(_selection_failures(diagnostics, score_report))
    warnings.extend(_quality_warnings(quality))
    warnings.extend(_review_warnings(review))
    warnings.extend(_selection_warnings(diagnostics))
    warnings.extend(_package_warnings(package))

    status = FAIL if failures else WARNING if warnings else PASS
    return {
        "run_id": _value(run_manifest, "run_id", run_dir.name),
        "status": status,
        "mode": _run_mode(run_manifest),
        "run_dir": _display_ref(run_dir),
        "workflow": _value(run_manifest, "workflow", "unknown"),
        "package_id": _value(package, "package_id", "unknown"),
        "candidate_count": _int_value(diagnostics, "candidate_count"),
        "selected_count": _int_value(diagnostics, "selected_count"),
        "failures": failures,
        "warnings": warnings,
    }


def _required_file_failures(run_dir: Path) -> list[str]:
    required = [
        "run_manifest.json",
        "finished_package_manifest.json",
        "quality_report.json",
        "review_report.json",
        "package_report.md",
        "highlight_score_report.json",
        "selection_diagnostics.json",
    ]
    return [f"missing {name}" for name in required if not (run_dir / name).is_file()]


def _package_failures(package: dict[str, Any] | None) -> list[str]:
    if package is None:
        return []
    failures: list[str] = []
    if package.get("status") not in {"succeeded", "success", "pass"}:
        failures.append(f"package status is {package.get('status', 'missing')}")
    for asset in _assets(package):
        if asset.get("required") is True and asset.get("exists") is False:
            failures.append(f"required asset missing: {asset.get('role', 'unknown')}")
    return failures


def _package_warnings(package: dict[str, Any] | None) -> list[str]:
    if package is None:
        return []
    warnings: list[str] = []
    for asset in _assets(package):
        if asset.get("required") is not True and asset.get("exists") is False:
            warnings.append(f"optional asset missing: {asset.get('role', 'unknown')}")
    raw_warnings = package.get("warnings")
    if isinstance(raw_warnings, list):
        warnings.extend(f"package: {warning}" for warning in raw_warnings)
    return warnings


def _quality_failures(quality: dict[str, Any] | None) -> list[str]:
    if quality is None:
        return []
    return [] if quality.get("status") == PASS else [f"quality status is {quality.get('status', 'missing')}"]


def _quality_warnings(quality: dict[str, Any] | None) -> list[str]:
    raw_warnings = quality.get("warnings") if quality else None
    if not isinstance(raw_warnings, list):
        return []
    return [f"quality: {warning}" for warning in raw_warnings]


def _review_failures(review: dict[str, Any] | None) -> list[str]:
    if review is None:
        return []
    return [] if review.get("status") == "passed" else [f"review status is {review.get('status', 'missing')}"]


def _review_warnings(review: dict[str, Any] | None) -> list[str]:
    summary = review.get("summary") if review else None
    warnings = _int_value(summary, "warnings")
    return [f"review: {warnings} warnings"] if warnings > 0 else []


def _selection_failures(
    diagnostics: dict[str, Any] | None,
    score_report: dict[str, Any] | None,
) -> list[str]:
    if diagnostics is None:
        return []
    failures: list[str] = []
    if diagnostics.get("status") not in {"succeeded", "success", PASS}:
        failures.append(f"selection diagnostics status is {diagnostics.get('status', 'missing')}")
    selected_count = _int_value(diagnostics, "selected_count")
    candidate_count = _int_value(diagnostics, "candidate_count")
    if selected_count < 1:
        failures.append("no selected candidates")
    if candidate_count < selected_count:
        failures.append("candidate count is smaller than selected count")
    selected_ids = score_report.get("selected_candidate_ids") if score_report else None
    if isinstance(selected_ids, list) and len(selected_ids) != selected_count:
        failures.append("selected candidate count does not match score report")
    return failures


def _selection_warnings(diagnostics: dict[str, Any] | None) -> list[str]:
    raw_warnings = diagnostics.get("warnings") if diagnostics else None
    if not isinstance(raw_warnings, list):
        return []
    warnings: list[str] = []
    for warning in raw_warnings:
        if isinstance(warning, dict):
            warnings.append(f"selection: {warning.get('code', 'unknown')}")
        else:
            warnings.append(f"selection: {warning}")
    return warnings


def _assets(package: dict[str, Any]) -> list[dict[str, Any]]:
    assets = package.get("assets")
    return [asset for asset in assets if isinstance(asset, dict)] if isinstance(assets, list) else []


def _overall_status(summary: dict[str, int]) -> str:
    if summary["failed"] > 0:
        return FAIL
    if summary["warning"] > 0:
        return WARNING
    return PASS


def _run_mode(run_manifest: dict[str, Any] | None) -> str:
    mode = run_manifest.get("workflow_mode") if run_manifest else None
    if isinstance(mode, str) and mode:
        return mode
    workflow = str(run_manifest.get("workflow", "")) if run_manifest else ""
    if "video_script" in workflow:
        return "video_script"
    if "ocr" in workflow:
        return "ocr"
    return "video_only"


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _value(payload: dict[str, Any] | None, key: str, default: str) -> str:
    if payload is None:
        return default
    value = payload.get(key)
    return str(value) if value is not None else default


def _int_value(payload: dict[str, Any] | None, key: str) -> int:
    if not payload:
        return 0
    value = payload.get(key)
    return value if isinstance(value, int) else 0


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")
