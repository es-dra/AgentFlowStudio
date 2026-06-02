from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS, FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_next_operator_action_result_render import (
    render_next_operator_action_result_markdown,
    write_next_operator_action_result_report,
)
from agentflow.memory.production_next_operator_start_event import NEXT_OPERATOR_START_EVENT_KIND


NEXT_OPERATOR_ACTION_RESULT_KIND = "agentflow_production_memory_next_operator_action_result"
SUPPORTED_NEXT_OPERATOR_ACTION_DECISIONS = frozenset({"completed", "blocked", "deferred"})
DECISION_STATUSES = {
    "completed": "action_completed",
    "blocked": "action_blocked",
    "deferred": "action_deferred",
}
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


def load_next_operator_start_event(path: str | Path) -> dict[str, Any]:
    payload = _load_json_object(Path(path), "next operator start event")
    if payload.get("kind") != NEXT_OPERATOR_START_EVENT_KIND:
        raise ValueError(f"next operator action result requires kind {NEXT_OPERATOR_START_EVENT_KIND}")
    return payload


def load_next_operator_action_result(path: str | Path) -> dict[str, Any]:
    payload = _load_json_object(Path(path), "next operator action result")
    if payload.get("kind") != NEXT_OPERATOR_ACTION_RESULT_KIND:
        raise ValueError(f"next operator action result requires kind {NEXT_OPERATOR_ACTION_RESULT_KIND}")
    return payload


def build_next_operator_action_result_from_start_event_path(
    start_event_path: str | Path,
    *,
    decision: str,
    summary: str,
    result_refs: list[str] | None = None,
    operator_role: str,
    recorded_at: str,
) -> dict[str, Any]:
    event_ref = Path(start_event_path)
    event = load_next_operator_start_event(event_ref)
    return build_next_operator_action_result(
        event,
        decision=decision,
        summary=summary,
        result_refs=result_refs,
        operator_role=operator_role,
        recorded_at=recorded_at,
        start_event_path=event_ref,
    )


def build_next_operator_action_result(
    start_event: dict[str, Any],
    *,
    decision: str,
    summary: str,
    result_refs: list[str] | None = None,
    operator_role: str,
    recorded_at: str,
    start_event_path: str | Path | None = None,
) -> dict[str, Any]:
    """Record the outcome of the next operator's recorded action."""
    refs = [str(ref).strip() for ref in _list(result_refs) if str(ref).strip()]
    _validate_start_event(start_event)
    _validate_inputs(decision, summary, refs, operator_role, recorded_at)
    started = _started(start_event)
    if decision == "completed" and not started:
        raise ValueError("completed action result requires started next operator start event")
    if decision == "completed" and not refs:
        raise ValueError("completed action result requires result_refs")

    result = {
        "kind": NEXT_OPERATOR_ACTION_RESULT_KIND,
        "artifact_type": NEXT_OPERATOR_ACTION_RESULT_KIND,
        "schema_version": start_event.get("schema_version", SCHEMA_VERSION),
        "action_result_id": _safe_id(
            "next-operator-action-result",
            str(start_event.get("source_operator_loop_id", "unknown")),
            decision,
            recorded_at,
        ),
        "action_result_scope": "next_operator_start_event",
        "result_status": DECISION_STATUSES[decision],
        "action_decision": decision,
        "summary": summary,
        "operator_role": operator_role,
        "recorded_at": recorded_at,
        "source_start_event_id": start_event.get("start_event_id", "unknown"),
        "source_start_event_path": _source_path(start_event_path),
        "source_start_event_status": start_event.get("event_status", "unknown"),
        "source_start_decision": start_event.get("start_decision", "unknown"),
        "source_start_packet_id": start_event.get("source_start_packet_id", "unknown"),
        "source_start_packet_path": start_event.get("source_start_packet_path", "not_recorded"),
        "source_start_packet_status": start_event.get("source_start_packet_status", "unknown"),
        "source_ready_for_next_operator": start_event.get("source_ready_for_next_operator") is True,
        "source_operator_loop_id": start_event.get("source_operator_loop_id", "unknown"),
        "source_project_id": start_event.get("source_project_id", "unknown"),
        "source_next_operator_action": start_event.get("source_next_operator_action", "unknown"),
        "result_refs": refs,
        "source_blocked_items": _list(start_event.get("source_blocked_items")),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "action_result_is_memory": False,
        "action_result_is_acceptance": False,
        "action_result_is_execution": False,
        "creates_memory_candidate": False,
        "creates_promotion_decision": False,
        "controls": _controls(start_event, decision, refs, started),
        "claim_boundaries": _claim_boundaries(),
        "non_claims": _non_claims(),
    }
    _reject_unsafe(result, allow_run_refs=True)
    return result


def _validate_start_event(event: dict[str, Any]) -> None:
    if event.get("kind") != NEXT_OPERATOR_START_EVENT_KIND:
        raise ValueError(f"next operator action result requires kind {NEXT_OPERATOR_START_EVENT_KIND}")
    if event.get("provider_mode") != "no-provider":
        raise ValueError("next operator action result requires no-provider start event")
    if event.get("provider_calls_started") is not False:
        raise ValueError("next operator action result requires provider_calls_started false")
    if event.get("writes_long_term_memory") is not False:
        raise ValueError("next operator action result requires writes_long_term_memory false")
    if event.get("writes_company_kb") is not False:
        raise ValueError("next operator action result requires writes_company_kb false")
    if event.get("start_event_is_acceptance") is not False:
        raise ValueError("next operator action result requires non-acceptance start event")
    if event.get("start_event_is_execution") is not False:
        raise ValueError("next operator action result requires non-execution start event")
    if event.get("start_event_is_memory") is not False:
        raise ValueError("next operator action result requires non-memory start event")


def _validate_inputs(
    decision: str,
    summary: str,
    result_refs: list[str],
    operator_role: str,
    recorded_at: str,
) -> None:
    if decision not in SUPPORTED_NEXT_OPERATOR_ACTION_DECISIONS:
        raise ValueError(f"unsupported next operator action decision: {decision}")
    for label, value in {"summary": summary, "operator_role": operator_role, "recorded_at": recorded_at}.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    _reject_unsafe(
        {
            "summary": summary,
            "operator_role": operator_role,
            "recorded_at": recorded_at,
            "result_refs": result_refs,
        }
    )


def _started(event: dict[str, Any]) -> bool:
    return event.get("event_status") == "operator_started" and event.get("start_decision") == "started"


def _controls(
    event: dict[str, Any],
    decision: str,
    refs: list[str],
    started: bool,
) -> list[dict[str, str]]:
    return [
        _control("source_start_event_recorded", bool(event.get("start_event_id"))),
        _control("completed_requires_started_start_event", decision != "completed" or started),
        _control("completed_requires_result_refs", decision != "completed" or bool(refs)),
        _control("provider_calls_not_started", event.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", event.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", event.get("writes_company_kb") is False),
        _control("action_result_not_acceptance", True),
        _control("action_result_not_execution", True),
        _control("action_result_not_memory", True),
    ]


def _claim_boundaries() -> dict[str, str]:
    return {
        "human_acceptance": "not_claimed",
        "next_pass_execution": "not_claimed",
        "business_validation": "not_validated",
        "provider_success": "not_attempted",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
        "memory_promotion": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "not human acceptance",
        "not next-pass execution result",
        "not generated content",
        "not business validation",
        "not durable memory",
        "not provider success",
        "not Company KB promotion",
        "not memory promotion",
    ]


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _safe_id(*parts: str) -> str:
    raw = ":".join(parts)
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


def _source_path(path: str | Path | None) -> str:
    if path is None:
        return "not_recorded"
    event_path = Path(path)
    if event_path.is_absolute():
        return event_path.name
    return str(event_path).replace("\\", "/")


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} not found: {_source_path(path)}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {_source_path(path)}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _reject_unsafe(value: Any, *, allow_run_refs: bool = False) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if allow_run_refs:
        fragments = tuple(fragment for fragment in fragments if fragment != "data/processed/runs")
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("next operator action result contains unsafe path, media reference, provider URL, or secret")


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_OPERATOR_ACTION_RESULT_KIND",
    "SUPPORTED_NEXT_OPERATOR_ACTION_DECISIONS",
    "build_next_operator_action_result",
    "build_next_operator_action_result_from_start_event_path",
    "load_next_operator_action_result",
    "load_next_operator_start_event",
    "render_next_operator_action_result_markdown",
    "write_next_operator_action_result_report",
)
