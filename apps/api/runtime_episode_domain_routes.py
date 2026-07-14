from __future__ import annotations

import hashlib
import json
import re
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_episode_domain_contract import SAFE_ID, ProductionProjectAggregate, TenantScope
from apps.api.runtime_episode_domain_store import (
    AggregateIdempotencyConflictError,
    AggregateIntegrityError,
    AggregateNotFoundError,
    AggregateRetiredError,
    AggregateScopeError,
    AggregateVersionConflictError,
    EpisodeDomainAggregateStore,
    EpisodeDomainStoreError,
)
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


LOCAL_ORG_ID = "local-runtime"
LOCAL_ACTOR_ID = "local-creator"
_SAFE_ID_RE = re.compile(SAFE_ID, re.ASCII)


class EpisodeAggregateReplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_aggregate_version: int = Field(ge=0, strict=True)
    aggregate: ProductionProjectAggregate


IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=160,
        pattern=SAFE_ID,
    ),
]


def register_runtime_episode_domain_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    aggregate_store = EpisodeDomainAggregateStore(store.root)

    @app.get("/projects/{project_id}/episode-production-aggregate")
    def get_episode_production_aggregate(
        project_id: str,
        request: Request,
    ) -> dict[str, Any]:
        scope = _require_project_scope(store, auth, request, project_id)
        try:
            aggregate = aggregate_store.load(org_id=scope.org_id, project_id=project_id)
        except EpisodeDomainStoreError as exc:
            _raise_store_error(exc, request=request, project_id=project_id)
        if aggregate.scope != scope:
            _raise_api_error(
                request,
                project_id,
                status_code=500,
                error="episode_aggregate_integrity_failed",
                message="Episode production state failed its identity check.",
                stage="episode_aggregate_read",
            )
        aggregate_payload = _safe_aggregate_payload(
            aggregate,
            request=request,
            project_id=project_id,
            status_code=500,
            stage="episode_aggregate_read",
        )
        return {
            "aggregate": aggregate_payload,
            "aggregate_version": aggregate.aggregate_version,
        }

    @app.put("/projects/{project_id}/episode-production-aggregate")
    def replace_episode_production_aggregate(
        project_id: str,
        body: EpisodeAggregateReplaceRequest,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        scope = _require_project_scope(store, auth, request, project_id)
        _require_exact_aggregate_scope(body.aggregate, scope, request=request)
        _safe_aggregate_payload(
            body.aggregate,
            request=request,
            project_id=project_id,
            status_code=422,
            stage="episode_aggregate_validation",
        )
        payload_digest = _mutation_digest(
            project_id=project_id,
            expected_aggregate_version=body.expected_aggregate_version,
            aggregate=body.aggregate,
        )
        try:
            result = aggregate_store.save(
                body.aggregate,
                expected_aggregate_version=body.expected_aggregate_version,
                idempotency_key=idempotency_key,
                payload_digest=payload_digest,
            )
        except EpisodeDomainStoreError as exc:
            _raise_store_error(exc, request=request, project_id=project_id)
        aggregate_payload = _safe_aggregate_payload(
            result.aggregate,
            request=request,
            project_id=project_id,
            status_code=500,
            stage="episode_aggregate_write",
        )
        return {
            "aggregate": aggregate_payload,
            "aggregate_version": result.aggregate.aggregate_version,
            "replayed": result.replayed,
        }


def _require_project_scope(
    store: RuntimeStore,
    auth: RuntimeAuthStore,
    request: Request,
    project_id: str,
) -> TenantScope:
    if _SAFE_ID_RE.fullmatch(project_id) is None:
        _raise_api_error(
            request,
            project_id,
            status_code=422,
            error="episode_aggregate_project_id_invalid",
            message="Project identity is invalid.",
            stage="episode_aggregate_scope",
        )
    if store.is_project_deleted(project_id) or not store.project_manifest_path(project_id).is_file():
        _raise_api_error(
            request,
            project_id,
            status_code=404,
            error="project_not_found",
            message="Project was not found.",
            stage="episode_aggregate_scope",
        )
    try:
        manifest = store.ensure_project_manifest(project_id)
    except (OSError, ValueError) as exc:
        _raise_api_error(
            request,
            project_id,
            status_code=422,
            error="project_manifest_invalid",
            message="Project data is invalid.",
            stage="episode_aggregate_scope",
            cause=exc,
        )
    if str(manifest.get("project_id") or "") != project_id:
        _raise_api_error(
            request,
            project_id,
            status_code=422,
            error="project_manifest_identity_mismatch",
            message="Project identity does not match its stored record.",
            stage="episode_aggregate_scope",
        )
    if not auth.enabled():
        return TenantScope(
            org_id=LOCAL_ORG_ID,
            project_id=project_id,
            actor_id=LOCAL_ACTOR_ID,
        )
    user = auth.require_user(request)
    user_id = str(user.get("user_id") or "")
    if _SAFE_ID_RE.fullmatch(user_id) is None or not auth.user_can_access_project(user_id, project_id):
        _raise_api_error(
            request,
            project_id,
            status_code=403,
            error="project_access_denied",
            message="Project access is denied.",
            stage="episode_aggregate_scope",
        )
    # Runtime auth currently has personal project ownership, not a separate
    # organization object. Binding the personal org and actor to the verified
    # owner id is the only identity mapping the current Runtime can prove.
    return TenantScope(org_id=user_id, project_id=project_id, actor_id=user_id)


def _require_exact_aggregate_scope(
    aggregate: ProductionProjectAggregate,
    expected: TenantScope,
    *,
    request: Request,
) -> None:
    if aggregate.scope.project_id != expected.project_id:
        _raise_api_error(
            request,
            expected.project_id,
            status_code=409,
            error="episode_aggregate_project_mismatch",
            message="Aggregate project identity does not match the request path.",
            stage="episode_aggregate_scope",
        )
    if aggregate.scope.org_id != expected.org_id or aggregate.scope.actor_id != expected.actor_id:
        _raise_api_error(
            request,
            expected.project_id,
            status_code=403,
            error="episode_aggregate_scope_mismatch",
            message="Aggregate tenant or actor identity does not match the authenticated project owner.",
            stage="episode_aggregate_scope",
        )


def _mutation_digest(
    *,
    project_id: str,
    expected_aggregate_version: int,
    aggregate: ProductionProjectAggregate,
) -> str:
    payload = {
        "operation": "replace_episode_production_aggregate",
        "project_id": project_id,
        "expected_aggregate_version": expected_aggregate_version,
        "aggregate": aggregate.model_dump(mode="json"),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _safe_aggregate_payload(
    aggregate: ProductionProjectAggregate,
    *,
    request: Request,
    project_id: str,
    status_code: int,
    stage: str,
) -> dict[str, Any]:
    payload = aggregate.model_dump(mode="json")
    try:
        reject_unsafe_payload(payload)
    except ValueError as exc:
        _raise_api_error(
            request,
            project_id,
            status_code=status_code,
            error=(
                "episode_aggregate_unsafe_payload"
                if status_code < 500
                else "episode_aggregate_integrity_failed"
            ),
            message="Episode production state contains unsafe private data.",
            stage=stage,
            cause=exc,
        )
    return payload


def _raise_store_error(
    exc: EpisodeDomainStoreError,
    *,
    request: Request,
    project_id: str,
) -> None:
    if isinstance(exc, AggregateNotFoundError):
        _raise_api_error(
            request,
            project_id,
            status_code=404,
            error="episode_aggregate_not_found",
            message="Episode production state was not found.",
            stage="episode_aggregate_read",
            cause=exc,
        )
    if isinstance(exc, AggregateScopeError):
        _raise_api_error(
            request,
            project_id,
            status_code=403,
            error="episode_aggregate_scope_mismatch",
            message="Episode production state does not belong to this project scope.",
            stage="episode_aggregate_scope",
            cause=exc,
        )
    if isinstance(exc, AggregateIdempotencyConflictError):
        _raise_api_error(
            request,
            project_id,
            status_code=409,
            error="episode_aggregate_idempotency_conflict",
            message="This idempotency key was already used for a different mutation.",
            stage="episode_aggregate_write",
            cause=exc,
        )
    if isinstance(exc, AggregateVersionConflictError):
        _raise_api_error(
            request,
            project_id,
            status_code=409,
            error="episode_aggregate_version_conflict",
            message="Episode production state changed. Reload it before retrying.",
            stage="episode_aggregate_write",
            retryable=True,
            cause=exc,
        )
    if isinstance(exc, AggregateRetiredError):
        _raise_api_error(
            request,
            project_id,
            status_code=409,
            error="episode_aggregate_retired",
            message="Retired episode production state cannot be changed.",
            stage="episode_aggregate_write",
            cause=exc,
        )
    if isinstance(exc, AggregateIntegrityError):
        _raise_api_error(
            request,
            project_id,
            status_code=500,
            error="episode_aggregate_integrity_failed",
            message="Episode production state failed its integrity check.",
            stage="episode_aggregate_read",
            cause=exc,
        )
    _raise_api_error(
        request,
        project_id,
        status_code=500,
        error="episode_aggregate_store_failed",
        message="Episode production state could not be processed.",
        stage="episode_aggregate_store",
        cause=exc,
    )


def _raise_api_error(
    request: Request,
    project_id: str,
    *,
    status_code: int,
    error: str,
    message: str,
    stage: str,
    retryable: bool = False,
    cause: Exception | None = None,
) -> None:
    detail = safe_error_detail(
        error,
        message=message,
        project_id=project_id,
        action="episode_aggregate",
        stage=stage,
        retryable=retryable,
    )
    exception = HTTPException(status_code=status_code, detail=detail)
    if cause is None:
        raise exception
    raise exception from cause


__all__ = (
    "EpisodeAggregateReplaceRequest",
    "LOCAL_ACTOR_ID",
    "LOCAL_ORG_ID",
    "register_runtime_episode_domain_routes",
)
