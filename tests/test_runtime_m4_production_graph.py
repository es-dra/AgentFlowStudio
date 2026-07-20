from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_film_production_graph import READ_ONLY_SURFACES, compile_film_candidate, film_graph_projection
from apps.api.runtime_production_graph import (
    GraphIdempotencyConflict,
    GraphPlanningRequired,
    GraphVersionConflict,
    ProductionGraphStore,
    canonical_digest,
    execute_outside_graph_lock,
)
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_production_runs import real_story_recovery_route_enabled
from tools.evaluate_m4_canonical_production_graph import evaluate


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _candidate(tag: str, *, durations: list[int], character_names: list[str], scene_count: int = 1) -> dict:
    characters = [{"character_id": f"{tag}-character-{index}", "display_name": name, "aliases": []}
                  for index, name in enumerate(character_names, start=1)]
    scenes = [{"scene_id": f"{tag}-scene-{index}", "name": f"场景{index}", "lineage": [f"{tag}-revision"]}
              for index in range(1, scene_count + 1)]
    assets = [{"asset_id": f"{tag}-asset-{index}", "name": f"资产{index}", "kind": "reference"}
              for index in range(1, 3)]
    shots = [{"shot_id": f"{tag}-unit-{index}", "scene_id": scenes[(index - 1) % scene_count]["scene_id"],
              "duration_seconds": duration, "intent": f"意图{index}", "character_refs": [characters[0]["character_id"]],
              "asset_refs": [assets[(index - 1) % len(assets)]["asset_id"]]}
             for index, duration in enumerate(durations, start=1)]
    return {"schema_version": "afs.film_domain_pack.v0.1", "trusted_candidate": True, "source_digest": _digest(tag),
            "brief": {"brief_id": f"{tag}-brief"}, "script_revision": {"revision_id": f"{tag}-revision"},
            "characters": characters, "scenes": scenes, "assets": assets, "shots": shots,
            "delivery_id": f"{tag}-delivery", "timeline_refs": [f"{tag}-timeline"], "rights_refs": [f"{tag}-rights"]}


def _graph(tmp_path, project_id: str = "m4-project") -> ProductionGraphStore:
    return ProductionGraphStore(RuntimeStore(tmp_path / "runtime"))


@pytest.mark.parametrize("candidate", [
    _candidate("quiet", durations=[7, 11, 5], character_names=["林澈"], scene_count=1),
    _candidate("ensemble", durations=[3, 8, 6, 12, 4], character_names=["苏遥", "顾北", "田雨"], scene_count=3),
    _candidate("visual", durations=[9, 2, 14, 6], character_names=["岚"], scene_count=2),
])
def test_arbitrary_typed_candidates_compile_without_story_defaults(tmp_path, candidate):
    store = _graph(tmp_path)
    events = compile_film_candidate("m4-project", candidate)
    graph = store.append("m4-project", expected_version=0, idempotency_key=f"confirm-{candidate['brief']['brief_id']}",
                         semantic_digest=canonical_digest(candidate), events=events)
    assert graph["version"] == 1
    assert graph["reviews"] and graph["deliveries"]
    assert {item["metadata"]["duration_seconds"] for item in graph["nodes"].values() if item["category"] == "unit"} == set(candidate["shots"][index]["duration_seconds"] for index in range(len(candidate["shots"])))
    assert all(graph["provider_gates"][key] is False for key in graph["provider_gates"])


def test_untrusted_or_incomplete_candidate_fails_closed():
    with pytest.raises(GraphPlanningRequired):
        compile_film_candidate("m4-project", {"schema_version": "afs.film_domain_pack.v0.1", "trusted_candidate": False})


def test_all_m4_projections_share_one_graph_digest_and_legacy_is_read_only(tmp_path):
    store = _graph(tmp_path); candidate = _candidate("projection", durations=[4, 7], character_names=["沈一"])
    graph = store.append("m4-project", expected_version=0, idempotency_key="confirm", semantic_digest=canonical_digest(candidate), events=compile_film_candidate("m4-project", candidate))
    projections = [film_graph_projection(graph, surface) for surface in READ_ONLY_SURFACES]
    assert {(item["graph_version"], item["graph_digest"]) for item in projections} == {(graph["version"], graph["graph_digest"])}
    assert all(item["migration_state"] == "read_only_graph_projection" for item in projections)


def test_stale_and_parallel_writes_reject_and_idempotent_replay_is_stable(tmp_path):
    store = _graph(tmp_path); candidate = _candidate("conflict", durations=[5, 8], character_names=["纪宁"]); events = compile_film_candidate("m4-project", candidate)
    first = store.append("m4-project", expected_version=0, idempotency_key="same", semantic_digest=canonical_digest(candidate), events=events)
    replay = store.append("m4-project", expected_version=0, idempotency_key="same", semantic_digest=canonical_digest(candidate), events=events)
    assert replay["idempotent_replay"] is True and replay["graph_digest"] == first["graph_digest"]
    with pytest.raises(GraphIdempotencyConflict): store.append("m4-project", expected_version=1, idempotency_key="same", semantic_digest=_digest("other"), events=events)
    with pytest.raises(GraphVersionConflict): store.append("m4-project", expected_version=0, idempotency_key="next", semantic_digest=_digest("next"), events=events)


def test_attempt_is_durable_before_adapter_runs_reuses_artifact_and_recovers_crash(tmp_path):
    store = _graph(tmp_path); candidate = _candidate("work", durations=[6], character_names=["童舟"])
    graph = store.append("m4-project", expected_version=0, idempotency_key="confirm", semantic_digest=canonical_digest(candidate), events=compile_film_candidate("m4-project", candidate))
    work_id = "work-work-unit-1"; observed: list[str] = []

    def adapter(attempt):
        observed.append(attempt["attempt_id"])
        assert store.load("m4-project")["version"] >= graph["version"]  # proves no graph lock is held during dispatch
        return {"draft": "provider-free candidate"}

    complete = execute_outside_graph_lock(store, "m4-project", work_id=work_id, semantic_digest=_digest("paid-semantic"), lease_owner="test", adapter=adapter)
    assert complete["status"] == "completed" and observed
    reused = execute_outside_graph_lock(store, "m4-project", work_id=work_id, semantic_digest=_digest("paid-semantic"), lease_owner="test", adapter=lambda _attempt: pytest.fail("must reuse"))
    assert reused["status"] == "reused"

    with pytest.raises(RuntimeError):
        execute_outside_graph_lock(store, "m4-project", work_id=work_id, semantic_digest=_digest("crash-semantic"), lease_owner="test", adapter=lambda _attempt: (_ for _ in ()).throw(RuntimeError("crash")))
    after = store.load("m4-project")
    assert any(item["state"] == "reconcile_required" for item in after["attempts"].values())
    retried = execute_outside_graph_lock(store, "m4-project", work_id=work_id, semantic_digest=_digest("crash-semantic"), lease_owner="test", retry_token="retry-1", adapter=lambda _attempt: {"draft": "new artifact version"})
    assert retried["status"] == "completed"
    assert len(after["attempts"]) < len(retried["graph"]["attempts"])


def test_dependency_invalidation_only_marks_proven_descendants(tmp_path):
    store = _graph(tmp_path); candidate = _candidate("deps", durations=[4, 9], character_names=["杜衡"], scene_count=2)
    graph = store.append("m4-project", expected_version=0, idempotency_key="confirm", semantic_digest=canonical_digest(candidate), events=compile_film_candidate("m4-project", candidate))
    changed = "deps-character-1"
    invalidated = store.invalidate("m4-project", expected_version=graph["version"], idempotency_key="invalidate", changed_node_ids=[changed])
    assert invalidated["nodes"]["deps-unit-1"]["state"] == "invalidated"
    assert invalidated["nodes"]["deps-unit-2"]["state"] == "invalidated"
    assert invalidated["nodes"]["deps-scene-1"]["state"] == "active"  # upstream/location is preserved


def test_m4_api_confirms_only_typed_candidate_and_projects_same_authority(tmp_path):
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    rejected = client.post("/projects/m4-api/m4/film-candidates/confirm", json={"idempotency_key": "bad", "candidate": {}})
    assert rejected.status_code == 409 and rejected.json()["error"] == "planning_required"
    candidate = _candidate("api", durations=[5, 9, 3], character_names=["何弥"], scene_count=2)
    confirmed = client.post("/projects/m4-api/m4/film-candidates/confirm", json={"expected_graph_version": 0, "idempotency_key": "confirm", "candidate": candidate})
    assert confirmed.status_code == 200, confirmed.text
    graph = confirmed.json()["graph"]
    projections = [client.get(f"/projects/m4-api/m4/projections/{surface}").json() for surface in READ_ONLY_SURFACES]
    assert {(item["graph_version"], item["graph_digest"]) for item in projections} == {(graph["version"], graph["graph_digest"])}


def test_m4_independent_structure_evaluator_passes():
    report = evaluate(Path(__file__).resolve().parents[1])
    assert report["verdict"] == "PASS"
    assert report["provider_dispatch_count"] == 0 and report["cost_usd"] == 0


def test_fixed_real_story_route_is_closed_without_explicit_recovery_gate(monkeypatch):
    monkeypatch.delenv("AFS_ENABLE_REAL_STORY_RECOVERY_ROUTE", raising=False)
    assert real_story_recovery_route_enabled() is False
