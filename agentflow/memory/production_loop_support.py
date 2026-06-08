from __future__ import annotations

import json
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS, FAILED, PASSED

SOURCE_SECTIONS = (
    "project_input",
    "artifact_ledger",
    "feedback_events",
    "memory_candidates",
    "promotion_decisions",
)
SUPPORTED_PROMOTION_DECISIONS = frozenset({"promoted", "merged", "rejected", "expired", "blocked", "pending"})


def indexes(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {str(item.get("ref_id")): item for item in list_value(payload.get("artifact_ledger")) if item.get("ref_id")}
    feedback = {str(item.get("feedback_id")): item for item in list_value(payload.get("feedback_events")) if item.get("feedback_id")}
    candidates = {str(item.get("candidate_id")): item for item in list_value(payload.get("memory_candidates")) if item.get("candidate_id")}
    decisions = {str(item.get("decision_id")): item for item in list_value(payload.get("promotion_decisions")) if item.get("decision_id")}
    decisions_by_candidate = {str(item.get("candidate_id")): item for item in decisions.values() if item.get("candidate_id")}
    return {
        "artifacts": artifacts,
        "feedback": feedback,
        "candidates": candidates,
        "decisions": decisions,
        "decisions_by_candidate": decisions_by_candidate,
    }


def missing_references(payload: dict[str, Any]) -> list[str]:
    indexed = indexes(payload)
    known = set().union(indexed["artifacts"], indexed["feedback"], indexed["candidates"], indexed["decisions"])
    missing: list[str] = []
    missing.extend(ref for ref in list_value(dict_value(payload.get("project_input")).get("input_refs")) if ref not in indexed["artifacts"])
    for artifact in indexed["artifacts"].values():
        missing.extend(ref for ref in list_value(artifact.get("source_refs")) if ref not in known)
    missing.extend(event.get("target_ref") for event in indexed["feedback"].values() if event.get("target_ref") not in indexed["artifacts"])
    for candidate in indexed["candidates"].values():
        missing.extend(ref for ref in list_value(candidate.get("source_feedback_ids")) if ref not in indexed["feedback"])
    missing.extend(decision.get("candidate_id") for decision in indexed["decisions"].values() if decision.get("candidate_id") not in indexed["candidates"])
    missing.extend(ref for ref in requested_refs(payload) if ref not in known)
    return sorted({str(ref) for ref in missing if ref})


def requested_refs(payload: dict[str, Any]) -> list[str]:
    refs = list_value(dict_value(payload.get("next_pass_request")).get("requested_refs"))
    return [str(ref) for ref in refs if ref]


def source_sections_present(payload: dict[str, Any]) -> bool:
    return all(section in payload for section in SOURCE_SECTIONS)


def source_sections_typed(payload: dict[str, Any]) -> bool:
    return isinstance(payload.get("project_input"), dict) and all(
        isinstance(payload.get(section), list) for section in SOURCE_SECTIONS if section != "project_input"
    )


def record_ids_unique(payload: dict[str, Any]) -> bool:
    id_fields = {
        "artifact_ledger": "ref_id",
        "feedback_events": "feedback_id",
        "memory_candidates": "candidate_id",
        "promotion_decisions": "decision_id",
    }
    for section, field in id_fields.items():
        values = [item.get(field) for item in list_value(payload.get(section)) if item.get(field)]
        if len(values) != len(set(values)):
            return False
    return True


def promoted_memory_has_decision(payload: dict[str, Any]) -> bool:
    decisions = indexes(payload)["decisions_by_candidate"]
    return all(
        candidate.get("candidate_id") in decisions
        for candidate in list_value(payload.get("memory_candidates"))
        if candidate.get("status") == "promoted"
    )


def promotion_decisions_supported(payload: dict[str, Any]) -> bool:
    return all(item.get("decision") in SUPPORTED_PROMOTION_DECISIONS for item in list_value(payload.get("promotion_decisions")))


def provider_mode(payload: dict[str, Any]) -> str:
    return str(payload.get("provider_mode", "no-provider"))


def remote_provider_required(payload: dict[str, Any]) -> bool:
    return bool(payload.get("provider_route") or payload.get("requires_remote_provider"))


def has_private_fragment(payload: dict[str, Any]) -> bool:
    raw = json.dumps(payload, ensure_ascii=False).lower()
    return any(fragment.lower() in raw for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS)


def reference_message(payload: dict[str, Any]) -> str:
    missing = missing_references(payload)
    return "all source refs resolve" if not missing else f"missing refs: {', '.join(missing)}"


def project_id(payload: dict[str, Any]) -> str:
    return str(dict_value(payload.get("project_input")).get("project_id", "unknown"))


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}
