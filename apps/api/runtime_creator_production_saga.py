from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from agentflow.harness.json_io import exclusive_file_lock
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_episode_domain_contract import (
    SAFE_ID,
    EntityVersionRef,
    ProductionProjectAggregate,
    TenantScope,
)
from apps.api.runtime_episode_domain_routes import _require_project_scope
from apps.api.runtime_episode_domain_store import (
    EpisodeDomainAggregateStore,
    EpisodeDomainStoreError,
)
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_creator_production_integration import (
    CreatorProductionControlError,
    apply_creator_preview_episode_candidate,
    confirm_creator_preview_control_run,
    prepare_creator_preview_control_plan,
    read_creator_preview_control_projection,
    record_creator_preview_control_writeback,
)
from apps.api.runtime_store import RuntimeStore, safe_id


SAGA_SCHEMA_VERSION = "afs.creator-production-writeback-saga.v0.1"
_SAFE_ID_RE = re.compile(SAFE_ID, re.ASCII)
_STAMP = "2026-07-16T00:00:00+00:00"
_TERMINAL_PHASES = {"confirmed", "failed", "cancelled"}

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=160, pattern=SAFE_ID),
]


class CreatorProductionSagaError(RuntimeError):
    pass


class SagaIntegrityError(CreatorProductionSagaError):
    pass


class SagaConflictError(CreatorProductionSagaError):
    pass


class SagaRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreatorProductionRequest(SagaRequestModel):
    expected_aggregate_version: int = Field(ge=1, strict=True)
    episode_ref: EntityVersionRef
    shot_ref: EntityVersionRef
    scope: Literal["production_preview"] = "production_preview"
    expected_versions: dict[str, str] = Field(default_factory=dict, max_length=16)
    created_at: str = Field(default=_STAMP, min_length=1, max_length=64)
    crash_after: Literal[
        "none",
        "prepared",
        "control_applied",
        "artifact_prepared",
        "episode_applied",
        "before_confirmed",
        "confirmed",
    ] = "none"


def register_runtime_creator_production_saga_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    @app.post("/projects/{project_id}/creator-production-requests")
    def create_creator_production_request(
        project_id: str,
        body: CreatorProductionRequest,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        scope = _require_project_scope(store, auth, request, project_id)
        crash_after = _crash_after(request, body.crash_after)
        try:
            result = _execute_or_reconcile(
                store,
                scope=scope,
                request_body=body,
                idempotency_key=idempotency_key,
                crash_after=crash_after,
                require_new_or_same=True,
            )
        except _InjectedCrash as exc:
            _raise_saga_error(
                project_id,
                status_code=500,
                error="creator_production_injected_crash",
                message="Injected crash after durable saga phase.",
                stage=exc.phase,
                retryable=True,
                cause=exc,
            )
        except SagaConflictError as exc:
            _raise_saga_error(
                project_id,
                status_code=409,
                error=str(exc) or "creator_production_conflict",
                message="制作请求与当前镜头版本不一致，请刷新后重试。",
                stage="creator_production_request",
                retryable=True,
                cause=exc,
            )
        except SagaIntegrityError as exc:
            _raise_saga_error(
                project_id,
                status_code=500,
                error="creator_production_saga_integrity_failed",
                message="制作请求恢复记录校验失败，已停止处理。",
                stage="creator_production_recover",
                cause=exc,
            )
        except CreatorProductionControlError as exc:
            _raise_saga_error(
                project_id,
                status_code=409,
                error="creator_production_control_conflict",
                message="制作控制记录未能确认，候选不会写入工作区。",
                stage="creator_production_control",
                retryable=True,
                cause=exc,
            )
        except EpisodeDomainStoreError as exc:
            _raise_saga_error(
                project_id,
                status_code=409,
                error="creator_production_episode_conflict",
                message="Episode事实链已变化，制作候选未确认写回。",
                stage="creator_production_episode",
                retryable=True,
                cause=exc,
            )
        return result

    @app.post("/projects/{project_id}/creator-production-requests/reconcile")
    def reconcile_creator_production_requests(project_id: str, request: Request) -> dict[str, Any]:
        scope = _require_project_scope(store, auth, request, project_id)
        try:
            return {"requests": reconcile_creator_production_request_envelopes(store, scope=scope)}
        except SagaIntegrityError as exc:
            _raise_saga_error(
                project_id,
                status_code=500,
                error="creator_production_saga_integrity_failed",
                message="制作请求恢复记录校验失败，已停止处理。",
                stage="creator_production_recover",
                cause=exc,
            )

    @app.get("/projects/{project_id}/creator-production-requests")
    def list_creator_production_requests(project_id: str, request: Request) -> dict[str, Any]:
        scope = _require_project_scope(store, auth, request, project_id)
        try:
            return {"requests": reconcile_creator_production_request_envelopes(store, scope=scope)}
        except SagaIntegrityError as exc:
            _raise_saga_error(
                project_id,
                status_code=500,
                error="creator_production_saga_integrity_failed",
                message="制作请求恢复记录校验失败，已停止处理。",
                stage="creator_production_recover",
                cause=exc,
            )


def reconcile_creator_production_request_envelopes(
    store: RuntimeStore,
    *,
    scope: TenantScope,
) -> list[dict[str, Any]]:
    path = _saga_path(store, scope.project_id)
    lock_path = _lock_path(path)
    with exclusive_file_lock(lock_path):
        payload = _load_saga_file(path, scope=scope)
        changed = False
        for envelope in payload["envelopes"]:
            if envelope["phase"] in _TERMINAL_PHASES:
                continue
            try:
                _advance_envelope(store, scope, envelope, crash_after="none")
                changed = True
            except (CreatorProductionControlError, EpisodeDomainStoreError, SagaConflictError) as exc:
                envelope["phase"] = "failed"
                envelope["status"] = "failed"
                envelope["creator_status_label"] = "制作失败"
                envelope["failure"] = _safe_failure(str(exc) or type(exc).__name__)
                _seal_current_phase(envelope)
                changed = True
        if changed:
            _write_saga_file(path, payload, scope=scope)
        return [_public_envelope(item) for item in payload["envelopes"]]


def overlay_creator_production_requests(
    projection: dict[str, Any],
    store: RuntimeStore,
    *,
    scope: TenantScope,
) -> dict[str, Any]:
    requests = reconcile_creator_production_request_envelopes(store, scope=scope)
    by_shot: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in requests:
        ref = item["shot_ref"]
        by_shot.setdefault((ref["entity_type"], ref["entity_id"], ref["version_id"]), []).append(item)
    for shot in projection.get("workspace", {}).get("shots", []):
        ref = shot.get("ref") or {}
        rows = by_shot.get((ref.get("entity_type"), ref.get("entity_id"), ref.get("version_id")), [])
        shot["production_requests"] = rows
        shot["production_request"] = rows[-1] if rows else None
        actions = shot.setdefault("allowed_actions", [])
        actions.append(_production_action_for_request(rows[-1] if rows else None))
    projection.setdefault("workspace", {})["creator_production"] = {
        "requests": requests,
        "provider_dispatch_count": 0,
    }
    return projection


def join_creator_production_authoring_projection(
    projection: dict[str, Any],
    store: RuntimeStore,
    *,
    scope: TenantScope,
) -> dict[str, Any]:
    requests = reconcile_creator_production_request_envelopes(store, scope=scope)
    by_shot: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in requests:
        ref = item["shot_ref"]
        by_shot.setdefault((ref["entity_type"], ref["entity_id"], ref["version_id"]), []).append(item)
    for shot in projection.get("shots", []):
        ref = shot.get("ref") or {}
        rows = by_shot.get((ref.get("entity_type"), ref.get("entity_id"), ref.get("version_id")), [])
        current = rows[-1] if rows else None
        shot["production_requests"] = rows
        shot["production_request"] = current
        shot["production_status"] = current["status"] if current else "queued"
        shot["production_status_label"] = current["status_label"] if current else "尚未创建"
        action = _production_action_for_request(current)
        shot["allowed_actions"] = [
            *(shot.get("allowed_actions") or []),
            action,
        ]
    control_projection = read_creator_preview_control_projection(store, scope=scope)
    projection["creator_production"] = {
        "requests": requests,
        "control": control_projection,
        "provider_dispatch_count": control_projection["provider_dispatch_count"],
    }
    return projection


def _production_action_for_request(current: dict[str, Any] | None) -> dict[str, Any]:
    if current is None:
        return {
            "action": "create_production_preview",
            "enabled": True,
            "reason": "",
            "blocked_by": [],
        }
    status = current.get("status")
    if status == "failed":
        return {
            "action": "create_production_preview",
            "enabled": True,
            "reason": "上次制作失败，可重新创建。",
            "blocked_by": [],
        }
    if status == "done":
        candidate = current.get("candidate_ref")
        return {
            "action": "create_production_preview",
            "enabled": False,
            "reason": "已有候选等待审核。",
            "blocked_by": [candidate] if candidate else [],
        }
    if status == "blocked":
        return {
            "action": "create_production_preview",
            "enabled": False,
            "reason": "制作记录需要先由服务恢复。",
            "blocked_by": [],
        }
    return {
        "action": "create_production_preview",
        "enabled": False,
        "reason": "制作任务正在处理。",
        "blocked_by": [],
    }


def _execute_or_reconcile(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    request_body: CreatorProductionRequest,
    idempotency_key: str,
    crash_after: str,
    require_new_or_same: bool,
) -> dict[str, Any]:
    path = _saga_path(store, scope.project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_digest = _digest(_request_intent(request_body))
    with exclusive_file_lock(_lock_path(path)):
        payload = _load_saga_file(path, scope=scope)
        existing_key = payload["idempotency"].get(idempotency_key)
        if existing_key is not None:
            envelope = _find_envelope(payload, existing_key)
            if envelope["payload_digest"] != payload_digest:
                raise SagaConflictError("creator_production_idempotency_conflict")
        else:
            if not require_new_or_same:
                raise SagaConflictError("creator_production_request_missing")
            envelope = _prepare_envelope(
                store,
                scope=scope,
                body=request_body,
                idempotency_key=idempotency_key,
                payload_digest=payload_digest,
            )
            payload["envelopes"].append(envelope)
            payload["idempotency"][idempotency_key] = envelope["saga_id"]
            _write_saga_file(path, payload, scope=scope)
            _crash_if(crash_after, "prepared")
        def persist() -> None:
            _write_saga_file(path, payload, scope=scope)

        _advance_envelope(store, scope, envelope, crash_after=crash_after, persist=persist)
        _write_saga_file(path, payload, scope=scope)
        return {"request": _public_envelope(envelope)}


def _prepare_envelope(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    body: CreatorProductionRequest,
    idempotency_key: str,
    payload_digest: str,
) -> dict[str, Any]:
    aggregate = EpisodeDomainAggregateStore(store.root).load(
        org_id=scope.org_id,
        project_id=scope.project_id,
    )
    if aggregate.scope != scope:
        raise SagaConflictError("creator_production_scope_mismatch")
    if aggregate.aggregate_version != body.expected_aggregate_version:
        raise SagaConflictError("creator_production_stale_aggregate")
    shot = _exact_latest_shot(aggregate, body.shot_ref)
    _exact_latest_episode_contains_shot(aggregate, body.episode_ref, shot.as_ref())
    for key, version_id in body.expected_versions.items():
        if key == "shot" and version_id != shot.version_id:
            raise SagaConflictError("creator_production_stale_shot_version")
        if key == "episode" and version_id != body.episode_ref.version_id:
            raise SagaConflictError("creator_production_stale_episode_version")
    token = _digest({"key": idempotency_key, "payload": payload_digest})[:24]
    candidate_ref = EntityVersionRef(
        entity_type="asset_candidate",
        entity_id=f"candidate-{token}",
        version_id=f"candidate-{token}-v1",
    )
    envelope = {
        "saga_id": f"saga-{token}",
        "phase": "prepared",
        "status": "queued",
        "creator_status_label": "已排队",
        "payload_digest": payload_digest,
        "idempotency_key": idempotency_key,
        "created_at": _safe_stamp(body.created_at),
        "expected_aggregate_version": body.expected_aggregate_version,
        "episode_ref": body.episode_ref.model_dump(mode="json"),
        "shot_ref": shot.as_ref().model_dump(mode="json"),
        "protected_refs": [
            ref.model_dump(mode="json")
            for ref in _episode_shot_refs(aggregate, body.episode_ref)
            if ref != shot.as_ref()
        ],
        "control": {
            "plan": prepare_creator_preview_control_plan(store, scope=scope),
            "task": None,
            "run": None,
            "attempt": None,
            "registration_ref": None,
            "writeback_ref": None,
            "receipts": [],
            "control_receipt": None,
            "completion_receipt": None,
            "projection_digest": "",
            "event_count": 0,
            "next_expected_version": None,
        },
        "artifact": None,
        "candidate_ref": candidate_ref.model_dump(mode="json"),
        "episode": None,
        "failure": None,
        "phase_checksums": {},
        "provider_dispatch_count": 0,
    }
    _seal_current_phase(envelope)
    return envelope


def _advance_envelope(
    store: RuntimeStore,
    scope: TenantScope,
    envelope: dict[str, Any],
    *,
    crash_after: str,
    persist: Any | None = None,
) -> None:
    if envelope["phase"] == "prepared":
        manifest = _artifact_manifest(envelope)
        envelope["artifact"] = {
            "artifact_id": manifest["artifact_id"],
            "artifact_type": "production_preview_manifest",
            "content_digest": _digest(manifest),
            "manifest": manifest,
        }
        envelope["phase"] = "artifact_prepared"
        envelope["status"] = "running"
        envelope["creator_status_label"] = "正在生成候选"
        _seal_current_phase(envelope)
        if persist is not None:
            persist()
        _crash_if(crash_after, "artifact_prepared")
    if envelope["phase"] == "artifact_prepared":
        control = record_creator_preview_control_writeback(
            store,
            scope=scope,
            control_plan=envelope["control"]["plan"],
            idempotency_key=envelope["idempotency_key"],
            target_ref=EntityVersionRef.model_validate(envelope["shot_ref"]),
            protected_refs=tuple(
                EntityVersionRef.model_validate(item)
                for item in envelope.get("protected_refs", ())
            ),
            artifact_id=envelope["artifact"]["artifact_id"],
            artifact_digest=envelope["artifact"]["content_digest"],
            candidate_ref=EntityVersionRef.model_validate(envelope["candidate_ref"]),
            created_at=envelope["created_at"],
        )
        envelope["control"].update(control)
        envelope["phase"] = "control_applied"
        envelope["status"] = "running"
        envelope["creator_status_label"] = "已记录，正在写回"
        _seal_current_phase(envelope)
        if persist is not None:
            persist()
        _crash_if(crash_after, "control_applied")
    if envelope["phase"] == "control_applied":
        applied = apply_creator_preview_episode_candidate(
            store,
            scope=scope,
            control=envelope["control"],
            idempotency_key=envelope["idempotency_key"],
            created_at=envelope["created_at"],
        )
        envelope["episode"] = applied
        envelope["phase"] = "episode_applied"
        envelope["status"] = "running"
        envelope["creator_status_label"] = "候选已写回"
        _seal_current_phase(envelope)
        if persist is not None:
            persist()
        _crash_if(crash_after, "episode_applied")
        _crash_if(crash_after, "before_confirmed")
    if envelope["phase"] == "episode_applied":
        completed = confirm_creator_preview_control_run(
            store,
            scope=scope,
            control=envelope["control"],
            idempotency_key=envelope["idempotency_key"],
        )
        envelope["control"]["completion_receipt"] = completed["receipt"]
        envelope["control"]["projection_digest"] = completed["projection_digest"]
        envelope["control"]["event_count"] = completed["event_count"]
        envelope["control"]["provider_dispatch_count"] = completed["provider_dispatch_count"]
        envelope["phase"] = "confirmed"
        envelope["status"] = "done"
        envelope["creator_status_label"] = "候选待审核"
        envelope["control"]["task"]["state"] = "completed"
        envelope["control"]["run"]["state"] = "completed"
        envelope["control"]["attempt"]["state"] = "completed"
        _seal_current_phase(envelope)
        if persist is not None:
            persist()
        _crash_if(crash_after, "confirmed")


def _load_saga_file(path: Path, *, scope: TenantScope) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": SAGA_SCHEMA_VERSION,
            "scope": {"org_id": scope.org_id, "project_id": scope.project_id},
            "idempotency": {},
            "envelopes": [],
        }
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SagaIntegrityError("creator production saga envelope is unreadable") from exc
    if not isinstance(envelope, dict):
        raise SagaIntegrityError("creator production saga envelope must be an object")
    checksum = envelope.get("envelope_sha256")
    body = {key: value for key, value in envelope.items() if key != "envelope_sha256"}
    if envelope.get("schema_version") != SAGA_SCHEMA_VERSION or _digest(body) != checksum:
        raise SagaIntegrityError("creator production saga checksum does not match")
    if envelope.get("scope") != {"org_id": scope.org_id, "project_id": scope.project_id}:
        raise SagaIntegrityError("creator production saga scope does not match")
    if not isinstance(envelope.get("idempotency"), dict) or not isinstance(envelope.get("envelopes"), list):
        raise SagaIntegrityError("creator production saga shape is invalid")
    for key, saga_id in envelope["idempotency"].items():
        if _SAFE_ID_RE.fullmatch(str(key)) is None or _SAFE_ID_RE.fullmatch(str(saga_id)) is None:
            raise SagaIntegrityError("creator production saga idempotency index is invalid")
        _find_envelope(envelope, str(saga_id))
    for item in envelope["envelopes"]:
        _validate_current_phase_checksum(item)
    return body


def _write_saga_file(path: Path, payload: dict[str, Any], *, scope: TenantScope) -> None:
    payload = {
        "schema_version": SAGA_SCHEMA_VERSION,
        "scope": {"org_id": scope.org_id, "project_id": scope.project_id},
        "idempotency": dict(sorted(payload["idempotency"].items())),
        "envelopes": sorted(payload["envelopes"], key=lambda item: item["saga_id"]),
    }
    envelope = {**payload, "envelope_sha256": _digest(payload)}
    text = json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        _fsync_directory(path.parent)
    finally:
        temp_path.unlink(missing_ok=True)


def _public_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    control = envelope.get("control") or {}
    receipt = None
    if envelope["phase"] == "confirmed":
        receipt = {
            "receipt_id": _digest(
                {
                    "control": control.get("control_receipt"),
                    "completion": control.get("completion_receipt"),
                    "episode": envelope.get("episode"),
                }
            ),
            "control_receipt": control.get("control_receipt"),
            "completion_receipt": control.get("completion_receipt"),
            "episode_receipt": envelope.get("episode"),
            "writeback_ref": control.get("writeback_ref"),
            "candidate_ref": envelope.get("candidate_ref"),
            "episode_confirmed": True,
        }
    return {
        "request_id": envelope["saga_id"],
        "status": envelope["status"],
        "status_label": envelope["creator_status_label"],
        "phase": envelope["phase"],
        "task": control.get("task"),
        "run": control.get("run"),
        "attempt": control.get("attempt"),
        "shot_ref": envelope["shot_ref"],
        "episode_ref": envelope["episode_ref"],
        "candidate_ref": envelope["candidate_ref"] if envelope["phase"] == "confirmed" else None,
        "control": {
            "event_count": control.get("event_count", 0),
            "projection_digest": control.get("projection_digest", ""),
            "writeback_ref": control.get("writeback_ref"),
            "recorded": bool(control.get("writeback_ref")),
        },
        "receipt": receipt,
        "failure": envelope["failure"],
        "retry_action": "重新创建制作任务" if envelope["status"] == "failed" else None,
        "provider_dispatch_count": 0,
    }


def _find_envelope(payload: dict[str, Any], saga_id: str) -> dict[str, Any]:
    matches = [item for item in payload["envelopes"] if item.get("saga_id") == saga_id]
    if len(matches) != 1:
        raise SagaIntegrityError("creator production saga index does not resolve exactly")
    return matches[0]


def _seal_current_phase(envelope: dict[str, Any]) -> None:
    checksums = envelope.setdefault("phase_checksums", {})
    checksums[envelope["phase"]] = _digest(_phase_checksum_body(envelope))


def _validate_current_phase_checksum(envelope: dict[str, Any]) -> None:
    checksums = envelope.get("phase_checksums")
    if not isinstance(checksums, dict):
        raise SagaIntegrityError("creator production saga phase checksum is missing")
    phase = str(envelope.get("phase") or "")
    expected = checksums.get(phase)
    if not isinstance(expected, str) or _digest(_phase_checksum_body(envelope)) != expected:
        raise SagaIntegrityError("creator production saga phase checksum does not match")


def _phase_checksum_body(envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in envelope.items()
        if key != "phase_checksums"
    }


def _exact_latest_shot(aggregate: ProductionProjectAggregate, ref: EntityVersionRef):
    if ref.entity_type != "shot":
        raise SagaConflictError("creator_production_target_not_shot")
    matches = [item for item in aggregate.shots if item.as_ref() == ref]
    if len(matches) != 1:
        raise SagaConflictError("creator_production_shot_missing")
    latest = max((item for item in aggregate.shots if item.entity_id == ref.entity_id), key=lambda item: item.revision)
    if latest.as_ref() != ref:
        raise SagaConflictError("creator_production_stale_shot_version")
    return latest


def _exact_latest_episode_contains_shot(
    aggregate: ProductionProjectAggregate,
    episode_ref: EntityVersionRef,
    shot_ref: EntityVersionRef,
) -> None:
    if episode_ref.entity_type != "episode":
        raise SagaConflictError("creator_production_episode_invalid")
    episode = next((item for item in aggregate.episodes if item.as_ref() == episode_ref), None)
    if episode is None:
        raise SagaConflictError("creator_production_episode_missing")
    latest_episode = max(
        (item for item in aggregate.episodes if item.entity_id == episode_ref.entity_id),
        key=lambda item: item.revision,
    )
    if latest_episode.as_ref() != episode_ref:
        raise SagaConflictError("creator_production_stale_episode_version")
    scene_ids = {item.entity_id for item in aggregate.scenes if item.episode_ref == episode_ref}
    shot = next(item for item in aggregate.shots if item.as_ref() == shot_ref)
    if shot.scene_ref.entity_id not in scene_ids:
        raise SagaConflictError("creator_production_shot_outside_episode")


def _episode_shot_refs(
    aggregate: ProductionProjectAggregate,
    episode_ref: EntityVersionRef,
) -> tuple[EntityVersionRef, ...]:
    scene_ids = {item.entity_id for item in aggregate.scenes if item.episode_ref == episode_ref}
    latest: dict[str, Any] = {}
    for shot in aggregate.shots:
        if shot.scene_ref.entity_id not in scene_ids:
            continue
        current = latest.get(shot.entity_id)
        if current is None or shot.revision > current.revision:
            latest[shot.entity_id] = shot
    return tuple(item.as_ref() for item in sorted(latest.values(), key=lambda item: (item.sequence, item.entity_id)))


def _artifact_manifest(envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "afs.creator-production-preview-manifest.v0.1",
        "artifact_id": f"artifact-{envelope['saga_id'][5:]}",
        "kind": "production_preview",
        "shot_ref": envelope["shot_ref"],
        "safe_summary": "deterministic provider-free production preview candidate",
        "contains_media_bytes": False,
        "contains_private_path": False,
        "contains_signed_url": False,
        "provider_dispatch_count": 0,
    }


def _request_intent(body: CreatorProductionRequest) -> dict[str, Any]:
    value = body.model_dump(mode="json")
    value["crash_after"] = "none"
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _safe_stamp(value: str) -> str:
    return value if value and "+" in value else _STAMP


def _safe_failure(value: str) -> str:
    text = value.replace("/", "_").replace("\\", "_")
    return text[:240] or "creator production request failed"


def _saga_path(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "creator_production_saga" / "saga.json"


def _lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.lock")


def _crash_after(request: Request, body_value: str) -> str:
    header = request.headers.get("X-AFS-Crash-After")
    return header or body_value or "none"


class _InjectedCrash(RuntimeError):
    def __init__(self, phase: str) -> None:
        super().__init__(phase)
        self.phase = phase


def _crash_if(configured: str, phase: str) -> None:
    if configured == phase:
        raise _InjectedCrash(phase)


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _raise_saga_error(
    project_id: str,
    *,
    status_code: int,
    error: str,
    message: str,
    stage: str,
    retryable: bool = False,
    cause: Exception | None = None,
) -> None:
    exception = HTTPException(
        status_code=status_code,
        detail=safe_error_detail(
            error,
            message=message,
            project_id=project_id,
            action="creator_production_request",
            stage=stage,
            retryable=retryable,
        ),
    )
    if cause is None:
        raise exception
    raise exception from cause


__all__ = (
    "CreatorProductionRequest",
    "join_creator_production_authoring_projection",
    "overlay_creator_production_requests",
    "reconcile_creator_production_request_envelopes",
    "register_runtime_creator_production_saga_routes",
)
