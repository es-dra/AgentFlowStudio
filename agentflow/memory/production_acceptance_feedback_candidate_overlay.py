from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow.memory.production_acceptance_feedback_candidate_overlay_validation import (
    dict_value,
    list_value,
    reject_unsafe,
    validate_loop,
    validate_packet,
    validate_promotion_decision,
)
from agentflow.memory.production_loop import (
    SCHEMA_VERSION,
    build_production_memory_loop_run,
    write_production_memory_loop_run,
)

ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND = (
    "agentflow_production_memory_acceptance_feedback_candidate_promotion_overlay"
)


def load_acceptance_feedback_candidate_promotion_decision(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("acceptance feedback candidate promotion decision must be a JSON object")
    return payload


def build_loop_with_acceptance_feedback_candidate_reviewed_feedback(
    payload: dict[str, Any],
    packet: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> dict[str, Any]:
    """Overlay one explicitly reviewed acceptance feedback candidate onto a source loop."""
    validate_loop(payload)
    validate_packet(packet)
    validate_promotion_decision(packet, promotion_decision)

    derived = deepcopy(payload)
    candidate = deepcopy(dict_value(packet["memory_candidate"]))
    target_ref = str(candidate.get("target_ref", f"operator-run-package:{packet.get('source_operator_loop_id', 'unknown')}"))
    feedback_id = str(packet["source_acceptance_feedback_event_id"])
    _append_unique(derived["artifact_ledger"], _package_artifact(packet, target_ref), "ref_id")
    _append_unique(derived["feedback_events"], _acceptance_feedback_record(packet, candidate, feedback_id, target_ref), "feedback_id")
    _append_unique(derived["memory_candidates"], _acceptance_memory_candidate_record(candidate, packet), "candidate_id")
    _append_unique(derived["promotion_decisions"], _promotion_decision_record(promotion_decision), "decision_id")

    requested_refs = _requested_refs(derived)
    candidate_id = str(candidate["candidate_id"])
    if candidate_id not in requested_refs:
        requested_refs.append(candidate_id)

    reject_unsafe(derived, allow_source_refs=True)
    return derived


def build_acceptance_feedback_candidate_reviewed_run(
    payload: dict[str, Any],
    packet: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    derived_loop = build_loop_with_acceptance_feedback_candidate_reviewed_feedback(payload, packet, promotion_decision)
    run = build_production_memory_loop_run(derived_loop)
    overlay = build_acceptance_feedback_candidate_promotion_overlay(packet, promotion_decision, run)
    return derived_loop, run, overlay


def build_acceptance_feedback_candidate_promotion_overlay(
    packet: dict[str, Any],
    promotion_decision: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    validate_packet(packet)
    validate_promotion_decision(packet, promotion_decision)
    candidate_id = str(promotion_decision["candidate_id"])
    included_ids = {str(ref.get("ref_id")) for ref in list_value(run["context_bundle"].get("included_refs"))}
    blocked_ids = {str(ref.get("ref_id")) for ref in list_value(run["context_bundle"].get("blocked_refs"))}
    return {
        "kind": ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
        "artifact_type": ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
        "schema_version": packet.get("schema_version", SCHEMA_VERSION),
        "source_packet_id": packet.get("packet_id", "unknown"),
        "source_decision_id": promotion_decision.get("decision_id", "unknown"),
        "source_acceptance_feedback_event_id": packet.get("source_acceptance_feedback_event_id", "unknown"),
        "source_acceptance_decision": packet.get("source_acceptance_decision", "unknown"),
        "source_artifact_type": packet.get("source_artifact_type", "agentflow_production_memory_operator_run_package"),
        "source_artifact_path": packet.get("source_artifact_path", packet.get("source_package_path", "unknown")),
        "source_artifact_status": packet.get("source_artifact_status", packet.get("source_check_status", "unknown")),
        "source_ready_for_acceptance": packet.get("source_ready_for_acceptance") is True,
        "source_target_ref": dict_value(packet.get("memory_candidate")).get("target_ref", "unknown"),
        "source_target_artifact_type": dict_value(packet.get("memory_candidate")).get("target_artifact_type", "unknown"),
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
            "not new human acceptance",
            "not business validation",
            "not durable memory",
            "not provider success",
            "not Company KB promotion",
        ],
    }


def write_acceptance_feedback_candidate_reviewed_run(
    derived_loop: dict[str, Any],
    run: dict[str, Any],
    overlay: dict[str, Any],
    output_dir: str | Path,
) -> list[Path]:
    output_root = Path(output_dir)
    written_paths = [write_json(output_root / "derived_production_memory_loop.json", derived_loop)]
    written_paths.extend(write_production_memory_loop_run(run, output_root))
    written_paths.append(write_json(output_root / "acceptance_feedback_candidate_promotion_overlay.json", overlay))
    return written_paths


def _package_artifact(packet: dict[str, Any], target_ref: str) -> dict[str, Any]:
    candidate = dict_value(packet.get("memory_candidate"))
    artifact_type = candidate.get("target_artifact_type", packet.get("source_artifact_type", "agentflow_production_memory_operator_run_package"))
    label = _artifact_label(str(artifact_type))
    return {
        "ref_id": target_ref,
        "artifact_type": artifact_type,
        "title": f"{label} acceptance evidence",
        "status": "accepted" if candidate.get("status") == "candidate" else "blocked",
        "eligible_for_next_context": False,
        "summary": f"{label} captured as acceptance feedback evidence only.",
        "source_refs": [],
    }


def _acceptance_feedback_record(
    packet: dict[str, Any],
    candidate: dict[str, Any],
    feedback_id: str,
    target_ref: str,
) -> dict[str, Any]:
    return {
        "feedback_id": feedback_id,
        "target_ref": target_ref,
        "decision": packet.get("source_acceptance_decision", "unknown"),
        "summary": candidate.get("statement", ""),
        "status": "human_recorded",
        "reviewer_role": "operator",
        "writes_long_term_memory": False,
    }


def _acceptance_memory_candidate_record(candidate: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    record = deepcopy(candidate)
    record["candidate_is_promoted_memory"] = False
    record["writes_long_term_memory"] = False
    record["writes_company_kb"] = False
    record["source_acceptance_feedback_candidate_packet_id"] = packet.get("packet_id", "unknown")
    return record


def _promotion_decision_record(decision: dict[str, Any]) -> dict[str, Any]:
    record = deepcopy(decision)
    if isinstance(record.get("source_artifact_path"), str):
        record["source_artifact_path"] = _safe_source_path(record["source_artifact_path"])
    return record


def _safe_source_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if "data/processed/runs/" not in normalized:
        return normalized
    parts = [part for part in normalized.split("/") if part]
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return parts[-1] if parts else "unknown"


def _artifact_label(artifact_type: str) -> str:
    if artifact_type == "agentflow_production_memory_next_operator_action_result":
        return "next operator action result"
    return "operator run package"


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


__all__ = (
    "ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND",
    "build_acceptance_feedback_candidate_promotion_overlay",
    "build_acceptance_feedback_candidate_reviewed_run",
    "build_loop_with_acceptance_feedback_candidate_reviewed_feedback",
    "load_acceptance_feedback_candidate_promotion_decision",
    "write_acceptance_feedback_candidate_reviewed_run",
)
