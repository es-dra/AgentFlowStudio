from __future__ import annotations

from typing import Any

from ._constants import (
    ACK_STATES,
    ACTIVE_PENDING_STATES,
    ARCHIVE_EVALUATION_STATES,
    ARCHIVE_POLICIES,
    CLAIM_STATES,
    CONTROL_EVENT_ARTIFACT_TYPE,
    CONTROL_EVENT_SCHEMA_VERSION,
    CONTROL_REGISTER_ARTIFACT_TYPE,
    EVENT_TYPES,
    EVIDENCE_SOURCE_CLASSES,
    FIXED_ROLE_SURFACE_ROLES,
    IMPLEMENTATION_LANE_KINDS,
)
from ._helpers import reject_unsafe_markers, required_dict, required_text
from ._worker_final import (
    apply_worker_final_ingest,
    dedupe_worker_final_ingest_events,
    validate_worker_final_ingest,
)


def validate_control_event(event: dict[str, Any]) -> None:
    reject_unsafe_markers(event)
    if event.get("schema_version") != CONTROL_EVENT_SCHEMA_VERSION:
        raise ValueError(f"control event schema_version must be {CONTROL_EVENT_SCHEMA_VERSION}")
    if event.get("artifact_type") != CONTROL_EVENT_ARTIFACT_TYPE:
        raise ValueError(f"control event artifact_type must be {CONTROL_EVENT_ARTIFACT_TYPE}")
    if required_text(event, "event_type") not in EVENT_TYPES:
        raise ValueError("unsupported control event_type")
    required_text(event, "event_id")
    required_text(event, "recorded_at")
    required_text(event, "lane_id")
    required_text(event, "top_down_dispatch_id")
    required_text(event, "bottom_up_feedback_id")
    _validate_evidence_source(required_dict(event, "evidence_source"))
    payload = required_dict(event, "payload")
    event_type = str(event["event_type"])
    if event_type != "claim_state_changed" and "claim_state" in payload:
        raise ValueError("claim_state must use claim_state_changed events")
    if event_type != "non_claim_recorded" and "non_claims" in payload:
        raise ValueError("non_claims must use non_claim_recorded events")
    if event_type == "lane_registered":
        _validate_lane_registration(payload)
    elif event_type == "role_surface_registered":
        _validate_role_surface(required_dict(payload, "role_surface"))
    elif event_type == "artifact_attached":
        _validate_artifact_handle(required_dict(payload, "artifact_handle"))
    elif event_type == "claim_state_changed":
        _validate_claim_state_event(payload)
    elif event_type == "non_claim_recorded":
        _validate_non_claim_event(payload)
    elif event_type == "archive_policy_evaluated":
        _validate_archive_policy(required_dict(payload, "archive_policy"))
    elif event_type == "archive_executed":
        if payload.get("archive_execution_confirmed") is not True:
            raise ValueError("archive_executed event requires archive_execution_confirmed true")
    elif event_type == "ack_state_changed":
        _validate_ack(required_dict(payload, "ack"))
    elif event_type == "worker_final_ingested":
        worker_final = validate_worker_final_ingest(payload, event)
        _validate_ack(required_dict(worker_final, "ack"))
        _validate_archive_policy(required_dict(worker_final, "archive_policy"))
        if worker_final["archive_policy"].get("archive_execution_allowed") is True:
            if worker_final["ack"].get("ack_delivery_confirmed") is not True:
                raise ValueError("worker-final archive cannot be allowed before ack delivery confirmation")
        if "non_claims" in worker_final:
            _validate_non_claim_event({"non_claims": worker_final["non_claims"]})


def materialize_control_register(events: list[dict[str, Any]]) -> dict[str, Any]:
    lanes: dict[str, dict[str, Any]] = {}
    deduped_events = dedupe_worker_final_ingest_events(events)
    for event in deduped_events:
        validate_control_event(event)
        event_id = str(event["event_id"])
        lane = _lane(lanes, event)
        lane["event_ids"].append(event_id)
        lane["last_event_id"] = event_id
        source = event["evidence_source"]
        if source not in lane["evidence_sources"]:
            lane["evidence_sources"].append(source)
        _apply_event(lane, event)
    register = {
        "schema_version": CONTROL_EVENT_SCHEMA_VERSION,
        "artifact_type": CONTROL_REGISTER_ARTIFACT_TYPE,
        "register_scope": "active_pending_control_lanes",
        "materialized_from_event_count": len(deduped_events),
        "active_pending_lane_ids": sorted(
            lane_id for lane_id, lane in lanes.items() if lane.get("state") in ACTIVE_PENDING_STATES
        ),
        "lanes": [lanes[lane_id] for lane_id in sorted(lanes)],
    }
    validate_active_pending_register(register)
    return register


def validate_active_pending_register(register: dict[str, Any]) -> None:
    reject_unsafe_markers(register)
    if register.get("schema_version") != CONTROL_EVENT_SCHEMA_VERSION:
        raise ValueError(f"control register schema_version must be {CONTROL_EVENT_SCHEMA_VERSION}")
    if register.get("artifact_type") != CONTROL_REGISTER_ARTIFACT_TYPE:
        raise ValueError(f"control register artifact_type must be {CONTROL_REGISTER_ARTIFACT_TYPE}")
    lanes = register.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("control register requires lanes")
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("control register lanes must be objects")
        if lane.get("state") not in ACTIVE_PENDING_STATES:
            continue
        lane_id = required_text(lane, "lane_id")
        if lane.get("lane_kind") in IMPLEMENTATION_LANE_KINDS and not lane.get("implementation_artifact_handles"):
            raise ValueError(f"implementation artifact handle missing for active/pending lane: {lane_id}")
        for handle in lane.get("implementation_artifact_handles") or []:
            _validate_artifact_handle(handle)
        _validate_active_archive_and_ack(lane)
        _validate_required_role_surfaces(lane)


def _apply_event(lane: dict[str, Any], event: dict[str, Any]) -> None:
    payload = event["payload"]
    event_type = str(event["event_type"])
    if event_type == "lane_registered":
        lane["state"] = str(payload["lane_state"])
        lane["lane_kind"] = str(payload["lane_kind"])
        lane["route_basis"] = str(payload.get("route_basis") or "")
    elif event_type == "role_surface_registered":
        surface = payload["role_surface"]
        lane["fixed_role_surfaces"][surface["role"]] = surface
    elif event_type == "artifact_attached":
        handle = payload["artifact_handle"]
        lane["artifact_handles"].append(handle)
        if handle["artifact_role"] == "implementation":
            lane["implementation_artifact_handles"].append(handle)
    elif event_type == "claim_state_changed":
        claim = payload["claim_state"]
        lane["claim_states"][claim["claim_id"]] = claim
    elif event_type == "non_claim_recorded":
        lane["non_claims"].update(payload["non_claims"])
    elif event_type == "ack_state_changed":
        lane["ack"] = payload["ack"]
    elif event_type == "archive_policy_evaluated":
        lane["archive_policy"] = payload["archive_policy"]
    elif event_type == "archive_executed":
        _require_archive_execution_allowed(lane)
        lane["archive_execution"] = {"event_id": event["event_id"], "archive_execution_confirmed": True}
        lane["state"] = "archived"
    elif event_type == "worker_final_ingested":
        apply_worker_final_ingest(lane, event)


def _lane(lanes: dict[str, dict[str, Any]], event: dict[str, Any]) -> dict[str, Any]:
    lane_id = str(event["lane_id"])
    return lanes.setdefault(
        lane_id,
        {
            "lane_id": lane_id,
            "lane_kind": "unknown",
            "state": "pending_control",
            "top_down_dispatch_id": str(event["top_down_dispatch_id"]),
            "bottom_up_feedback_id": str(event["bottom_up_feedback_id"]),
            "route_basis": "",
            "event_ids": [],
            "last_event_id": "",
            "artifact_handles": [],
            "implementation_artifact_handles": [],
            "claim_states": {},
            "non_claims": {},
            "archive_policy": {},
            "archive_execution": {},
            "ack": {"ack_required": True, "ack_state": "no_ack", "ack_delivery_confirmed": False, "no_ack": True},
            "fixed_role_surfaces": {},
            "evidence_sources": [],
        },
    )


def _validate_lane_registration(payload: dict[str, Any]) -> None:
    if required_text(payload, "lane_state") not in ACTIVE_PENDING_STATES | {"blocked", "closed", "archived"}:
        raise ValueError("unsupported lane_state")
    required_text(payload, "lane_kind")


def _validate_evidence_source(source: dict[str, Any]) -> None:
    if required_text(source, "source_class") not in EVIDENCE_SOURCE_CLASSES:
        raise ValueError("unsupported evidence source classification")
    required_text(source, "source_ref")
    required_text(source, "safe_summary")


def _validate_role_surface(surface: dict[str, Any]) -> None:
    if required_text(surface, "role") not in FIXED_ROLE_SURFACE_ROLES:
        raise ValueError("unsupported fixed role surface role")
    required_text(surface, "surface_id")
    required_text(surface, "thread_ref")
    if surface.get("fixed_role_surface") is not True:
        raise ValueError("role surface must be fixed")


def _validate_artifact_handle(handle: dict[str, Any]) -> None:
    role = required_text(handle, "artifact_role")
    required_text(handle, "artifact_id")
    required_text(handle, "artifact_kind")
    required_text(handle, "uri")
    if handle.get("does_not_store_secrets") is not True:
        raise ValueError("artifact handle must declare does_not_store_secrets true")
    if handle.get("does_not_store_private_asset_bytes") is not True:
        raise ValueError("artifact handle must declare does_not_store_private_asset_bytes true")
    durability = required_dict(handle, "durability")
    if durability.get("is_durable") is not True:
        raise ValueError("artifact handle durability must be true")
    required_text(durability, "storage_medium")
    required_text(durability, "durability_state")
    required_text(durability, "ref")
    if role == "implementation" and not str(handle.get("uri") or "").strip():
        raise ValueError("implementation artifact handle uri must be non-empty")


def _validate_claim_state_event(payload: dict[str, Any]) -> None:
    claim = required_dict(payload, "claim_state")
    required_text(claim, "claim_id")
    if required_text(claim, "state") not in CLAIM_STATES:
        raise ValueError("unsupported claim state")
    if claim.get("first_class_claim_state_event") is not True:
        raise ValueError("claim state must be first-class event evidence")
    if claim.get("non_claim_separated") is not True:
        raise ValueError("claim state must declare non-claim separation")


def _validate_non_claim_event(payload: dict[str, Any]) -> None:
    non_claims = required_dict(payload, "non_claims")
    for key, value in non_claims.items():
        if not str(key).strip() or value is not False:
            raise ValueError("non-claim values must be explicit false boundaries")


def _validate_archive_policy(policy: dict[str, Any]) -> None:
    if required_text(policy, "policy") not in ARCHIVE_POLICIES:
        raise ValueError("unsupported archive policy")
    if policy.get("owner_manual_archive_excluded") != "no":
        raise ValueError("owner_manual_archive_excluded must be no")
    if policy.get("archive_after_ack_delivery_confirmed") is not True:
        raise ValueError("archive_after_ack_delivery_confirmed must be true")
    if policy.get("evaluated_before_archive_execution") is not True:
        raise ValueError("archive policy must be evaluated before archive execution")
    if required_text(policy, "evaluation_state") not in ARCHIVE_EVALUATION_STATES:
        raise ValueError("unsupported archive evaluation_state")
    if not isinstance(policy.get("archive_execution_allowed"), bool):
        raise ValueError("archive policy requires archive_execution_allowed bool")


def _validate_ack(ack: dict[str, Any]) -> None:
    if ack.get("ack_required") is not True:
        raise ValueError("control ack must be required for archive-sensitive lanes")
    if required_text(ack, "ack_state") not in ACK_STATES:
        raise ValueError("unsupported ack_state")
    if not isinstance(ack.get("ack_delivery_confirmed"), bool) or not isinstance(ack.get("no_ack"), bool):
        raise ValueError("ack requires bool delivery fields")
    if ack["ack_state"] == "no_ack" and (ack["ack_delivery_confirmed"] is not False or ack["no_ack"] is not True):
        raise ValueError("no_ack state must keep delivery unconfirmed")


def _require_archive_execution_allowed(lane: dict[str, Any]) -> None:
    policy = lane.get("archive_policy") or {}
    if policy.get("archive_execution_allowed") is not True:
        raise ValueError("archive execution requires prior allowed archive policy evaluation")
    if policy.get("archive_after_ack_delivery_confirmed") is True and lane.get("ack", {}).get("ack_delivery_confirmed") is not True:
        raise ValueError("archive execution requires ack delivery confirmation")


def _validate_active_archive_and_ack(lane: dict[str, Any]) -> None:
    ack = required_dict(lane, "ack")
    _validate_ack(ack)
    policy = required_dict(lane, "archive_policy")
    _validate_archive_policy(policy)
    if policy.get("archive_execution_allowed") is True and ack.get("ack_delivery_confirmed") is not True:
        raise ValueError("archive policy cannot allow execution before ack delivery confirmation")


def _validate_required_role_surfaces(lane: dict[str, Any]) -> None:
    surfaces = lane.get("fixed_role_surfaces")
    if not isinstance(surfaces, dict):
        raise ValueError("fixed role surfaces must be materialized")
    missing = sorted({"dispatcher", "cto_disposition", "implementation_worker"}.difference(surfaces))
    if lane.get("lane_kind") in IMPLEMENTATION_LANE_KINDS and missing:
        raise ValueError(f"implementation lane missing fixed role surfaces: {', '.join(missing)}")

__all__ = ("materialize_control_register", "validate_active_pending_register", "validate_control_event")
