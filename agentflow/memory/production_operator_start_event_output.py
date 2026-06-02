from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_next_operator_start_event import (
    NEXT_OPERATOR_START_EVENT_KIND,
    build_next_operator_start_event,
    write_next_operator_start_event_report,
)
from narratocut.utils import write_json


NEXT_OPERATOR_START_EVENT_ARTIFACTS = [
    {
        "artifact_type": NEXT_OPERATOR_START_EVENT_KIND,
        "path": "next_operator_start_event/next_operator_start_event.json",
        "required": True,
    },
    {
        "artifact_type": "markdown_report",
        "path": "next_operator_start_event/next_operator_start_event.md",
        "required": True,
    },
]


def write_next_operator_start_event_from_operator_loop(
    result: dict[str, Any],
    output_root: str | Path,
    *,
    decision: str,
    summary: str,
    operator_role: str,
    recorded_at: str,
) -> list[Path]:
    """Write a post-check start receipt and record it outside output_artifacts."""
    root = Path(output_root)
    packet = _dict(result.get("next_operator_start_packet"))
    if not packet:
        raise ValueError("write_next_operator_start_event requires next_operator_start_packet")
    event = build_next_operator_start_event(
        packet,
        decision=decision,
        summary=summary,
        operator_role=operator_role,
        recorded_at=recorded_at,
        start_packet_path="next_operator_start_packet/next_operator_start_packet.json",
    )
    written_paths = write_next_operator_start_event_report(event, root / "next_operator_start_event")
    result["next_operator_start_event"] = event
    manifest = result["manifest"]
    manifest["next_operator_start_event"] = _start_event_summary(event)
    manifest["post_check_artifacts"] = _post_check_artifacts(manifest.get("post_check_artifacts"))
    write_json(root / "production_memory_operator_loop_run.json", manifest)
    return written_paths


def _start_event_summary(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": event.get("kind", NEXT_OPERATOR_START_EVENT_KIND),
        "event_status": event.get("event_status", "unknown"),
        "start_decision": event.get("start_decision", "unknown"),
        "path": "next_operator_start_event/next_operator_start_event.json",
        "markdown_path": "next_operator_start_event/next_operator_start_event.md",
        "source_start_packet_status": event.get("source_start_packet_status", "unknown"),
        "source_ready_for_next_operator": event.get("source_ready_for_next_operator") is True,
        "source_next_operator_action": event.get("source_next_operator_action", "unknown"),
        "summary": event.get("summary", ""),
        "operator_role": event.get("operator_role", "unknown"),
        "provider_calls_started": event.get("provider_calls_started") is True,
        "writes_long_term_memory": event.get("writes_long_term_memory") is True,
        "writes_company_kb": event.get("writes_company_kb") is True,
        "start_event_is_memory": event.get("start_event_is_memory") is True,
        "start_event_is_acceptance": event.get("start_event_is_acceptance") is True,
        "start_event_is_execution": event.get("start_event_is_execution") is True,
    }


def _post_check_artifacts(existing: Any) -> list[dict[str, Any]]:
    by_path = {
        str(_dict(item).get("path", "")): _dict(item)
        for item in _list(existing)
        if _dict(item).get("path")
    }
    for artifact in NEXT_OPERATOR_START_EVENT_ARTIFACTS:
        by_path[artifact["path"]] = dict(artifact)
    return list(by_path.values())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_OPERATOR_START_EVENT_ARTIFACTS",
    "write_next_operator_start_event_from_operator_loop",
)
