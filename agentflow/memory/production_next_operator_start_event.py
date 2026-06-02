from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS, FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_start_packet import NEXT_OPERATOR_START_PACKET_KIND
from agentflow.memory.production_next_operator_start_event_render import (
    render_next_operator_start_event_markdown,
    write_next_operator_start_event_report,
)

NEXT_OPERATOR_START_EVENT_KIND = "agentflow_production_memory_next_operator_start_event"
SUPPORTED_NEXT_OPERATOR_START_DECISIONS = frozenset({"started", "blocked", "deferred"})
DECISION_STATUSES = {
    "started": "operator_started",
    "blocked": "start_blocked",
    "deferred": "start_deferred",
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


def load_next_operator_start_packet(path: str | Path) -> dict[str, Any]:
    payload = _load_json_object(Path(path), "next operator start packet")
    if payload.get("kind") != NEXT_OPERATOR_START_PACKET_KIND:
        raise ValueError(f"next operator start event requires kind {NEXT_OPERATOR_START_PACKET_KIND}")
    return payload


def load_next_operator_start_event(path: str | Path) -> dict[str, Any]:
    payload = _load_json_object(Path(path), "next operator start event")
    if payload.get("kind") != NEXT_OPERATOR_START_EVENT_KIND:
        raise ValueError(f"next operator start event requires kind {NEXT_OPERATOR_START_EVENT_KIND}")
    return payload


def build_next_operator_start_event_from_packet_path(
    packet_path: str | Path,
    *,
    decision: str,
    summary: str,
    operator_role: str,
    recorded_at: str,
) -> dict[str, Any]:
    packet_ref = Path(packet_path)
    packet = load_next_operator_start_packet(packet_ref)
    return build_next_operator_start_event(
        packet,
        decision=decision,
        summary=summary,
        operator_role=operator_role,
        recorded_at=recorded_at,
        start_packet_path=packet_ref,
    )


def build_next_operator_start_event(
    packet: dict[str, Any],
    *,
    decision: str,
    summary: str,
    operator_role: str,
    recorded_at: str,
    start_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    """Record whether the next operator started from a checked start packet."""
    _validate_packet(packet)
    _validate_inputs(decision, summary, operator_role, recorded_at)
    ready = _packet_ready(packet)
    if decision == "started" and not ready:
        raise ValueError("started start event requires ready next operator start packet")

    action = _dict(packet.get("next_operator_action"))
    event = {
        "kind": NEXT_OPERATOR_START_EVENT_KIND,
        "artifact_type": NEXT_OPERATOR_START_EVENT_KIND,
        "schema_version": packet.get("schema_version", SCHEMA_VERSION),
        "start_event_id": _safe_id(
            "next-operator-start-event",
            str(packet.get("source_operator_loop_id", "unknown")),
            decision,
            recorded_at,
        ),
        "start_event_scope": "next_operator_start_packet",
        "event_status": DECISION_STATUSES[decision],
        "start_decision": decision,
        "summary": summary,
        "operator_role": operator_role,
        "recorded_at": recorded_at,
        "source_start_packet_id": packet.get("start_packet_id", "unknown"),
        "source_start_packet_path": _source_path(start_packet_path),
        "source_operator_loop_id": packet.get("source_operator_loop_id", "unknown"),
        "source_project_id": packet.get("project_id", "unknown"),
        "source_start_packet_status": packet.get("start_packet_status", "unknown"),
        "source_ready_for_next_operator": packet.get("ready_for_next_operator") is True,
        "source_next_operator_action": str(action.get("action", "unknown")),
        "source_blocked_items": _list(packet.get("blocked_items")),
        "source_failed_controls": _list(packet.get("failed_controls")),
        "operator_prompt_excerpt": _excerpt(packet.get("operator_prompt_excerpt") or packet.get("operator_prompt")),
        "start_requirements": [str(item) for item in _list(packet.get("start_requirements"))],
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "start_event_is_memory": False,
        "start_event_is_acceptance": False,
        "start_event_is_execution": False,
        "creates_memory_candidate": False,
        "creates_promotion_decision": False,
        "controls": _controls(packet, decision, ready),
        "claim_boundaries": _claim_boundaries(),
        "non_claims": _non_claims(),
    }
    _reject_unsafe(
        {
            "summary": summary,
            "operator_role": operator_role,
            "operator_prompt_excerpt": event["operator_prompt_excerpt"],
        },
        allow_run_refs=True,
    )
    return event


def _validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("kind") != NEXT_OPERATOR_START_PACKET_KIND:
        raise ValueError(f"next operator start event requires kind {NEXT_OPERATOR_START_PACKET_KIND}")
    if packet.get("provider_mode") != "no-provider":
        raise ValueError("next operator start event requires no-provider start packet")
    if packet.get("provider_calls_started") is not False:
        raise ValueError("next operator start event requires provider_calls_started false")
    if packet.get("writes_long_term_memory") is not False:
        raise ValueError("next operator start event requires writes_long_term_memory false")
    if packet.get("writes_company_kb") is not False:
        raise ValueError("next operator start event requires writes_company_kb false")


def _validate_inputs(decision: str, summary: str, operator_role: str, recorded_at: str) -> None:
    if decision not in SUPPORTED_NEXT_OPERATOR_START_DECISIONS:
        raise ValueError(f"unsupported next operator start decision: {decision}")
    for label, value in {"summary": summary, "operator_role": operator_role, "recorded_at": recorded_at}.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    _reject_unsafe({"summary": summary, "operator_role": operator_role})


def _packet_ready(packet: dict[str, Any]) -> bool:
    return (
        packet.get("start_packet_status") == "ready"
        and packet.get("ready_for_next_operator") is True
        and not _list(packet.get("blocked_items"))
        and not _list(packet.get("failed_controls"))
    )


def _controls(packet: dict[str, Any], decision: str, ready: bool) -> list[dict[str, str]]:
    return [
        _control("source_start_packet_ready_for_started_decision", decision != "started" or ready),
        _control("provider_calls_not_started", packet.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", packet.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", packet.get("writes_company_kb") is False),
        _control("start_event_not_acceptance", True),
        _control("start_event_not_execution", True),
        _control("start_event_not_memory", True),
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
    packet_path = Path(path)
    if packet_path.is_absolute():
        return packet_path.name
    return str(packet_path).replace("\\", "/")


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
        raise ValueError("next operator start event contains unsafe path, media reference, provider URL, or secret")


def _excerpt(value: Any, limit: int = 480) -> str:
    text = str(value or "").replace("\n", " ").strip()
    while "  " in text:
        text = text.replace("  ", " ")
    return f"{text[: limit - 3].strip()}..." if len(text) > limit else text


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_OPERATOR_START_EVENT_KIND",
    "SUPPORTED_NEXT_OPERATOR_START_DECISIONS",
    "build_next_operator_start_event",
    "build_next_operator_start_event_from_packet_path",
    "load_next_operator_start_event",
    "load_next_operator_start_packet",
    "render_next_operator_start_event_markdown",
    "write_next_operator_start_event_report",
)
