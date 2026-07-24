"""Single-writer, provider-free canonical production graph kernel.

The kernel deliberately has no domain vocabulary.  Domain packs compile typed
candidate input into generic graph records; UI and legacy surfaces only project
those records back out.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

from agentflow.harness.json_io import exclusive_file_lock
from apps.api.runtime_store import RuntimeStore, safe_id


GRAPH_SCHEMA_VERSION = "afs.production_graph.v0.1"
ZERO_PROVIDER_GATES = {name: False for name in ("llm", "image", "video", "audio", "asr", "vision", "external_download")}


class ProductionGraphError(RuntimeError):
    pass


class GraphVersionConflict(ProductionGraphError):
    pass


class GraphIdempotencyConflict(ProductionGraphError):
    pass


class GraphPlanningRequired(ProductionGraphError):
    pass


class GraphIntegrityError(ProductionGraphError):
    pass


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def graph_path(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "production_graph" / "graph.json"


def graph_lock_path(store: RuntimeStore, project_id: str) -> Path:
    return graph_path(store, project_id).with_suffix(".lock")


def graph_has_authority(store: RuntimeStore, project_id: str) -> bool:
    """Return whether a sealed, non-empty graph owns product mutations."""
    path = graph_path(store, project_id)
    if not path.exists():
        return False
    graph = ProductionGraphStore(store).load(project_id)
    return bool(graph.get("nodes"))


class ProductionGraphStore:
    """Append-only graph envelope with optimistic version and semantic replay."""

    def __init__(self, store: RuntimeStore) -> None:
        self.store = store

    def load(self, project_id: str) -> dict[str, Any]:
        path = graph_path(self.store, project_id)
        with exclusive_file_lock(graph_lock_path(self.store, project_id)):
            return self._read(path, project_id)

    def ensure(self, project_id: str) -> dict[str, Any]:
        path = graph_path(self.store, project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with exclusive_file_lock(graph_lock_path(self.store, project_id)):
            if path.exists():
                return self._read(path, project_id)
            graph = _empty_graph(project_id)
            self._write(path, graph)
            return graph

    def append(self, project_id: str, *, expected_version: int, idempotency_key: str,
               semantic_digest: str, events: list[Mapping[str, Any]]) -> dict[str, Any]:
        """Persist events once.  Callers must dispatch external work after this returns."""
        if not events:
            raise ProductionGraphError("graph mutation requires at least one event")
        path = graph_path(self.store, project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with exclusive_file_lock(graph_lock_path(self.store, project_id)):
            graph = self._read(path, project_id) if path.exists() else _empty_graph(project_id)
            replay = graph["idempotency"].get(idempotency_key)
            if replay:
                if replay["semantic_digest"] != semantic_digest:
                    raise GraphIdempotencyConflict("idempotency key has a different semantic request")
                return {**deepcopy(graph), "idempotent_replay": True}
            if graph["version"] != expected_version:
                raise GraphVersionConflict(f"expected graph version {expected_version}, current {graph['version']}")
            next_graph = deepcopy(graph)
            for raw in events:
                _apply_event(next_graph, dict(raw))
            next_graph["version"] += 1
            next_graph["updated_at"] = _now()
            next_graph["idempotency"][idempotency_key] = {"semantic_digest": semantic_digest, "version": next_graph["version"]}
            _seal(next_graph)
            self._write(path, next_graph)
            return {**deepcopy(next_graph), "idempotent_replay": False}

    def reserve_attempt(self, project_id: str, *, expected_version: int, idempotency_key: str,
                        work_id: str, semantic_digest: str, lease_owner: str) -> dict[str, Any]:
        graph = self.ensure(project_id)
        reusable = _selected_artifact_for_semantic(graph, semantic_digest)
        if reusable:
            return {"status": "reused", "graph": graph, "artifact_version": reusable, "provider_dispatch_count": 0}
        attempt_id = f"attempt-{uuid4().hex[:16]}"
        event = {"type": "attempt_reserved", "attempt_id": attempt_id, "work_id": work_id,
                 "semantic_digest": semantic_digest, "lease_owner": lease_owner, "lease_token": uuid4().hex,
                 "state": "reserved"}
        updated = self.append(project_id, expected_version=expected_version, idempotency_key=idempotency_key,
                              semantic_digest=canonical_digest({"reserve": semantic_digest, "work_id": work_id}), events=[event])
        if updated.get("idempotent_replay"):
            matching = [item for item in updated["attempts"].values() if item.get("work_id") == work_id and item.get("semantic_digest") == semantic_digest]
            if not matching:
                raise GraphIntegrityError("reservation replay has no durable attempt")
            prior = max(matching, key=lambda item: item.get("attempt_number", 0))
            return {"status": "reconcile_required" if prior.get("state") in {"dispatched", "reconcile_required"} else "replayed",
                    "graph": updated, "attempt": prior, "provider_dispatch_count": 0}
        return {"status": "reserved", "graph": updated, "attempt": updated["attempts"][attempt_id], "provider_dispatch_count": 0}

    def mark_dispatched(self, project_id: str, *, expected_version: int, attempt_id: str, lease_token: str) -> dict[str, Any]:
        return self.append(project_id, expected_version=expected_version, idempotency_key=f"dispatch-{attempt_id}",
                           semantic_digest=canonical_digest({"attempt": attempt_id, "lease": lease_token, "state": "dispatched"}),
                           events=[{"type": "attempt_state", "attempt_id": attempt_id, "lease_token": lease_token, "state": "dispatched"}])

    def complete_attempt(self, project_id: str, *, expected_version: int, attempt_id: str, lease_token: str,
                         artifact_digest: str, candidate_payload: Mapping[str, Any]) -> dict[str, Any]:
        artifact_id = f"artifact-{uuid4().hex[:16]}"
        events = [
            {"type": "artifact_recorded", "artifact_id": artifact_id, "attempt_id": attempt_id,
             "artifact_digest": artifact_digest, "payload": dict(candidate_payload)},
            {"type": "attempt_state", "attempt_id": attempt_id, "lease_token": lease_token, "state": "succeeded",
             "artifact_id": artifact_id},
        ]
        return self.append(project_id, expected_version=expected_version, idempotency_key=f"complete-{attempt_id}",
                           semantic_digest=canonical_digest({"attempt": attempt_id, "artifact": artifact_digest}), events=events)

    def select_artifact(self, project_id: str, *, expected_version: int, idempotency_key: str,
                        selection_key: str, artifact_id: str) -> dict[str, Any]:
        return self.append(project_id, expected_version=expected_version, idempotency_key=idempotency_key,
                           semantic_digest=canonical_digest({"selection": selection_key, "artifact": artifact_id}),
                           events=[{"type": "artifact_selected", "selection_key": selection_key, "artifact_id": artifact_id}])

    def invalidate(self, project_id: str, *, expected_version: int, idempotency_key: str,
                   changed_node_ids: list[str]) -> dict[str, Any]:
        graph = self.load(project_id)
        descendants = _descendants(graph, set(changed_node_ids))
        return self.append(project_id, expected_version=expected_version, idempotency_key=idempotency_key,
                           semantic_digest=canonical_digest({"changed": sorted(changed_node_ids), "descendants": sorted(descendants)}),
                           events=[{"type": "nodes_invalidated", "changed_node_ids": changed_node_ids,
                                    "invalidated_node_ids": sorted(descendants),
                                    "dependency_evidence": _dependency_evidence(graph, set(changed_node_ids), descendants)}])

    def reconcile(self, project_id: str, *, expected_version: int, attempt_id: str) -> dict[str, Any]:
        """A crash after dispatch becomes durable reconciliation, never a blind redispatch."""
        return self.append(project_id, expected_version=expected_version, idempotency_key=f"reconcile-{attempt_id}",
                           semantic_digest=canonical_digest({"attempt": attempt_id, "reconcile": True}),
                           events=[{"type": "attempt_reconcile_required", "attempt_id": attempt_id}])

    def _read(self, path: Path, project_id: str) -> dict[str, Any]:
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GraphIntegrityError("canonical production graph is unreadable") from exc
        if not isinstance(graph, dict) or graph.get("schema_version") != GRAPH_SCHEMA_VERSION or graph.get("project_id") != project_id:
            raise GraphIntegrityError("canonical production graph scope/schema mismatch")
        stored = graph.get("graph_digest")
        check = {key: value for key, value in graph.items() if key != "graph_digest"}
        if stored != canonical_digest(check):
            raise GraphIntegrityError("canonical production graph digest mismatch")
        _validate_graph(graph)
        return graph

    def _write(self, path: Path, graph: Mapping[str, Any]) -> None:
        _validate_graph(graph)
        _atomic_json(path, graph)


def execute_outside_graph_lock(store: ProductionGraphStore, project_id: str, *, work_id: str, semantic_digest: str,
                               lease_owner: str, adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]], retry_token: str = "") -> dict[str, Any]:
    """Provider-shaped adapter seam.  No graph lock is held while ``adapter`` runs."""
    graph = store.ensure(project_id)
    reservation_key = f"reserve-{semantic_digest}" if not retry_token else f"reserve-{semantic_digest}-{retry_token}"
    reservation = store.reserve_attempt(project_id, expected_version=graph["version"], idempotency_key=reservation_key,
                                        work_id=work_id, semantic_digest=semantic_digest, lease_owner=lease_owner)
    if reservation["status"] != "reserved":
        return reservation
    attempt = reservation["attempt"]
    dispatched = store.mark_dispatched(project_id, expected_version=reservation["graph"]["version"], attempt_id=attempt["attempt_id"], lease_token=attempt["lease_token"])
    try:
        output = dict(adapter({"attempt_id": attempt["attempt_id"], "semantic_digest": semantic_digest}))
    except BaseException:
        store.reconcile(project_id, expected_version=dispatched["version"], attempt_id=attempt["attempt_id"])
        raise
    completed = store.complete_attempt(project_id, expected_version=dispatched["version"], attempt_id=attempt["attempt_id"],
                                       lease_token=attempt["lease_token"], artifact_digest=canonical_digest(output), candidate_payload=output)
    return {"status": "completed", "graph": completed, "attempt_id": attempt["attempt_id"], "provider_dispatch_count": 0}


def graph_projection(graph: Mapping[str, Any], *, surface: str) -> dict[str, Any]:
    return {"surface": surface, "migration_state": "read_only_graph_projection", "project_id": graph["project_id"],
            "graph_version": graph["version"], "graph_digest": graph["graph_digest"], "nodes": deepcopy(graph["nodes"]),
            "relations": deepcopy(graph["relations"]), "provider_dispatch_count": 0}


def _empty_graph(project_id: str) -> dict[str, Any]:
    graph = {"schema_version": GRAPH_SCHEMA_VERSION, "project_id": project_id, "version": 0, "events": [], "nodes": {},
             "relations": [], "work": {}, "attempts": {}, "artifacts": {}, "selections": {}, "reviews": {}, "deliveries": {},
             "idempotency": {}, "provider_gates": dict(ZERO_PROVIDER_GATES), "created_at": _now(), "updated_at": _now(),
             "migration": {"legacy_surfaces": "read_only_projection_only", "legacy_writeback": "rejected_for_m4_graph_slice"}}
    _seal(graph)
    return graph


def _apply_event(graph: dict[str, Any], event: dict[str, Any]) -> None:
    event_type = str(event.get("type") or "")
    event["event_id"] = event.get("event_id") or f"event-{uuid4().hex[:16]}"
    event["recorded_at"] = _now()
    if event_type == "node_upserted":
        node = dict(event.get("node") or {})
        node_id = str(node.get("node_id") or "")
        if not node_id: raise ProductionGraphError("node event requires node_id")
        graph["nodes"][node_id] = {**node, "state": node.get("state", "active")}
    elif event_type == "relation_upserted":
        relation = {key: event.get(key) for key in ("from_id", "to_id", "relation_type")}
        if not all(relation.values()): raise ProductionGraphError("relation event is incomplete")
        if relation not in graph["relations"]: graph["relations"].append(relation)
    elif event_type == "relation_removed":
        relation = {key: event.get(key) for key in ("from_id", "to_id", "relation_type")}
        if not all(relation.values()): raise ProductionGraphError("relation removal is incomplete")
        graph["relations"] = [item for item in graph["relations"] if item != relation]
    elif event_type == "work_created":
        work_id = str(event.get("work_id") or "")
        if not work_id: raise ProductionGraphError("work event requires work_id")
        graph["work"][work_id] = {"work_id": work_id, "state": "planned", "semantic_digest": event.get("semantic_digest", ""), "depends_on": list(event.get("depends_on", []))}
    elif event_type == "attempt_reserved":
        if event["work_id"] not in graph["work"]: raise ProductionGraphError("attempt references unknown work")
        graph["attempts"][event["attempt_id"]] = {key: event.get(key) for key in ("attempt_id", "work_id", "semantic_digest", "lease_owner", "lease_token", "state")}
        graph["attempts"][event["attempt_id"]]["attempt_number"] = 1 + sum(item["work_id"] == event["work_id"] for item in graph["attempts"].values() if item["attempt_id"] != event["attempt_id"])
    elif event_type == "attempt_state":
        attempt = graph["attempts"].get(event.get("attempt_id"))
        if not attempt or attempt.get("lease_token") != event.get("lease_token"): raise ProductionGraphError("attempt lease mismatch")
        attempt["state"] = event["state"]
        if event.get("artifact_id"): attempt["artifact_id"] = event["artifact_id"]
    elif event_type == "attempt_reconcile_required":
        attempt = graph["attempts"].get(event.get("attempt_id"))
        if not attempt: raise ProductionGraphError("unknown attempt")
        attempt["state"] = "reconcile_required"
    elif event_type == "artifact_recorded":
        attempt = graph["attempts"].get(event.get("attempt_id"))
        if not attempt: raise ProductionGraphError("artifact references unknown attempt")
        graph["artifacts"][event["artifact_id"]] = {"artifact_id": event["artifact_id"], "attempt_id": event["attempt_id"], "semantic_digest": attempt["semantic_digest"], "artifact_digest": event["artifact_digest"], "candidate": dict(event.get("payload") or {}), "version": 1, "state": "candidate"}
    elif event_type == "artifact_selected":
        if event.get("artifact_id") not in graph["artifacts"]: raise ProductionGraphError("selection references unknown artifact")
        graph["selections"][event["selection_key"]] = {"artifact_id": event["artifact_id"], "version": len(graph["selections"]) + 1}
    elif event_type == "review_recorded":
        review_id = str(event.get("review_id") or "")
        if not review_id or event.get("target_id") not in graph["nodes"]: raise ProductionGraphError("review references unknown target")
        graph["reviews"][review_id] = {"review_id": review_id, "target_id": event["target_id"], "state": event.get("state", "pending"),
                                        "evidence_refs": list(event.get("evidence_refs", []))}
    elif event_type == "review_updated":
        review = graph["reviews"].get(event.get("review_id"))
        if not review: raise ProductionGraphError("review update references unknown review")
        if event.get("state") not in {"pending", "approved", "rejected", "redo_planned"}:
            raise ProductionGraphError("unsupported review state")
        review["state"] = event["state"]
        review["evidence_refs"] = list(event.get("evidence_refs", review.get("evidence_refs", [])))
    elif event_type == "delivery_recorded":
        delivery_id = str(event.get("delivery_id") or "")
        if not delivery_id or event.get("target_id") not in graph["nodes"]: raise ProductionGraphError("delivery references unknown target")
        graph["deliveries"][delivery_id] = {"delivery_id": delivery_id, "target_id": event["target_id"], "state": event.get("state", "planned"),
                                              "timeline_refs": list(event.get("timeline_refs", [])), "rights_refs": list(event.get("rights_refs", [])),
                                              "cost_refs": list(event.get("cost_refs", [])), "provenance_refs": list(event.get("provenance_refs", []))}
    elif event_type == "delivery_updated":
        delivery = graph["deliveries"].get(event.get("delivery_id"))
        if not delivery: raise ProductionGraphError("delivery update references unknown delivery")
        if event.get("state") not in {"planned", "review_ready", "blocked"}:
            raise ProductionGraphError("unsupported delivery state")
        delivery["state"] = event["state"]
    elif event_type == "nodes_invalidated":
        for node_id in event.get("invalidated_node_ids", []):
            if node_id in graph["nodes"]: graph["nodes"][node_id]["state"] = "invalidated"
    elif event_type == "node_metadata_updated":
        node = graph["nodes"].get(event.get("node_id"))
        if not node: raise ProductionGraphError("mutation references unknown node")
        node.setdefault("metadata", {}).update(dict(event.get("patch") or {}))
        node["state"] = "active"
    elif event_type == "node_state_updated":
        node = graph["nodes"].get(event.get("node_id"))
        if not node: raise ProductionGraphError("state update references unknown node")
        if event.get("state") not in {"active", "invalidated"}:
            raise ProductionGraphError("unsupported node state")
        node["state"] = event["state"]
        node.setdefault("metadata", {}).update(dict(event.get("metadata_patch") or {}))
    else:
        raise ProductionGraphError(f"unsupported graph event {event_type}")
    graph["events"].append(event)


def _selected_artifact_for_semantic(graph: Mapping[str, Any], semantic_digest: str) -> dict[str, Any] | None:
    for artifact in graph["artifacts"].values():
        if artifact.get("semantic_digest") == semantic_digest and artifact.get("state") == "candidate": return deepcopy(artifact)
    return None


def _descendants(graph: Mapping[str, Any], changed: set[str]) -> set[str]:
    descendants = set(changed); frontier = set(changed)
    while frontier:
        next_ids = {relation["to_id"] for relation in graph["relations"] if relation["from_id"] in frontier} - descendants
        descendants.update(next_ids); frontier = next_ids
    return descendants - changed


def impacted_descendants(graph: Mapping[str, Any], changed_node_ids: list[str]) -> dict[str, Any]:
    changed = set(changed_node_ids)
    if not changed <= set(graph.get("nodes", {})): raise ProductionGraphError("impact preview references unknown node")
    descendants = _descendants(graph, changed)
    return {"changed_node_ids": sorted(changed), "invalidated_node_ids": sorted(descendants),
            "preserved_node_ids": sorted(set(graph["nodes"]) - descendants - changed),
            "dependency_evidence": _dependency_evidence(graph, changed, descendants)}


def _dependency_evidence(graph: Mapping[str, Any], changed: set[str], descendants: set[str]) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    frontier = set(changed)
    reached = set(changed)
    while frontier:
        layer = [relation for relation in graph["relations"]
                 if relation["from_id"] in frontier and relation["to_id"] in descendants]
        evidence.extend(dict(relation) for relation in layer)
        next_ids = {relation["to_id"] for relation in layer} - reached
        reached.update(next_ids)
        frontier = next_ids
    return evidence


def _seal(graph: dict[str, Any]) -> None:
    graph.pop("graph_digest", None); graph["graph_digest"] = canonical_digest(graph)


def _validate_graph(graph: Mapping[str, Any]) -> None:
    if graph.get("schema_version") != GRAPH_SCHEMA_VERSION: raise GraphIntegrityError("unsupported graph schema")
    if any(graph.get("provider_gates", {}).get(key) for key in ZERO_PROVIDER_GATES): raise GraphIntegrityError("M4 graph keeps provider gates closed")
    node_ids = set(graph.get("nodes", {}))
    for relation in graph.get("relations", []):
        if relation.get("from_id") not in node_ids or relation.get("to_id") not in node_ids: raise GraphIntegrityError("relation references missing node")


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent)); temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":")); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists(): temp_path.unlink()


def _now() -> str:
    return datetime.now(UTC).isoformat()
