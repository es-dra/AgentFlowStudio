from __future__ import annotations

import hashlib
import os
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI, HTTPException, Request

from agentflow.harness.json_io import exclusive_file_lock, write_json
from agentflow_studio.model_gateway.image_utils import image_dimensions, image_mime_type_from_bytes
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_asset_evidence import authoritative_source_evidence
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_image_assets import image_asset_file_path, image_asset_metadata
from apps.api.runtime_production_graph import (
    GraphIdempotencyConflict,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
    graph_has_authority,
    graph_path,
)
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


SCHEMA_VERSION = "afs.image_admission_manifest.v0.1"
PROMPT_CONTRACT_VERSION = "afs.image_prompt_contract.v0.1"
SERVICE_ID = "image_relay"
LEGACY_SERVICE_ID = "codex_image"
MODEL_ID = "gpt-image-2"
TRUE_VALUES = {"1", "true", "yes", "on"}
ITEM_TYPES = {"character_design", "scene_plate", "prop_design", "shot_keyframe"}
ITEM_STATES = {"planned", "reserved", "processing", "candidate", "approved", "rejected", "failed", "cancelled"}
COMMANDS = {
    "compile",
    "lock",
    "reserve_dispatch",
    "record_job",
    "record_candidate",
    "record_failure",
    "approve",
    "reject",
    "replace",
    "inspect_next_batch",
    "create_recovery_manifest",
    "create_next_batch_manifest",
    "cancel_batch",
}
ASPECT_SIZES = {
    "1:1": "1024x1024",
    "3:4": "960x1280",
    "16:9": "1280x720",
}
FIXTURE_MEDIA = {
    "1:1": "image-admission-review-square.png",
    "3:4": "image-admission-review-portrait.png",
    "16:9": "image-admission-review-landscape.png",
}


def register_runtime_image_admission_routes(
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

    @app.get("/projects/{project_id}/m6/image-admission")
    def get_image_admission(project_id: str, request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        manifest = load_image_admission_manifest(store, project_id)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": manifest.get("status", "empty") if manifest else "empty",
            "manifest": manifest,
            "capability": image_admission_capability(),
            "budget_contract": budget_contract(),
            "provider_dispatch_count": int((manifest or {}).get("budget", {}).get("dispatches_reserved") or 0),
            "external_cost_usd": str((manifest or {}).get("budget", {}).get("estimated_reserved_usd") or "0.0000"),
        }

    @app.post("/projects/{project_id}/m6/image-admission/commands/preview")
    def preview_image_admission(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        try:
            result = preview_image_admission_command(store, project_id, body)
            reject_unsafe_payload(result)
            return result
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/projects/{project_id}/m6/image-admission/commands/confirm")
    def confirm_image_admission(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        if str((body.get("command") or {}).get("type") or "") == "inspect_next_batch":
            raise HTTPException(status_code=422, detail="next image batch inspection cannot be confirmed")
        lock_path = _manifest_path(store, project_id).with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with exclusive_file_lock(lock_path):
                existing = load_image_admission_manifest(store, project_id)
                replay = _idempotent_receipt(existing, body.get("command"))
                if replay:
                    return {
                        "schema_version": SCHEMA_VERSION,
                        "status": "confirmed",
                        "idempotent_replay": True,
                        "command": _safe_command(body.get("command")),
                        "result": {"manifest": existing, "graph_mutation": 0},
                        "receipt": replay,
                        "provider_dispatch_count": 0,
                        "external_cost_usd": "0.0000",
                    }
                preview = preview_image_admission_command(store, project_id, body)
                if str(body.get("preview_digest") or "") != preview["preview_digest"]:
                    raise ValueError("image admission preview is stale; review the impact again")
                result = deepcopy(preview["result"]["manifest"])
                command = preview["command"]
                if command["type"] == "record_candidate" and command.get("fixture") is True:
                    item = _manifest_item(result, command.get("item_id"))
                    _materialize_fixture_candidate(store, project_id, item)
                if command["type"] == "approve":
                    result = _approve_to_graph(
                        store,
                        graph_store,
                        project_id,
                        result,
                        command,
                    )
                result["updated_at"] = _now()
                path = _manifest_path(store, project_id)
                path.parent.mkdir(parents=True, exist_ok=True)
                reject_unsafe_payload(result)
                if command["type"] in {"create_recovery_manifest", "create_next_batch_manifest"}:
                    _archive_manifest_once(store, project_id, existing)
                write_json(path, result)
            return {
                **preview,
                "status": "confirmed",
                "result": {"manifest": result, "graph_mutation": 1 if command["type"] == "approve" else 0},
                "receipt": result.get("receipts", [])[-1] if result.get("receipts") else {},
            }
        except (GraphVersionConflict, GraphIdempotencyConflict) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (ProductionGraphError, KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


def preview_image_admission_command(
    store: RuntimeStore,
    project_id: str,
    body: Mapping[str, Any],
) -> dict[str, Any]:
    command = _safe_command(body.get("command"))
    requested_at = _requested_at(body)
    if command["type"] == "compile":
        manifest = compile_image_admission_manifest(project_id, body.get("source"), created_at=requested_at)
        _append_receipt(
            manifest,
            {"item_id": "manifest"},
            "manifest_compiled",
            command,
            recorded_at=requested_at,
        )
        before = {}
    else:
        before = load_image_admission_manifest(store, project_id)
        if not before:
            raise ValueError("image admission manifest has not been compiled")
        _assert_source_current(
            store,
            project_id,
            before,
            body.get("source"),
            command_type=command["type"],
        )
        manifest = _apply_command(
            store,
            project_id,
            before,
            command,
            source_value=body.get("source"),
            recorded_at=requested_at,
        )
    impact = _impact(before, manifest, command)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "preview",
        "command": command,
        "impact": impact,
        "result": {
            "manifest": manifest,
            "graph_mutation": 0,
        },
        "provider_dispatch_count": 0,
        "external_cost_usd": "0.0000",
        "requires_confirmation": True,
    }
    payload["preview_digest"] = canonical_digest(payload)
    return payload


def compile_image_admission_manifest(
    project_id: str,
    source_value: Any,
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    timestamp = created_at or _now()
    source = _source_contract(project_id, source_value)
    bible = source["asset_bible"]
    if bible.get("status") != "locked" or not bible.get("locked_revision_id"):
        raise ValueError("image admission requires a locked Asset Bible revision")
    coverage = bible.get("coverage") if isinstance(bible.get("coverage"), Mapping) else {}
    if not coverage.get("coverage_pass") or int(coverage.get("unresolved_required") or 0) != 0:
        raise ValueError("image admission requires complete resolved occurrence coverage")
    quality = (
        bible.get("recognition_quality")
        if isinstance(bible.get("recognition_quality"), Mapping)
        else {}
    )
    if quality.get("status") != "pass" or not coverage.get("quality_pass"):
        raise ValueError("image admission requires a passed asset recognition quality gate")
    candidate_set = (
        bible.get("candidate_set")
        if isinstance(bible.get("candidate_set"), Mapping)
        else {}
    )
    source_traceability = _source_traceability_contract(bible, candidate_set)
    if source_traceability["status"] != "complete":
        raise ValueError(
            "image admission requires traceable source evidence for every applied shot: "
            f"{source_traceability['traceable_shot_count']}/"
            f"{source_traceability['shot_total']} traceable"
        )
    active = [
        _asset(item)
        for item in bible.get("assets", [])
        if isinstance(item, Mapping) and item.get("review_state") == "approved"
    ]
    _assert_assets_creatively_ready(active)
    art_direction = _art_direction_contract(source.get("art_direction"), require_complete=True)
    characters = [item for item in active if item["asset_type"] == "character"]
    scenes = [item for item in active if item["asset_type"] == "scene"]
    props = [item for item in active if item["asset_type"] == "prop"]
    if not scenes:
        raise ValueError("at least one approved scene asset is required")
    shot_grounding = source.get("shot_grounding") if isinstance(source.get("shot_grounding"), Mapping) else {}
    scene_index = sorted(
        [
            dict(item)
            for item in (
                shot_grounding.get("scenes")
                or candidate_set.get("scene_index", [])
            )
            if isinstance(item, Mapping)
        ],
        key=lambda item: (int(item.get("number") or 9999), str(item.get("scene_id") or "")),
    )
    shot_index = sorted(
        [
            dict(item)
            for item in (
                shot_grounding.get("shots")
                or candidate_set.get("shot_index", [])
            )
            if isinstance(item, Mapping)
        ],
        key=lambda item: (int(item.get("number") or 9999), str(item.get("shot_id") or "")),
    )
    if not scene_index or not shot_index:
        raise ValueError("applied shot plan must provide stable scene and shot indexes")
    if len(shot_index) <= 3:
        selected_shots = shot_index
    else:
        pressure_shot = max(
            shot_index[1:-1],
            key=lambda shot: (
                _shot_reference_count(active, str(shot.get("shot_id") or "")),
                -int(shot.get("number") or 0),
            ),
        )
        selected_shots = [shot_index[0], pressure_shot, shot_index[-1]]
    source_fingerprint = canonical_digest(_source_fingerprint_payload(source))
    items: list[dict[str, Any]] = []
    for asset in sorted(characters, key=lambda item: item["stable_id"]):
        items.append(
            _asset_item(
                asset,
                "character_design",
                "3:4",
                source_fingerprint,
                art_direction=art_direction,
            )
        )
    for asset in sorted(scenes, key=lambda item: item["stable_id"]):
        items.append(
            _asset_item(
                asset,
                "scene_plate",
                "16:9",
                source_fingerprint,
                art_direction=art_direction,
            )
        )
    for asset in sorted(props, key=lambda item: item["stable_id"]):
        items.append(
            _asset_item(
                asset,
                "prop_design",
                "1:1",
                source_fingerprint,
                art_direction=art_direction,
            )
        )
    shot_roles = (
        ["single_shot"]
        if len(selected_shots) == 1
        else ["opening", "closing_relation"]
        if len(selected_shots) == 2
        else ["opening", "continuity_pressure", "closing_relation"]
    )
    for role, shot in zip(shot_roles, selected_shots, strict=True):
        shot_id = str(shot.get("shot_id") or "")
        reference_assets = [
            item["stable_id"]
            for item in active
            if shot_id in item["occurrences"]["shot_ids"]
            or str(shot.get("scene_id") or "") in item["occurrences"]["scene_ids"]
        ]
        items.append(
            _keyframe_item(
                shot,
                role,
                sorted(set(reference_assets)),
                source_fingerprint,
                art_direction=art_direction,
                reference_assets=[
                    item
                    for item in active
                    if item["stable_id"] in reference_assets
                ],
                negative_locks=sorted(
                    {
                        lock
                        for item in active
                        if item["stable_id"] in reference_assets
                        for lock in item["negative_locks"]
                    }
                ),
            )
        )
    if not items or len({item["item_id"] for item in items}) != len(items):
        raise ValueError("image admission compiler must produce unique items")
    contract = budget_contract()
    capability = image_admission_capability()
    manifest_contract = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "version": 1,
        "source": {key: value for key, value in source.items() if key != "asset_bible"},
        "source_fingerprint": source_fingerprint,
        "art_direction": art_direction,
        "creative_grounding": {
            "status": "ready",
            "prompt_contract_version": PROMPT_CONTRACT_VERSION,
            "source_fingerprint": source_fingerprint,
            "source_evidence_summary": source_traceability,
        },
        "selection_summary": {
            "canonical_character_count": len(characters),
            "canonical_scene_count": len(scenes),
            "canonical_prop_count": len(props),
            "applied_shot_count": len(shot_index),
            "representative_shot_count": len(selected_shots),
            "item_count": len(items),
        },
        "items": items,
        "budget_contract": contract,
        "provider_contract": {
            "service_id": SERVICE_ID,
            "model": MODEL_ID,
            "concurrency": 1,
            "candidate_count": 1,
            "auto_retry": 0,
            "capability": capability,
        },
    }
    manifest_hash = canonical_digest(manifest_contract)
    return {
        **manifest_contract,
        "manifest_id": f"image-admission-{manifest_hash[:16]}",
        "manifest_hash": manifest_hash,
        "accepted_graph_snapshots": [
            {
                "version": source["production_graph_version"],
                "graph_digest": source["production_graph_digest"],
                "reason": "manifest_source",
            }
        ],
        "status": "draft",
        "locked_at": "",
        "stale_reason": "",
        "budget": {
            "dispatches_reserved": 0,
            "estimated_reserved_usd": "0.0000",
            "remaining_dispatches": int(contract["max_dispatches"]),
            "remaining_estimated_usd": contract["max_estimated_usd"],
        },
        "receipts": [],
        "history": [],
        "created_at": timestamp,
        "updated_at": timestamp,
        "provider_dispatch_count": 0,
        "actual_usd": None,
        "billing_verification_state": "unverified",
    }


def load_image_admission_manifest(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = _manifest_path(store, project_id)
    if not path.is_file():
        return {}
    value = read_json(path)
    reject_unsafe_payload(value)
    if value.get("schema_version") != SCHEMA_VERSION or value.get("project_id") != project_id:
        raise ValueError("image admission manifest storage scope is invalid")
    return value


def budget_contract(max_dispatches: int = 1) -> dict[str, Any]:
    if max_dispatches < 1:
        raise ValueError("image admission dispatch limit must be positive")
    unit = _money_env("AFS_IMAGE_ADMISSION_UNIT_ESTIMATE_USD", "0.0377")
    configured_maximum = _money_env("AFS_IMAGE_ADMISSION_MAX_ESTIMATED_USD", "0.3500")
    configured_program_maximum = _money_env("AFS_MEDIA_PROGRAM_MAX_USD", "50.0000")
    program_maximum = min(configured_program_maximum, Decimal("50.0000"))
    requested_maximum = unit * max_dispatches
    maximum = min(requested_maximum, configured_maximum, program_maximum)
    if (
        unit <= 0
        or configured_maximum < requested_maximum
        or configured_program_maximum <= 0
        or program_maximum < requested_maximum
    ):
        raise ValueError("image admission pricing must be positive")
    return {
        "currency": "USD",
        "unit_estimate_usd": _money(unit),
        "max_dispatches": max_dispatches,
        "max_estimated_usd": _money(maximum),
        "program_max_usd": _money(program_maximum),
        "concurrency": 1,
        "candidate_count": 1,
        "auto_retry": 0,
        "price_source": os.getenv(
            "AFS_IMAGE_ADMISSION_PRICE_SOURCE",
            "Crazyrouter public gpt-image-2 pricing",
        )[:160],
        "price_as_of": os.getenv("AFS_IMAGE_ADMISSION_PRICE_AS_OF", "2026-06-06")[:32],
        "disclosure": "公开估算，非最终账单",
    }


def image_admission_capability() -> dict[str, Any]:
    capability = {
        "service_id": SERVICE_ID,
        "configured_from": LEGACY_SERVICE_ID,
        "model": MODEL_ID,
        "exact_model": False,
        "configured": False,
        "image_gate_open": _gate_open(),
        "fixture_mode": _fixture_mode(),
        "reference_image_slots": 0,
        "trusted_image_edit": False,
        "keyframe_continuity_ready": False,
        "blocker": "图片服务未配置",
    }
    try:
        registry = load_provider_registry()
        descriptor = registry.descriptor(SERVICE_ID)
        service = registry.store.service(SERVICE_ID)
        configured_model = str(service.get("model") or "")
        exact_model = configured_model == MODEL_ID
        reference_slots = int(descriptor.reference_image_slots or 0)
        edit = descriptor.image_edit_capabilities
        trusted_edit = bool(
            descriptor.image_edit_capabilities_present
            and edit.supports_image_edit
            and edit.max_reference_images > 0
        )
        capability.update(
            {
                "configured": exact_model,
                "exact_model": exact_model,
                "reference_image_slots": reference_slots,
                "trusted_image_edit": trusted_edit,
                "input_fidelity_modes": list(edit.input_fidelity_modes),
                "keyframe_continuity_ready": exact_model and (reference_slots > 0 or trusted_edit),
                "blocker": (
                    ""
                    if exact_model and (reference_slots > 0 or trusted_edit)
                    else "图片服务没有绑定本次要求的精确模型"
                    if not exact_model
                    else "当前图片适配器未声明受信任的参考图或编辑输入能力"
                ),
            }
        )
    except (ModelGatewayError, OSError, ValueError):
        pass
    return capability


def validate_image_admission_reservation(
    store: RuntimeStore,
    project_id: str,
    *,
    manifest_id: str,
    item_id: str,
    reservation_token: str,
) -> dict[str, Any]:
    manifest = load_image_admission_manifest(store, project_id)
    if not manifest:
        raise ValueError("image admission manifest is required")
    if manifest.get("status") != "locked":
        raise ValueError("image admission manifest must be locked")
    if manifest.get("manifest_id") != manifest_id:
        raise ValueError("image admission manifest id mismatch")
    item = _manifest_item(manifest, item_id)
    if item.get("state") != "reserved" or item.get("reservation_token") != reservation_token:
        raise ValueError("image admission reservation is missing or stale")
    return {"manifest": manifest, "item": item}


def enforce_image_admission_keyframe_request(
    store: RuntimeStore,
    project_id: str,
    request: Any,
) -> dict[str, Any] | None:
    manifest = load_image_admission_manifest(store, project_id)
    if not manifest or manifest.get("status") != "locked":
        return None
    parameters = request.node_parameters if isinstance(request.node_parameters, dict) else {}
    binding = parameters.get("image_admission") if isinstance(parameters.get("image_admission"), dict) else {}
    validated = validate_image_admission_reservation(
        store,
        project_id,
        manifest_id=str(binding.get("manifest_id") or ""),
        item_id=str(binding.get("item_id") or ""),
        reservation_token=str(binding.get("reservation_token") or ""),
    )
    _assert_manifest_creative_ready(validated["manifest"])
    capability = image_admission_capability()
    if not capability["configured"] or not capability["exact_model"]:
        raise ValueError(capability["blocker"])
    item = validated["item"]
    if request.candidate_count != 1:
        raise ValueError("image admission requires one independent candidate per dispatch")
    if request.provider_service_id != SERVICE_ID:
        raise ValueError("image admission must use the locked image relay service")
    if request.aspect_ratio != item.get("aspect_ratio"):
        raise ValueError("keyframe request aspect ratio differs from the locked manifest")
    prompt_contract = item.get("prompt_contract") if isinstance(item.get("prompt_contract"), Mapping) else {}
    expected_prompt = str(prompt_contract.get("provider_prompt") or "")
    if not expected_prompt or request.prompt_text != expected_prompt:
        raise ValueError("image request prompt differs from the locked creative grounding contract")
    if canonical_digest(expected_prompt) != prompt_contract.get("provider_prompt_digest"):
        raise ValueError("image request prompt contract digest is invalid")
    if request.style != validated["manifest"].get("art_direction", {}).get("visual_style"):
        raise ValueError("image request style differs from the locked art direction")
    if list(request.asset_refs or []) != list(item.get("reference_media_ids") or []):
        raise ValueError("keyframe request references differ from the locked manifest")
    expected_node_id = item.get("target_shot_id") or next(iter(item.get("target_asset_ids") or []), item["item_id"])
    if request.node_id != expected_node_id:
        raise ValueError("keyframe request target differs from the locked manifest")
    if parameters.get("disable_provider_retry") is not True:
        raise ValueError("image admission forbids implicit provider retry")
    if item.get("item_type") == "shot_keyframe" and not image_admission_capability()["keyframe_continuity_ready"]:
        raise ValueError("keyframe continuity is blocked by the configured image reference capability")
    return validated


def _apply_command(
    store: RuntimeStore,
    project_id: str,
    before: Mapping[str, Any],
    command: Mapping[str, Any],
    *,
    source_value: Any = None,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    timestamp = recorded_at or _now()
    manifest = deepcopy(before)
    command_type = command["type"]
    if command_type == "lock":
        if manifest.get("status") != "draft":
            raise ValueError("only a draft image admission manifest can be locked")
        items = manifest.get("items", [])
        if not items or len({str(item.get("item_id") or "") for item in items}) != len(items):
            raise ValueError("image admission manifest must contain unique items")
        _assert_manifest_creative_ready(manifest)
        manifest["status"] = "locked"
        manifest["locked_at"] = timestamp
        _append_receipt(manifest, {"item_id": "manifest"}, "manifest_locked", command, recorded_at=timestamp)
    elif command_type == "reserve_dispatch":
        _reserve_dispatch(store, project_id, manifest, command, recorded_at=timestamp)
    elif command_type == "record_candidate":
        _record_candidate(store, project_id, manifest, command, recorded_at=timestamp)
    elif command_type == "record_job":
        item = _manifest_item(manifest, command.get("item_id"))
        if item.get("state") not in {"reserved", "processing"}:
            raise ValueError("only a reserved image admission item can bind a generation job")
        job_id = _token(command.get("provider_job_id"), "provider_job_id")
        if item.get("provider_job_id") and item["provider_job_id"] != job_id:
            raise ValueError("image admission item already belongs to another generation job")
        item["provider_job_id"] = job_id
        item["state"] = "processing"
        _append_receipt(manifest, item, "job_recorded", command, recorded_at=timestamp)
    elif command_type == "record_failure":
        item = _manifest_item(manifest, command.get("item_id"))
        fixture = command.get("fixture") is True
        if fixture and not _fixture_mode():
            raise ValueError("deterministic media fixtures are disabled")
        allowed_states = {"reserved", "processing"} | ({"planned"} if fixture else set())
        if item.get("state") not in allowed_states:
            raise ValueError("only a reserved or processing item can record a dispatch failure")
        item["state"] = "failed"
        item["error_category"] = str(
            command.get("error_category") or ("deterministic_fixture_failure" if fixture else "generation_failed")
        )[:80]
        _append_receipt(manifest, item, "failed", command, recorded_at=timestamp)
    elif command_type == "approve":
        item = _manifest_item(manifest, command.get("item_id"))
        if item.get("state") != "candidate" or not item.get("candidate"):
            raise ValueError("only a candidate image can be approved")
        _assert_candidate_media_available(store, project_id, item)
        item["state"] = "approved"
        _append_receipt(manifest, item, "approved", command, recorded_at=timestamp)
    elif command_type == "reject":
        item = _manifest_item(manifest, command.get("item_id"))
        if item.get("state") != "candidate":
            raise ValueError("only a candidate image can be rejected")
        item["state"] = "rejected"
        _append_receipt(manifest, item, "rejected", command, recorded_at=timestamp)
    elif command_type == "replace":
        item = _manifest_item(manifest, command.get("item_id"))
        if item.get("state") not in {"candidate", "rejected", "failed"}:
            raise ValueError("only a candidate, rejected, or failed item can be replaced")
        if (
            item.get("state") == "failed"
            and int(manifest.get("budget", {}).get("remaining_dispatches") or 0) <= 0
        ):
            raise ValueError("failed image belongs to an exhausted manifest; create a new recovery manifest")
        if item.get("candidate"):
            manifest["history"].append(
                {
                    "item_id": item["item_id"],
                    "candidate": deepcopy(item["candidate"]),
                    "retired_at": timestamp,
                    "reason": str(command.get("reason") or "replacement requested")[:160],
                }
            )
        item.pop("candidate", None)
        item.pop("reservation_token", None)
        item["state"] = "planned"
        _append_receipt(manifest, item, "replacement_planned", command, recorded_at=timestamp)
    elif command_type == "create_recovery_manifest":
        manifest = _create_recovery_manifest(
            project_id,
            before,
            source_value,
            command,
            recorded_at=timestamp,
        )
    elif command_type == "create_next_batch_manifest":
        manifest = _create_next_batch_manifest(
            store,
            project_id,
            before,
            source_value,
            command,
            recorded_at=timestamp,
        )
    elif command_type == "inspect_next_batch":
        if before.get("status") not in {"locked", "cancelled"}:
            raise ValueError("only a finished image manifest can prepare the next image batch")
        if any(
            entry.get("state") in {"planned", "reserved", "processing", "candidate"}
            for entry in before.get("items", [])
        ):
            raise ValueError("finish or stop the current image batch before preparing the next batch")
        fresh = compile_image_admission_manifest(project_id, source_value, created_at=timestamp)
        _assert_continuation_price_current(before, fresh)
        completed_ids = _historically_sent_item_ids(store, project_id, before)
        options = [
            deepcopy(item)
            for item in fresh.get("items", [])
            if item.get("item_id") not in completed_ids
        ]
        manifest["next_batch_options"] = [
            item
            for item in options
            if item.get("item_type") != "shot_keyframe"
            or _bind_approved_reference_media(
                store,
                project_id,
                [item],
                require_complete=False,
            )
        ]
    elif command_type == "cancel_batch":
        cancelled = 0
        for item in manifest.get("items", []):
            if item.get("state") == "planned":
                item["state"] = "cancelled"
                cancelled += 1
        manifest["status"] = "cancelled" if cancelled else manifest.get("status")
        manifest["cancel_semantics"] = {
            "unsent_cancelled": cancelled,
            "in_flight_cancelled": 0,
            "statement": "仅停止尚未发送的项目；同步处理中项目未宣称已取消。",
        }
        _append_receipt(manifest, {"item_id": "batch"}, "batch_cancelled", command, recorded_at=timestamp)
    else:
        raise ValueError("unsupported image admission command")
    manifest["updated_at"] = timestamp
    return manifest


def _create_recovery_manifest(
    project_id: str,
    before: Mapping[str, Any],
    source_value: Any,
    command: Mapping[str, Any],
    *,
    recorded_at: str,
) -> dict[str, Any]:
    if before.get("status") != "locked":
        raise ValueError("only a locked image manifest can create a recovery manifest")
    if isinstance(before.get("recovery_contract"), Mapping):
        raise ValueError("the active manifest is already a single-item recovery manifest")
    if str(command.get("source_manifest_id") or "") != str(before.get("manifest_id") or ""):
        raise ValueError("recovery source manifest is stale")
    item = _manifest_item(before, command.get("item_id"))
    if item.get("state") != "failed":
        raise ValueError("only a failed image item can create a recovery manifest")
    if any(
        entry.get("state") in {"reserved", "processing", "candidate"}
        for entry in before.get("items", [])
    ):
        raise ValueError("active image work must finish before creating a recovery manifest")
    contract = before.get("budget_contract") if isinstance(before.get("budget_contract"), Mapping) else {}
    budget = before.get("budget") if isinstance(before.get("budget"), Mapping) else {}
    if (
        int(contract.get("max_dispatches") or 0) != 1
        or int(contract.get("auto_retry", -1)) != 0
        or int(contract.get("concurrency") or 0) != 1
        or int(contract.get("candidate_count") or 0) != 1
        or not _recovery_budget_is_exact(contract)
        or not _recovery_budget_is_consumed(contract, budget)
        or int(before.get("provider_dispatch_count") or 0) != 1
    ):
        raise ValueError("recovery requires one exhausted single-dispatch manifest")

    fresh = compile_image_admission_manifest(project_id, source_value, created_at=recorded_at)
    if (
        fresh["budget_contract"]["unit_estimate_usd"] != contract.get("unit_estimate_usd")
        or fresh["budget_contract"]["max_estimated_usd"] != contract.get("max_estimated_usd")
    ):
        raise ValueError("recovery pricing changed; review the image budget before creating a new manifest")
    fresh_item = _manifest_item(fresh, item["item_id"])
    if canonical_digest(_recovery_item_contract(item)) != canonical_digest(
        _recovery_item_contract(fresh_item)
    ):
        raise ValueError(
            "recovery item no longer matches the current Asset Bible and shot grounding"
        )
    fresh["version"] = int(before.get("version") or 1) + 1
    fresh["items"] = [deepcopy(fresh_item)]
    fresh["selection_summary"] = {
        **fresh["selection_summary"],
        "item_count": 1,
        "recovery_item_count": 1,
    }
    fresh["recovery_contract"] = {
        "kind": "single_item_failure_recovery",
        "generation": 1,
        "source_manifest_id": before["manifest_id"],
        "source_manifest_hash": before["manifest_hash"],
        "source_manifest_archived": True,
        "selected_item_id": item["item_id"],
        "previous_error_category": str(item.get("error_category") or "generation_failed")[:80],
        "previous_dispatches_reserved": int(budget.get("dispatches_reserved") or 0),
        "previous_estimated_reserved_usd": str(budget.get("estimated_reserved_usd") or "0.0000"),
        "new_max_dispatches": 1,
        "new_max_estimated_usd": fresh["budget_contract"]["max_estimated_usd"],
        "auto_retry": 0,
        "requires_separate_generation_confirmation": True,
    }
    manifest_hash = canonical_digest(_manifest_contract_payload(fresh))
    fresh["manifest_hash"] = manifest_hash
    fresh["manifest_id"] = f"image-admission-recovery-{manifest_hash[:16]}"
    fresh["status"] = "locked"
    fresh["locked_at"] = recorded_at
    fresh["provider_dispatch_count"] = 0
    fresh["actual_usd"] = None
    fresh["billing_verification_state"] = "unverified"
    _append_receipt(
        fresh,
        fresh["items"][0],
        "recovery_manifest_created",
        command,
        recorded_at=recorded_at,
    )
    return fresh


def _create_next_batch_manifest(
    store: RuntimeStore,
    project_id: str,
    before: Mapping[str, Any],
    source_value: Any,
    command: Mapping[str, Any],
    *,
    recorded_at: str,
) -> dict[str, Any]:
    if before.get("status") not in {"locked", "cancelled"}:
        raise ValueError("only a finished image manifest can create the next image batch")
    if str(command.get("source_manifest_id") or "") != str(before.get("manifest_id") or ""):
        raise ValueError("next image batch source manifest is stale")
    if any(
        entry.get("state") in {"planned", "reserved", "processing", "candidate"}
        for entry in before.get("items", [])
    ):
        raise ValueError("finish or stop the current image batch before preparing the next batch")

    selected_ids = command.get("item_ids")
    if not isinstance(selected_ids, list) or not selected_ids:
        raise ValueError("select one or more unique items for the next image batch")
    selected_ids = [_token(value, "item_id") for value in selected_ids]
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("select one or more unique items for the next image batch")

    fresh = compile_image_admission_manifest(project_id, source_value, created_at=recorded_at)
    _assert_continuation_price_current(before, fresh)
    completed_ids = _historically_sent_item_ids(store, project_id, before)
    eligible = {
        str(item["item_id"]): item
        for item in fresh.get("items", [])
        if item.get("item_id") not in completed_ids
    }
    if any(item_id not in eligible for item_id in selected_ids):
        raise ValueError("next image batch selection contains completed or unavailable items")

    selected = [deepcopy(eligible[item_id]) for item_id in selected_ids]
    _bind_approved_reference_media(store, project_id, selected)
    contract = budget_contract(len(selected))
    fresh["version"] = int(before.get("version") or 1) + 1
    fresh["items"] = selected
    fresh["selection_summary"] = {
        **fresh["selection_summary"],
        "item_count": len(selected),
        "next_batch_item_count": len(selected),
        "eligible_item_count": len(eligible),
        "completed_item_count": len(completed_ids),
    }
    fresh["budget_contract"] = contract
    fresh["budget"] = {
        "dispatches_reserved": 0,
        "estimated_reserved_usd": "0.0000",
        "remaining_dispatches": len(selected),
        "remaining_estimated_usd": contract["max_estimated_usd"],
    }
    fresh["continuation_contract"] = {
        "kind": "next_image_batch",
        "source_manifest_id": before["manifest_id"],
        "source_manifest_hash": before["manifest_hash"],
        "source_manifest_archived": True,
        "selected_item_ids": selected_ids,
        "selected_item_count": len(selected),
        "new_max_dispatches": len(selected),
        "new_max_estimated_usd": contract["max_estimated_usd"],
        "auto_retry": 0,
        "requires_separate_generation_confirmation": True,
    }
    manifest_hash = canonical_digest(_manifest_contract_payload(fresh))
    fresh["manifest_hash"] = manifest_hash
    fresh["manifest_id"] = f"image-admission-batch-{manifest_hash[:16]}"
    fresh["status"] = "locked"
    fresh["locked_at"] = recorded_at
    fresh["provider_dispatch_count"] = 0
    fresh["actual_usd"] = None
    fresh["billing_verification_state"] = "unverified"
    _append_receipt(
        fresh,
        {"item_id": "batch"},
        "next_batch_manifest_created",
        command,
        recorded_at=recorded_at,
    )
    return fresh


def _assert_continuation_price_current(
    before: Mapping[str, Any],
    fresh: Mapping[str, Any],
) -> None:
    previous_contract = (
        before.get("budget_contract")
        if isinstance(before.get("budget_contract"), Mapping)
        else {}
    )
    fresh_contract = (
        fresh.get("budget_contract")
        if isinstance(fresh.get("budget_contract"), Mapping)
        else {}
    )
    if (
        fresh_contract.get("unit_estimate_usd")
        != previous_contract.get("unit_estimate_usd")
        or fresh_contract.get("program_max_usd")
        != previous_contract.get("program_max_usd")
    ):
        raise ValueError("image pricing changed; review the current price before preparing the next batch")


def _historically_sent_item_ids(
    store: RuntimeStore,
    project_id: str,
    active: Mapping[str, Any],
) -> set[str]:
    manifests: list[Mapping[str, Any]] = [active]
    history_dir = _manifest_path(store, project_id).parent / "history"
    if history_dir.is_dir():
        for path in sorted(history_dir.glob("*.json")):
            archived = read_json(path)
            reject_unsafe_payload(archived)
            if (
                archived.get("schema_version") != SCHEMA_VERSION
                or archived.get("project_id") != project_id
                or safe_id(str(archived.get("manifest_id") or "")) != path.stem
            ):
                raise ValueError("archived image manifest storage scope is invalid")
            manifests.append(archived)
    return {
        str(item["item_id"])
        for manifest in manifests
        for item in manifest.get("items", [])
        if isinstance(item, Mapping)
        and item.get("item_id")
        and (
            item.get("state") not in {"planned", "cancelled"}
            or int(item.get("dispatch_ordinal") or 0) > 0
        )
    }


def _bind_approved_reference_media(
    store: RuntimeStore,
    project_id: str,
    items: list[dict[str, Any]],
    *,
    require_complete: bool = True,
) -> bool:
    if not any(item.get("item_type") == "shot_keyframe" for item in items):
        return True
    if not graph_has_authority(store, project_id):
        if require_complete:
            raise ValueError("keyframe selection requires approved same-project reference media")
        return False
    graph = ProductionGraphStore(store).load(project_id)
    approved_nodes = {
        str(node_id): node
        for node_id, node in graph.get("nodes", {}).items()
        if node.get("state") == "active"
        and node.get("metadata", {}).get("kind") == "approved_image"
    }
    media_by_target: dict[str, set[str]] = {}
    for relation in graph.get("relations", []):
        if (
            isinstance(relation, Mapping)
            and relation.get("relation_type") == "approved_image"
            and str(relation.get("to_id") or "") in approved_nodes
        ):
            image_asset_id = str(
                approved_nodes[str(relation["to_id"])].get("metadata", {}).get("image_asset_id") or ""
            )
            if image_asset_id:
                media_by_target.setdefault(str(relation.get("from_id") or ""), set()).add(image_asset_id)
    for item in items:
        if item.get("item_type") != "shot_keyframe":
            continue
        reference_asset_ids = [str(value) for value in item.get("reference_asset_ids", [])]
        if any(not media_by_target.get(asset_id) for asset_id in reference_asset_ids):
            if require_complete:
                raise ValueError(
                    "keyframe selection requires approved reference images for every canonical asset"
                )
            return False
        references = sorted(
            {
                media_id
                for asset_id in reference_asset_ids
                for media_id in media_by_target.get(str(asset_id), set())
            }
        )[:4]
        if not references:
            raise ValueError("keyframe selection requires approved character, scene, or prop reference images")
        _validate_reference_media(store, project_id, references)
        item["reference_media_ids"] = references
    return True


def _manifest_contract_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "project_id",
        "version",
        "source",
        "source_fingerprint",
        "art_direction",
        "creative_grounding",
        "selection_summary",
        "items",
        "budget_contract",
        "provider_contract",
        "recovery_contract",
        "continuation_contract",
    )
    return {key: deepcopy(manifest[key]) for key in keys if key in manifest}


def _recovery_budget_is_exact(contract: Mapping[str, Any]) -> bool:
    try:
        unit = Decimal(str(contract.get("unit_estimate_usd")))
        maximum = Decimal(str(contract.get("max_estimated_usd")))
        program_maximum = Decimal(str(contract.get("program_max_usd")))
        return (
            str(contract.get("currency") or "") == "USD"
            and unit > 0
            and _money(unit) == _money(maximum)
            and maximum <= program_maximum
        )
    except (InvalidOperation, TypeError, ValueError):
        return False


def _recovery_budget_is_consumed(
    contract: Mapping[str, Any],
    budget: Mapping[str, Any],
) -> bool:
    try:
        return (
            int(budget.get("dispatches_reserved") or 0) == 1
            and int(budget.get("remaining_dispatches") or 0) == 0
            and _money(Decimal(str(budget.get("estimated_reserved_usd"))))
            == _money(Decimal(str(contract.get("max_estimated_usd"))))
            and _money(Decimal(str(budget.get("remaining_estimated_usd"))))
            == "0.0000"
        )
    except (InvalidOperation, TypeError, ValueError):
        return False


def _recovery_item_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    runtime_fields = {
        "candidate",
        "dispatch_ordinal",
        "error_category",
        "promotion",
        "provider_job_id",
        "reservation_token",
        "state",
    }
    return {
        key: deepcopy(value)
        for key, value in item.items()
        if key not in runtime_fields
    }


def _reserve_dispatch(
    store: RuntimeStore,
    project_id: str,
    manifest: dict[str, Any],
    command: Mapping[str, Any],
    *,
    recorded_at: str | None = None,
) -> None:
    if manifest.get("status") != "locked":
        raise ValueError("image admission manifest must be locked before dispatch")
    _assert_manifest_creative_ready(manifest)
    if not _gate_open():
        raise ValueError("图片能力未启用；未发送任何外部请求")
    item = _manifest_item(manifest, command.get("item_id"))
    if item.get("state") not in {"planned", "failed", "rejected"}:
        raise ValueError("image admission item is not dispatchable")
    capability = image_admission_capability()
    if item["item_type"] == "shot_keyframe":
        if not item.get("reference_asset_ids"):
            raise ValueError("keyframe continuity requires canonical reference assets")
        if not item.get("reference_media_ids"):
            raise ValueError("keyframe continuity requires approved reference media")
        if not capability["keyframe_continuity_ready"]:
            raise ValueError(capability["blocker"])
        _validate_reference_media(store, project_id, item["reference_media_ids"])
    budget = manifest["budget"]
    contract = manifest["budget_contract"]
    dispatches = int(budget.get("dispatches_reserved") or 0)
    next_cost = Decimal(str(budget.get("estimated_reserved_usd") or "0")) + Decimal(
        str(contract["unit_estimate_usd"])
    )
    if dispatches + 1 > int(contract["max_dispatches"]):
        raise ValueError("本批图片发送次数已达到硬上限")
    if next_cost > Decimal(str(contract["max_estimated_usd"])):
        raise ValueError("本批图片费用估算已达到硬上限")
    ordinal = dispatches + 1
    token = canonical_digest(
        {
            "manifest_id": manifest["manifest_id"],
            "item_id": item["item_id"],
            "ordinal": ordinal,
            "idempotency_key": command.get("idempotency_key"),
        }
    )
    item["state"] = "reserved"
    item["dispatch_ordinal"] = ordinal
    item["reservation_token"] = token
    budget["dispatches_reserved"] = ordinal
    budget["estimated_reserved_usd"] = _money(next_cost)
    budget["remaining_dispatches"] = int(contract["max_dispatches"]) - ordinal
    budget["remaining_estimated_usd"] = _money(
        Decimal(str(contract["max_estimated_usd"])) - next_cost
    )
    manifest["provider_dispatch_count"] = ordinal
    _append_receipt(manifest, item, "reserved", command, recorded_at=recorded_at)


def _record_candidate(
    store: RuntimeStore,
    project_id: str,
    manifest: dict[str, Any],
    command: Mapping[str, Any],
    *,
    recorded_at: str | None = None,
) -> None:
    timestamp = recorded_at or _now()
    item = _manifest_item(manifest, command.get("item_id"))
    fixture = command.get("fixture") is True
    if fixture and not _fixture_mode():
        raise ValueError("deterministic media fixtures are disabled")
    if not fixture and item.get("state") not in {"reserved", "processing"}:
        raise ValueError("provider candidate requires an atomic dispatch reservation")
    candidate = (
        _fixture_candidate(store, project_id, item)
        if fixture
        else command.get("candidate") if isinstance(command.get("candidate"), Mapping) else {}
    )
    image_asset_id = _token(candidate.get("image_asset_id"), "candidate.image_asset_id")
    sha = str(candidate.get("sha256") or "")
    if len(sha) != 64 or any(char not in "0123456789abcdef" for char in sha):
        raise ValueError("candidate.sha256 must be a lowercase SHA-256 digest")
    width = int(candidate.get("width") or 0)
    height = int(candidate.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("candidate dimensions are required")
    image_format = str(candidate.get("format") or "png").lower()
    if image_format not in {"png", "jpeg", "jpg"}:
        raise ValueError("image admission candidates must be PNG or JPEG")
    preview_url = str(candidate.get("preview_url") or "")
    expected_preview = f"/projects/{safe_id(project_id)}/image-assets/{safe_id(image_asset_id)}/preview"
    if preview_url != expected_preview:
        raise ValueError("candidate preview URL is outside the same project image asset route")
    item["candidate"] = {
        "image_asset_id": image_asset_id,
        "sha256": sha,
        "format": "jpeg" if image_format == "jpg" else image_format,
        "width": width,
        "height": height,
        "preview_url": preview_url,
        "fixture": fixture,
        "recorded_at": timestamp,
    }
    item["state"] = "candidate"
    _append_receipt(manifest, item, "candidate_recorded", command, recorded_at=timestamp)


def _fixture_candidate(
    store: RuntimeStore,
    project_id: str,
    item: Mapping[str, Any],
) -> dict[str, Any]:
    aspect_ratio = str(item.get("aspect_ratio") or "")
    filename = FIXTURE_MEDIA.get(aspect_ratio)
    if not filename:
        raise ValueError("deterministic fixture does not support this aspect ratio")
    source = _fixture_media_root() / filename
    if not source.is_file():
        raise ValueError("deterministic fixture media is unavailable")
    image_bytes = source.read_bytes()
    if image_mime_type_from_bytes(image_bytes) != "image/png":
        raise ValueError("deterministic fixture media must be a valid PNG")
    dimensions = image_dimensions(image_bytes)
    expected_width, expected_height = (
        int(value) for value in str(item.get("size") or "").split("x", maxsplit=1)
    )
    if not dimensions or (
        dimensions["width"],
        dimensions["height"],
    ) != (expected_width, expected_height):
        raise ValueError("deterministic fixture dimensions differ from the locked manifest")
    sha = hashlib.sha256(image_bytes).hexdigest()
    asset_id = f"fixture_img_{canonical_digest({'project': project_id, 'item': item.get('item_id'), 'sha': sha})[:16]}"
    return {
        "image_asset_id": asset_id,
        "sha256": sha,
        "format": "png",
        "width": dimensions["width"],
        "height": dimensions["height"],
        "preview_url": (
            f"/projects/{safe_id(project_id)}/image-assets/{safe_id(asset_id)}/preview"
        ),
        "fixture_source": filename,
    }


def _materialize_fixture_candidate(
    store: RuntimeStore,
    project_id: str,
    item: Mapping[str, Any],
) -> None:
    candidate = item.get("candidate") if isinstance(item.get("candidate"), Mapping) else {}
    expected = _fixture_candidate(store, project_id, item)
    for field in ("image_asset_id", "sha256", "format", "width", "height", "preview_url"):
        if candidate.get(field) != expected[field]:
            raise ValueError("deterministic fixture candidate metadata is stale")
    source = _fixture_media_root() / expected["fixture_source"]
    image_bytes = source.read_bytes()
    asset_id = expected["image_asset_id"]
    asset_dir = (
        store.projects_dir
        / safe_id(project_id)
        / "image_assets"
        / safe_id(asset_id)
    ).resolve()
    asset_dir.relative_to(store.root.resolve())
    asset_dir.mkdir(parents=True, exist_ok=True)
    image_path = asset_dir / "source.png"
    image_path.write_bytes(image_bytes)
    metadata = {
        "artifact_type": "agentflow_deterministic_fixture_image_asset",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "asset_id": asset_id,
        "source_node_id": next(iter(item.get("target_asset_ids") or []), item.get("target_shot_id")),
        "role": "image_admission_review_fixture",
        "filename": expected["fixture_source"],
        "mime_type": "image/png",
        "file_suffix": ".png",
        "byte_count": len(image_bytes),
        "sha256": expected["sha256"],
        "preview_url": expected["preview_url"],
        "width": expected["width"],
        "height": expected["height"],
        "aspect_ratio": item.get("aspect_ratio"),
        "fixture": True,
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }
    reject_unsafe_payload(metadata)
    write_json(asset_dir / "image_asset.json", metadata)


def _assert_candidate_media_available(
    store: RuntimeStore,
    project_id: str,
    item: Mapping[str, Any],
) -> None:
    candidate = item.get("candidate") if isinstance(item.get("candidate"), Mapping) else {}
    asset_id = _token(candidate.get("image_asset_id"), "candidate.image_asset_id")
    try:
        metadata = image_asset_metadata(store, project_id, asset_id)
        image_asset_file_path(store, project_id, asset_id)
    except (KeyError, ValueError) as exc:
        raise ValueError("candidate media is missing or unavailable for review") from exc
    expected = {
        "sha256": candidate.get("sha256"),
        "width": candidate.get("width"),
        "height": candidate.get("height"),
        "preview_url": candidate.get("preview_url"),
        "mime_type": "image/jpeg" if candidate.get("format") == "jpeg" else "image/png",
    }
    if any(metadata.get(field) != value for field, value in expected.items()):
        raise ValueError("candidate media is missing or differs from its verified review metadata")


def _fixture_media_root() -> Path:
    return Path(__file__).resolve().parents[2] / "apps" / "studio" / "assets" / "test-fixtures"


def _approve_to_graph(
    store: RuntimeStore,
    graph_store: ProductionGraphStore,
    project_id: str,
    manifest: dict[str, Any],
    command: Mapping[str, Any],
) -> dict[str, Any]:
    if not graph_has_authority(store, project_id):
        raise ValueError("approval requires an existing authoritative ProductionGraph; legacy data is not migrated implicitly")
    item = _manifest_item(manifest, command.get("item_id"))
    candidate = item.get("candidate") or {}
    graph = graph_store.load(project_id)
    target_ids = [*item.get("target_asset_ids", [])]
    if item.get("target_shot_id"):
        target_ids.append(item["target_shot_id"])
    missing = sorted(set(target_ids) - set(graph.get("nodes", {})))
    if missing:
        raise ValueError("approval targets are missing from authoritative ProductionGraph")
    node_id = f"image-media-{safe_id(manifest['manifest_id'])}-{safe_id(item['item_id'])}"
    events: list[dict[str, Any]] = [
        {
            "type": "node_upserted",
            "node": {
                "node_id": node_id,
                "category": "artifact",
                "state": "active",
                "metadata": {
                    "kind": "approved_image",
                    "manifest_id": manifest["manifest_id"],
                    "manifest_hash": manifest["manifest_hash"],
                    "item_id": item["item_id"],
                    "image_asset_id": candidate["image_asset_id"],
                    "sha256": candidate["sha256"],
                    "format": candidate["format"],
                    "width": candidate["width"],
                    "height": candidate["height"],
                    "asset_bible_revision_id": manifest["source"]["asset_bible_revision_id"],
                    "shot_candidate_id": manifest["source"]["shot_candidate_id"],
                    "billing_verification_state": "unverified",
                    "actual_usd": None,
                },
            },
        }
    ]
    for target_id in sorted(set(target_ids)):
        events.append(
            {
                "type": "relation_upserted",
                "from_id": target_id,
                "to_id": node_id,
                "relation_type": "approved_image",
            }
        )
    key = str(command.get("idempotency_key") or f"approve-{manifest['manifest_id']}-{item['item_id']}")
    updated = graph_store.append(
        project_id,
        expected_version=int(graph["version"]),
        idempotency_key=key,
        semantic_digest=canonical_digest(
            {
                "manifest_hash": manifest["manifest_hash"],
                "item_id": item["item_id"],
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
    graph_snapshot = {
        "version": updated["version"],
        "graph_digest": updated["graph_digest"],
        "reason": f"approved:{item['item_id']}",
    }
    if graph_snapshot not in manifest.setdefault("accepted_graph_snapshots", []):
        manifest["accepted_graph_snapshots"].append(graph_snapshot)
    manifest["receipts"][-1]["candidate_promotion_revision"] = updated["version"]
    if item["item_type"] != "shot_keyframe":
        for keyframe in manifest.get("items", []):
            if (
                keyframe.get("item_type") == "shot_keyframe"
                and set(item.get("target_asset_ids", [])) & set(keyframe.get("reference_asset_ids", []))
            ):
                keyframe["reference_media_ids"] = sorted(
                    set(keyframe.get("reference_media_ids", [])) | {candidate["image_asset_id"]}
                )
    return manifest


def _validate_reference_media(
    store: RuntimeStore,
    project_id: str,
    reference_media_ids: list[str],
) -> list[dict[str, Any]]:
    if len(reference_media_ids) > 4:
        raise ValueError("keyframe continuity accepts at most four approved reference media")
    if not graph_has_authority(store, project_id):
        raise ValueError("approved reference media require an authoritative ProductionGraph")
    graph = ProductionGraphStore(store).load(project_id)
    approved_media = {
        str(node.get("metadata", {}).get("image_asset_id") or ""): node
        for node in graph.get("nodes", {}).values()
        if node.get("state") == "active"
        and node.get("metadata", {}).get("kind") == "approved_image"
    }
    total_bytes = 0
    result = []
    for raw_id in reference_media_ids:
        asset_id = _token(raw_id, "reference_media_id")
        if asset_id not in approved_media:
            raise ValueError("reference media must be approved in the same project ProductionGraph")
        try:
            metadata = image_asset_metadata(store, project_id, asset_id)
        except (KeyError, ValueError) as exc:
            raise ValueError("reference media metadata is missing or invalid") from exc
        if metadata.get("mime_type") not in {"image/png", "image/jpeg"}:
            raise ValueError("reference media format must be PNG or JPEG")
        if not metadata.get("sha256") or int(metadata.get("width") or 0) <= 0 or int(metadata.get("height") or 0) <= 0:
            raise ValueError("reference media digest and dimensions are required")
        byte_count = int(metadata.get("byte_count") or 0)
        if byte_count <= 0 or byte_count > 8 * 1024 * 1024:
            raise ValueError("reference media exceeds the per-file byte limit")
        total_bytes += byte_count
        result.append(
            {
                "image_asset_id": asset_id,
                "sha256": metadata["sha256"],
                "mime_type": metadata["mime_type"],
                "width": int(metadata["width"]),
                "height": int(metadata["height"]),
                "byte_count": byte_count,
            }
        )
    if total_bytes > 24 * 1024 * 1024:
        raise ValueError("reference media exceed the total byte limit")
    return result


def _source_contract(project_id: str, value: Any) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else {}
    bible = source.get("asset_bible") if isinstance(source.get("asset_bible"), Mapping) else {}
    if not bible:
        raise ValueError("image admission source requires Asset Bible state")
    candidate_set = bible.get("candidate_set") if isinstance(bible.get("candidate_set"), Mapping) else {}
    art_direction = _art_direction_contract(bible.get("art_direction"), require_complete=False)
    submitted_art_direction = _art_direction_contract(source.get("art_direction"), require_complete=False)
    if any(submitted_art_direction.get(field) for field in ("visual_style", "medium", "palette", "lighting")):
        if submitted_art_direction != art_direction:
            raise ValueError("image admission art direction must match the persisted Asset Bible truth")
    shot_grounding = _shot_grounding_contract(
        source.get("shot_grounding"),
        candidate_set=candidate_set,
    )
    return {
        "project_id": project_id,
        "authority_mode": str(source.get("authority_mode") or "legacy_studio_adapter"),
        "production_graph_version": int(source.get("production_graph_version") or 0),
        "production_graph_digest": str(source.get("production_graph_digest") or ""),
        "studio_state_version": str(source.get("studio_state_version") or ""),
        "asset_bible_revision_id": _token(
            bible.get("locked_revision_id") or bible.get("current_revision_id"),
            "asset_bible_revision_id",
        ),
        "candidate_set_id": _token(candidate_set.get("candidate_set_id"), "candidate_set_id"),
        "shot_candidate_id": _token(candidate_set.get("shot_candidate_id"), "shot_candidate_id"),
        "script_revision_id": _token(candidate_set.get("script_revision_id"), "script_revision_id"),
        "art_direction": art_direction,
        "shot_grounding": shot_grounding,
        "asset_bible": deepcopy(dict(bible)),
    }


def _source_traceability_contract(
    bible: Mapping[str, Any],
    candidate_set: Mapping[str, Any],
) -> dict[str, Any]:
    known_shot_ids = {
        str(item.get("shot_id") or "")
        for item in candidate_set.get("shot_index", [])
        if isinstance(item, Mapping) and item.get("shot_id")
    }
    traceable_shot_ids: set[str] = set()
    evidence_records = []
    for asset in bible.get("assets", []):
        if not isinstance(asset, Mapping) or asset.get("review_state") != "approved":
            continue
        asset_shot_ids, asset_records = authoritative_source_evidence(asset, known_shot_ids)
        traceable_shot_ids.update(asset_shot_ids)
        for evidence in asset_records:
            evidence_records.append(
                {
                    "asset_id": str(asset.get("stable_id") or ""),
                    **evidence,
                }
            )
    evidence_records.sort(
        key=lambda item: (
            item["asset_id"],
            item["source_type"],
            item["source_id"],
            item["scene_ids"],
            item["shot_ids"],
        )
    )
    missing = known_shot_ids - traceable_shot_ids
    return {
        "status": "complete" if known_shot_ids and not missing else "blocked",
        "shot_total": len(known_shot_ids),
        "traceable_shot_count": len(traceable_shot_ids),
        "missing_shot_count": len(missing),
        "evidence_record_count": len(evidence_records),
        "evidence_digest": canonical_digest(evidence_records),
    }


def _source_fingerprint_payload(source: Mapping[str, Any]) -> dict[str, Any]:
    bible = source["asset_bible"]
    return {
        "project_id": source["project_id"],
        "authority_mode": source["authority_mode"],
        "asset_bible_revision_id": source["asset_bible_revision_id"],
        "candidate_set_id": source["candidate_set_id"],
        "shot_candidate_id": source["shot_candidate_id"],
        "script_revision_id": source["script_revision_id"],
        "asset_digest": canonical_digest(bible.get("assets", [])),
        "coverage_digest": canonical_digest(bible.get("coverage", {})),
        "art_direction_digest": canonical_digest(source.get("art_direction", {})),
        "shot_grounding_digest": canonical_digest(source.get("shot_grounding", {})),
    }


def _assert_source_current(
    store: RuntimeStore,
    project_id: str,
    manifest: Mapping[str, Any],
    source_value: Any,
    *,
    command_type: str,
) -> None:
    if str(manifest.get("project_id") or "") != project_id:
        raise ValueError("image admission manifest project identity mismatch")
    source = _source_contract(project_id, source_value)
    fingerprint = canonical_digest(_source_fingerprint_payload(source))
    if fingerprint != manifest.get("source_fingerprint"):
        raise ValueError("image admission manifest source is stale; compile and review a new manifest")
    observed_graph = (
        int(source["production_graph_version"]),
        str(source["production_graph_digest"]),
    )
    accepted_graphs = {
        (int(item.get("version") or 0), str(item.get("graph_digest") or ""))
        for item in manifest.get("accepted_graph_snapshots", [])
        if isinstance(item, Mapping)
    }
    if command_type not in {
        "create_recovery_manifest",
        "create_next_batch_manifest",
        "inspect_next_batch",
    }:
        if observed_graph in accepted_graphs:
            return
        raise ValueError("image admission ProductionGraph source is stale; compile and review a new manifest")
    if not graph_path(store, project_id).is_file():
        if observed_graph == (0, "") and observed_graph in accepted_graphs:
            return
        raise ValueError("image admission continuation graph lineage is unavailable")
    try:
        current_graph = ProductionGraphStore(store).load(project_id)
    except ProductionGraphError as exc:
        raise ValueError("image admission continuation graph lineage is unavailable") from exc
    current_snapshot = (
        int(current_graph.get("version") or 0),
        str(current_graph.get("graph_digest") or ""),
    )
    if observed_graph != current_snapshot:
        raise ValueError("image admission continuation graph source is not the current project graph")
    if observed_graph in accepted_graphs:
        return
    accepted_versions = {version for version, _digest in accepted_graphs}
    if not accepted_versions or observed_graph[0] <= max(accepted_versions):
        raise ValueError("image admission continuation graph lineage is stale")


def _asset(value: Mapping[str, Any]) -> dict[str, Any]:
    occurrences = value.get("occurrences") if isinstance(value.get("occurrences"), Mapping) else {}
    asset_type = str(value.get("asset_type") or "")
    if asset_type not in {"character", "scene", "prop"}:
        raise ValueError("image admission supports character, scene, and prop assets")
    return {
        "stable_id": _token(value.get("stable_id"), "asset.stable_id"),
        "display_name": str(value.get("display_name") or "待确认资产")[:120],
        "aliases": sorted(
            {
                str(item).strip()[:120]
                for item in value.get("aliases", [])
                if str(item).strip()
            }
        ),
        "asset_type": asset_type,
        "importance": str(value.get("importance") or ""),
        "visual_identity": str(value.get("visual_identity") or "").strip()[:600],
        "positive_traits": [
            str(item).strip()[:160]
            for item in value.get("positive_traits", [])
            if str(item).strip()
        ][:24],
        "continuity_states": [
            {
                "state_id": str(item.get("state_id") or "")[:160],
                "label": str(item.get("label") or "").strip()[:160],
                "status": str(item.get("status") or "")[:40],
                "scene_ids": [
                    _token(scene_id, "continuity scene")
                    for scene_id in item.get("scene_ids", [])
                ],
                "shot_ids": [
                    _token(shot_id, "continuity shot")
                    for shot_id in item.get("shot_ids", [])
                ],
            }
            for item in value.get("continuity_states", [])
            if isinstance(item, Mapping) and str(item.get("label") or "").strip()
        ][:16],
        "pending_fields": sorted(
            {
                str(item).strip()[:80]
                for item in value.get("pending_fields", [])
                if str(item).strip()
            }
        ),
        "occurrences": {
            "scene_ids": sorted({_token(item, "scene occurrence") for item in occurrences.get("scene_ids", [])}),
            "shot_ids": sorted({_token(item, "shot occurrence") for item in occurrences.get("shot_ids", [])}),
        },
        "negative_locks": sorted({str(item)[:160] for item in value.get("negative_locks", []) if str(item).strip()}),
        "source_evidence": [
            deepcopy(item) for item in value.get("source_evidence", []) if isinstance(item, Mapping)
        ][:24],
    }


def _asset_item(
    asset: Mapping[str, Any],
    item_type: str,
    aspect: str,
    source_fingerprint: str,
    *,
    art_direction: Mapping[str, Any],
) -> dict[str, Any]:
    stable_id = str(asset["stable_id"])
    item = {
        "item_id": f"admit-{item_type}-{canonical_digest(stable_id)[:10]}",
        "item_type": item_type,
        "label": asset["display_name"],
        "target_asset_ids": [stable_id],
        "target_shot_id": "",
        "aspect_ratio": aspect,
        "size": ASPECT_SIZES[aspect],
        "candidate_count": 1,
        "negative_locks": asset["negative_locks"],
        "asset_grounding": _asset_grounding(asset),
        "source_evidence": asset["source_evidence"],
        "occurrence_references": deepcopy(asset["occurrences"]),
        "reference_asset_ids": [],
        "reference_media_ids": [],
        "source_fingerprint": source_fingerprint,
        "state": "planned",
    }
    item["prompt_contract"] = _prompt_contract(item, art_direction=art_direction)
    return item


def _keyframe_item(
    shot: Mapping[str, Any],
    role: str,
    reference_asset_ids: list[str],
    source_fingerprint: str,
    *,
    art_direction: Mapping[str, Any],
    reference_assets: list[Mapping[str, Any]],
    negative_locks: list[str],
) -> dict[str, Any]:
    shot_id = _token(shot.get("shot_id"), "shot_id")
    shot_grounding = _shot_item_grounding(shot)
    item = {
        "item_id": f"admit-shot-keyframe-{canonical_digest({'shot': shot_id, 'role': role})[:10]}",
        "item_type": "shot_keyframe",
        "label": str(shot.get("title") or f"镜头 {shot.get('number') or ''}")[:120],
        "keyframe_role": role,
        "target_asset_ids": [],
        "target_shot_id": shot_id,
        "aspect_ratio": "16:9",
        "size": ASPECT_SIZES["16:9"],
        "candidate_count": 1,
        "negative_locks": negative_locks,
        "shot_grounding": shot_grounding,
        "reference_asset_grounding": [
            _asset_grounding(asset)
            for asset in sorted(reference_assets, key=lambda value: str(value["stable_id"]))
        ],
        "source_evidence": [{"shot_id": shot_id, "scene_id": str(shot.get("scene_id") or "")}],
        "occurrence_references": {
            "scene_ids": [str(shot.get("scene_id") or "")],
            "shot_ids": [shot_id],
        },
        "reference_asset_ids": reference_asset_ids,
        "reference_media_ids": [],
        "source_fingerprint": source_fingerprint,
        "state": "planned",
    }
    item["prompt_contract"] = _prompt_contract(item, art_direction=art_direction)
    return item


def _assert_assets_creatively_ready(assets: list[Mapping[str, Any]]) -> None:
    if not assets:
        raise ValueError("image admission requires approved assets")
    blockers = []
    for asset in assets:
        pending = {
            str(item)
            for item in asset.get("pending_fields", [])
            if str(item) in {"positive_traits", "visual_identity", "continuity_state"}
        }
        continuity_ready = any(
            item.get("status") == "confirmed" and str(item.get("label") or "").strip()
            for item in asset.get("continuity_states", [])
            if isinstance(item, Mapping)
        )
        missing = []
        if "visual_identity" in pending or not str(asset.get("visual_identity") or "").strip():
            missing.append("视觉身份")
        if "positive_traits" in pending or not asset.get("positive_traits"):
            missing.append("正向视觉特征")
        if "continuity_state" in pending or not continuity_ready:
            missing.append("连续性状态")
        if missing:
            blockers.append(f"{asset.get('display_name') or '待确认资产'}：{'、'.join(missing)}")
    if blockers:
        raise ValueError("图片准入创意依据不完整：" + "；".join(blockers[:9]))


def _art_direction_contract(value: Any, *, require_complete: bool) -> dict[str, Any]:
    data = value if isinstance(value, Mapping) else {}
    labels = {
        "visual_style": "视觉风格",
        "medium": "媒介与质感",
        "palette": "色彩方案",
        "lighting": "光线规则",
    }
    result = {
        field: str(data.get(field) or "").strip()[:240]
        for field in labels
    }
    confirmed_at = str(data.get("confirmed_at") or "")[:80]
    result.update(
        {
            "status": "confirmed" if all(result.values()) and confirmed_at else "pending",
            "source": "human_review",
            "confirmed_at": confirmed_at,
        }
    )
    if require_complete and result["status"] != "confirmed":
        missing = [label for field, label in labels.items() if not result[field]]
        raise ValueError(
            "图片准入需要先审核并确认统一美术方向"
            + (f"：缺少{'、'.join(missing)}" if missing else "")
        )
    return result


def _shot_grounding_contract(value: Any, *, candidate_set: Mapping[str, Any]) -> dict[str, Any]:
    data = value if isinstance(value, Mapping) else {}
    known_scenes = {
        str(item.get("scene_id") or "")
        for item in candidate_set.get("scene_index", [])
        if isinstance(item, Mapping)
    }
    known_shots = {
        str(item.get("shot_id") or "")
        for item in candidate_set.get("shot_index", [])
        if isinstance(item, Mapping)
    }
    scenes = []
    for item in data.get("scenes", []):
        if not isinstance(item, Mapping):
            continue
        scene_id = _token(item.get("scene_id"), "shot grounding scene_id")
        if known_scenes and scene_id not in known_scenes:
            raise ValueError("shot grounding contains a scene outside the locked candidate set")
        scenes.append(
            {
                "scene_id": scene_id,
                "name": str(item.get("name") or item.get("title") or "")[:160],
                "number": int(item.get("number") or len(scenes) + 1),
                "description": str(item.get("description") or "")[:600],
            }
        )
    shots = []
    for item in data.get("shots", []):
        if not isinstance(item, Mapping):
            continue
        shot_id = _token(item.get("shot_id"), "shot grounding shot_id")
        scene_id = _token(item.get("scene_id"), "shot grounding shot scene_id")
        if known_shots and shot_id not in known_shots:
            raise ValueError("shot grounding contains a shot outside the locked candidate set")
        if known_scenes and scene_id not in known_scenes:
            raise ValueError("shot grounding shot belongs to an unknown scene")
        shots.append(_shot_item_grounding({**item, "shot_id": shot_id, "scene_id": scene_id}))
    if not scenes:
        scenes = [
            {
                "scene_id": _token(item.get("scene_id"), "candidate scene_id"),
                "name": str(item.get("name") or "")[:160],
                "number": int(item.get("number") or index + 1),
                "description": str(item.get("description") or "")[:600],
            }
            for index, item in enumerate(candidate_set.get("scene_index", []))
            if isinstance(item, Mapping)
        ]
    if not shots:
        shots = [
            _shot_item_grounding(item)
            for item in candidate_set.get("shot_index", [])
            if isinstance(item, Mapping)
        ]
    return {
        "scenes": sorted(scenes, key=lambda item: (item["number"], item["scene_id"])),
        "shots": sorted(shots, key=lambda item: (item["number"], item["shot_id"])),
    }


def _shot_item_grounding(shot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "shot_id": _token(shot.get("shot_id"), "shot_id"),
        "scene_id": _token(shot.get("scene_id"), "shot scene_id"),
        "number": int(shot.get("number") or 0),
        "title": str(shot.get("title") or "")[:160],
        "purpose": str(shot.get("purpose") or shot.get("narrative_purpose") or "")[:400],
        "shot_size": str(shot.get("shot_size") or "")[:80],
        "composition": str(shot.get("composition") or "")[:240],
        "camera_angle": str(shot.get("camera_angle") or "")[:160],
        "movement": str(shot.get("movement") or shot.get("camera_motion") or "")[:240],
        "action": str(shot.get("action") or shot.get("description") or "")[:400],
        "dialogue": str(shot.get("dialogue") or "")[:400],
        "emotion": str(shot.get("emotion") or "")[:240],
        "continuity_cues": [
            str(item).strip()[:160]
            for item in shot.get("continuity_cues", [])
            if str(item).strip()
        ][:16],
    }


def _asset_grounding(asset: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stable_id": asset["stable_id"],
        "display_name": asset["display_name"],
        "asset_type": asset["asset_type"],
        "aliases": list(asset.get("aliases", [])),
        "visual_identity": asset["visual_identity"],
        "positive_traits": list(asset["positive_traits"]),
        "continuity_states": deepcopy(asset["continuity_states"]),
        "negative_locks": list(asset["negative_locks"]),
        "pending_fields": list(asset["pending_fields"]),
        "source_evidence": deepcopy(asset["source_evidence"]),
        "occurrences": deepcopy(asset["occurrences"]),
    }


def _prompt_contract(item: Mapping[str, Any], *, art_direction: Mapping[str, Any]) -> dict[str, Any]:
    grounding = item.get("asset_grounding") if isinstance(item.get("asset_grounding"), Mapping) else {}
    references = [
        value for value in item.get("reference_asset_grounding", []) if isinstance(value, Mapping)
    ]
    shot = item.get("shot_grounding") if isinstance(item.get("shot_grounding"), Mapping) else {}
    item_type_label = {
        "character_design": "角色设定",
        "scene_plate": "场景净板",
        "prop_design": "核心道具",
        "shot_keyframe": "镜头关键帧",
    }.get(str(item.get("item_type") or ""), "图片项目")
    sections = [
        ("生成目标", f"{item['label']}（{item_type_label}），独立单图，尺寸 {item['size']}。"),
        (
            "统一美术方向",
            "；".join(
                [
                    f"视觉风格：{art_direction['visual_style']}",
                    f"媒介与质感：{art_direction['medium']}",
                    f"色彩方案：{art_direction['palette']}",
                    f"光线规则：{art_direction['lighting']}",
                ]
            ),
        ),
    ]
    if grounding:
        sections.extend(
            [
                (
                    "资产身份",
                    "；".join(
                        [
                            f"名称：{grounding['display_name']}",
                            f"别名：{'、'.join(grounding['aliases']) or '无'}",
                            f"视觉身份：{grounding['visual_identity']}",
                            f"正向特征：{'、'.join(grounding['positive_traits'])}",
                        ]
                    ),
                ),
                (
                    "保持一致",
                    "；".join(
                        item["label"]
                        for item in grounding["continuity_states"]
                        if item.get("status") == "confirmed"
                    ),
                ),
            ]
        )
    if shot:
        sections.append(
            (
                "镜头依据",
                "；".join(
                    [
                        f"镜头：{shot['title'] or '未提供'}",
                        f"叙事目的：{shot['purpose'] or '未提供'}",
                        f"景别：{shot['shot_size'] or '未提供'}",
                        f"构图：{shot['composition'] or '未提供'}",
                        f"机位：{shot['camera_angle'] or '未提供'}",
                        f"运动：{shot['movement'] or '未提供'}",
                        f"动作：{shot['action'] or '未提供'}",
                        f"对白：{shot['dialogue'] or '未提供'}",
                        f"情绪：{shot['emotion'] or '未提供'}",
                        f"连续性提示：{'、'.join(shot['continuity_cues']) or '未提供'}",
                    ]
                ),
            )
        )
    if references:
        sections.append(
            (
                "引用资产",
                "；".join(
                    f"{ref['display_name']}：{ref['visual_identity']}；正向特征{'、'.join(ref['positive_traits'])}；"
                    f"连续性{'、'.join(state['label'] for state in ref['continuity_states'] if state.get('status') == 'confirmed')}"
                    for ref in references
                ),
            )
        )
    sections.append(
        (
            "禁止项",
            "；".join(_localized_negative_lock(value) for value in item.get("negative_locks", []))
            or "无额外禁止项",
        )
    )
    provider_prompt = "\n".join(f"【{title}】{content}" for title, content in sections)
    return {
        "schema_version": PROMPT_CONTRACT_VERSION,
        "art_direction": deepcopy(dict(art_direction)),
        "sections": [{"title": title, "content": content} for title, content in sections],
        "provider_prompt": provider_prompt,
        "provider_prompt_digest": canonical_digest(provider_prompt),
    }


def _localized_negative_lock(value: Any) -> str:
    raw = str(value or "").strip()
    return {
        "no text, captions, watermarks, interface elements, or borders": "禁止添加文字、水印、界面元素或边框",
        "do not add text/watermark/ui/borders": "禁止添加文字、水印、界面元素或边框",
        "do not change character identity": "禁止改变角色身份",
        "do not change identity": "禁止改变角色身份",
        "do not add unrequested characters": "禁止添加未要求的角色",
        "do not add chairs or stools unless approved": "未经确认，禁止添加椅子或凳子",
        "do not add eaves unless approved": "未经确认，禁止添加屋檐元素",
        "do not add unrequested set pieces": "禁止添加未要求的场景陈设",
        "do not change prop function": "禁止改变道具功能",
        "do not duplicate the prop unless scripted": "剧本未要求时，禁止复制该道具",
        "do not move to a different location": "禁止移动到其他场景",
    }.get(raw.lower(), raw)


def _assert_manifest_creative_ready(manifest: Mapping[str, Any]) -> None:
    _art_direction_contract(manifest.get("art_direction"), require_complete=True)
    persisted_budget = (
        manifest.get("budget_contract")
        if isinstance(manifest.get("budget_contract"), Mapping)
        else {}
    )
    current_budget = budget_contract(int(persisted_budget.get("max_dispatches") or 1))
    budget_fields = (
        "currency",
        "unit_estimate_usd",
        "max_dispatches",
        "max_estimated_usd",
        "program_max_usd",
        "concurrency",
        "candidate_count",
        "auto_retry",
    )
    if any(persisted_budget.get(field) != current_budget[field] for field in budget_fields):
        raise ValueError("图片清单费用合同已更新，请重新预览清单")
    items = manifest.get("items", [])
    if not items:
        raise ValueError("image admission creative grounding requires at least one item")
    for item in items:
        prompt = item.get("prompt_contract") if isinstance(item.get("prompt_contract"), Mapping) else {}
        provider_prompt = str(prompt.get("provider_prompt") or "")
        if (
            prompt.get("schema_version") != PROMPT_CONTRACT_VERSION
            or not provider_prompt
            or canonical_digest(provider_prompt) != prompt.get("provider_prompt_digest")
            or item.get("source_fingerprint") != manifest.get("source_fingerprint")
        ):
            raise ValueError("image admission creative grounding is incomplete or stale")
        if item.get("item_type") == "shot_keyframe":
            if not item.get("shot_grounding") or not item.get("reference_asset_grounding"):
                raise ValueError("keyframe creative grounding requires shot facts and approved asset references")
def _shot_reference_count(assets: list[Mapping[str, Any]], shot_id: str) -> int:
    return sum(shot_id in item["occurrences"]["shot_ids"] for item in assets)


def _manifest_item(manifest: Mapping[str, Any], item_id: Any) -> dict[str, Any]:
    token = _token(item_id, "item_id")
    item = next((item for item in manifest.get("items", []) if item.get("item_id") == token), None)
    if not item:
        raise ValueError("image admission item was not found")
    return item


def _append_receipt(
    manifest: dict[str, Any],
    item: Mapping[str, Any],
    state: str,
    command: Mapping[str, Any],
    *,
    recorded_at: str | None = None,
) -> None:
    candidate = item.get("candidate") if isinstance(item.get("candidate"), Mapping) else {}
    receipt = {
        "receipt_id": f"image-admission-receipt-{canonical_digest({'manifest': manifest['manifest_id'], 'item': item.get('item_id'), 'state': state, 'count': len(manifest.get('receipts', []))})[:16]}",
        "manifest_id": manifest["manifest_id"],
        "manifest_hash": manifest["manifest_hash"],
        "item_id": item.get("item_id"),
        "idempotency_key": str(command.get("idempotency_key") or ""),
        "command_digest": _command_semantic_digest(command),
        "provider": "api_relay",
        "service_id": SERVICE_ID,
        "model": MODEL_ID,
        "provider_job_id": item.get("provider_job_id"),
        "dispatch_ordinal": item.get("dispatch_ordinal"),
        "estimated_usd": (
            manifest["budget_contract"]["unit_estimate_usd"]
            if item.get("dispatch_ordinal")
            else "0.0000"
        ),
        "actual_usd": None,
        "billing_verification_state": "unverified",
        "input_digest": item.get("source_fingerprint"),
        "source_digest": manifest.get("source_fingerprint"),
        "output_sha256": candidate.get("sha256"),
        "format": candidate.get("format"),
        "width": candidate.get("width"),
        "height": candidate.get("height"),
        "candidate_revision": len(
            [receipt for receipt in manifest.get("receipts", []) if receipt.get("item_id") == item.get("item_id")]
        )
        + 1,
        "candidate_promotion_revision": None,
        "state": state,
        "recorded_at": recorded_at or _now(),
        "error_category": str(command.get("error_category") or ""),
        "cancel_semantics": manifest.get("cancel_semantics"),
        "provider_raw_response_stored": False,
    }
    manifest.setdefault("receipts", []).append(receipt)


def _impact(before: Mapping[str, Any], after: Mapping[str, Any], command: Mapping[str, Any]) -> dict[str, Any]:
    before_states = {item.get("item_id"): item.get("state") for item in before.get("items", [])}
    changed = [
        item["item_id"]
        for item in after.get("items", [])
        if before_states.get(item["item_id"]) != item.get("state")
    ]
    impact = {
        "item_ids": changed or [item["item_id"] for item in after.get("items", [])],
        "item_count": len(after.get("items", [])),
        "manifest_status_before": before.get("status", "empty"),
        "manifest_status_after": after.get("status", "empty"),
        "dispatches_reserved_before": int(before.get("budget", {}).get("dispatches_reserved") or 0),
        "dispatches_reserved_after": int(after.get("budget", {}).get("dispatches_reserved") or 0),
        "graph_mutation_before_confirm": 0,
        "provider_calls_before_confirm": 0,
        "preserved_on_cancel": True,
        "command_type": command["type"],
    }
    if command["type"] == "create_recovery_manifest":
        impact["recovery_manifest"] = {
            "creates_new_manifest": True,
            "previous_manifest_preserved_on_confirm": True,
            "selected_item_count": 1,
            "previous_dispatches_preserved": int(
                before.get("budget", {}).get("dispatches_reserved") or 0
            ),
            "previous_estimated_reserved_usd": str(
                before.get("budget", {}).get("estimated_reserved_usd") or "0.0000"
            ),
            "new_max_dispatches": int(
                after.get("budget_contract", {}).get("max_dispatches") or 0
            ),
            "new_max_estimated_usd": str(
                after.get("budget_contract", {}).get("max_estimated_usd") or "0.0000"
            ),
            "auto_retry": int(after.get("budget_contract", {}).get("auto_retry") or 0),
            "provider_calls_before_confirm": 0,
            "requires_separate_generation_confirmation": True,
        }
    if command["type"] == "create_next_batch_manifest":
        impact["next_batch_manifest"] = {
            "creates_new_manifest": True,
            "previous_manifest_preserved_on_confirm": True,
            "selected_items": [
                {
                    "label": str(item.get("label") or ""),
                    "item_type": str(item.get("item_type") or ""),
                    "reference_media_count": len(item.get("reference_media_ids") or []),
                }
                for item in after.get("items", [])
            ],
            "selected_item_count": len(after.get("items", [])),
            "previous_dispatches_preserved": int(
                before.get("budget", {}).get("dispatches_reserved") or 0
            ),
            "new_max_dispatches": int(
                after.get("budget_contract", {}).get("max_dispatches") or 0
            ),
            "new_max_estimated_usd": str(
                after.get("budget_contract", {}).get("max_estimated_usd") or "0.0000"
            ),
            "auto_retry": int(after.get("budget_contract", {}).get("auto_retry") or 0),
            "provider_calls_before_confirm": 0,
            "requires_separate_generation_confirmation": True,
        }
    return impact


def _safe_command(value: Any) -> dict[str, Any]:
    command = value if isinstance(value, Mapping) else {}
    command_type = str(command.get("type") or "")
    if command_type not in COMMANDS:
        raise ValueError("unsupported image admission command")
    allowed = {
        "type",
        "item_id",
        "idempotency_key",
        "candidate",
        "fixture",
        "reason",
        "error_category",
        "provider_job_id",
        "source_manifest_id",
        "item_ids",
    }
    return {key: deepcopy(value) for key, value in command.items() if key in allowed}


def _idempotent_receipt(manifest: Mapping[str, Any], command_value: Any) -> dict[str, Any]:
    if not manifest:
        return {}
    command = _safe_command(command_value)
    key = str(command.get("idempotency_key") or "")
    if not key:
        return {}
    item_id = str(command.get("item_id") or ("manifest" if command["type"] in {"compile", "lock"} else "batch"))
    receipt = next(
        (
            receipt
            for receipt in manifest.get("receipts", [])
            if receipt.get("idempotency_key") == key and receipt.get("item_id") == item_id
        ),
        None,
    )
    if not receipt:
        return {}
    if receipt.get("command_digest") != _command_semantic_digest(command):
        raise ValueError("image admission idempotency key conflicts with another command")
    return deepcopy(receipt)


def _command_semantic_digest(command_value: Any) -> str:
    command = _safe_command(command_value)
    return canonical_digest(
        {
            key: value
            for key, value in command.items()
            if key != "idempotency_key"
        }
    )


def _manifest_path(store: RuntimeStore, project_id: str):
    return store.projects_dir / safe_id(project_id) / "image_admission" / "manifest.json"


def _archive_manifest_once(
    store: RuntimeStore,
    project_id: str,
    manifest: Mapping[str, Any],
) -> None:
    manifest_id = safe_id(str(manifest.get("manifest_id") or ""))
    path = (
        store.projects_dir
        / safe_id(project_id)
        / "image_admission"
        / "history"
        / f"{manifest_id}.json"
    )
    if path.is_file():
        archived = read_json(path)
        reject_unsafe_payload(archived)
        if canonical_digest(archived) != canonical_digest(manifest):
            raise ValueError("archived image manifest conflicts with the immutable source ledger")
        return
    reject_unsafe_payload(manifest)
    write_json(path, deepcopy(manifest))


def _money_env(name: str, default: str) -> Decimal:
    try:
        return Decimal(os.getenv(name, default))
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a decimal amount") from exc


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001")))


def _gate_open() -> bool:
    return os.getenv("AFS_ALLOW_REMOTE_IMAGE", "").strip().lower() in TRUE_VALUES


def _fixture_mode() -> bool:
    return os.getenv("AFS_ALLOW_DETERMINISTIC_MEDIA_FIXTURES", "").strip().lower() in TRUE_VALUES


def _token(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    if not raw or safe_id(raw) != raw:
        raise ValueError(f"{field} is required and must be a stable id")
    return raw


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _requested_at(body: Mapping[str, Any]) -> str:
    raw = str(body.get("requested_at") or "").strip()
    if not raw:
        return "1970-01-01T00:00:00+00:00"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("requested_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


__all__ = (
    "SCHEMA_VERSION",
    "budget_contract",
    "compile_image_admission_manifest",
    "enforce_image_admission_keyframe_request",
    "image_admission_capability",
    "load_image_admission_manifest",
    "preview_image_admission_command",
    "register_runtime_image_admission_routes",
    "validate_image_admission_reservation",
)
