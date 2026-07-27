"""Film Domain Pack adapter for the canonical production graph.

This module accepts only trusted, typed candidates.  It does not infer entities
from prose, manufacture a plan, or provide sample-content fallbacks.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_production_graph import (
    GraphPlanningRequired,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
    execute_outside_graph_lock,
    graph_projection,
    impacted_descendants,
)
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id
from apps.api.runtime_video_candidates import candidate_file
from apps.api.runtime_video_constants import VIDEO_SUFFIX_TYPES


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
    sequence = dict(candidate.get("sequence") or {})
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
    sequence_id = str(sequence.get("sequence_id") or "")
    delivery_id = str(candidate.get("delivery_id") or "delivery")
    graph_ids = [brief_id, revision_id, delivery_id, *([sequence_id] if sequence_id else []),
                 *(item["character_id"] for item in characters), *(item["scene_id"] for item in scenes),
                 *(item["asset_id"] for item in assets), *(item["shot_id"] for item in shots)]
    if len(graph_ids) != len(set(graph_ids)):
        raise GraphPlanningRequired("planning_required: IDs must be unique across the film production graph")
    events: list[dict[str, Any]] = [
        _node(brief_id, "input", {"source_digest": source_digest}),
        _node(revision_id, "revision", {"source_digest": source_digest}),
        _relation(brief_id, revision_id, "derived_from"),
    ]
    if sequence_id:
        events.extend([_node(sequence_id, "collection", {"name": str(sequence.get("name") or "制作序列"),
                                                           "target_duration_seconds": float(sequence.get("target_duration_seconds") or 0)}),
                       _relation(revision_id, sequence_id, "derived_from")])
    for item in characters:
        metadata = _film_metadata(item, exclude={"character_id"})
        metadata.update({"display_name": item["display_name"], "aliases": list(item.get("aliases", []))})
        events.extend([_node(item["character_id"], "entity", metadata),
                       _relation(revision_id, item["character_id"], "derived_from")])
    for item in scenes:
        metadata = _film_metadata(item, exclude={"scene_id"})
        metadata.update({"name": item.get("name", ""), "lineage": list(item.get("lineage", []))})
        events.extend([_node(item["scene_id"], "location", metadata),
                       _relation(revision_id, item["scene_id"], "derived_from")])
        if sequence_id: events.append(_relation(sequence_id, item["scene_id"], "contains"))
    for item in assets:
        metadata = _film_metadata(item, exclude={"asset_id"})
        metadata.update({"name": item.get("name", ""), "kind": item.get("kind", "")})
        events.extend([_node(item["asset_id"], "resource", metadata),
                       _relation(revision_id, item["asset_id"], "derived_from")])
    for item in shots:
        shot_id = item["shot_id"]
        metadata = _film_metadata(item, exclude={"shot_id", "scene_id", "character_refs", "asset_refs"})
        metadata.update({"duration_seconds": item["duration_seconds"], "intent": item.get("intent", "")})
        events.append(_node(shot_id, "unit", metadata))
        events.append(_relation(item["scene_id"], shot_id, "contains"))
        for ref in [*item.get("character_refs", []), *item.get("asset_refs", [])]: events.append(_relation(ref, shot_id, "required_by"))
        events.append({"type": "work_created", "work_id": f"work-{shot_id}", "semantic_digest": canonical_digest(item),
                       "depends_on": [shot_id, item["scene_id"], *item.get("character_refs", []), *item.get("asset_refs", [])]})
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

    @app.get("/projects/{project_id}/m5/sequence-workspace")
    def sequence_workspace(project_id: str, request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        graph = graph_store.ensure(project_id)
        if not graph["nodes"]:
            return {"status": "planning_required", "project_id": project_id,
                    "message": "请导入剧本或确认可信的制作方案。", "graph_version": graph["version"],
                    "graph_digest": graph["graph_digest"], "provider_dispatch_count": 0}
        return _sequence_workspace_projection(graph, project_id=project_id, store=store)

    @app.get("/projects/{project_id}/approved-video-assets/{media_node_id}/preview")
    def approved_video_preview(
        project_id: str,
        media_node_id: str,
        request: Request,
    ) -> FileResponse:
        require_access(request, project_id)
        if safe_id(media_node_id) != media_node_id:
            raise HTTPException(status_code=404, detail="approved video not found")
        try:
            graph = graph_store.load(project_id)
        except ProductionGraphError as exc:
            raise HTTPException(status_code=404, detail="approved video not found") from exc
        record = graph.get("nodes", {}).get(media_node_id)
        metadata = (
            record.get("metadata")
            if isinstance(record, Mapping) and isinstance(record.get("metadata"), Mapping)
            else {}
        )
        receipt = _approved_video_receipts(store, project_id).get(media_node_id)
        approved_relation_sources = {
            str(relation.get("from_id") or "")
            for relation in graph.get("relations", [])
            if relation.get("to_id") == media_node_id
            and relation.get("relation_type") == "approved_video"
        }
        if (
            not receipt
            or approved_relation_sources != {receipt["source_shot_id"]}
            or receipt["source_shot_id"] not in graph.get("nodes", {})
            or not isinstance(record, Mapping)
            or record.get("category") != "artifact"
            or record.get("state") != "active"
            or metadata.get("kind") != "approved_video"
            or not _video_receipt_matches_node(receipt, metadata)
        ):
            raise HTTPException(status_code=404, detail="approved video not found")
        return FileResponse(
            receipt["_media_path"],
            media_type=receipt["mime_type"],
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/projects/{project_id}/m5/impact-preview")
    def impact_preview(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id); graph = graph_store.load(project_id)
        try:
            impact = impacted_descendants(graph, list(body["changed_node_ids"]))
        except (ProductionGraphError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=409, detail="graph impact preview rejected") from exc
        return {"status": "preview", "graph_version": graph["version"], "graph_digest": graph["graph_digest"], "impact": impact,
                "command": {"type": "m5_graph_mutation", "requires_confirmation": True}, "provider_dispatch_count": 0}

    @app.post("/projects/{project_id}/m5/mutations/confirm")
    def confirm_mutation(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id); graph = graph_store.load(project_id)
        try:
            changed = list(body["changed_node_ids"]); impact = impacted_descendants(graph, changed)
            events = [{"type": "node_metadata_updated", "node_id": body["node_id"], "patch": dict(body.get("patch") or {})},
                      {"type": "nodes_invalidated", **impact}]
            updated = graph_store.append(project_id, expected_version=int(body["expected_graph_version"]), idempotency_key=str(body["idempotency_key"]),
                                         semantic_digest=canonical_digest({"node": body["node_id"], "patch": body.get("patch"), "impact": impact}), events=events)
        except (ProductionGraphError, GraphVersionConflict, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail="graph mutation rejected") from exc
        return {"status": "confirmed", "receipt": {"graph_version": updated["version"], "graph_digest": updated["graph_digest"], "impact": impact,
                                                        "undo_available": False, "recovery": "refresh_and_retry_on_version_conflict"},
                "graph": updated, "provider_dispatch_count": 0, "cost_usd": 0}

    @app.post("/projects/{project_id}/m5/actions/confirm")
    def confirm_sequence_action(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id); graph = graph_store.load(project_id)
        action = str(body.get("action") or "")
        try:
            events = _sequence_action_events(graph, action, body)
            updated = graph_store.append(
                project_id,
                expected_version=int(body["expected_graph_version"]),
                idempotency_key=str(body["idempotency_key"]),
                semantic_digest=canonical_digest({"action": action, "payload": body.get("payload") or {}}),
                events=events,
            )
        except (ProductionGraphError, GraphVersionConflict, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail="graph lifecycle action rejected") from exc
        return {"status": "confirmed", "receipt": {"action": action, "graph_version": updated["version"],
                "graph_digest": updated["graph_digest"], "undo_available": False, "recovery": "refresh_and_retry_on_version_conflict"},
                "graph": updated, "provider_dispatch_count": 0, "cost_usd": 0}


def _node(node_id: str, category: str, metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {"type": "node_upserted", "node": {"node_id": node_id, "category": category, "metadata": dict(metadata)}}


def _relation(from_id: str, to_id: str, relation_type: str) -> dict[str, Any]:
    return {"type": "relation_upserted", "from_id": from_id, "to_id": to_id, "relation_type": relation_type}


def _film_metadata(item: Mapping[str, Any], *, exclude: set[str]) -> dict[str, Any]:
    metadata = {}
    for key, value in item.items():
        if key in exclude:
            continue
        metadata[key] = deepcopy(value)
    return metadata


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


def _sequence_workspace_projection(
    graph: Mapping[str, Any],
    *,
    project_id: str,
    store: RuntimeStore | None = None,
) -> dict[str, Any]:
    nodes = graph["nodes"]
    sequences = [node for node in nodes.values() if node.get("category") == "collection"]
    scenes = [node for node in nodes.values() if node.get("category") == "location"]
    units = [node for node in nodes.values() if node.get("category") == "unit"]
    resources = [node for node in nodes.values() if node.get("category") == "resource"]
    references = [node for node in resources if node.get("metadata", {}).get("kind") in {"reference", "reference_set"}]
    production_aids = [
        node for node in resources
        if node.get("metadata", {}).get("classification") == "production_aid"
        or node.get("metadata", {}).get("kind") in {"closeup", "reference", "reference_set", "style"}
    ]
    props = [
        node for node in resources
        if node.get("metadata", {}).get("kind") == "prop"
        and node.get("metadata", {}).get("classification") != "production_aid"
    ]
    approved_media = _approved_media_projection(
        nodes,
        graph["relations"],
        project_id=project_id,
        store=store,
    )
    versions = sorted(({"version": item["version"]} for item in graph["idempotency"].values()), key=lambda item: item["version"], reverse=True)
    return {"status": "ready", "project_id": safe_id(project_id),
            "graph_version": graph["version"], "graph_digest": graph["graph_digest"],
            "migration_state": "graph_backed_single_truth", "sequence": {
            "script_revisions": [node for node in nodes.values() if node.get("category") == "revision"],
            "characters": [node for node in nodes.values() if node.get("category") == "entity"],
            "sequences": sequences, "scenes": scenes, "shots": units, "props": props, "reference_sets": references, "production_aids": production_aids,
            "approved_media": approved_media,
            "dependencies": graph["relations"], "tasks": list(graph["work"].values()), "candidates": list(graph["artifacts"].values()),
            "selections": [{"selection_key": key, **value} for key, value in graph["selections"].items()],
            "reviews": list(graph["reviews"].values()), "delivery_plan": list(graph["deliveries"].values()), "version_history": versions},
            "storyboard": {"mode": "read_only", "graph_version": graph["version"], "graph_digest": graph["graph_digest"], "shots": units},
            "evidence_details_available": True, "provider_dispatch_count": 0, "cost_usd": 0}


def _approved_media_projection(
    nodes: Mapping[str, Mapping[str, Any]],
    relations: list[Mapping[str, Any]],
    *,
    project_id: str,
    store: RuntimeStore | None = None,
) -> list[dict[str, Any]]:
    targets_by_media: dict[str, tuple[str, list[str]]] = {}
    for relation in relations:
        relation_type = str(relation.get("relation_type") or "")
        media_kind = {
            "approved_image": "image",
            "approved_video": "video",
        }.get(relation_type)
        if not media_kind:
            continue
        media_id = str(relation.get("to_id") or "")
        target_id = str(relation.get("from_id") or "")
        if media_id and target_id in nodes:
            current_kind, targets = targets_by_media.setdefault(
                media_id,
                (media_kind, []),
            )
            if current_kind == media_kind:
                targets.append(target_id)

    media_records: dict[str, dict[str, Any]] = {}
    video_receipts = _approved_video_receipts(store, project_id)
    for node_id, record in nodes.items():
        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
        relation_kind = targets_by_media.get(node_id, ("", []))[0]
        image_asset_id = str(metadata.get("image_asset_id") or "")
        if (
            record.get("category") != "artifact"
            or record.get("state") != "active"
            or relation_kind != "image"
            or metadata.get("kind") != "approved_image"
            or not image_asset_id
            or safe_id(image_asset_id) != image_asset_id
            or node_id not in targets_by_media
        ):
            continue
        media_records[node_id] = {
            "media_node_id": node_id,
            "media_kind": "image",
            "preview_url": (
                f"/projects/{safe_id(project_id)}/image-assets/"
                f"{image_asset_id}/preview"
            ),
            "width": int(metadata.get("width") or 0),
            "height": int(metadata.get("height") or 0),
            "approval_graph_version": _positive_int(
                metadata.get("approval_graph_version")
            ),
        }

    for node_id, record in nodes.items():
        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
        relation_kind = targets_by_media.get(node_id, ("", []))[0]
        if (
            record.get("category") != "artifact"
            or record.get("state") != "active"
            or relation_kind != "video"
            or metadata.get("kind") != "approved_video"
        ):
            continue
        receipt = video_receipts.get(node_id)
        relation_targets = set(targets_by_media.get(node_id, ("", []))[1])
        if (
            not receipt
            or relation_targets != {receipt["source_shot_id"]}
            or not _video_receipt_matches_node(receipt, metadata)
        ):
            continue
        media_records[node_id] = {
            "media_node_id": node_id,
            "media_kind": "video",
            "preview_url": receipt["preview_url"],
            "mime_type": receipt["mime_type"],
            "container": receipt["container"],
            "width": receipt["width"],
            "height": receipt["height"],
            "duration_sec": receipt["duration_sec"],
            "codec": receipt["codec"],
            "model": str(metadata.get("model") or ""),
            "resolution": str(metadata.get("resolution") or ""),
            "approval_graph_version": receipt["approval_graph_version"],
            "lineage": {
                "source_kind": "approved_video_receipt",
                "target_relation": "approved_video",
            },
        }

    media_by_target: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for media_id, (media_kind, targets) in targets_by_media.items():
        if media_id not in media_records:
            continue
        for target_id in sorted(set(targets)):
            media_by_target.setdefault(
                (target_id, media_kind),
                [],
            ).append(media_records[media_id])

    approved_media: list[dict[str, Any]] = []
    for (target_id, _media_kind), candidates in sorted(media_by_target.items()):
        selected = _current_approved_media(candidates)
        if selected is None:
            continue
        approved_media.append({**selected, "target_node_ids": [target_id]})
    return approved_media


def _approved_video_receipts(
    store: RuntimeStore | None,
    project_id: str,
) -> dict[str, dict[str, Any]]:
    if store is None:
        return {}
    root = store.projects_dir / safe_id(project_id) / "video_admission"
    paths = [root / "manifest.json", *sorted((root / "history").glob("*.json"))]
    receipts: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.is_file():
            continue
        try:
            manifest = read_json(path)
            reject_unsafe_payload(manifest)
        except (OSError, TypeError, ValueError):
            continue
        item = manifest.get("item") if isinstance(manifest.get("item"), Mapping) else {}
        candidate = item.get("candidate") if isinstance(item.get("candidate"), Mapping) else {}
        promotion = item.get("promotion") if isinstance(item.get("promotion"), Mapping) else {}
        source = manifest.get("source") if isinstance(manifest.get("source"), Mapping) else {}
        source_shot = (
            source.get("shot")
            if isinstance(source.get("shot"), Mapping)
            else {}
        )
        technical_qa = (
            candidate.get("technical_qa")
            if isinstance(candidate.get("technical_qa"), Mapping)
            else {}
        )
        node_id = str(promotion.get("production_graph_node_id") or "")
        job_id = str(candidate.get("job_id") or "")
        candidate_id = str(candidate.get("candidate_id") or "")
        source_shot_id = str(source_shot.get("shot_id") or "")
        if (
            item.get("state") != "approved"
            or technical_qa.get("status") != "pass"
            or not node_id
            or not job_id
            or safe_id(job_id) != job_id
            or not candidate_id
            or safe_id(candidate_id) != candidate_id
            or not source_shot_id
            or safe_id(source_shot_id) != source_shot_id
        ):
            continue
        media_path = candidate_file(store.run_dir(project_id, job_id), candidate_id)
        if media_path is None:
            continue
        mime_type = VIDEO_SUFFIX_TYPES.get(media_path.suffix.lower(), "")
        if not mime_type or mime_type != str(technical_qa.get("container") or ""):
            continue
        receipts[node_id] = {
            "manifest_id": str(manifest.get("manifest_id") or ""),
            "manifest_hash": str(manifest.get("manifest_hash") or ""),
            "job_id": job_id,
            "candidate_id": candidate_id,
            "source_shot_id": source_shot_id,
            "sha256": str(candidate.get("sha256") or ""),
            "byte_count": _positive_int(candidate.get("byte_count")),
            "preview_url": (
                f"/projects/{safe_id(project_id)}/approved-video-assets/"
                f"{safe_id(node_id)}/preview"
            ),
            "mime_type": mime_type,
            "container": str(technical_qa.get("container") or ""),
            "width": int(technical_qa.get("width") or 0),
            "height": int(technical_qa.get("height") or 0),
            "duration_sec": float(technical_qa.get("duration_sec") or 0),
            "codec": str(technical_qa.get("codec") or ""),
            "approval_graph_version": _positive_int(promotion.get("graph_version")),
            "_media_path": media_path,
        }
    return receipts


def _video_receipt_matches_node(
    receipt: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> bool:
    media_path = receipt.get("_media_path")
    expected_sha = str(receipt.get("sha256") or "")
    if (
        not hasattr(media_path, "is_file")
        or not media_path.is_file()
        or len(expected_sha) != 64
        or int(receipt.get("byte_count") or 0) <= 0
        or media_path.stat().st_size != int(receipt["byte_count"])
        or _file_sha256(media_path) != expected_sha
    ):
        return False
    return (
        receipt.get("manifest_id") == metadata.get("manifest_id")
        and receipt.get("manifest_hash") == metadata.get("manifest_hash")
        and receipt.get("job_id") == metadata.get("job_id")
        and receipt.get("candidate_id") == metadata.get("candidate_id")
        and (
            not metadata.get("source_shot_id")
            or receipt.get("source_shot_id") == metadata.get("source_shot_id")
        )
        and receipt.get("sha256") == metadata.get("sha256")
        and receipt.get("byte_count") == _positive_int(metadata.get("byte_count"))
        and int(receipt.get("width") or 0) > 0
        and int(receipt.get("height") or 0) > 0
        and float(receipt.get("duration_sec") or 0) > 0
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_approved_media(
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if len(candidates) == 1:
        return candidates[0]
    versioned = [
        candidate
        for candidate in candidates
        if int(candidate.get("approval_graph_version") or 0) > 0
    ]
    if not versioned:
        return None
    highest = max(int(candidate["approval_graph_version"]) for candidate in versioned)
    current = [
        candidate
        for candidate in versioned
        if int(candidate["approval_graph_version"]) == highest
    ]
    return current[0] if len(current) == 1 else None


def _positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _sequence_action_events(graph: Mapping[str, Any], action: str, body: Mapping[str, Any]) -> list[dict[str, Any]]:
    payload = dict(body.get("payload") or {})
    if action == "select_candidate":
        artifact_id = str(payload["artifact_id"])
        if artifact_id not in graph["artifacts"]: raise ProductionGraphError("candidate selection references unknown artifact")
        return [{"type": "artifact_selected", "selection_key": str(payload.get("selection_key") or "sequence_delivery"),
                 "artifact_id": artifact_id}]
    if action == "review_decision":
        review_id = str(payload["review_id"]); state = str(payload["state"])
        if review_id not in graph["reviews"] or state not in {"approved", "rejected"}:
            raise ProductionGraphError("review decision is invalid")
        return [{"type": "review_updated", "review_id": review_id, "state": state,
                 "evidence_refs": list(payload.get("evidence_refs") or graph["reviews"][review_id].get("evidence_refs", []))}]
    if action == "redo_rejected":
        review_id = str(payload["review_id"]); review = graph["reviews"].get(review_id)
        if not review or review.get("state") != "rejected": raise ProductionGraphError("redo requires a rejected review")
        work_id = f"redo-{review_id}-v{int(body['expected_graph_version']) + 1}"
        return [{"type": "work_created", "work_id": work_id,
                 "semantic_digest": canonical_digest({"redo": review_id, "version": body["expected_graph_version"]}),
                 "depends_on": [review["target_id"]]},
                {"type": "review_updated", "review_id": review_id, "state": "redo_planned"}]
    if action == "delivery_state":
        delivery_id = str(payload["delivery_id"]); state = str(payload["state"])
        if delivery_id not in graph["deliveries"] or state not in {"planned", "review_ready", "blocked"}:
            raise ProductionGraphError("delivery state is invalid")
        return [{"type": "delivery_updated", "delivery_id": delivery_id, "state": state}]
    raise ProductionGraphError("unsupported graph lifecycle action")
