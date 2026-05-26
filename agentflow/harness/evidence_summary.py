from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_VALIDATION_SCHEMA_VERSION, FAILED, PASSED, WARNING


SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION
ARTIFACT_TYPE = "agentflow_evidence_summary"


def build_evidence_summary(
    *,
    surface: str,
    source_status: Any,
    checks: list[dict[str, Any]] | None = None,
    artifact_refs: list[str | Path] | None = None,
    machine_verification: str = "reported",
    human_acceptance: str = "not_reviewed",
    business_validation: str = "not_validated",
    memory_promotion: str = "not_decided",
) -> dict[str, Any]:
    """Build a compact, contract-compatible evidence summary for QA surfaces."""
    normalized_checks = [_normalize_status(check.get("status")) for check in checks or []]
    source = _normalize_status(source_status)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "surface": surface,
        "source_status": source,
        "status": _overall_status(source, normalized_checks),
        "counts": _counts(normalized_checks),
        "artifact_refs": _artifact_refs(artifact_refs or []),
        "decision_boundary": {
            "machine_verification": machine_verification,
            "human_acceptance": human_acceptance,
            "business_validation": business_validation,
            "memory_promotion": memory_promotion,
        },
    }


def build_review_evidence_summary(*, status: Any, sections: list[dict[str, Any]]) -> dict[str, Any]:
    return build_evidence_summary(
        surface="review_report",
        source_status=status,
        checks=[check for section in sections for check in section["checks"]],
        artifact_refs=[
            "review_report.json",
            "run_manifest.json",
            "trace.json",
            "quality_report.json",
        ],
    )


def _overall_status(source_status: str, check_statuses: list[str]) -> str:
    statuses = [source_status, *check_statuses]
    if FAILED in statuses:
        return FAILED
    if WARNING in statuses:
        return WARNING
    return PASSED


def _counts(statuses: list[str]) -> dict[str, int]:
    return {
        "total": len(statuses),
        "passed": sum(1 for status in statuses if status == PASSED),
        "failed": sum(1 for status in statuses if status == FAILED),
        "warnings": sum(1 for status in statuses if status == WARNING),
    }


def _artifact_refs(refs: list[str | Path]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for ref in refs:
        value = str(ref).replace("\\", "/")
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def _normalize_status(status: Any) -> str:
    value = str(status or "").strip().lower()
    if value in {"pass", "passed", "success", "succeeded", "found", "ok"}:
        return PASSED
    if value in {"warn", "warning", "passed_with_warnings"}:
        return WARNING
    return FAILED


__all__ = ("ARTIFACT_TYPE", "SCHEMA_VERSION", "build_evidence_summary", "build_review_evidence_summary")
