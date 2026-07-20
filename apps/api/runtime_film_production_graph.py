"""Film Domain Pack adapter for the canonical production graph.

This module accepts only trusted, typed candidates.  It does not infer entities
from prose, manufacture a plan, or provide sample-content fallbacks.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_production_graph import (
    GraphPlanningRequired,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
    execute_outside_graph_lock,
    graph_projection,
)
from apps.api.runtime_store import RuntimeStore


FILM_DOMAIN_PACK_SCHEMA_VERSION = "afs.film_domain_pack.v0.1"
READ_ONLY_SURFACES = {"episode", "script_core_truth", "production_control", "studio", "canvas", "storyboard", "api"}


def compile_film_candidate(project_id: str, candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Compile a supplied candidate into generic graph events without guessing."""
    if candidate.get("schema_version") != FILM_DOMAIN_PACK_SCHEMA_VERSION or candidate.get("trusted_candidate") is not True:
        raise GraphPlanningRequired("planning_required: a trusted typed film candidate is required")
    source_digest = str(candidate.get("source_digest") or "")
    if len(source_digest) != 64:
        raise GraphPlanningRequired("planning_required: source digest is required")
    brief = _mapping(candidate, "brief")
    revision = _mapping(candidate, "script_revision")
    characters = _list(candidate, "characters")
    scenes = _list(candidate, "scenes")
    assets = _list(candidate, "assets")
    shots = _list(candidate, "shots")
    if not brief or not revision or not characters or not scenes or not shots:
        raise GraphPlanningRequired("planning_required: brief, revision, named entities, scenes, and shots are required")
    _unique_ids(characters, "character_id"); _unique_ids(scenes, "scene_id"); _unique_ids(assets, "asset_id"); _unique_ids(shots, "shot_id")
    character_ids, scene_ids, asset_ids = ({item["character_id"] for item in characters}, {item["scene_id"] for item in scenes}, {item["asset_id"] for item in assets})
    for character in characters:
        if not str(character.get("display_name") or "").strip():
            raise GraphPlanningRequired("planning_required: character display names are required")
    for shot in shots:
        if float(shot.get("duration_seconds") or 0) <= 0 or shot.get("scene_id") not in scene_ids:
            raise GraphPlanningRequired("planning_required: each shot needs positive duration and a known scene")
        if not set(shot.get("character_refs", [])) <= character_ids or not set(shot.get("asset_refs", [])) <= asset_ids:
            raise GraphPlanningRequired("planning_required: shot references must resolve to supplied entities")

    brief_id = str(brief.get("brief_id") or "brief")
    revision_id = str(revision.get("revision_id") or "revision")
    events: list[dict[str, Any]] = [
        _node(brief_id, "input", {"source_digest": source_digest}),
        _node(revision_id, "revision", {"source_digest": source_digest}),
        _relation(brief_id, revision_id, "derived_from"),
    ]
    for item in characters:
        events.extend([_node(item["character_id"], "entity", {"display_name": item["display_name"], "aliases": list(item.get("aliases", []))}),
                       _relation(revision_id, item["character_id"], "derived_from")])
    for item in scenes:
        events.extend([_node(item["scene_id"], "location", {"name": item.get("name", ""), "lineage": list(item.get("lineage", []))}),
                       _relation(revision_id, item["scene_id"], "derived_from")])
    for item in assets:
        events.extend([_node(item["asset_id"], "resource", {"name": item.get("name", ""), "kind": item.get("kind", "")}),
                       _relation(revision_id, item["asset_id"], "derived_from")])
    for item in shots:
        shot_id = item["shot_id"]
        events.append(_node(shot_id, "unit", {"duration_seconds": item["duration_seconds"], "intent": item.get("intent", "")}))
        events.append(_relation(item["scene_id"], shot_id, "contains"))
        for ref in [*item.get("character_refs", []), *item.get("asset_refs", [])]: events.append(_relation(ref, shot_id, "required_by"))
        events.append({"type": "work_created", "work_id": f"work-{shot_id}", "semantic_digest": canonical_digest(item),
                       "depends_on": [shot_id, item["scene_id"], *item.get("character_refs", []), *item.get("asset_refs", [])]})
    delivery_id = str(candidate.get("delivery_id") or "delivery")
    events.extend([_node(delivery_id, "delivery", {"timeline_refs": list(candidate.get("timeline_refs", [])),
                                                       "rights_refs": list(candidate.get("rights_refs", [])), "cost_refs": []}),
                   *[_relation(shot["shot_id"], delivery_id, "contributes_to") for shot in shots],
                   {"type": "review_recorded", "review_id": f"review-{delivery_id}", "target_id": delivery_id,
                    "state": "pending", "evidence_refs": [source_digest]},
                   {"type": "delivery_recorded", "delivery_id": delivery_id, "target_id": delivery_id, "state": "planned",
                    "timeline_refs": list(candidate.get("timeline_refs", [])), "rights_refs": list(candidate.get("rights_refs", [])),
                    "cost_refs": [], "provenance_refs": [source_digest]}])
    return events


def film_graph_projection(graph: Mapping[str, Any], surface: str) -> dict[str, Any]:
    result = graph_projection(graph, surface=surface)
    result["domain_pack"] = "film"
    result["projection_mode"] = "read_only"
    return result


def register_runtime_film_production_graph_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    graph_store = ProductionGraphStore(store)

    def require_access(request: Request, project_id: str) -> None:
        if auth.enabled():
            user = auth.require_user(request)
            if not auth.user_can_access_project(str(user["user_id"]), project_id): raise HTTPException(status_code=403, detail="project access denied")

    @app.get("/projects/{project_id}/m4/production-graph")
    def get_graph(project_id: str, request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        return {"graph": graph_store.ensure(project_id), "provider_dispatch_count": 0}

    @app.post("/projects/{project_id}/m4/film-candidates/confirm")
    def confirm_candidate(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        try:
            events = compile_film_candidate(project_id, body["candidate"])
            result = graph_store.append(project_id, expected_version=int(body.get("expected_graph_version", 0)),
                                        idempotency_key=str(body["idempotency_key"]), semantic_digest=canonical_digest(body["candidate"]), events=events)
        except GraphPlanningRequired:
            return JSONResponse(status_code=409, content={"error": "planning_required", "status": "blocked", "project_id": project_id,
                                                          "provider_dispatch_count": 0, "cost_usd": 0})
        except (GraphPlanningRequired, GraphVersionConflict, ProductionGraphError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail={"error": "m4_graph_rejected", "reason": str(exc), "planning_required": isinstance(exc, GraphPlanningRequired)}) from exc
        return {"graph": result, "provider_dispatch_count": 0}

    @app.get("/projects/{project_id}/m4/projections/{surface}")
    def get_projection(project_id: str, surface: str, request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        if surface not in READ_ONLY_SURFACES: raise HTTPException(status_code=404, detail="projection surface not found")
        return film_graph_projection(graph_store.ensure(project_id), surface)

    @app.post("/projects/{project_id}/m4/work/{work_id}/fake-execute")
    def fake_execute(project_id: str, work_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        payload = dict(body.get("candidate_payload") or {})
        semantic_digest = str(body.get("semantic_digest") or canonical_digest(payload))
        try:
            result = execute_outside_graph_lock(graph_store, project_id, work_id=work_id, semantic_digest=semantic_digest,
                                                lease_owner="m4_fake_adapter", adapter=lambda _attempt: payload)
        except ProductionGraphError as exc:
            raise HTTPException(status_code=409, detail={"error": "m4_execution_rejected", "reason": str(exc)}) from exc
        return result

    @app.post("/projects/{project_id}/m4/invalidate")
    def invalidate(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        try:
            graph = graph_store.invalidate(project_id, expected_version=int(body["expected_graph_version"]),
                                           idempotency_key=str(body["idempotency_key"]), changed_node_ids=list(body["changed_node_ids"]))
        except (ProductionGraphError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail={"error": "m4_invalidation_rejected", "reason": str(exc)}) from exc
        return {"graph": graph, "provider_dispatch_count": 0}


def _node(node_id: str, category: str, metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {"type": "node_upserted", "node": {"node_id": node_id, "category": category, "metadata": dict(metadata)}}


def _relation(from_id: str, to_id: str, relation_type: str) -> dict[str, Any]:
    return {"type": "relation_upserted", "from_id": from_id, "to_id": to_id, "relation_type": relation_type}


def _mapping(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    item = value.get(name)
    if not isinstance(item, Mapping): raise GraphPlanningRequired(f"planning_required: typed {name} is required")
    return dict(item)


def _list(value: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    item = value.get(name)
    if not isinstance(item, list): raise GraphPlanningRequired(f"planning_required: typed {name} is required")
    return [dict(row) for row in item if isinstance(row, Mapping)]


def _unique_ids(items: list[Mapping[str, Any]], key: str) -> None:
    values = [str(item.get(key) or "") for item in items]
    if not values or any(not value for value in values) or len(values) != len(set(values)):
        raise GraphPlanningRequired(f"planning_required: unique {key} values are required")
