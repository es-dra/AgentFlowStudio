from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.harness.agentflow_production_quality import build_agentflow_production_quality_report


def build_agentflow_production_review_section(root: str | Path) -> dict[str, Any]:
    report = build_agentflow_production_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "agentflow_production_artifacts",
        "status": _review_status(checks),
        "checks": checks,
    }


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


__all__ = ("build_agentflow_production_review_section",)
