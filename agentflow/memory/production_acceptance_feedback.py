from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_run_package_check import OPERATOR_RUN_PACKAGE_CHECK_KIND
from narratocut.utils import write_json

ACCEPTANCE_FEEDBACK_EVENT_KIND = "agentflow_production_memory_acceptance_feedback_event"
SUPPORTED_ACCEPTANCE_DECISIONS = frozenset({"accepted", "rejected", "needs_revision"})
UNSAFE_EXTRA_FRAGMENTS = (
    "http://",
    "https://",
    "file://",
    "data:image/",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".mp4",
    ".mov",
)
ALLOWED_SOURCE_REF_FRAGMENTS = ("data/processed/runs",)


def load_operator_run_package_check(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("operator run package check must be a JSON object")
    return payload


def build_production_memory_acceptance_feedback_event(
    package_check: dict[str, Any],
    *,
    decision: str,
    summary: str,
    reviewer_role: str,
    reviewed_at: str,
    acceptance_scope: str = "operator_run_package",
) -> dict[str, Any]:
    """Record a human-supplied package acceptance decision without promotion side effects."""
    _validate_package_check(package_check)
    _validate_inputs(decision, summary, reviewer_role, reviewed_at, acceptance_scope)
    if decision == "accepted" and not _passed_ready(package_check):
        raise ValueError("accepted acceptance feedback requires passed ready package check")

    event = {
        "kind": ACCEPTANCE_FEEDBACK_EVENT_KIND,
        "artifact_type": ACCEPTANCE_FEEDBACK_EVENT_KIND,
        "schema_version": package_check.get("schema_version", SCHEMA_VERSION),
        "feedback_id": _safe_id(
            "acceptance-feedback",
            str(package_check.get("source_operator_loop_id", "unknown")),
            decision,
            reviewed_at,
        ),
        "feedback_scope": "operator_run_package_check",
        "status": "human_recorded",
        "source_operator_loop_id": package_check.get("source_operator_loop_id", "unknown"),
        "source_project_id": package_check.get("project_id", "unknown"),
        "source_package_path": package_check.get("package_path", "unknown"),
        "source_check_status": package_check.get("check_status", "unknown"),
        "source_ready_for_handoff": package_check.get("ready_for_handoff") is True,
        "source_checked_item_count": package_check.get("checked_item_count", 0),
        "acceptance_scope": acceptance_scope,
        "acceptance_decision": decision,
        "summary": summary,
        "reviewer_role": reviewer_role,
        "reviewed_at": reviewed_at,
        "human_acceptance_recorded": True,
        "business_validation": "not_validated",
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "feedback_is_memory": False,
        "creates_memory_candidate": False,
        "creates_promotion_decision": False,
        "claim_boundaries": _claim_boundaries(decision),
        "non_claims": _non_claims(),
        "controls": _controls(package_check, decision),
    }
    _reject_unsafe(event, allow_source_refs=True)
    return event


def write_production_memory_acceptance_feedback_event(event: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "acceptance_feedback_event.json", event)
    md_path = output_root / "acceptance_feedback_event.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_acceptance_feedback_markdown(event), encoding="utf-8")
    return [json_path, md_path]


def render_acceptance_feedback_markdown(event: dict[str, Any]) -> str:
    boundaries = _dict(event.get("claim_boundaries"))
    return "\n".join(
        [
            "# Production Memory Acceptance Feedback Event",
            "",
            f"Status: {event.get('status', 'unknown')}",
            f"Decision: {event.get('acceptance_decision', 'unknown')}",
            f"Scope: {event.get('acceptance_scope', 'unknown')}",
            f"Source check: {event.get('source_check_status', 'unknown')}",
            f"Ready for handoff: {_bool_label(event.get('source_ready_for_handoff'))}",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            f"Human acceptance: {boundaries.get('human_acceptance', 'unknown')}",
            f"Business validation: {boundaries.get('business_validation', 'not_validated')}",
            "",
            "## Summary",
            str(event.get("summary", "")),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(event.get("non_claims"))),
            "",
        ]
    )


def _validate_package_check(package_check: dict[str, Any]) -> None:
    if package_check.get("kind") != OPERATOR_RUN_PACKAGE_CHECK_KIND:
        raise ValueError(f"acceptance feedback requires kind {OPERATOR_RUN_PACKAGE_CHECK_KIND}")
    if package_check.get("provider_calls_started") is not False:
        raise ValueError("acceptance feedback requires provider_calls_started false")
    if package_check.get("writes_long_term_memory") is not False:
        raise ValueError("acceptance feedback requires writes_long_term_memory false")
    if package_check.get("writes_company_kb") is not False:
        raise ValueError("acceptance feedback requires writes_company_kb false")
    _reject_unsafe(package_check, allow_source_refs=True)


def _validate_inputs(
    decision: str,
    summary: str,
    reviewer_role: str,
    reviewed_at: str,
    acceptance_scope: str,
) -> None:
    for label, value in {
        "summary": summary,
        "reviewer_role": reviewer_role,
        "reviewed_at": reviewed_at,
        "acceptance_scope": acceptance_scope,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    if decision not in SUPPORTED_ACCEPTANCE_DECISIONS:
        raise ValueError(f"unsupported acceptance feedback decision: {decision}")
    _reject_unsafe(
        {
            "summary": summary,
            "reviewer_role": reviewer_role,
            "acceptance_scope": acceptance_scope,
        }
    )


def _passed_ready(package_check: dict[str, Any]) -> bool:
    return package_check.get("check_status") == "passed" and package_check.get("ready_for_handoff") is True


def _controls(package_check: dict[str, Any], decision: str) -> list[dict[str, str]]:
    return [
        _control("provider_calls_not_started", package_check.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", package_check.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", package_check.get("writes_company_kb") is False),
        _control("accepted_requires_ready_package_check", decision != "accepted" or _passed_ready(package_check)),
    ]


def _claim_boundaries(decision: str) -> dict[str, str]:
    return {
        "human_acceptance": decision,
        "business_validation": "not_validated",
        "provider_success": "not_claimed",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
        "memory_promotion": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "not business validation",
        "not durable memory",
        "not provider success",
        "not Company KB promotion",
        "not memory promotion",
    ]


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": "passed" if passed else "failed"}


def _safe_id(*parts: str) -> str:
    raw = ":".join(parts)
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


def _reject_unsafe(value: Any, *, allow_source_refs: bool = False) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if allow_source_refs:
        fragments = tuple(
            fragment for fragment in fragments if fragment not in ALLOWED_SOURCE_REF_FRAGMENTS
        )
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("production memory acceptance feedback contains unsafe path, media reference, provider URL, or secret")


def _bool_label(value: Any) -> str:
    return "true" if value is True else "false"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "ACCEPTANCE_FEEDBACK_EVENT_KIND",
    "SUPPORTED_ACCEPTANCE_DECISIONS",
    "build_production_memory_acceptance_feedback_event",
    "load_operator_run_package_check",
    "render_acceptance_feedback_markdown",
    "write_production_memory_acceptance_feedback_event",
)
