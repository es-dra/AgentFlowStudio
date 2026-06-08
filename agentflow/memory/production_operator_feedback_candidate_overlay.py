from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_loop import (
    KIND,
    SCHEMA_VERSION,
    build_production_memory_loop_run,
    write_production_memory_loop_run,
)
from agentflow.memory.production_operator_feedback_candidate import OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND
from agentflow.memory.production_operator_feedback_candidate_promotion import (
    OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
    OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISIONS,
    REUSE_ALLOWED_DECISIONS,
)
from agentflow.harness.json_io import write_json

OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND = (
    "agentflow_production_memory_operator_feedback_candidate_promotion_overlay"
)
UNSAFE_EXTRA_FRAGMENTS = (
    "http://",
    "https://",
    "file://",
    "data:image/",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
)


def load_operator_feedback_candidate_promotion_decision(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("operator feedback candidate promotion decision must be a JSON object")
    return payload


def build_loop_with_operator_feedback_candidate_reviewed_feedback(
    payload: dict[str, Any],
    packet: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> dict[str, Any]:
    """Overlay one explicitly reviewed operator feedback candidate onto a source loop."""
    _validate_loop(payload)
    _validate_packet(packet)
    _validate_promotion_decision(packet, promotion_decision)

    derived = deepcopy(payload)
    candidate = deepcopy(_dict(packet["memory_candidate"]))
    target_ref = str(candidate.get("target_ref", f"operator-node:{packet.get('source_target_node_id', 'unknown')}"))
    feedback_id = str(packet["source_feedback_event_id"])
    _append_unique(derived["artifact_ledger"], _operator_node_artifact(packet, target_ref), "ref_id")
    _append_unique(derived["feedback_events"], _operator_feedback_record(packet, feedback_id, target_ref), "feedback_id")
    _append_unique(derived["memory_candidates"], _operator_memory_candidate_record(candidate, packet), "candidate_id")
    _append_unique(derived["promotion_decisions"], deepcopy(promotion_decision), "decision_id")

    requested_refs = _requested_refs(derived)
    candidate_id = str(candidate["candidate_id"])
    if candidate_id not in requested_refs:
        requested_refs.append(candidate_id)

    _reject_unsafe(derived)
    return derived


def build_operator_feedback_candidate_reviewed_run(
    payload: dict[str, Any],
    packet: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    derived_loop = build_loop_with_operator_feedback_candidate_reviewed_feedback(payload, packet, promotion_decision)
    run = build_production_memory_loop_run(derived_loop)
    overlay = build_operator_feedback_candidate_promotion_overlay(packet, promotion_decision, run)
    return derived_loop, run, overlay


def build_operator_feedback_candidate_promotion_overlay(
    packet: dict[str, Any],
    promotion_decision: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    _validate_packet(packet)
    _validate_promotion_decision(packet, promotion_decision)
    candidate_id = str(promotion_decision["candidate_id"])
    included_ids = {str(ref.get("ref_id")) for ref in _list(run["context_bundle"].get("included_refs"))}
    blocked_ids = {str(ref.get("ref_id")) for ref in _list(run["context_bundle"].get("blocked_refs"))}
    return {
        "kind": OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
        "artifact_type": OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
        "schema_version": packet.get("schema_version", SCHEMA_VERSION),
        "source_packet_id": packet.get("packet_id", "unknown"),
        "source_decision_id": promotion_decision.get("decision_id", "unknown"),
        "source_feedback_event_id": packet.get("source_feedback_event_id", "unknown"),
        "candidate_id": candidate_id,
        "decision": promotion_decision.get("decision", "unknown"),
        "decision_effect": "included_in_context" if candidate_id in included_ids else "blocked_from_context",
        "candidate_included_in_context": candidate_id in included_ids,
        "candidate_blocked_from_context": candidate_id in blocked_ids,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "run_readiness": run["pass_readiness"].get("overall_status", "unknown"),
        "context_bundle_id": run["context_bundle"].get("bundle_id", "unknown"),
        "non_claims": [
            "not human acceptance",
            "not business validation",
            "not durable memory",
            "not provider success",
            "not Company KB promotion",
        ],
    }


def write_operator_feedback_candidate_reviewed_run(
    derived_loop: dict[str, Any],
    run: dict[str, Any],
    overlay: dict[str, Any],
    output_dir: str | Path,
) -> list[Path]:
    output_root = Path(output_dir)
    written_paths = [write_json(output_root / "derived_production_memory_loop.json", derived_loop)]
    written_paths.extend(write_production_memory_loop_run(run, output_root))
    written_paths.append(write_json(output_root / "operator_feedback_candidate_promotion_overlay.json", overlay))
    return written_paths


def _validate_loop(payload: dict[str, Any]) -> None:
    if payload.get("kind") != KIND:
        raise ValueError(f"operator feedback candidate overlay requires kind {KIND}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"operator feedback candidate overlay requires schema_version {SCHEMA_VERSION}")
    for section in ("artifact_ledger", "feedback_events", "memory_candidates", "promotion_decisions"):
        if not isinstance(payload.get(section), list):
            raise ValueError(f"{section} must be a list")


def _validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("kind") != OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND:
        raise ValueError(f"operator feedback candidate overlay requires kind {OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND}")
    if packet.get("candidate_generation_status") != "candidate_only":
        raise ValueError("operator feedback candidate overlay requires candidate_only packet")
    if packet.get("provider_calls_started") is not False:
        raise ValueError("operator feedback candidate overlay requires provider_calls_started false")
    if packet.get("writes_long_term_memory") is not False or packet.get("writes_company_kb") is not False:
        raise ValueError("operator feedback candidate overlay requires no memory or Company KB writes")
    candidate = _dict(packet.get("memory_candidate"))
    if not isinstance(candidate.get("candidate_id"), str) or not candidate["candidate_id"].strip():
        raise ValueError("operator feedback candidate overlay requires memory_candidate.candidate_id")
    _reject_unsafe(packet)


def _validate_promotion_decision(packet: dict[str, Any], decision: dict[str, Any]) -> None:
    candidate = _dict(packet.get("memory_candidate"))
    template = _dict(packet.get("promotion_decision_template"))
    if decision.get("kind") != OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND:
        raise ValueError("explicit operator feedback candidate promotion decision is required")
    if decision.get("source_packet_id") != packet.get("packet_id"):
        raise ValueError("operator feedback candidate decision source_packet_id must match packet")
    if decision.get("source_feedback_event_id") != packet.get("source_feedback_event_id"):
        raise ValueError("operator feedback candidate decision source_feedback_event_id must match packet")
    if decision.get("source_promotion_decision_template_id") != template.get("decision_id"):
        raise ValueError("operator feedback candidate decision must preserve source pending template id")
    if decision.get("candidate_id") != candidate.get("candidate_id"):
        raise ValueError("operator feedback candidate decision candidate_id must match packet")
    if decision.get("decision") not in OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISIONS:
        raise ValueError("operator feedback candidate decision must be reviewed")
    if decision.get("review_mode") != "explicit_operator_decision" or decision.get("template_only") is not False:
        raise ValueError("explicit operator feedback candidate promotion decision is required")
    if decision.get("provider_calls_started") is not False:
        raise ValueError("operator feedback candidate decision must not start provider calls")
    if decision.get("writes_long_term_memory") is not False or decision.get("writes_company_kb") is not False:
        raise ValueError("operator feedback candidate decision must not write memory or Company KB")
    if decision.get("decision") in REUSE_ALLOWED_DECISIONS and candidate.get("status") != "candidate":
        raise ValueError("only candidate operator feedback can be promoted or merged")
    _reject_unsafe(decision)


def _operator_node_artifact(packet: dict[str, Any], target_ref: str) -> dict[str, Any]:
    return {
        "ref_id": target_ref,
        "title": packet.get("source_target_node_id", target_ref),
        "status": "accepted" if _dict(packet.get("memory_candidate")).get("status") == "candidate" else "blocked",
        "eligible_for_next_context": False,
        "summary": "Operator-loop node captured as feedback evidence only.",
        "source_refs": [],
    }


def _operator_feedback_record(packet: dict[str, Any], feedback_id: str, target_ref: str) -> dict[str, Any]:
    candidate = _dict(packet.get("memory_candidate"))
    return {
        "feedback_id": feedback_id,
        "target_ref": target_ref,
        "decision": "accepted" if candidate.get("status") == "candidate" else "rejected",
        "summary": candidate.get("statement", ""),
        "status": "reviewed",
        "reviewer_role": "operator",
        "writes_long_term_memory": False,
    }


def _operator_memory_candidate_record(candidate: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    record = deepcopy(candidate)
    record["candidate_is_promoted_memory"] = False
    record["writes_long_term_memory"] = False
    record["writes_company_kb"] = False
    record["source_operator_feedback_candidate_packet_id"] = packet.get("packet_id", "unknown")
    return record


def _requested_refs(loop: dict[str, Any]) -> list[Any]:
    next_pass_request = loop.setdefault("next_pass_request", {})
    if not isinstance(next_pass_request, dict):
        raise ValueError("next_pass_request must be an object")
    refs = next_pass_request.setdefault("requested_refs", [])
    if not isinstance(refs, list):
        raise ValueError("next_pass_request.requested_refs must be a list")
    return refs


def _append_unique(items: list[Any], item: dict[str, Any], id_field: str) -> None:
    item_id = item.get(id_field)
    if not isinstance(item_id, str) or not item_id:
        raise ValueError(f"{id_field} is required")
    existing_ids = {entry.get(id_field) for entry in items if isinstance(entry, dict)}
    if item_id not in existing_ids:
        items.append(item)


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("production memory operator feedback candidate overlay contains unsafe path, media reference, provider URL, or secret")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND",
    "build_loop_with_operator_feedback_candidate_reviewed_feedback",
    "build_operator_feedback_candidate_promotion_overlay",
    "build_operator_feedback_candidate_reviewed_run",
    "load_operator_feedback_candidate_promotion_decision",
    "write_operator_feedback_candidate_reviewed_run",
)
