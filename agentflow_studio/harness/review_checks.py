from __future__ import annotations

from typing import Any


PASSED = "passed"
WARNING = "warning"
FAILED = "failed"


def build_quality_report_check(quality_report: dict[str, Any] | None) -> dict[str, Any]:
    failed_count = 0
    warning_count = 0
    if not quality_report:
        return _check(
            "quality_report_passed",
            FAILED,
            "quality_report.json is missing; run inspect-run before review-run",
            {"failed_checks": 0, "warnings": 0, "missing_quality_report": True},
        )
    checks = quality_report.get("checks")
    if isinstance(checks, list):
        failed_count = sum(1 for check in checks if check.get("status") == "fail")
        warning_count = sum(1 for check in checks if check.get("status") == "warning")
    report_warnings = quality_report.get("warnings")
    if isinstance(report_warnings, list):
        warning_count += len(report_warnings)
    if quality_report.get("status") != "pass" or failed_count > 0:
        status = FAILED
    elif warning_count > 0:
        status = WARNING
    else:
        status = PASSED
    return _check(
        "quality_report_passed",
        status,
        "quality_report.json has no failed checks",
        {"failed_checks": failed_count, "warnings": warning_count},
    )


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
