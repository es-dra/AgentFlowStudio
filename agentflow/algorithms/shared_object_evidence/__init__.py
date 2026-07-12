from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


ALGORITHM_ID = "afs.shared_object_evidence.v0.1"
INPUT_CONTRACT = "repo-local shared object/evidence fixture with canonical refs and non-claims"
OUTPUT_CONTRACT = "deterministic validation report for refs, graph boundary, evidence gaps, and handoff envelope"
FAILURE_MODES = (
    "duplicate_ref_id",
    "unresolved_reference",
    "unapproved_production_graph_node",
    "unsafe_payload_marker",
    "claim_state_collapse",
    "incomplete_handoff_envelope",
)
EVIDENCE_BOUNDARY = "structure-verified local fixture only; no Runtime route, provider smoke, UI readiness, or acceptance claim"

GRAPH_STAGE = "storyboard_candidate_graph"
PROPOSED_GRAPH_STAGE = "proposed_future_extension"
REFERENCE_POLICY = "reference_only_no_node_write"
CURRENT_ALLOWED_GRAPH_NODE_TYPES = {"script", "shot", "asset", "fixed_visual_asset", "quality_report"}
PROTECTED_NON_CLAIMS = {
    "provider_smoke",
    "generated_media_quality",
    "human_creative_acceptance",
    "human_acceptance",
    "business_validation",
    "public_release",
    "legal_patent_readiness",
    "deploy_runtime_health",
    "runtime_health",
    "companyos_projection",
    "cos_active_rule_promotion",
}
REF_LIST_FIELDS = (
    "source_refs",
    "evidence_refs",
    "shot_refs",
    "branch_shot_refs",
    "asset_refs",
    "required_asset_refs",
    "node_refs",
    "target_refs",
    "applies_to_refs",
)
REF_VALUE_FIELDS = (
    "production_graph_ref",
    "source_asset_candidate_ref",
    "source_evidence_ref",
    "target_ref",
    "reuse_scope",
)
UNSAFE_MARKERS = tuple(
    fragment.lower()
    for fragment in (
        *AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS,
        "provider_raw",
        "provider raw",
        "raw_provider_response",
        "data_base64",
        "generated_media_bytes",
        ".obsidian",
        "week planner",
        "/users/",
        "/home/",
        "/tmp/",
        "customer_private",
        "real_cost",
    )
)


def load_json_fixture(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("shared object evidence fixture must be a JSON object")
    return payload


def load_shared_object_evidence_fixture(path: str | Path) -> dict[str, Any]:
    return validate_shared_object_evidence_fixture(load_json_fixture(path))


def validate_shared_object_evidence_fixture(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_unsafe_markers(payload)
    objects = payload.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("fixture objects must be a non-empty list")
    refs = _refs_by_id(objects)
    _validate_fixture_non_claims(payload)
    _validate_objects(objects, refs)
    _validate_references(objects, refs)
    graph_report = _validate_production_graph_boundary(objects, refs)
    _validate_handoff_envelopes(objects, refs)
    counts = Counter(str(item.get("object_type") or "") for item in objects)
    sorted_ref_ids = sorted(refs)
    handoffs = [item for item in objects if item.get("object_type") == "handoff_envelope"]
    return {
        "fixture_id": _required_text(payload, "fixture_id"),
        "fixture_claim_level": _required_text(payload, "fixture_claim_level"),
        "summary": {
            "object_count": len(objects),
            "evidence_reference_count": counts["evidence_reference"],
            "handoff_envelope_count": counts["handoff_envelope"],
            "production_graph_node_count": counts["production_graph_node"],
            "production_graph_reference_count": counts["production_graph_reference"],
            "proposed_graph_extension_count": graph_report["proposed_graph_extension_count"],
        },
        "object_type_counts": dict(sorted(counts.items())),
        "sorted_ref_ids": sorted_ref_ids,
        "non_claims": dict(payload.get("non_claims") or {}),
        "production_graph_boundary": {
            "current_allowed_node_types": sorted(CURRENT_ALLOWED_GRAPH_NODE_TYPES),
            "reference_policy": REFERENCE_POLICY,
            "proposed_extensions_require_evaluator": True,
        },
        "stage1_residual": _stage1_residual(handoffs),
    }


def _refs_by_id(objects: list[Any]) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for item in objects:
        if not isinstance(item, dict):
            raise ValueError("fixture object must be a JSON object")
        ref_id = _required_text(item, "ref_id")
        if ref_id in refs:
            raise ValueError(f"duplicate ref_id: {ref_id}")
        refs[ref_id] = item
    return refs


def _validate_objects(objects: list[dict[str, Any]], refs: dict[str, dict[str, Any]]) -> None:
    for item in objects:
        _required_text(item, "object_type")
        _required_text(item, "owner_lane")
        _required_text(item, "review_state")
        evidence_state = _required_text(item, "evidence_state")
        if item.get("unsafe_payload_markers_present") is not False:
            raise ValueError(f"unsafe marker flag must be false: {item['ref_id']}")
        if evidence_state == "partial" and not str(item.get("evidence_gap_reason") or "").strip():
            raise ValueError(f"partial evidence requires evidence_gap_reason: {item['ref_id']}")
        if item.get("object_type") == "fixed_asset":
            _validate_fixed_asset(item, refs)
        _validate_object_non_claims(item)


def _validate_fixed_asset(item: dict[str, Any], refs: dict[str, dict[str, Any]]) -> None:
    candidate_ref = _required_text(item, "source_asset_candidate_ref")
    evidence_ref = _required_text(item, "source_evidence_ref")
    if refs.get(candidate_ref, {}).get("object_type") != "asset_candidate":
        raise ValueError(f"fixed asset source candidate must resolve: {item['ref_id']}")
    if refs.get(evidence_ref, {}).get("object_type") != "evidence_reference":
        raise ValueError(f"fixed asset source evidence must resolve: {item['ref_id']}")
    if item.get("provider_calls_started") is not False:
        raise ValueError(f"protected non-claim provider_calls_started collapsed: {item['ref_id']}")
    if item.get("human_creative_acceptance_claimed") is not False:
        raise ValueError(f"protected non-claim human creative acceptance collapsed: {item['ref_id']}")


def _validate_references(objects: list[dict[str, Any]], refs: dict[str, dict[str, Any]]) -> None:
    for item in objects:
        for field in REF_LIST_FIELDS:
            value = item.get(field)
            if value is None:
                continue
            if not isinstance(value, list):
                raise ValueError(f"{field} must be a list: {item['ref_id']}")
            for ref in value:
                _require_resolved_ref(str(ref), refs, owner=item["ref_id"], field=field)
        for field in REF_VALUE_FIELDS:
            value = item.get(field)
            if value:
                _require_resolved_ref(str(value), refs, owner=item["ref_id"], field=field)


def _validate_production_graph_boundary(
    objects: list[dict[str, Any]], refs: dict[str, dict[str, Any]]
) -> dict[str, int]:
    proposed_count = 0
    for item in objects:
        if item.get("object_type") == "production_graph_node":
            node_type = _required_text(item, "node_type")
            policy = _required_text(item, "allowed_node_policy")
            stage = _required_text(item, "graph_stage")
            if node_type in CURRENT_ALLOWED_GRAPH_NODE_TYPES and policy == "current_allowed" and stage == GRAPH_STAGE:
                continue
            if policy == "evaluator_required" and stage == PROPOSED_GRAPH_STAGE:
                proposed_count += 1
                continue
            raise ValueError(f"unapproved production graph node: {item['ref_id']}")
        if item.get("object_type") == "production_graph_reference":
            if item.get("extension_policy") != REFERENCE_POLICY:
                raise ValueError(f"production graph reference must be reference-only: {item['ref_id']}")
            for ref_id in item.get("node_refs") or []:
                node = refs.get(str(ref_id)) or {}
                if node.get("object_type") != "production_graph_node":
                    raise ValueError(f"production graph reference node ref must resolve to node: {item['ref_id']}")
                if node.get("allowed_node_policy") != "current_allowed":
                    raise ValueError(f"production graph reference cannot write proposed node: {item['ref_id']}")
    return {"proposed_graph_extension_count": proposed_count}


def _validate_handoff_envelopes(objects: list[dict[str, Any]], refs: dict[str, dict[str, Any]]) -> None:
    for item in objects:
        if item.get("object_type") != "handoff_envelope":
            continue
        for field in ("target_refs", "next_owner", "next_action", "close_condition", "reuse_scope"):
            if not item.get(field):
                raise ValueError(f"incomplete handoff envelope missing {field}: {item['ref_id']}")
        if not item.get("evidence_refs") and not item.get("evidence_gap_reason"):
            raise ValueError(f"incomplete handoff envelope missing evidence route: {item['ref_id']}")
        if not isinstance(item.get("non_claims"), dict) or not item["non_claims"]:
            raise ValueError(f"incomplete handoff envelope missing non_claims: {item['ref_id']}")
        _require_resolved_ref(str(item["reuse_scope"]), refs, owner=item["ref_id"], field="reuse_scope")


def _validate_fixture_non_claims(payload: dict[str, Any]) -> None:
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, dict):
        raise ValueError("fixture non_claims must be present")
    for claim in PROTECTED_NON_CLAIMS:
        if claim in non_claims and non_claims[claim] is not False:
            raise ValueError(f"protected non-claim collapsed: {claim}")


def _validate_object_non_claims(item: dict[str, Any]) -> None:
    non_claims = item.get("non_claims")
    if not isinstance(non_claims, dict):
        return
    for claim in PROTECTED_NON_CLAIMS:
        if claim in non_claims and non_claims[claim] is not False:
            raise ValueError(f"protected non-claim collapsed: {item['ref_id']} {claim}")


def _reject_unsafe_markers(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    for marker in UNSAFE_MARKERS:
        if marker and marker in serialized:
            raise ValueError("unsafe marker found in shared object evidence fixture")


def _require_resolved_ref(ref: str, refs: dict[str, dict[str, Any]], *, owner: str, field: str) -> None:
    if ref not in refs:
        raise ValueError(f"unresolved reference in {owner}.{field}: {ref}")


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ValueError(f"missing required field: {field}")
    return value


def _stage1_residual(handoffs: list[dict[str, Any]]) -> str:
    blockers = [str(item) for handoff in handoffs for item in (handoff.get("blockers") or [])]
    if "stage1_evaluator_system_error_residual" in blockers:
        return "evaluator_system_error_residual_carried"
    return "not_recorded"


__all__ = (
    "ALGORITHM_ID",
    "CURRENT_ALLOWED_GRAPH_NODE_TYPES",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "GRAPH_STAGE",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "PROTECTED_NON_CLAIMS",
    "REFERENCE_POLICY",
    "load_json_fixture",
    "load_shared_object_evidence_fixture",
    "validate_shared_object_evidence_fixture",
)
