from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_acceptance_feedback import (
    ACCEPTANCE_FEEDBACK_EVENT_KIND,
    SUPPORTED_ACCEPTANCE_DECISIONS,
    render_acceptance_feedback_markdown,
    write_production_memory_acceptance_feedback_event,
)
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_next_operator_action_result import NEXT_OPERATOR_ACTION_RESULT_KIND


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


def load_next_operator_action_result(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("next operator action result must be a JSON object")
    if payload.get("kind") != NEXT_OPERATOR_ACTION_RESULT_KIND:
        raise ValueError(f"action-result acceptance feedback requires kind {NEXT_OPERATOR_ACTION_RESULT_KIND}")
    return payload


def build_production_memory_action_result_acceptance_feedback_event(
    action_result: dict[str, Any],
    *,
    decision: str,
    summary: str,
    reviewer_role: str,
    reviewed_at: str,
    action_result_path: str | Path | None = None,
) -> dict[str, Any]:
    """Record human acceptance feedback for a next-operator action result."""
    _validate_action_result(action_result)
    _validate_inputs(decision, summary, reviewer_role, reviewed_at)
    ready = _completed_action_result(action_result)
    if decision == "accepted" and not ready:
        raise ValueError("accepted action result feedback requires completed action result")

    event = {
        "kind": ACCEPTANCE_FEEDBACK_EVENT_KIND,
        "artifact_type": ACCEPTANCE_FEEDBACK_EVENT_KIND,
        "schema_version": action_result.get("schema_version", SCHEMA_VERSION),
        "feedback_id": _safe_id(
            "action-result-acceptance-feedback",
            str(action_result.get("action_result_id", "unknown")),
            decision,
            reviewed_at,
        ),
        "feedback_scope": "next_operator_action_result",
        "status": "human_recorded",
        "source_operator_loop_id": action_result.get("source_operator_loop_id", "unknown"),
        "source_project_id": action_result.get("source_project_id", "unknown"),
        "source_artifact_type": NEXT_OPERATOR_ACTION_RESULT_KIND,
        "source_artifact_path": _source_path(action_result_path),
        "source_artifact_status": action_result.get("result_status", "unknown"),
        "source_action_result_id": action_result.get("action_result_id", "unknown"),
        "source_action_result_status": action_result.get("result_status", "unknown"),
        "source_action_decision": action_result.get("action_decision", "unknown"),
        "source_next_operator_action": action_result.get("source_next_operator_action", "unknown"),
        "source_start_event_status": action_result.get("source_start_event_status", "unknown"),
        "source_result_refs": _list(action_result.get("result_refs")),
        "source_result_ref_count": len(_list(action_result.get("result_refs"))),
        "source_ready_for_acceptance": ready,
        "acceptance_scope": "next_operator_action_result",
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
        "controls": _controls(action_result, decision, ready),
    }
    _reject_unsafe(event, allow_source_refs=True)
    return event


def build_production_memory_action_result_acceptance_feedback_event_from_path(
    action_result_path: str | Path,
    *,
    decision: str,
    summary: str,
    reviewer_role: str,
    reviewed_at: str,
) -> dict[str, Any]:
    """Load a next-operator action result and record human acceptance feedback."""
    action_result_ref = Path(action_result_path)
    return build_production_memory_action_result_acceptance_feedback_event(
        load_next_operator_action_result(action_result_ref),
        decision=decision,
        summary=summary,
        reviewer_role=reviewer_role,
        reviewed_at=reviewed_at,
        action_result_path=action_result_ref,
    )


def _validate_action_result(action_result: dict[str, Any]) -> None:
    if action_result.get("kind") != NEXT_OPERATOR_ACTION_RESULT_KIND:
        raise ValueError(f"action-result acceptance feedback requires kind {NEXT_OPERATOR_ACTION_RESULT_KIND}")
    if action_result.get("provider_mode") != "no-provider":
        raise ValueError("action-result acceptance feedback requires no-provider action result")
    if action_result.get("provider_calls_started") is not False:
        raise ValueError("action-result acceptance feedback requires provider_calls_started false")
    if action_result.get("writes_long_term_memory") is not False:
        raise ValueError("action-result acceptance feedback requires writes_long_term_memory false")
    if action_result.get("writes_company_kb") is not False:
        raise ValueError("action-result acceptance feedback requires writes_company_kb false")
    if action_result.get("action_result_is_acceptance") is not False:
        raise ValueError("action-result acceptance feedback requires action_result_is_acceptance false")
    if action_result.get("action_result_is_execution") is not False:
        raise ValueError("action-result acceptance feedback requires action_result_is_execution false")
    if action_result.get("action_result_is_memory") is not False:
        raise ValueError("action-result acceptance feedback requires action_result_is_memory false")
    if action_result.get("creates_memory_candidate") is not False:
        raise ValueError("action-result acceptance feedback requires creates_memory_candidate false")
    if action_result.get("creates_promotion_decision") is not False:
        raise ValueError("action-result acceptance feedback requires creates_promotion_decision false")
    _reject_unsafe(action_result, allow_source_refs=True)


def _validate_inputs(decision: str, summary: str, reviewer_role: str, reviewed_at: str) -> None:
    if decision not in SUPPORTED_ACCEPTANCE_DECISIONS:
        raise ValueError(f"unsupported acceptance feedback decision: {decision}")
    for label, value in {"summary": summary, "reviewer_role": reviewer_role, "reviewed_at": reviewed_at}.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    _reject_unsafe({"summary": summary, "reviewer_role": reviewer_role})


def _completed_action_result(action_result: dict[str, Any]) -> bool:
    return (
        action_result.get("result_status") == "action_completed"
        and action_result.get("action_decision") == "completed"
        and bool(_list(action_result.get("result_refs")))
    )


def _controls(action_result: dict[str, Any], decision: str, ready: bool) -> list[dict[str, str]]:
    return [
        _control("provider_calls_not_started", action_result.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", action_result.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", action_result.get("writes_company_kb") is False),
        _control("accepted_requires_completed_action_result", decision != "accepted" or ready),
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
        "not generated content approval",
    ]


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": "passed" if passed else "failed"}


def _source_path(path: str | Path | None) -> str:
    if path is None:
        return "unknown"
    source_path = Path(path)
    if source_path.is_absolute():
        if source_path.parent.name:
            return f"{source_path.parent.name}/{source_path.name}"
        return source_path.name
    return str(path).replace("\\", "/")


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
        fragments = tuple(fragment for fragment in fragments if fragment not in ALLOWED_SOURCE_REF_FRAGMENTS)
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("action-result acceptance feedback contains unsafe path, media reference, provider URL, or secret")


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "build_production_memory_action_result_acceptance_feedback_event",
    "build_production_memory_action_result_acceptance_feedback_event_from_path",
    "load_next_operator_action_result",
    "render_acceptance_feedback_markdown",
    "write_production_memory_acceptance_feedback_event",
)
