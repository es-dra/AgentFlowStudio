from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_feedback import FEEDBACK_CAPTURE_KIND
from agentflow.memory.production_loop import (
    KIND,
    SCHEMA_VERSION,
    build_production_memory_loop_run,
    write_production_memory_loop_run,
)
from agentflow_studio.utils import write_json

PROMOTION_DECISION_KIND = "agentflow_production_memory_promotion_decision"
REVIEWED_PROMOTION_DECISIONS = frozenset({"promoted", "merged", "rejected", "expired", "blocked"})


def load_production_memory_feedback_capture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("production memory feedback capture must be a JSON object")
    return payload


def load_production_memory_promotion_decision(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("production memory promotion decision must be a JSON object")
    return payload


def build_production_memory_promotion_decision(
    capture: dict[str, Any],
    *,
    decision: str,
    rationale: str,
    reviewer_role: str,
    decided_at: str,
) -> dict[str, Any]:
    """Record an explicit operator decision without writing durable memory."""
    _validate_capture(capture)
    _validate_review_inputs(decision, rationale, reviewer_role, decided_at)

    candidate = _dict(capture.get("memory_candidate"))
    candidate_id = str(candidate["candidate_id"])
    source_feedback_ids = _source_feedback_ids(capture)
    promotion_decision = {
        "kind": PROMOTION_DECISION_KIND,
        "artifact_type": PROMOTION_DECISION_KIND,
        "schema_version": SCHEMA_VERSION,
        "decision_id": _safe_id("promotion:reviewed", candidate_id, decided_at),
        "candidate_id": candidate_id,
        "source_candidate_id": candidate_id,
        "source_feedback_ids": source_feedback_ids,
        "decision": decision,
        "review_mode": "explicit_operator_decision",
        "reviewer_role": reviewer_role,
        "rationale": rationale,
        "decided_at": decided_at,
        "template_only": False,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "source_loop_id": capture.get("source_loop_id", "unknown"),
        "claim_boundaries": {
            "human_acceptance": "not_reviewed",
            "business_validation": "not_validated",
            "provider_success": "not_attempted",
            "durable_memory_runtime": "not_implemented",
        },
    }
    _reject_unsafe(promotion_decision)
    return promotion_decision


def build_loop_with_reviewed_feedback(
    payload: dict[str, Any],
    capture: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> dict[str, Any]:
    """Overlay reviewed feedback onto a source loop without mutating it."""
    _validate_loop(payload)
    _validate_capture(capture)
    _validate_promotion_decision(capture, promotion_decision)
    _validate_source_loop_match(payload, capture, promotion_decision)

    derived = deepcopy(payload)
    candidate_id = str(_dict(capture.get("memory_candidate"))["candidate_id"])
    _append_unique(derived["feedback_events"], deepcopy(capture["feedback_event"]), "feedback_id")
    _append_unique(derived["memory_candidates"], deepcopy(capture["memory_candidate"]), "candidate_id")
    _append_unique(derived["promotion_decisions"], deepcopy(promotion_decision), "decision_id")

    next_pass_request = _dict(derived.setdefault("next_pass_request", {}))
    requested_refs = next_pass_request.setdefault("requested_refs", [])
    if not isinstance(requested_refs, list):
        raise ValueError("next_pass_request.requested_refs must be a list")
    if candidate_id not in requested_refs:
        requested_refs.append(candidate_id)

    _reject_unsafe(derived)
    return derived


def build_reviewed_feedback_run(
    payload: dict[str, Any],
    capture: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    derived_loop = build_loop_with_reviewed_feedback(payload, capture, promotion_decision)
    run = build_production_memory_loop_run(derived_loop)
    return derived_loop, run


def write_production_memory_promotion_decision(decision: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    return [write_json(output_root / "promotion_decision.json", decision)]


def write_reviewed_feedback_run(
    derived_loop: dict[str, Any],
    run: dict[str, Any],
    output_dir: str | Path,
) -> list[Path]:
    output_root = Path(output_dir)
    written_paths = [write_json(output_root / "derived_production_memory_loop.json", derived_loop)]
    written_paths.extend(write_production_memory_loop_run(run, output_root))
    return written_paths


def _validate_loop(payload: dict[str, Any]) -> None:
    if payload.get("kind") != KIND:
        raise ValueError(f"reviewed feedback overlay requires kind {KIND}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"reviewed feedback overlay requires schema_version {SCHEMA_VERSION}")
    for section in ("feedback_events", "memory_candidates", "promotion_decisions"):
        if not isinstance(payload.get(section), list):
            raise ValueError(f"{section} must be a list")
    if "next_pass_request" in payload and not isinstance(payload.get("next_pass_request"), dict):
        raise ValueError("next_pass_request must be an object")


def _validate_capture(capture: dict[str, Any]) -> None:
    if capture.get("kind") != FEEDBACK_CAPTURE_KIND:
        raise ValueError(f"promotion review requires kind {FEEDBACK_CAPTURE_KIND}")
    candidate = _dict(capture.get("memory_candidate"))
    feedback_event = _dict(capture.get("feedback_event"))
    if not isinstance(candidate.get("candidate_id"), str) or not candidate["candidate_id"]:
        raise ValueError("feedback capture memory_candidate.candidate_id is required")
    if not isinstance(feedback_event.get("feedback_id"), str) or not feedback_event["feedback_id"]:
        raise ValueError("feedback capture feedback_event.feedback_id is required")
    if feedback_event["feedback_id"] not in _source_feedback_ids(capture):
        raise ValueError("feedback capture candidate must reference its feedback event")
    _reject_unsafe(capture)


def _validate_review_inputs(decision: str, rationale: str, reviewer_role: str, decided_at: str) -> None:
    for label, value in {
        "decision": decision,
        "rationale": rationale,
        "reviewer_role": reviewer_role,
        "decided_at": decided_at,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    if decision not in REVIEWED_PROMOTION_DECISIONS:
        raise ValueError(f"unsupported reviewed promotion decision: {decision}")
    _reject_unsafe(
        {
            "decision": decision,
            "rationale": rationale,
            "reviewer_role": reviewer_role,
            "decided_at": decided_at,
        }
    )


def _validate_promotion_decision(capture: dict[str, Any], promotion_decision: dict[str, Any]) -> None:
    candidate_id = _dict(capture.get("memory_candidate"))["candidate_id"]
    if promotion_decision.get("kind") != PROMOTION_DECISION_KIND:
        raise ValueError(f"promotion decision requires kind {PROMOTION_DECISION_KIND}")
    if promotion_decision.get("candidate_id") != candidate_id:
        raise ValueError("promotion decision candidate_id must match feedback capture candidate")
    if promotion_decision.get("source_candidate_id") != candidate_id:
        raise ValueError("promotion decision source_candidate_id must match feedback capture candidate")
    decision_feedback_ids = _string_list(promotion_decision.get("source_feedback_ids"))
    if not set(_source_feedback_ids(capture)) <= set(decision_feedback_ids):
        raise ValueError("promotion decision must preserve feedback capture source refs")
    if promotion_decision.get("decision") not in REVIEWED_PROMOTION_DECISIONS:
        raise ValueError("promotion decision must be a reviewed terminal decision")
    if promotion_decision.get("review_mode") != "explicit_operator_decision":
        raise ValueError("promotion decision requires explicit_operator_decision review_mode")
    if promotion_decision.get("template_only") is not False:
        raise ValueError("promotion decision must not be a pending template")
    if promotion_decision.get("provider_calls_started") is not False:
        raise ValueError("promotion decision must not start provider calls")
    if promotion_decision.get("writes_long_term_memory") is not False:
        raise ValueError("promotion decision must not write long-term memory")
    _reject_unsafe(promotion_decision)


def _validate_source_loop_match(
    payload: dict[str, Any],
    capture: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> None:
    loop_id = payload.get("loop_id")
    source_loop_ids = {
        value
        for value in (capture.get("source_loop_id"), promotion_decision.get("source_loop_id"))
        if isinstance(value, str) and value != "unknown"
    }
    if source_loop_ids and source_loop_ids != {loop_id}:
        raise ValueError("feedback capture and promotion decision must reference the source loop_id")


def _append_unique(items: list[Any], item: dict[str, Any], id_field: str) -> None:
    item_id = item.get(id_field)
    if not isinstance(item_id, str) or not item_id:
        raise ValueError(f"{id_field} is required")
    existing_ids = {entry.get(id_field) for entry in items if isinstance(entry, dict)}
    if item_id in existing_ids:
        raise ValueError(f"duplicate {id_field}: {item_id}")
    items.append(item)


def _source_feedback_ids(capture: dict[str, Any]) -> list[str]:
    candidate = _dict(capture.get("memory_candidate"))
    source_feedback_ids = candidate.get("source_feedback_ids")
    if isinstance(source_feedback_ids, list) and source_feedback_ids:
        return _string_list(source_feedback_ids)
    feedback_id = _dict(capture.get("feedback_event")).get("feedback_id")
    return [str(feedback_id)] if feedback_id else []


def _safe_id(prefix: str, target_ref: str, created_at: str) -> str:
    raw = f"{prefix}:{target_ref}:{created_at}"
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    if any(fragment.lower() in raw for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS):
        raise ValueError("production memory promotion contains unsafe path, generated artifact path, or secret")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


__all__ = (
    "PROMOTION_DECISION_KIND",
    "REVIEWED_PROMOTION_DECISIONS",
    "build_loop_with_reviewed_feedback",
    "build_production_memory_promotion_decision",
    "build_reviewed_feedback_run",
    "load_production_memory_feedback_capture",
    "load_production_memory_promotion_decision",
    "write_production_memory_promotion_decision",
    "write_reviewed_feedback_run",
)
