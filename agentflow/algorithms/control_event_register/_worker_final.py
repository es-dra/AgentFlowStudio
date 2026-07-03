from __future__ import annotations

from typing import Any

from ._constants import (
    WORKER_FINAL_CLOSE_STATES,
    WORKER_FINAL_INGEST_CONTRACT,
    WORKER_FINAL_RECOVERY_SOURCES,
)
from ._helpers import required_dict, required_text


def dedupe_worker_final_ingest_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_events: dict[str, dict[str, Any]] = {}
    seen_worker_finals: dict[tuple[str, str], str] = {}
    for event in events:
        event_id = required_text(event, "event_id")
        top_down_dispatch_id = required_text(event, "top_down_dispatch_id")
        bottom_up_feedback_id = required_text(event, "bottom_up_feedback_id")
        event_type = str(event.get("event_type") or "")

        previous_event = seen_events.get(event_id)
        if previous_event is not None:
            if event_type == "worker_final_ingested" and previous_event == event:
                continue
            raise ValueError(f"duplicate control event_id: {event_id}")

        if event_type == "worker_final_ingested":
            worker_key = (top_down_dispatch_id, bottom_up_feedback_id)
            previous_worker_event_id = seen_worker_finals.get(worker_key)
            if previous_worker_event_id and previous_worker_event_id != event_id:
                raise ValueError("duplicate worker-final TD/BU ingest")
            seen_worker_finals[worker_key] = event_id

        seen_events[event_id] = event
        deduped.append(event)
    return deduped


def validate_worker_final_ingest(payload: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    worker_final = required_dict(payload, "worker_final_ingest")
    if required_text(worker_final, "ingest_contract") != WORKER_FINAL_INGEST_CONTRACT:
        raise ValueError("unsupported worker-final ingest contract")
    _require_equal(worker_final, "canonical_event_id", required_text(event, "event_id"))
    _require_equal(worker_final, "top_down_dispatch_id", required_text(event, "top_down_dispatch_id"))
    _require_equal(worker_final, "bottom_up_feedback_id", required_text(event, "bottom_up_feedback_id"))
    if required_text(worker_final, "close_state") not in WORKER_FINAL_CLOSE_STATES:
        raise ValueError("unsupported worker-final close_state")
    required_text(worker_final, "safe_summary")
    required_text(worker_final, "source_thread_id")
    _validate_recovery_sources(worker_final.get("recovery_sources"))
    _validate_idempotency(required_dict(worker_final, "idempotency"), event)
    return worker_final


def apply_worker_final_ingest(lane: dict[str, Any], event: dict[str, Any]) -> None:
    worker_final = event["payload"]["worker_final_ingest"]
    ingests = lane.setdefault("worker_final_ingests", [])
    ingests.append(
        {
            "event_id": event["event_id"],
            "ingest_contract": worker_final["ingest_contract"],
            "top_down_dispatch_id": worker_final["top_down_dispatch_id"],
            "bottom_up_feedback_id": worker_final["bottom_up_feedback_id"],
            "close_state": worker_final["close_state"],
            "source_thread_id": worker_final["source_thread_id"],
            "recovery_sources": worker_final["recovery_sources"],
            "idempotency": worker_final["idempotency"],
            "safe_summary": worker_final["safe_summary"],
        }
    )
    lane["worker_final_recovery_sources"] = sorted(
        {source["source_type"] for ingest in ingests for source in ingest["recovery_sources"]}
    )
    lane["ack"] = worker_final["ack"]
    lane["archive_policy"] = worker_final["archive_policy"]
    lane["non_claims"].update(worker_final.get("non_claims") or {})


def _require_equal(payload: dict[str, Any], field: str, expected: str) -> None:
    if required_text(payload, field) != expected:
        raise ValueError(f"worker-final canonical field mismatch: {field}")


def _validate_recovery_sources(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError("worker-final recovery_sources must be a non-empty list")
    seen_sources: set[str] = set()
    for source in value:
        if not isinstance(source, dict):
            raise ValueError("worker-final recovery source must be an object")
        source_type = required_text(source, "source_type")
        if source_type not in WORKER_FINAL_RECOVERY_SOURCES:
            raise ValueError("unsupported worker-final recovery source")
        if source_type in seen_sources:
            raise ValueError("duplicate worker-final recovery source")
        seen_sources.add(source_type)
        required_text(source, "source_ref")
        required_text(source, "safe_summary")


def _validate_idempotency(idempotency: dict[str, Any], event: dict[str, Any]) -> None:
    if idempotency.get("dedupe_strategy") != "td_bu_event_ids":
        raise ValueError("worker-final idempotency must use td_bu_event_ids")
    if idempotency.get("duplicate_handling") != "skip_identical_reject_conflict":
        raise ValueError("unsupported worker-final duplicate handling")
    if idempotency.get("idempotent") is not True:
        raise ValueError("worker-final ingest must declare idempotent true")
    keys = required_dict(idempotency, "dedupe_keys")
    _require_equal(keys, "event_id", required_text(event, "event_id"))
    _require_equal(keys, "top_down_dispatch_id", required_text(event, "top_down_dispatch_id"))
    _require_equal(keys, "bottom_up_feedback_id", required_text(event, "bottom_up_feedback_id"))


__all__ = (
    "apply_worker_final_ingest",
    "dedupe_worker_final_ingest_events",
    "validate_worker_final_ingest",
)
