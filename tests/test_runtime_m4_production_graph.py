from __future__ import annotations

import hashlib
import subprocess
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
from tools.evaluate_m5_sequence_workspace import evaluate as evaluate_m5


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
            "sequence": {"sequence_id": f"{tag}-sequence", "name": f"{tag}制作序列", "target_duration_seconds": sum(durations)},
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
    collision = _candidate("collision", durations=[5], character_names=["温言"])
    collision["sequence"]["sequence_id"] = collision["characters"][0]["character_id"]
    with pytest.raises(GraphPlanningRequired, match="unique across"):
        compile_film_candidate("m4-project", collision)


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


def test_m5_sequence_workspace_is_graph_backed_and_mutations_are_impact_confirmed(tmp_path):
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    empty = client.get("/projects/m5-api/m5/sequence-workspace")
    assert empty.json()["status"] == "planning_required"
    assert empty.json()["project_id"] == "m5-api"
    assert empty.json()["provider_dispatch_count"] == 0
    candidate = _candidate("m5", durations=[4, 8, 3], character_names=["许静", "卫南"], scene_count=2)
    confirmed = client.post("/projects/m5-api/m4/film-candidates/confirm", json={"expected_graph_version": 0, "idempotency_key": "confirm-m5", "candidate": candidate})
    graph = confirmed.json()["graph"]
    workspace = client.get("/projects/m5-api/m5/sequence-workspace").json()
    assert workspace["migration_state"] == "graph_backed_single_truth"
    assert len(workspace["sequence"]["sequences"]) == 1
    assert workspace["graph_digest"] == graph["graph_digest"] == workspace["storyboard"]["graph_digest"]
    preview = client.post("/projects/m5-api/m5/impact-preview", json={"changed_node_ids": ["m5-character-1"]}).json()
    assert preview["status"] == "preview" and preview["impact"]["invalidated_node_ids"]
    mutation = client.post("/projects/m5-api/m5/mutations/confirm", json={"expected_graph_version": graph["version"], "idempotency_key": "edit-m5", "node_id": "m5-character-1", "changed_node_ids": ["m5-character-1"], "patch": {"display_name": "许静（修订）"}})
    assert mutation.status_code == 200
    assert mutation.json()["receipt"]["graph_version"] == graph["version"] + 1


def test_m5_workspace_selects_one_graph_versioned_approved_image_per_shot(
    tmp_path,
) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    candidate = _candidate(
        "approved-media",
        durations=[6],
        character_names=["程墨"],
        scene_count=1,
    )
    graph = client.post(
        "/projects/m5-approved-media/m4/film-candidates/confirm",
        json={
            "expected_graph_version": 0,
            "idempotency_key": "confirm-approved-media",
            "candidate": candidate,
        },
    ).json()["graph"]
    shot_id = "approved-media-unit-1"
    graph_store = ProductionGraphStore(RuntimeStore(tmp_path / "runtime"))
    legacy = graph_store.append(
        "m5-approved-media",
        expected_version=graph["version"],
        idempotency_key="legacy-approved-media",
        semantic_digest=canonical_digest({"legacy": ["a", "b"]}),
        events=[
            *[
                {
                    "type": "node_upserted",
                    "node": {
                        "node_id": f"approved-{suffix}",
                        "category": "artifact",
                        "state": "active",
                        "metadata": {
                            "kind": "approved_image",
                            "image_asset_id": f"image-{suffix}",
                            "width": 1280,
                            "height": 720,
                        },
                    },
                }
                for suffix in ("a", "b")
            ],
            *[
                {
                    "type": "relation_upserted",
                    "from_id": shot_id,
                    "to_id": f"approved-{suffix}",
                    "relation_type": "approved_image",
                }
                for suffix in ("a", "b")
            ],
        ],
    )
    ambiguous = client.get(
        "/projects/m5-approved-media/m5/sequence-workspace"
    ).json()
    assert ambiguous["sequence"]["approved_media"] == []

    current_version = legacy["version"] + 1
    current = graph_store.append(
        "m5-approved-media",
        expected_version=legacy["version"],
        idempotency_key="current-approved-media",
        semantic_digest=canonical_digest({"current": "c"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "approved-c",
                    "category": "artifact",
                    "state": "active",
                    "metadata": {
                        "kind": "approved_image",
                        "image_asset_id": "image-c",
                        "width": 1280,
                        "height": 720,
                        "approval_graph_version": current_version,
                    },
                },
            },
            {
                "type": "relation_upserted",
                "from_id": shot_id,
                "to_id": "approved-c",
                "relation_type": "approved_image",
            },
        ],
    )
    selected = client.get(
        "/projects/m5-approved-media/m5/sequence-workspace"
    ).json()["sequence"]["approved_media"]
    assert len(selected) == 1
    assert selected[0]["media_node_id"] == "approved-c"
    assert selected[0]["approval_graph_version"] == current_version
    assert selected[0]["target_node_ids"] == [shot_id]

    graph_store.append(
        "m5-approved-media",
        expected_version=current["version"],
        idempotency_key="conflicting-approved-media",
        semantic_digest=canonical_digest({"conflict": "d"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "approved-d",
                    "category": "artifact",
                    "state": "active",
                    "metadata": {
                        "kind": "approved_image",
                        "image_asset_id": "image-d",
                        "width": 1280,
                        "height": 720,
                        "approval_graph_version": current_version,
                    },
                },
            },
            {
                "type": "relation_upserted",
                "from_id": shot_id,
                "to_id": "approved-d",
                "relation_type": "approved_image",
            },
        ],
    )
    tied = client.get(
        "/projects/m5-approved-media/m5/sequence-workspace"
    ).json()
    assert tied["sequence"]["approved_media"] == []


def test_m5_impact_preview_rejects_under_and_over_invalidation(tmp_path):
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    candidate = _candidate("impact", durations=[4, 9, 3], character_names=["乔安", "闻笙"], scene_count=2)
    graph = client.post("/projects/m5-impact/m4/film-candidates/confirm", json={
        "expected_graph_version": 0, "idempotency_key": "confirm-impact", "candidate": candidate}).json()["graph"]

    scene = client.post("/projects/m5-impact/m5/impact-preview", json={"changed_node_ids": ["impact-scene-1"]}).json()["impact"]
    assert {"impact-unit-1", "impact-unit-3", "impact-delivery"} <= set(scene["invalidated_node_ids"])
    assert "impact-unit-2" in scene["preserved_node_ids"]
    assert "impact-scene-2" in scene["preserved_node_ids"]

    shot = client.post("/projects/m5-impact/m5/impact-preview", json={"changed_node_ids": ["impact-unit-2"]}).json()["impact"]
    assert shot["invalidated_node_ids"] == ["impact-delivery"]
    assert {"impact-unit-1", "impact-unit-3", "impact-scene-1"} <= set(shot["preserved_node_ids"])
    assert shot["dependency_evidence"] == [{"from_id": "impact-unit-2", "to_id": "impact-delivery", "relation_type": "contributes_to"}]
    assert graph["version"] == 1


def test_m5_candidate_review_redo_and_delivery_actions_are_versioned_in_graph_only(tmp_path):
    runtime_root = tmp_path / "runtime"; client = TestClient(create_runtime_app(runtime_root=runtime_root))
    candidate = _candidate("lifecycle", durations=[3, 7], character_names=["周岚", "方启"], scene_count=2)
    confirmed = client.post("/projects/m5-lifecycle/m4/film-candidates/confirm", json={
        "expected_graph_version": 0, "idempotency_key": "confirm", "candidate": candidate}).json()["graph"]
    executed = client.post("/projects/m5-lifecycle/m4/work/work-lifecycle-unit-1/fake-execute", json={
        "candidate_payload": {"media_version": "draft-a"}, "semantic_digest": _digest("draft-a")}).json()
    graph = executed["graph"]
    artifact_id = next(iter(graph["artifacts"]))

    selected = client.post("/projects/m5-lifecycle/m5/actions/confirm", json={"expected_graph_version": graph["version"],
        "idempotency_key": "select", "action": "select_candidate", "payload": {"artifact_id": artifact_id}}).json()["graph"]
    review_id = next(iter(selected["reviews"]))
    rejected = client.post("/projects/m5-lifecycle/m5/actions/confirm", json={"expected_graph_version": selected["version"],
        "idempotency_key": "reject", "action": "review_decision", "payload": {"review_id": review_id, "state": "rejected"}}).json()["graph"]
    redone = client.post("/projects/m5-lifecycle/m5/actions/confirm", json={"expected_graph_version": rejected["version"],
        "idempotency_key": "redo", "action": "redo_rejected", "payload": {"review_id": review_id}}).json()["graph"]
    delivery_id = next(iter(redone["deliveries"]))
    delivered = client.post("/projects/m5-lifecycle/m5/actions/confirm", json={"expected_graph_version": redone["version"],
        "idempotency_key": "delivery", "action": "delivery_state", "payload": {"delivery_id": delivery_id, "state": "review_ready"}})
    assert delivered.status_code == 200
    final_graph = delivered.json()["graph"]
    assert final_graph["selections"] and final_graph["reviews"][review_id]["state"] == "redo_planned"
    assert any(work_id.startswith("redo-") for work_id in final_graph["work"])
    assert final_graph["deliveries"][delivery_id]["state"] == "review_ready"
    assert final_graph["selections"]["sequence_delivery"]["artifact_id"] == artifact_id
    workspace = client.get("/projects/m5-lifecycle/m5/sequence-workspace").json()
    assert workspace["graph_version"] == workspace["storyboard"]["graph_version"] == final_graph["version"]
    assert workspace["graph_digest"] == workspace["storyboard"]["graph_digest"] == final_graph["graph_digest"]
    assert workspace["sequence"]["selections"] and workspace["sequence"]["version_history"]
    assert not (runtime_root / "projects" / "m5-lifecycle" / "studio_state.json").exists()

    forbidden_parallel_write = client.put("/projects/m5-lifecycle/studio-state", json={"state": {
        "meta": {"projectId": "m5-lifecycle"}, "nodes": {"parallel": {"id": "parallel", "type": "text"}}}})
    assert forbidden_parallel_write.status_code == 409
    assert "production graph is authoritative" in forbidden_parallel_write.text

    stale = client.post("/projects/m5-lifecycle/m5/actions/confirm", json={"expected_graph_version": graph["version"],
        "idempotency_key": "stale", "action": "delivery_state", "payload": {"delivery_id": delivery_id, "state": "planned"}})
    assert stale.status_code == 409


def test_m5_canvas_projection_is_pruned_from_every_studio_persistence_snapshot():
    script = r'''
import { initialState, snapshotStudioState } from "./apps/studio/src/store-state.js";
const state = initialState("m5-persist");
state.nodes.user = { id: "user", type: "text", title: "用户文本", params: {} };
state.nodes.graph = { id: "graph", type: "shot", title: "图投影", params: { productionGraphProjection: "canonical_production_graph_projection" } };
state.nodes.legacy = { id: "legacy", type: "text", title: "旧投影", params: { productionGraphLegacyProjection: "read_only_legacy_projection" } };
state.edges.keep = { id: "keep", from: "user", to: "user", relation_type: "manual" };
state.edges.drop = { id: "drop", from: "user", to: "graph", relation_type: "production_graph_required_by" };
state.order = ["user", "graph", "legacy"];
state.production.production_graph_projection = { graph_version: 4, graph_digest: "a".repeat(64) };
const persisted = snapshotStudioState(state);
if (!persisted.nodes.user || persisted.nodes.graph || persisted.nodes.legacy || persisted.edges.drop || persisted.order.includes("graph") || persisted.order.includes("legacy")) process.exit(2);
if (persisted.production && Object.keys(persisted.production).length) process.exit(3);
'''
    completed = subprocess.run(["node", "--input-type=module", "-e", script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_m5_runtime_persistence_controller_cancels_pending_save_and_fails_closed():
    script = r'''
import { initialState } from "./apps/studio/src/store-state.js";
import { createRuntimePersistenceController } from "./apps/studio/src/store-runtime-persistence-controller.js";
const state = initialState("m5-mode");
let calls = 0;
const runtime = { saveStudioState: async () => { calls += 1; return { state_version: `v${calls}` }; } };
const notices = [];
const controller = createRuntimePersistenceController({ getRuntime: () => runtime, getState: () => state, notify: (meta) => notices.push(meta) });
controller.schedule();
controller.setMode("production_graph_read_only");
await new Promise((resolve) => setTimeout(resolve, 760));
await controller.flush();
if (calls !== 0) process.exit(2);
if (state.ui.saveState !== "制作图同步" || !state.ui.saveMessage.includes("同一制作图版本")) process.exit(3);
if (notices.at(-1)?.renderScope !== "save-status") process.exit(4);
controller.reset();
await controller.flush();
if (calls !== 1) process.exit(5);
'''
    completed = subprocess.run(["node", "--input-type=module", "-e", script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_m5_sequence_workspace_auth_is_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true"); monkeypatch.setenv("AFS_INVITE_CODES", "m5-owner-code,m5-other-code")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    def register(email: str, code: str) -> dict[str, str]:
        response = client.post("/auth/register", json={"email": email, "password": "strong-password-123",
            "display_name": email.split("@", 1)[0], "invite_code": code})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['session_token']}"}
    owner = register("m5-owner@example.com", "m5-owner-code"); other = register("m5-other@example.com", "m5-other-code")
    assert client.post("/projects", json={"project_id": "m5-owned", "goal": "auth"}, headers=owner).status_code == 200
    assert client.get("/projects/m5-owned/m5/sequence-workspace").status_code == 401
    assert client.get("/projects/m5-owned/m5/sequence-workspace", headers=owner).status_code == 200
    assert client.get("/projects/m5-owned/m5/sequence-workspace", headers=other).status_code == 403
    candidate = _candidate("owned", durations=[6, 4], character_names=["秦悦"], scene_count=1)
    payload = {"expected_graph_version": 0, "idempotency_key": "owner-confirm", "candidate": candidate}
    assert client.post("/projects/m5-owned/m4/film-candidates/confirm", json=payload).status_code == 401
    assert client.post("/projects/m5-owned/m4/film-candidates/confirm", json=payload, headers=other).status_code == 403
    assert client.post("/projects/m5-owned/m4/film-candidates/confirm", json=payload, headers=owner).status_code == 200


def test_m4_independent_structure_evaluator_passes():
    report = evaluate(Path(__file__).resolve().parents[1])
    assert report["verdict"] == "PASS"
    assert report["provider_dispatch_count"] == 0 and report["cost_usd"] == 0


def test_fixed_real_story_route_is_closed_without_explicit_recovery_gate(monkeypatch):
    monkeypatch.delenv("AFS_ENABLE_REAL_STORY_RECOVERY_ROUTE", raising=False)
    assert real_story_recovery_route_enabled() is False


def test_m5_adversarial_evaluator_rejects_parallel_truth_and_preserves_shell_reachability():
    report = evaluate_m5(Path(__file__).resolve().parents[1])
    assert report["verdict"] == "PASS", report["findings"]
    shell = (Path(__file__).resolve().parents[1] / "apps/studio/src/product-shell.js").read_text(encoding="utf-8")
    assert "return buildGraphSequenceWorkspace" not in shell
    assert all(token in shell for token in ("buildCanvasWorkspace", "buildStoryboardWorkspace", "buildAgentChat"))


def test_m5_adversarial_evaluator_rejects_each_critical_architecture_regression(tmp_path):
    root = Path(__file__).resolve().parents[1]
    relative_files = [
        "apps/studio/src/product-shell.js", "apps/studio/src/runtime-client.js",
        "apps/studio/src/production-graph-workspace-projection.js", "apps/studio/src/agent-chat-lifecycle.js",
        "apps/studio/src/store-state.js", "apps/studio/src/canvas-node-body.js",
        "apps/studio/src/prompt-bar.js",
        "apps/studio/src/store.js", "apps/studio/src/store-runtime-persistence-controller.js",
        "apps/api/runtime_film_production_graph.py", "apps/api/runtime_production_graph.py",
        "apps/api/runtime_studio_state.py",
    ]
    originals = {name: (root / name).read_text(encoding="utf-8") for name in relative_files}
    mutations = [
        ("apps/studio/src/product-shell.js", lambda text: text + "\nreturn buildGraphSequenceWorkspace;\n"),
        ("apps/studio/src/product-shell.js", lambda text: text.replace("buildAgentChat", "removedAgentChat")),
        ("apps/studio/src/production-graph-workspace-projection.js", lambda text: text.replace("applyProductionGraphCanvasProjection", "missingCanvasProjection")),
        ("apps/studio/src/runtime-client.js", lambda text: text.replace("confirmSequenceAction", "missingSequenceAction")),
        ("apps/api/runtime_film_production_graph.py", lambda text: text + "\n# studio_state write regression\n"),
        ("apps/api/runtime_film_production_graph.py", lambda text: text.replace("redo_rejected", "redo_removed")),
        ("apps/api/runtime_production_graph.py", lambda text: text.replace("review_updated", "review_update_removed")),
        ("apps/studio/src/product-shell.js", lambda text: text.replace("buildGraphCanvasStatus", "missingPlanningStatus")),
        ("apps/studio/src/store-state.js", lambda text: text.replace("projectedNodeIds", "untrackedProjectionIds")),
        ("apps/studio/src/store-runtime-persistence-controller.js", lambda text: text.replace("production_graph_read_only", "graph_write_enabled")),
        ("apps/studio/src/store.js", lambda text: text.replace("createRuntimePersistenceController", "inlineRuntimePersistenceState")),
        ("apps/studio/src/store.js", lambda text: text + "\nlet runtimePersistenceMode = 'studio_state'; if (runtimePersistenceMode) mode = 'production_graph_read_only';\n"),
        ("apps/studio/src/canvas-node-body.js", lambda text: text.replace("node.params?.productionGraphLegacyProjection", "false")),
        ("apps/studio/src/prompt-bar.js", lambda text: text.replace("node?.params?.productionGraphProjection", "false")),
        ("apps/api/runtime_studio_state.py", lambda text: text.replace("graph_has_authority(store, project_id)", "False")),
        ("apps/studio/src/product-shell.js", lambda text: text.replace("stageProductionGraphCandidateCommand", "candidateImportDisconnected")),
        ("apps/studio/src/product-shell.js", lambda text: text.replace("selectedGraphTarget", "graphSelectionDisconnected")),
    ]
    for index, (name, mutate) in enumerate(mutations):
        case_root = tmp_path / f"case-{index}"
        for relative, source in originals.items():
            target = case_root / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(source, encoding="utf-8")
        target = case_root / name; target.write_text(mutate(originals[name]), encoding="utf-8")
        report = evaluate_m5(case_root)
        assert report["verdict"] == "FAIL", (index, name, report)
