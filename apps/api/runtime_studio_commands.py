from __future__ import annotations

from typing import Any, Literal, Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_production_graph import (
    GraphIntegrityError,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
    impacted_descendants,
)
from apps.api.runtime_store import RuntimeStore, safe_id
from apps.api.runtime_studio_safety import assert_safe_public_payload


class StudioCommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudioReworkPreviewRequest(StudioCommandModel):
    target_entity_id: str = Field(min_length=1, max_length=160)
    expected_graph_version: int = Field(ge=1)
    expected_graph_digest: str = Field(min_length=64, max_length=64)


class StudioReworkConfirmRequest(StudioReworkPreviewRequest):
    preview_id: str = Field(min_length=64, max_length=64)
    idempotency_key: str = Field(min_length=1, max_length=160)


class StudioReworkPreviewReceipt(StudioCommandModel):
    schema_version: Literal["afs.studio_rework_preview.v0.1"] = (
        "afs.studio_rework_preview.v0.1"
    )
    status: Literal["preview"] = "preview"
    preview_id: str
    project_id: str
    graph_version: int = Field(ge=1)
    graph_digest: str
    target_entity_id: str
    impact_refs: list[str] = Field(default_factory=list)
    keep_refs: list[str] = Field(default_factory=list)
    dependency_evidence: list[dict[str, str]] = Field(default_factory=list)
    cost_available: Literal[False] = False
    requires_confirmation: Literal[True] = True
    provider_dispatch_count: Literal[0] = 0


class StudioReworkConfirmReceipt(StudioCommandModel):
    schema_version: Literal["afs.studio_command_receipt.v0.1"] = (
        "afs.studio_command_receipt.v0.1"
    )
    status: Literal["confirmed"] = "confirmed"
    action: Literal["plan_local_rework"] = "plan_local_rework"
    receipt_id: str
    project_id: str
    graph_version: int = Field(ge=1)
    graph_digest: str
    target_entity_id: str
    task_id: str
    impact_refs: list[str] = Field(default_factory=list)
    dispatch_state: Literal["planned_not_dispatched"] = "planned_not_dispatched"
    idempotent_replay: bool = False
    provider_dispatch_count: Literal[0] = 0


def register_runtime_studio_command_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    graph_store = ProductionGraphStore(store)

    @app.post(
        "/api/v1/projects/{project_id}/studio/commands/rework/preview",
        tags=["studio-v1"],
        response_model=StudioReworkPreviewReceipt,
    )
    def preview_local_rework(
        project_id: str,
        body: StudioReworkPreviewRequest,
        request: Request,
    ) -> StudioReworkPreviewReceipt:
        _require_project_access(store, auth, request, project_id)
        graph = _load_exact_graph(graph_store, project_id, body)
        return StudioReworkPreviewReceipt.model_validate(
            build_rework_preview(project_id, graph, body.target_entity_id)
        )

    @app.post(
        "/api/v1/projects/{project_id}/studio/commands/rework/confirm",
        tags=["studio-v1"],
        response_model=StudioReworkConfirmReceipt,
    )
    def confirm_local_rework(
        project_id: str,
        body: StudioReworkConfirmRequest,
        request: Request,
    ) -> StudioReworkConfirmReceipt:
        _require_project_access(store, auth, request, project_id)
        task_id = _task_id(body.target_entity_id, body.expected_graph_version + 1)
        semantic_digest = _rework_semantic_digest(
            body.preview_id,
            body.target_entity_id,
        )
        current = _load_graph(graph_store, project_id)
        replay = current.get("idempotency", {}).get(body.idempotency_key)
        if isinstance(replay, Mapping):
            if replay.get("semantic_digest") != semantic_digest:
                raise HTTPException(
                    status_code=409,
                    detail="idempotency key belongs to a different command",
                )
            return StudioReworkConfirmReceipt.model_validate(
                _confirm_receipt(
                    project_id=project_id,
                    graph=current,
                    body=body,
                    task_id=task_id,
                    impact_refs=_replayed_impact_refs(current, task_id),
                    idempotent_replay=True,
                )
            )
        graph = _load_exact_graph(graph_store, project_id, body)
        preview = build_rework_preview(
            project_id,
            graph,
            body.target_entity_id,
        )
        if preview["preview_id"] != body.preview_id:
            raise HTTPException(
                status_code=409,
                detail="rework preview does not match the current graph",
            )
        events: list[dict[str, Any]] = [
            {
                "type": "work_created",
                "work_id": task_id,
                "semantic_digest": semantic_digest,
                "depends_on": [body.target_entity_id],
            },
            {
                "type": "nodes_invalidated",
                "changed_node_ids": [body.target_entity_id],
                "invalidated_node_ids": list(preview["impact_refs"]),
                "preserved_node_ids": list(preview["keep_refs"]),
                "dependency_evidence": list(preview["dependency_evidence"]),
            },
        ]
        try:
            updated = graph_store.append(
                project_id,
                expected_version=body.expected_graph_version,
                idempotency_key=body.idempotency_key,
                semantic_digest=semantic_digest,
                events=events,
            )
        except (GraphVersionConflict, ProductionGraphError) as exc:
            raise HTTPException(
                status_code=409,
                detail="local rework confirmation was rejected",
            ) from exc
        return StudioReworkConfirmReceipt.model_validate(
            _confirm_receipt(
                project_id=project_id,
                graph=updated,
                body=body,
                task_id=task_id,
                impact_refs=list(preview["impact_refs"]),
                idempotent_replay=bool(updated.get("idempotent_replay")),
            )
        )


def build_rework_preview(
    project_id: str,
    graph: Mapping[str, Any],
    target_entity_id: str,
) -> dict[str, Any]:
    target_id = safe_id(target_entity_id)
    target = graph.get("nodes", {}).get(target_id)
    if (
        target_id != target_entity_id
        or not isinstance(target, Mapping)
        or target.get("category") != "unit"
        or target.get("state") == "invalidated"
    ):
        raise HTTPException(
            status_code=409,
            detail="local rework requires an active shot target",
        )
    if _has_planned_rework(graph, target_id):
        raise HTTPException(
            status_code=409,
            detail="local rework is already planned for this shot",
        )
    try:
        impact = impacted_descendants(graph, [target_id])
    except ProductionGraphError as exc:
        raise HTTPException(
            status_code=409,
            detail="local rework impact preview was rejected",
        ) from exc
    safe_impact = {
        "changed_node_ids": [target_id],
        "invalidated_node_ids": [
            safe_id(value) for value in impact.get("invalidated_node_ids", [])
        ],
        "preserved_node_ids": [
            safe_id(value) for value in impact.get("preserved_node_ids", [])
        ],
        "dependency_evidence": [
            {
                "from_id": safe_id(item.get("from_id")),
                "to_id": safe_id(item.get("to_id")),
                "relation_type": safe_id(item.get("relation_type")),
            }
            for item in impact.get("dependency_evidence", [])
            if isinstance(item, Mapping)
        ],
    }
    preview_basis = {
        "project_id": safe_id(project_id),
        "graph_version": int(graph.get("version") or 0),
        "graph_digest": str(graph.get("graph_digest") or ""),
        "target_entity_id": target_id,
        "impact": safe_impact,
    }
    receipt = {
        "status": "preview",
        "preview_id": canonical_digest(preview_basis),
        "project_id": safe_id(project_id),
        "graph_version": preview_basis["graph_version"],
        "graph_digest": preview_basis["graph_digest"],
        "target_entity_id": target_id,
        "impact_refs": safe_impact["invalidated_node_ids"],
        "keep_refs": safe_impact["preserved_node_ids"],
        "dependency_evidence": safe_impact["dependency_evidence"],
        "cost_available": False,
        "requires_confirmation": True,
        "provider_dispatch_count": 0,
    }
    assert_safe_public_payload(receipt)
    return receipt


def _load_exact_graph(
    graph_store: ProductionGraphStore,
    project_id: str,
    body: StudioReworkPreviewRequest,
) -> dict[str, Any]:
    graph = _load_graph(graph_store, project_id)
    if (
        int(graph.get("version") or 0) != body.expected_graph_version
        or str(graph.get("graph_digest") or "") != body.expected_graph_digest
    ):
        raise HTTPException(
            status_code=409,
            detail="production graph changed; refresh before continuing",
        )
    return graph


def _load_graph(
    graph_store: ProductionGraphStore,
    project_id: str,
) -> dict[str, Any]:
    try:
        graph = graph_store.load(project_id)
    except GraphIntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="production graph integrity check failed",
        ) from exc
    return graph


def _confirm_receipt(
    *,
    project_id: str,
    graph: Mapping[str, Any],
    body: StudioReworkConfirmRequest,
    task_id: str,
    impact_refs: list[str],
    idempotent_replay: bool,
) -> dict[str, Any]:
    receipt = {
        "status": "confirmed",
        "action": "plan_local_rework",
        "receipt_id": canonical_digest(
            {
                "idempotency_key": body.idempotency_key,
                "preview_id": body.preview_id,
            }
        ),
        "project_id": safe_id(project_id),
        "graph_version": int(graph["version"]),
        "graph_digest": str(graph["graph_digest"]),
        "target_entity_id": safe_id(body.target_entity_id),
        "task_id": task_id,
        "impact_refs": impact_refs,
        "dispatch_state": "planned_not_dispatched",
        "idempotent_replay": idempotent_replay,
        "provider_dispatch_count": 0,
    }
    assert_safe_public_payload(receipt)
    return receipt


def _replayed_impact_refs(
    graph: Mapping[str, Any],
    task_id: str,
) -> list[str]:
    events = list(graph.get("events", []))
    for index, event in enumerate(events):
        if (
            isinstance(event, Mapping)
            and event.get("type") == "work_created"
            and event.get("work_id") == task_id
        ):
            for later in events[index + 1 : index + 3]:
                if (
                    isinstance(later, Mapping)
                    and later.get("type") == "nodes_invalidated"
                ):
                    return [
                        safe_id(value)
                        for value in later.get("invalidated_node_ids", [])
                    ]
    return []


def _rework_semantic_digest(
    preview_id: str,
    target_entity_id: str,
) -> str:
    return canonical_digest(
        {
            "action": "plan_local_rework",
            "preview_id": preview_id,
            "target_entity_id": target_entity_id,
        }
    )


def _require_project_access(
    store: RuntimeStore,
    auth: RuntimeAuthStore,
    request: Request,
    project_id: str,
) -> None:
    if (
        not project_id
        or store.is_project_deleted(project_id)
        or not store.project_manifest_path(project_id).is_file()
    ):
        raise HTTPException(status_code=404, detail="project not found")
    if not auth.enabled():
        return
    user = auth.require_user(request)
    if not auth.user_can_access_project(str(user.get("user_id") or ""), project_id):
        raise HTTPException(status_code=403, detail="project access denied")


def _task_id(target_entity_id: str, graph_version: int) -> str:
    return safe_id(f"rework-{target_entity_id}-v{graph_version}")[:160]


def _has_planned_rework(
    graph: Mapping[str, Any],
    target_entity_id: str,
) -> bool:
    prefix = f"rework-{target_entity_id}-v"
    return any(
        str(work_id).startswith(prefix)
        and isinstance(work, Mapping)
        and str(work.get("state") or "") == "planned"
        for work_id, work in graph.get("work", {}).items()
    )


__all__ = (
    "StudioReworkConfirmReceipt",
    "StudioReworkPreviewReceipt",
    "build_rework_preview",
    "register_runtime_studio_command_routes",
)
