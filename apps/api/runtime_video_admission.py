from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI, HTTPException, Request

from agentflow.harness.json_io import exclusive_file_lock, write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from agentflow_studio.slicing_sop.video_metadata import probe_video_metadata
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_image_admission import load_image_admission_manifest
from apps.api.runtime_image_assets import image_asset_metadata
from apps.api.runtime_models import VideoGenerationRequest
from apps.api.runtime_production_graph import (
    GraphIdempotencyConflict,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
    graph_has_authority,
)
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id
from apps.api.runtime_video_candidates import candidate_file
from apps.api.runtime_video_constants import SAFE_CANDIDATE_ID


SCHEMA_VERSION = "afs.video_admission_manifest.v0.1"
SERVICE_ID = "seedance_i2v"
MODEL_ID = "doubao-seedance-2-0"
CREATE_ENDPOINT = "/volc/v1/contents/generations/tasks"
QUERY_ENDPOINT = f"{CREATE_ENDPOINT}/{{id}}"
RESOLUTION = "720p"
DURATION_SEC = 6
MAX_DISPATCHES = 1
AUTO_RETRY = 0
HARD_BUDGET_USD = Decimal("2.00")
COMMANDS = {
    "compile",
    "reserve_dispatch",
    "record_job",
    "record_candidate",
    "record_failure",
    "approve",
    "reject",
}


def register_runtime_video_admission_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    graph_store = ProductionGraphStore(store)

    def require_access(request: Request, project_id: str) -> None:
        store.ensure_project_manifest(project_id)
        if auth.enabled():
            user = auth.require_user(request)
            if not auth.user_can_access_project(str(user["user_id"]), project_id):
                raise HTTPException(status_code=403, detail="project access denied")

    @app.get("/projects/{project_id}/m6/video-admission")
    def get_video_admission(project_id: str, request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        manifest = load_video_admission_manifest(store, project_id)
        readiness = video_admission_readiness(store, project_id)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": manifest.get("status", "empty") if manifest else "empty",
            "manifest": manifest,
            "readiness": readiness,
            "capability": video_admission_capability(),
            "provider_dispatch_count": int((manifest or {}).get("provider_dispatch_count") or 0),
            "external_cost_usd": None,
        }

    @app.post("/projects/{project_id}/m6/video-admission/commands/preview")
    def preview_video_admission(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        try:
            result = preview_video_admission_command(store, project_id, body)
            reject_unsafe_payload(result)
            return result
        except (KeyError, ValueError, ProductionGraphError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/projects/{project_id}/m6/video-admission/commands/confirm")
    def confirm_video_admission(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        path = _manifest_path(store, project_id)
        lock_path = path.with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with exclusive_file_lock(lock_path):
                existing = load_video_admission_manifest(store, project_id)
                reconciled = _reconcile_existing_approval(
                    graph_store,
                    project_id,
                    existing,
                    body.get("command"),
                    timestamp=_requested_at(body),
                )
                if reconciled:
                    preview = _preview_payload(
                        existing,
                        reconciled,
                        _safe_command(body.get("command")),
                    )
                    if str(body.get("preview_digest") or "") != preview["preview_digest"]:
                        raise ValueError("video admission preview is stale; review the impact again")
                    write_json(path, reconciled)
                    return {
                        **preview,
                        "status": "confirmed",
                        "idempotent_replay": True,
                        "result": {"manifest": reconciled, "graph_mutation": 0},
                        "receipt": reconciled.get("receipts", [])[-1],
                        "provider_dispatch_count": 0,
                        "external_cost_usd": None,
                    }
                replay = _idempotent_receipt(existing, body.get("command"))
                if replay:
                    return {
                        "schema_version": SCHEMA_VERSION,
                        "status": "confirmed",
                        "idempotent_replay": True,
                        "result": {"manifest": existing, "graph_mutation": 0},
                        "receipt": replay,
                        "provider_dispatch_count": 0,
                        "external_cost_usd": None,
                    }
                preview = preview_video_admission_command(store, project_id, body)
                if str(body.get("preview_digest") or "") != preview["preview_digest"]:
                    raise ValueError("video admission preview is stale; review the impact again")
                result = deepcopy(preview["result"]["manifest"])
                command = preview["command"]
                graph_mutation = 0
                if command["type"] == "approve":
                    result = _approve_to_graph(store, graph_store, project_id, result, command)
                    graph_mutation = 1
                result["updated_at"] = _now()
                path.parent.mkdir(parents=True, exist_ok=True)
                reject_unsafe_payload(result)
                write_json(path, result)
            return {
                **preview,
                "status": "confirmed",
                "result": {"manifest": result, "graph_mutation": graph_mutation},
                "receipt": result.get("receipts", [])[-1] if result.get("receipts") else {},
            }
        except (GraphVersionConflict, GraphIdempotencyConflict) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (KeyError, ValueError, ProductionGraphError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


def video_admission_readiness(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    capability = video_admission_capability()
    if not capability["configured"]:
        return {
            "status": "blocked",
            "reason": "exact non-fast Seedance 2.0 720p/6s reference capability is not configured",
            "next_action": "等待视频能力准备完成。",
            "provider_dispatch_count": 0,
        }
    try:
        source = _source_contract(store, project_id)
    except (KeyError, ValueError, ProductionGraphError) as exc:
        return {
            "status": "blocked",
            "reason": str(exc),
            "next_action": "请先批准镜头 01 关键帧与所需参考图片。",
            "provider_dispatch_count": 0,
        }
    return {
        "status": "ready",
        "shot_id": source["shot"]["shot_id"],
        "shot_label": source["shot"]["label"],
        "first_frame_label": source["keyframe"]["label"],
        "reference_count": len(source["references"]),
        "next_action": "预览视频生成确认卡。",
        "provider_dispatch_count": 0,
    }


def video_admission_capability() -> dict[str, Any]:
    configured_model = ""
    configured_endpoint = ""
    configured_query_endpoint = ""
    reference_slots = 0
    duration_supported = False
    resolution_supported = False
    reference_mode_supported = False
    artifact_hosts_configured = False
    pricing_verified = False
    worst_case_output_tokens = 0
    worst_case_cost_usd = ""
    try:
        registry = load_provider_registry()
        service = registry.store.service(SERVICE_ID)
        descriptor = registry.descriptor(SERVICE_ID)
        configured_model = str(service.get("model") or "")
        configured_endpoint = str(service.get("endpoint") or "")
        configured_query_endpoint = str(service.get("query_endpoint") or "")
        artifact_hosts_configured = bool(service.get("allowed_artifact_hosts"))
        pricing = _pricing_exposure_contract(service)
        pricing_verified = pricing["verified"]
        worst_case_output_tokens = pricing["worst_case_output_tokens"]
        worst_case_cost_usd = pricing["worst_case_cost_usd"]
        reference_slots = int(descriptor.reference_image_slots or 0)
        duration_supported = DURATION_SEC in descriptor.supported_durations_sec
        resolution_supported = RESOLUTION in descriptor.supported_resolutions
        reference_mode_supported = "reference_images" in descriptor.frame_modes
    except (ModelGatewayError, KeyError, OSError, ValueError, InvalidOperation):
        pass
    exact_model = configured_model == MODEL_ID
    exact_endpoint = configured_endpoint == CREATE_ENDPOINT
    exact_query_endpoint = configured_query_endpoint == QUERY_ENDPOINT
    exact_request_shape = (
        reference_slots >= 4
        and duration_supported
        and resolution_supported
        and reference_mode_supported
        and artifact_hosts_configured
        and pricing_verified
    )
    return {
        "service_id": SERVICE_ID,
        "model": MODEL_ID,
        "non_fast": True,
        "create_endpoint": CREATE_ENDPOINT,
        "resolution": RESOLUTION,
        "duration_sec": DURATION_SEC,
        "configured": (
            exact_model
            and exact_endpoint
            and exact_query_endpoint
            and exact_request_shape
        ),
        "exact_model": exact_model,
        "exact_endpoint": exact_endpoint,
        "exact_query_endpoint": exact_query_endpoint,
        "reference_image_slots": reference_slots,
        "duration_supported": duration_supported,
        "resolution_supported": resolution_supported,
        "reference_mode_supported": reference_mode_supported,
        "artifact_hosts_configured": artifact_hosts_configured,
        "pricing_verified": pricing_verified,
        "worst_case_output_tokens": worst_case_output_tokens,
        "worst_case_cost_usd": worst_case_cost_usd,
        "provider_enforced_cost_cap": False,
        "provider_calls_started": False,
    }


def preview_video_admission_command(
    store: RuntimeStore,
    project_id: str,
    body: Mapping[str, Any],
) -> dict[str, Any]:
    command = _safe_command(body.get("command"))
    requested_at = _requested_at(body)
    if command["type"] == "compile":
        before: dict[str, Any] = {}
        manifest = compile_video_admission_manifest(store, project_id, created_at=requested_at)
        _append_receipt(manifest, "manifest_compiled", command, requested_at)
    else:
        before = load_video_admission_manifest(store, project_id)
        if not before:
            raise ValueError("video admission manifest has not been prepared")
        manifest = _reconcile_existing_approval(
            ProductionGraphStore(store),
            project_id,
            before,
            command,
            timestamp=requested_at,
        )
        if manifest is None:
            _assert_manifest_current(store, project_id, before)
            manifest = _apply_command(
                before,
                command,
                requested_at,
                store=store,
                project_id=project_id,
            )
    return _preview_payload(before, manifest, command)


def _preview_payload(
    before: Mapping[str, Any],
    manifest: Mapping[str, Any],
    command: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "preview",
        "command": dict(command),
        "impact": _impact(before, manifest, command),
        "result": {"manifest": deepcopy(dict(manifest)), "graph_mutation": 0},
        "provider_dispatch_count": 0,
        "external_cost_usd": None,
        "requires_confirmation": True,
    }
    payload["preview_digest"] = canonical_digest(payload)
    return payload


def compile_video_admission_manifest(
    store: RuntimeStore,
    project_id: str,
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    timestamp = created_at or _now()
    if not video_admission_capability()["configured"]:
        raise ValueError(
            "exact non-fast Seedance 2.0 720p/6s reference capability is not configured"
        )
    source = _source_contract(store, project_id)
    contract = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "version": 1,
        "source": source,
        "provider_contract": {
            "service_id": SERVICE_ID,
            "model": MODEL_ID,
            "model_variant": "non_fast",
            "create_endpoint": CREATE_ENDPOINT,
            "query_endpoint": QUERY_ENDPOINT,
            "resolution": RESOLUTION,
            "duration_sec": DURATION_SEC,
            "candidate_count": 1,
            "max_dispatches": MAX_DISPATCHES,
            "auto_retry": AUTO_RETRY,
        },
        "budget_contract": {
            "currency": "USD",
            "hard_ceiling_usd": _money(HARD_BUDGET_USD),
            "classification": "program_stop_ceiling_not_provider_enforced_estimate_or_actual",
            "billing_mode": "provider_output_tokens",
            "provider_enforced_cost_cap": False,
            "program_stop_ceiling_only": True,
            "pricing_verification_state": "verified",
            "worst_case_output_tokens": int(
                video_admission_capability()["worst_case_output_tokens"]
            ),
            "worst_case_cost_usd": str(
                video_admission_capability()["worst_case_cost_usd"]
            ),
            "actual_charge_usd": None,
            "actual_charge_verification": "unverified",
        },
        "item": {
            "item_id": f"video-{safe_id(source['shot']['shot_id'])}",
            "state": "planned",
            "label": source["shot"]["label"],
            "provider_job_id": "",
            "network_disposition": "never_started",
            "candidate": None,
            "error_category": "",
        },
    }
    manifest_hash = canonical_digest(contract)
    return {
        **contract,
        "manifest_id": f"video-admission-{manifest_hash[:16]}",
        "manifest_hash": manifest_hash,
        "status": "locked",
        "budget": {
            "dispatches_reserved": 0,
            "remaining_dispatches": MAX_DISPATCHES,
            "hard_ceiling_usd": _money(HARD_BUDGET_USD),
            "actual_charge_usd": None,
            "actual_charge_verification": "unverified",
        },
        "provider_dispatch_count": 0,
        "receipts": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def load_video_admission_manifest(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = _manifest_path(store, project_id)
    if not path.is_file():
        return {}
    value = read_json(path)
    reject_unsafe_payload(value)
    if value.get("schema_version") != SCHEMA_VERSION or value.get("project_id") != project_id:
        raise ValueError("video admission storage scope is invalid")
    return value


def enforce_video_admission_request(
    store: RuntimeStore,
    project_id: str,
    request: VideoGenerationRequest,
) -> dict[str, Any]:
    if request.provider_service_id != SERVICE_ID:
        return {}
    manifest = load_video_admission_manifest(store, project_id)
    if not manifest:
        raise ValueError("exact Seedance generation requires a confirmed video admission")
    _assert_manifest_current(store, project_id, manifest)
    item = manifest["item"]
    source = manifest["source"]
    expected_refs = [entry["image_asset_id"] for entry in source["references"]]
    checks = {
        "video_admission_manifest_id": (request.video_admission_manifest_id, manifest["manifest_id"]),
        "video_admission_manifest_hash": (request.video_admission_manifest_hash, manifest["manifest_hash"]),
        "video_admission_item_id": (request.video_admission_item_id, item["item_id"]),
        "video_admission_reservation_token": (
            request.video_admission_reservation_token,
            item.get("reservation_token"),
        ),
        "first_frame_image_asset_id": (
            request.first_frame_image_asset_id,
            source["keyframe"]["image_asset_id"],
        ),
        "reference_image_asset_ids": (list(request.reference_image_asset_ids), expected_refs),
        "duration_sec": (request.duration_sec, DURATION_SEC),
        "resolution": (request.resolution.lower(), RESOLUTION),
        "candidate_count": (request.candidate_count, 1),
    }
    mismatches = [name for name, (actual, expected) in checks.items() if actual != expected]
    if mismatches:
        raise ValueError(f"video admission request differs from confirmed contract: {', '.join(mismatches)}")
    if item.get("state") not in {"reserved", "dispatch_prepared", "reconcile_required", "processing"}:
        raise ValueError("video admission item is not reserved for its one allowed dispatch")
    return manifest


def claim_video_admission_dispatch(
    store: RuntimeStore,
    project_id: str,
    request: VideoGenerationRequest,
    *,
    job_id: str,
) -> dict[str, Any]:
    if request.provider_service_id != SERVICE_ID:
        return {}
    path = _manifest_path(store, project_id)
    lock_path = path.with_suffix(".lock")
    with exclusive_file_lock(lock_path):
        manifest = enforce_video_admission_request(store, project_id, request)
        item = manifest["item"]
        if item.get("state") in {"dispatch_prepared", "reconcile_required", "processing"}:
            if item.get("provider_job_id") == job_id:
                return manifest
            raise ValueError("video admission dispatch was already claimed")
        if int(manifest["budget"]["dispatches_reserved"]) != 1:
            raise ValueError("video admission dispatch budget is not reserved")
        item["state"] = "dispatch_prepared"
        item["provider_job_id"] = job_id
        item["dispatch_claimed_at"] = _now()
        item["network_disposition"] = "never_started"
        manifest["provider_dispatch_count"] = 0
        _append_receipt(
            manifest,
            "dispatch_prepared",
            {"type": "dispatch_claim", "idempotency_key": f"dispatch-{job_id}"},
            manifest["item"]["dispatch_claimed_at"],
        )
        manifest["updated_at"] = _now()
        reject_unsafe_payload(manifest)
        write_json(path, manifest)
        return manifest


def mark_video_admission_network_started(
    store: RuntimeStore,
    project_id: str,
    *,
    job_id: str,
) -> dict[str, Any]:
    path = _manifest_path(store, project_id)
    with exclusive_file_lock(path.with_suffix(".lock")):
        manifest = load_video_admission_manifest(store, project_id)
        item = manifest.get("item") or {}
        if item.get("provider_job_id") != job_id:
            raise ValueError("video dispatch job identity does not match")
        if item.get("state") == "reconcile_required":
            return manifest
        if item.get("state") != "dispatch_prepared":
            raise ValueError("video dispatch was not durably prepared")
        item["state"] = "reconcile_required"
        item["network_disposition"] = "may_have_dispatched"
        manifest["provider_dispatch_count"] = 1
        _append_receipt(
            manifest,
            "provider_submit_started",
            {"type": "dispatch_start", "idempotency_key": f"dispatch-start-{job_id}"},
            _now(),
        )
        manifest["updated_at"] = _now()
        write_json(path, manifest)
        return manifest


def mark_video_admission_task_recorded(
    store: RuntimeStore,
    project_id: str,
    *,
    job_id: str,
    provider_task_fingerprint: str,
) -> dict[str, Any]:
    path = _manifest_path(store, project_id)
    with exclusive_file_lock(path.with_suffix(".lock")):
        manifest = load_video_admission_manifest(store, project_id)
        item = manifest.get("item") or {}
        if item.get("provider_job_id") != job_id:
            raise ValueError("video dispatch job identity does not match")
        if item.get("state") == "processing":
            return manifest
        if item.get("state") != "reconcile_required":
            raise ValueError("video dispatch is not awaiting task reconciliation")
        item["state"] = "processing"
        item["network_disposition"] = "dispatched_with_task_identity"
        item["provider_task_fingerprint"] = str(provider_task_fingerprint or "")[:32]
        _append_receipt(
            manifest,
            "provider_task_recorded",
            {"type": "task_record", "idempotency_key": f"task-record-{job_id}"},
            _now(),
        )
        manifest["updated_at"] = _now()
        write_json(path, manifest)
        return manifest


def video_admission_generation_request(manifest: Mapping[str, Any], *, generated_at: str) -> dict[str, Any]:
    item = manifest["item"]
    source = manifest["source"]
    return {
        "node_id": source["shot"]["shot_id"],
        "prompt_text": source["prompt_contract"]["provider_prompt"],
        "provider_service_id": SERVICE_ID,
        "first_frame_image_asset_id": source["keyframe"]["image_asset_id"],
        "reference_image_asset_ids": [entry["image_asset_id"] for entry in source["references"]],
        "duration_sec": DURATION_SEC,
        "resolution": RESOLUTION,
        "aspect_ratio": source["keyframe"].get("aspect_ratio") or "16:9",
        "motion": source["prompt_contract"]["motion"],
        "candidate_count": 1,
        "video_admission_manifest_id": manifest["manifest_id"],
        "video_admission_manifest_hash": manifest["manifest_hash"],
        "video_admission_item_id": item["item_id"],
        "video_admission_reservation_token": item.get("reservation_token"),
        "generated_at": generated_at,
    }


def _source_contract(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    if not graph_has_authority(store, project_id):
        raise ValueError("video readiness requires an authoritative ProductionGraph")
    graph = ProductionGraphStore(store).load(project_id)
    image_manifest = load_image_admission_manifest(store, project_id)
    if not image_manifest:
        raise ValueError("video readiness requires an approved shot keyframe")
    if image_manifest.get("status") != "locked":
        raise ValueError("video readiness requires a locked image admission manifest")
    keyframes = [
        item
        for item in image_manifest.get("items", [])
        if item.get("item_type") == "shot_keyframe"
        and item.get("state") == "approved"
        and isinstance(item.get("candidate"), Mapping)
    ]
    if not keyframes:
        raise ValueError("video readiness requires an approved shot keyframe")
    shot_rows = {
        str(item.get("shot_id") or ""): item
        for item in (image_manifest.get("source", {}).get("shot_grounding", {}).get("shots") or [])
        if isinstance(item, Mapping)
    }
    shot_one_rows = [
        row for row in shot_rows.values()
        if int(row.get("number") or 0) == 1
    ]
    if len(shot_one_rows) != 1:
        raise ValueError("video readiness requires exactly one applied shot numbered 1")
    shot = shot_one_rows[0]
    shot_id = str(shot.get("shot_id") or "")
    matching_keyframes = [
        item for item in keyframes
        if str(item.get("target_shot_id") or "") == shot_id
    ]
    if len(matching_keyframes) != 1:
        raise ValueError("video readiness requires one approved keyframe bound exactly to shot 01")
    keyframe = matching_keyframes[0]
    candidate = keyframe["candidate"]
    first_frame = _validated_approved_image(
        store,
        project_id,
        graph,
        str(candidate.get("image_asset_id") or ""),
    )
    media_by_target = _approved_media_by_target(graph)
    if first_frame["image_asset_id"] not in media_by_target.get(shot_id, set()):
        raise ValueError("approved shot 01 keyframe is not bound to shot 01 in ProductionGraph")
    canonical_target_ids = _canonical_target_ids_for_shot(graph, shot_id)
    declared_target_ids = {
        str(item) for item in keyframe.get("reference_asset_ids", []) if str(item)
    }
    if not canonical_target_ids or declared_target_ids != canonical_target_ids:
        raise ValueError("approved shot 01 keyframe reference pack is not bound to every canonical shot asset")
    selected_reference_ids = {
        str(item)
        for item in keyframe.get("reference_media_ids", [])
        if str(item) and str(item) != first_frame["image_asset_id"]
    }
    reference_ids: list[tuple[str, str]] = []
    for target_id in sorted(canonical_target_ids):
        selected_for_target = sorted(
            selected_reference_ids & media_by_target.get(target_id, set())
        )
        if len(selected_for_target) != 1:
            raise ValueError("approved reference pack must select exactly one image for each canonical shot asset")
        reference_ids.append((target_id, selected_for_target[0]))
    if not reference_ids or len(reference_ids) > 3:
        raise ValueError("approved reference pack must contain one to three canonical reference images")
    references = [
        {
            **_validated_approved_image(store, project_id, graph, asset_id),
            "target_asset_id": target_id,
            "label": _canonical_target_label(graph, target_id),
        }
        for target_id, asset_id in reference_ids
    ]
    current_snapshot = {
        "version": int(graph["version"]),
        "graph_digest": str(graph["graph_digest"]),
    }
    accepted = {
        (int(item.get("version") or 0), str(item.get("graph_digest") or ""))
        for item in image_manifest.get("accepted_graph_snapshots", [])
        if isinstance(item, Mapping)
    }
    if (current_snapshot["version"], current_snapshot["graph_digest"]) not in accepted:
        raise ValueError("approved keyframe lineage is stale against the current ProductionGraph")
    labels = _canonical_labels_for_shot(graph, shot_id)
    prompt_contract = _prompt_contract(
        _normalized_video_shot_semantics(graph, shot_id, shot),
        labels,
    )
    return {
        "production_graph": current_snapshot,
        "asset_bible_revision_id": str(image_manifest.get("source", {}).get("asset_bible_revision_id") or ""),
        "shot_candidate_id": str(image_manifest.get("source", {}).get("shot_candidate_id") or ""),
        "shot": {
            "shot_id": shot_id,
            "number": 1,
            "label": str(shot.get("title") or "镜头 01"),
        },
        "keyframe": {
            **first_frame,
            "label": str(keyframe.get("label") or "镜头关键帧"),
            "aspect_ratio": str(keyframe.get("aspect_ratio") or "16:9"),
        },
        "references": references,
        "canonical_entities": labels,
        "prompt_contract": prompt_contract,
    }


def _canonical_labels_for_shot(graph: Mapping[str, Any], shot_id: str) -> dict[str, list[str]]:
    nodes = graph.get("nodes", {})
    result = {"characters": [], "scenes": [], "props": []}
    for node_id in sorted(_canonical_target_ids_for_shot(graph, shot_id)):
        node = nodes.get(node_id) or {}
        metadata = node.get("metadata") or {}
        label = str(metadata.get("display_name") or metadata.get("name") or "").strip()
        if not label:
            continue
        if node.get("category") == "entity":
            result["characters"].append(label)
        elif node.get("category") == "location":
            result["scenes"].append(label)
        elif node.get("category") == "resource" and metadata.get("kind") == "prop":
            result["props"].append(label)
    return result


def _canonical_target_ids_for_shot(graph: Mapping[str, Any], shot_id: str) -> set[str]:
    nodes = graph.get("nodes", {})
    candidate_ids = {
        str(item.get("from_id") or "")
        for item in graph.get("relations", [])
        if item.get("to_id") == shot_id
        and item.get("relation_type") in {"required_by", "contains"}
    }
    return {
        node_id
        for node_id in candidate_ids
        if (
            (nodes.get(node_id) or {}).get("category") in {"entity", "location"}
            or (
                (nodes.get(node_id) or {}).get("category") == "resource"
                and (nodes.get(node_id) or {}).get("metadata", {}).get("kind") == "prop"
            )
        )
    }


def _approved_media_by_target(graph: Mapping[str, Any]) -> dict[str, set[str]]:
    approved_nodes = {
        str(node_id): str(node.get("metadata", {}).get("image_asset_id") or "")
        for node_id, node in graph.get("nodes", {}).items()
        if node.get("state") == "active"
        and node.get("metadata", {}).get("kind") == "approved_image"
    }
    result: dict[str, set[str]] = {}
    for relation in graph.get("relations", []):
        approved_node_id = str(relation.get("to_id") or "")
        if relation.get("relation_type") != "approved_image" or approved_node_id not in approved_nodes:
            continue
        image_asset_id = approved_nodes[approved_node_id]
        if image_asset_id:
            result.setdefault(str(relation.get("from_id") or ""), set()).add(image_asset_id)
    return result


def _canonical_target_label(graph: Mapping[str, Any], target_id: str) -> str:
    node = (graph.get("nodes") or {}).get(target_id) or {}
    metadata = node.get("metadata") or {}
    label = str(metadata.get("display_name") or metadata.get("name") or "").strip()
    if not label:
        raise ValueError("canonical reference pack target is missing its creator-facing label")
    return label


def _normalized_video_shot_semantics(
    graph: Mapping[str, Any],
    shot_id: str,
    shot_grounding: Mapping[str, Any],
) -> dict[str, Any]:
    graph_shot = (graph.get("nodes") or {}).get(shot_id) or {}
    if graph_shot.get("state") != "active" or graph_shot.get("category") != "unit":
        raise ValueError("video readiness requires the applied shot in ProductionGraph")
    metadata = graph_shot.get("metadata") or {}

    def first_text(*values: Any) -> str:
        return next(
            (str(value).strip() for value in values if str(value or "").strip()),
            "",
        )

    continuity = [
        str(item).strip()
        for item in shot_grounding.get("continuity_cues", [])
        if str(item).strip()
    ]
    if not continuity:
        continuity = [
            str(item).strip()
            for item in metadata.get("continuity_cues", [])
            if str(item).strip()
        ]
    return {
        "action": first_text(
            shot_grounding.get("action"),
            metadata.get("action"),
            metadata.get("blocking"),
            metadata.get("intent"),
        ),
        "composition": first_text(
            shot_grounding.get("composition"),
            metadata.get("composition"),
            shot_grounding.get("shot_size"),
            metadata.get("shot_size"),
        ),
        "camera_angle": first_text(
            shot_grounding.get("camera_angle"),
            metadata.get("camera_angle"),
        ),
        "movement": first_text(
            shot_grounding.get("movement"),
            metadata.get("movement"),
            metadata.get("camera_movement"),
        ),
        "emotion": first_text(
            shot_grounding.get("emotion"),
            metadata.get("emotion"),
            shot_grounding.get("purpose"),
            metadata.get("narrative_purpose"),
        ),
        "continuity_cues": continuity,
    }


def _prompt_contract(shot: Mapping[str, Any], labels: Mapping[str, list[str]]) -> dict[str, Any]:
    action = str(shot.get("action") or shot.get("intent") or "").strip()
    composition = str(shot.get("composition") or "").strip()
    camera = str(shot.get("camera_angle") or "").strip()
    movement = str(shot.get("movement") or "").strip()
    emotion = str(shot.get("emotion") or "").strip()
    continuity = [str(item).strip() for item in shot.get("continuity_cues", []) if str(item).strip()]
    if not action or not composition or not camera or not movement or not emotion:
        raise ValueError("shot 01 needs action, composition, camera, movement, and emotion before video readiness")
    entity_lines = [
        f"Canonical characters: {', '.join(labels['characters']) or 'none'}.",
        f"Canonical scene: {', '.join(labels['scenes']) or 'none'}.",
        f"Canonical props: {', '.join(labels['props']) or 'none'}.",
    ]
    prompt = "\n".join(
        [
            "Create one continuous image-to-video shot from the approved first frame.",
            *entity_lines,
            f"Shot action: {action}",
            f"Composition: {composition}",
            f"Camera angle: {camera}",
            f"Camera movement: {movement}",
            f"Emotion: {emotion}",
            f"Continuity: {'; '.join(continuity) if continuity else 'preserve the approved first frame and canonical entities.'}",
            "Do not add characters, locations, props, text, logos, watermarks, or plot events.",
        ]
    )
    return {
        "schema_version": "afs.video_prompt_contract.v0.1",
        "provider_prompt": prompt,
        "motion": movement,
        "canonical_entities": deepcopy(dict(labels)),
        "shot_action": action,
        "composition": composition,
        "camera_angle": camera,
        "camera_movement": movement,
        "emotion": emotion,
        "continuity_cues": continuity,
        "keyword_rewrite": False,
        "sample_fallback": False,
    }


def _validated_approved_image(
    store: RuntimeStore,
    project_id: str,
    graph: Mapping[str, Any],
    asset_id: str,
) -> dict[str, Any]:
    approved = {
        str(node.get("metadata", {}).get("image_asset_id") or "")
        for node in graph.get("nodes", {}).values()
        if node.get("state") == "active"
        and node.get("metadata", {}).get("kind") == "approved_image"
    }
    if not asset_id or asset_id not in approved:
        raise ValueError("video reference media must be approved in the same project ProductionGraph")
    metadata = image_asset_metadata(store, project_id, asset_id)
    if metadata.get("mime_type") not in {"image/png", "image/jpeg"}:
        raise ValueError("video reference media must be PNG or JPEG")
    if not metadata.get("sha256") or int(metadata.get("width") or 0) <= 0 or int(metadata.get("height") or 0) <= 0:
        raise ValueError("video reference media need digest and dimensions")
    return {
        "image_asset_id": asset_id,
        "sha256": str(metadata["sha256"]),
        "mime_type": str(metadata["mime_type"]),
        "width": int(metadata["width"]),
        "height": int(metadata["height"]),
        "byte_count": int(metadata.get("byte_count") or 0),
    }


def _apply_command(
    before: Mapping[str, Any],
    command: Mapping[str, Any],
    timestamp: str,
    *,
    store: RuntimeStore,
    project_id: str,
) -> dict[str, Any]:
    manifest = deepcopy(dict(before))
    item = manifest["item"]
    command_type = command["type"]
    if command_type == "reserve_dispatch":
        if item.get("state") != "planned":
            raise ValueError("only a planned video can reserve its one dispatch")
        if int(manifest["budget"]["remaining_dispatches"]) != 1:
            raise ValueError("video admission dispatch budget is exhausted")
        item["state"] = "reserved"
        item["reservation_token"] = (
            f"video-reservation-"
            f"{canonical_digest({'manifest_hash': manifest['manifest_hash'], 'idempotency_key': command['idempotency_key']})[:32]}"
        )
        manifest["budget"]["dispatches_reserved"] = 1
        manifest["budget"]["remaining_dispatches"] = 0
        _append_receipt(manifest, "dispatch_reserved", command, timestamp)
    elif command_type == "record_job":
        if item.get("state") != "processing":
            raise ValueError("video job can only be recorded after dispatch claim")
        job_id = str(command.get("provider_job_id") or "").strip()
        if not job_id:
            raise ValueError("video job id is required")
        if item.get("provider_job_id") not in {"", job_id}:
            raise ValueError("video job identity cannot change")
        item["provider_job_id"] = job_id
        _append_receipt(manifest, "job_recorded", command, timestamp)
    elif command_type == "record_candidate":
        if item.get("state") != "processing":
            raise ValueError("video candidate requires a processing item")
        candidate = _safe_candidate(
            command.get("candidate"),
            project_id=str(manifest.get("project_id") or ""),
        )
        if candidate["job_id"] != item.get("provider_job_id"):
            raise ValueError("video candidate job identity does not match")
        candidate = _technical_candidate(store, project_id, candidate)
        item["state"] = "candidate"
        item["candidate"] = candidate
        _append_receipt(manifest, "candidate_recorded", command, timestamp)
    elif command_type == "record_failure":
        if item.get("state") != "processing":
            raise ValueError("only a processing video can record failure")
        item["state"] = "failed"
        item["error_category"] = str(command.get("error_category") or "generation_failed")[:80]
        _append_receipt(manifest, "failure_recorded", command, timestamp)
    elif command_type == "approve":
        if item.get("state") != "candidate":
            raise ValueError("only a video candidate can be approved")
        item["state"] = "approved"
        _append_receipt(manifest, "approved", command, timestamp)
    elif command_type == "reject":
        if item.get("state") != "candidate":
            raise ValueError("only a video candidate can be rejected")
        item["state"] = "rejected"
        _append_receipt(manifest, "rejected", command, timestamp)
    else:
        raise ValueError("unsupported video admission command")
    manifest["updated_at"] = timestamp
    return manifest


def _approve_to_graph(
    store: RuntimeStore,
    graph_store: ProductionGraphStore,
    project_id: str,
    manifest: dict[str, Any],
    command: Mapping[str, Any],
) -> dict[str, Any]:
    item = manifest["item"]
    candidate = item.get("candidate") or {}
    graph = graph_store.load(project_id)
    _assert_manifest_current(store, project_id, manifest)
    job_id = str(candidate.get("job_id") or "")
    candidate_id = str(candidate.get("candidate_id") or "")
    path = candidate_file(store.run_dir(project_id, job_id), candidate_id)
    if path is None:
        raise ValueError("video candidate media is missing or unavailable for review")
    data = path.read_bytes()
    if not data or hashlib.sha256(data).hexdigest() != candidate.get("sha256"):
        raise ValueError("video candidate differs from its review metadata")
    if (candidate.get("technical_qa") or {}).get("status") != "pass":
        raise ValueError("video candidate has not passed technical review")
    node_id = f"video-media-{safe_id(manifest['manifest_id'])}"
    events = [
        {
            "type": "node_upserted",
            "node": {
                "node_id": node_id,
                "category": "artifact",
                "state": "active",
                "metadata": {
                    "kind": "approved_video",
                    "manifest_id": manifest["manifest_id"],
                    "manifest_hash": manifest["manifest_hash"],
                    "job_id": job_id,
                    "candidate_id": candidate_id,
                    "sha256": candidate["sha256"],
                    "byte_count": candidate["byte_count"],
                    "model": MODEL_ID,
                    "resolution": RESOLUTION,
                    "duration_sec": DURATION_SEC,
                    "billing_verification_state": "unverified",
                    "actual_usd": None,
                    "provider_reported_output_tokens": (
                        (candidate.get("usage_evidence") or {}).get("output_tokens")
                    ),
                    "approval_idempotency_key": str(
                        command.get("idempotency_key") or f"approve-{manifest['manifest_id']}"
                    ),
                },
            },
        },
        {
            "type": "relation_upserted",
            "from_id": manifest["source"]["shot"]["shot_id"],
            "to_id": node_id,
            "relation_type": "approved_video",
        },
    ]
    updated = graph_store.append(
        project_id,
        expected_version=int(graph["version"]),
        idempotency_key=str(command.get("idempotency_key") or f"approve-{manifest['manifest_id']}"),
        semantic_digest=canonical_digest(
            {
                "manifest_hash": manifest["manifest_hash"],
                "candidate_sha256": candidate["sha256"],
            }
        ),
        events=events,
    )
    item["promotion"] = {
        "production_graph_node_id": node_id,
        "graph_version": updated["version"],
        "graph_digest": updated["graph_digest"],
        "idempotent_replay": bool(updated.get("idempotent_replay")),
        "promoted_at": _now(),
    }
    return manifest


def _reconcile_existing_approval(
    graph_store: ProductionGraphStore,
    project_id: str,
    manifest: Mapping[str, Any],
    command_value: Any,
    *,
    timestamp: str,
) -> dict[str, Any] | None:
    command = dict(command_value) if isinstance(command_value, Mapping) else {}
    if (
        command.get("type") != "approve"
        or not manifest
        or (manifest.get("item") or {}).get("state") != "candidate"
    ):
        return None
    candidate = (manifest.get("item") or {}).get("candidate") or {}
    node_id = f"video-media-{safe_id(str(manifest.get('manifest_id') or ''))}"
    graph = graph_store.load(project_id)
    node = (graph.get("nodes") or {}).get(node_id) or {}
    metadata = node.get("metadata") or {}
    if not node:
        return None
    if (
        metadata.get("kind") != "approved_video"
        or metadata.get("manifest_hash") != manifest.get("manifest_hash")
        or metadata.get("sha256") != candidate.get("sha256")
        or metadata.get("job_id") != candidate.get("job_id")
        or metadata.get("candidate_id") != candidate.get("candidate_id")
        or metadata.get("model") != MODEL_ID
        or metadata.get("resolution") != RESOLUTION
        or int(metadata.get("duration_sec") or 0) != DURATION_SEC
    ):
        raise ValueError("existing video graph promotion conflicts with the approval ledger")
    relation_matches = [
        relation
        for relation in graph.get("relations", [])
        if relation.get("from_id") == manifest.get("source", {}).get("shot", {}).get("shot_id")
        and relation.get("to_id") == node_id
        and relation.get("relation_type") == "approved_video"
    ]
    if len(relation_matches) != 1:
        raise ValueError("existing video graph promotion has an invalid shot binding")
    reconciled = deepcopy(dict(manifest))
    reconciled["item"]["state"] = "approved"
    reconciled["item"]["promotion"] = {
        "production_graph_node_id": node_id,
        "graph_version": int(graph["version"]),
        "graph_digest": str(graph["graph_digest"]),
        "idempotent_replay": True,
        "promoted_at": timestamp,
    }
    _append_receipt(reconciled, "approved", command, timestamp)
    reconciled["updated_at"] = timestamp
    reject_unsafe_payload(reconciled)
    return reconciled


def _assert_manifest_current(store: RuntimeStore, project_id: str, manifest: Mapping[str, Any]) -> None:
    graph = ProductionGraphStore(store).load(project_id)
    source = manifest.get("source") or {}
    expected = source.get("production_graph") or {}
    if (
        int(expected.get("version") or 0) != int(graph.get("version") or 0)
        or str(expected.get("graph_digest") or "") != str(graph.get("graph_digest") or "")
    ):
        raise ValueError("video admission ProductionGraph source is stale")


def _safe_command(value: Any) -> dict[str, Any]:
    command = dict(value) if isinstance(value, Mapping) else {}
    command_type = str(command.get("type") or "")
    if command_type not in COMMANDS:
        raise ValueError("unsupported video admission command")
    key = str(command.get("idempotency_key") or "").strip()
    if not key:
        raise ValueError("video admission command requires idempotency_key")
    safe = {"type": command_type, "idempotency_key": key[:180]}
    for field in ("provider_job_id", "error_category"):
        if command.get(field):
            safe[field] = str(command[field])[:180]
    if command_type == "record_candidate":
        safe["candidate"] = _safe_candidate(command.get("candidate"))
    return safe


def _safe_candidate(value: Any, *, project_id: str = "") -> dict[str, Any]:
    candidate = dict(value) if isinstance(value, Mapping) else {}
    job_id = str(candidate.get("job_id") or "")
    candidate_id = str(candidate.get("candidate_id") or "")
    preview_url = str(candidate.get("preview_url") or "")
    sha256 = str(candidate.get("sha256") or "").lower()
    byte_count = int(candidate.get("byte_count") or 0)
    expected_preview = (
        f"/projects/{safe_id(project_id)}/video-generations/"
        f"{safe_id(job_id)}/candidates/{candidate_id}/preview"
        if project_id and job_id and candidate_id
        else ""
    )
    if (
        not job_id
        or safe_id(job_id) != job_id
        or not SAFE_CANDIDATE_ID.fullmatch(candidate_id)
        or not preview_url.startswith("/projects/")
    ):
        raise ValueError("video candidate identity and same-origin preview are required")
    if expected_preview and preview_url != expected_preview:
        raise ValueError("video candidate preview must match its current project and job")
    if len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
        raise ValueError("video candidate sha256 is invalid")
    if byte_count <= 0:
        raise ValueError("video candidate byte count is invalid")
    return {
        "job_id": job_id,
        "candidate_id": candidate_id,
        "preview_url": preview_url,
        "sha256": sha256,
        "byte_count": byte_count,
        **(
            {"usage_evidence": _safe_usage_evidence(candidate["usage_evidence"])}
            if isinstance(candidate.get("usage_evidence"), Mapping)
            else {}
        ),
        **(
            {"technical_qa": deepcopy(dict(candidate["technical_qa"]))}
            if isinstance(candidate.get("technical_qa"), Mapping)
            else {}
        ),
    }


def _safe_usage_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "provider_reported_usage": bool(value.get("provider_reported_usage")),
        "provider_reported_cost": False,
        "actual_charge_verification": "unverified",
    }
    output_tokens = value.get("output_tokens")
    if isinstance(output_tokens, (int, float)) and 0 <= output_tokens <= 10**12:
        result["output_tokens"] = output_tokens
    elif output_tokens is not None:
        raise ValueError("video candidate output token evidence is invalid")
    return result


def _pricing_exposure_contract(service: Mapping[str, Any]) -> dict[str, Any]:
    contract = (
        service.get("pricing_exposure_contract")
        if isinstance(service.get("pricing_exposure_contract"), Mapping)
        else {}
    )
    output_token_usd = Decimal(str(contract.get("output_token_usd") or "0"))
    worst_case_output_tokens = int(contract.get("worst_case_output_tokens") or 0)
    worst_case_cost = Decimal(str(contract.get("worst_case_cost_usd") or "0"))
    calculated = output_token_usd * worst_case_output_tokens
    verified = (
        contract.get("verification_state") == "verified"
        and contract.get("billing_mode") == "provider_output_tokens"
        and bool(str(contract.get("source_checked_at") or "").strip())
        and output_token_usd > 0
        and worst_case_output_tokens > 0
        and worst_case_cost == calculated
        and worst_case_cost <= HARD_BUDGET_USD
        and contract.get("provider_enforced_cost_cap") is False
    )
    return {
        "verified": verified,
        "worst_case_output_tokens": worst_case_output_tokens,
        "worst_case_cost_usd": f"{worst_case_cost:.2f}" if worst_case_cost > 0 else "",
    }


def _technical_candidate(
    store: RuntimeStore,
    project_id: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    path = candidate_file(
        store.run_dir(project_id, str(candidate["job_id"])),
        str(candidate["candidate_id"]),
    )
    if path is None or path.suffix.lower() != ".mp4":
        raise ValueError("video candidate failed technical validation")
    data = path.read_bytes()
    if (
        not data
        or len(data) != int(candidate["byte_count"])
        or hashlib.sha256(data).hexdigest() != candidate["sha256"]
    ):
        raise ValueError("video candidate failed technical validation")
    metadata = probe_video_metadata(path)
    width = int(metadata.width or 0)
    height = int(metadata.height or 0)
    duration = float(metadata.duration_sec or 0.0)
    if (
        metadata.probe_status != "succeeded"
        or 720 not in {width, height}
        or not (5.5 <= duration <= 6.5)
        or not str(metadata.codec or "")
    ):
        raise ValueError("video candidate failed technical validation")
    return {
        **dict(candidate),
        "technical_qa": {
            "status": "pass",
            "container": "video/mp4",
            "width": width,
            "height": height,
            "duration_sec": round(duration, 3),
            "codec": str(metadata.codec),
            "decode_probe": "passed",
        },
    }


def _impact(before: Mapping[str, Any], after: Mapping[str, Any], command: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "command": command["type"],
        "state_before": str((before.get("item") or {}).get("state") or "empty"),
        "state_after": str((after.get("item") or {}).get("state") or ""),
        "dispatches_reserved_before": int((before.get("budget") or {}).get("dispatches_reserved") or 0),
        "dispatches_reserved_after": int((after.get("budget") or {}).get("dispatches_reserved") or 0),
        "graph_mutation": 0,
        "provider_dispatch_count": 0,
    }


def _append_receipt(
    manifest: dict[str, Any],
    event: str,
    command: Mapping[str, Any],
    timestamp: str,
) -> None:
    manifest.setdefault("receipts", []).append(
        {
            "event": event,
            "command_type": str(command.get("type") or ""),
            "idempotency_key": str(command.get("idempotency_key") or ""),
            "recorded_at": timestamp,
        }
    )


def _idempotent_receipt(
    manifest: Mapping[str, Any],
    command_value: Any,
) -> dict[str, Any] | None:
    command = dict(command_value) if isinstance(command_value, Mapping) else {}
    key = str(command.get("idempotency_key") or "")
    if not key:
        return None
    for receipt in manifest.get("receipts", []) if isinstance(manifest, Mapping) else []:
        if isinstance(receipt, Mapping) and receipt.get("idempotency_key") == key:
            if receipt.get("command_type") != command.get("type"):
                raise ValueError("video admission idempotency key has a different command")
            return dict(receipt)
    return None


def _requested_at(body: Mapping[str, Any]) -> str:
    value = str(body.get("requested_at") or "").strip()
    return value or _now()


def _manifest_path(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "video_admission" / "manifest.json"


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = (
    "AUTO_RETRY",
    "CREATE_ENDPOINT",
    "DURATION_SEC",
    "HARD_BUDGET_USD",
    "MAX_DISPATCHES",
    "MODEL_ID",
    "RESOLUTION",
    "SCHEMA_VERSION",
    "SERVICE_ID",
    "claim_video_admission_dispatch",
    "compile_video_admission_manifest",
    "enforce_video_admission_request",
    "load_video_admission_manifest",
    "preview_video_admission_command",
    "register_runtime_video_admission_routes",
    "video_admission_capability",
    "video_admission_generation_request",
    "video_admission_readiness",
)
