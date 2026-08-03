"""AuthoritativeScriptFact → Production Graph feed (feature-flagged side channel)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_authoritative_facts_graph import (
    FEED_PRODUCTION_GRAPH_ENV,
    NAMESPACED_REVISION_NODES_ENV,
    authoritative_fact_graph_node_id,
    authoritative_revision_graph_node_id,
    candidate_facts_feed_production_graph_enabled,
    compile_authoritative_facts_to_graph_events,
    feed_authoritative_facts_to_production_graph,
    namespaced_revision_nodes_enabled,
)
from apps.api.runtime_candidate_confirmation import (
    CONFIRMATION_LOOP_ENV,
    RECOVERABLE_GRAPH_FEED_ENV,
    GraphFeedStatus,
    inject_raw_junk_candidate,
    load_ledger,
    recoverable_graph_feed_enabled,
    save_ledger,
)
from datetime import datetime, timezone

from apps.api.runtime_candidate_fact_status import (
    AuthoritativeScriptFact,
    CandidateFact,
    CandidateStatus,
    ClaimedText,
    EvidenceSpan,
)
from apps.api.runtime_film_production_graph import compile_film_candidate
from apps.api.runtime_m6_script_plan_asset_bible import (
    IMPROVED_EXTRACTION_ENV,
    M6_REUSE_SCRIPT_TRUTH_REVISION_ENV,
    build_m6_script_plan_asset_bible,
)
from apps.api.runtime_production_graph import (
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
)
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


SCRIPTS = Path(__file__).resolve().parents[1] / "docs" / "internal-notes" / "test-scripts-character-scene"
SEA = (SCRIPTS / "02_industry_standard_letter_by_the_sea.txt").read_text(encoding="utf-8")
PHOTO = (SCRIPTS / "04_mixed_format_old_photo.txt").read_text(encoding="utf-8")
HOME = (SCRIPTS / "03_labeled_fields_homecoming.txt").read_text(encoding="utf-8")


def _client(tmp_path) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=tmp_path))


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post("/projects", json={"project_id": project_id, "goal": f"{project_id} story"})
    assert response.status_code == 200, response.text


def _create_revision(client: TestClient, project_id: str, text: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": text},
    )
    assert response.status_code == 200, response.text
    return response.json()["revision"]


def _enable_confirmation(monkeypatch) -> None:
    monkeypatch.setenv(CONFIRMATION_LOOP_ENV, "true")
    monkeypatch.setenv(IMPROVED_EXTRACTION_ENV, "true")


def _refresh(client: TestClient, project_id: str, revision: dict) -> dict:
    response = client.post(
        f"/projects/{project_id}/candidate-facts/review/refresh",
        json={
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


_DIGEST = "a" * 64


def _auth_fact(**overrides) -> AuthoritativeScriptFact:
    base = {
        "authoritative_fact_id": "af_char_1",
        "source_candidate_fact_id": "cf_1",
        "project_id": "proj_unit",
        "source_revision_id": "scrrev_abc",
        "source_revision_digest": _DIGEST,
        "field_path": "identity.display_name",
        "entity_kind": "character",
        "entity_id": "char_1",
        "text": "苏晴",
        "evidence_spans": [EvidenceSpan(start=0, end=2, quote="苏晴")],
        "promotion_kind": "human_confirmation",
        "human_confirmed_by": "tester",
        "promoted_at": datetime(2026, 8, 3, tzinfo=timezone.utc),
        "source_confidence": 0.9,
    }
    base.update(overrides)
    return AuthoritativeScriptFact(**base)


def test_feed_gate_defaults_off(monkeypatch) -> None:
    monkeypatch.delenv(FEED_PRODUCTION_GRAPH_ENV, raising=False)
    monkeypatch.delenv(NAMESPACED_REVISION_NODES_ENV, raising=False)
    monkeypatch.delenv(RECOVERABLE_GRAPH_FEED_ENV, raising=False)
    assert candidate_facts_feed_production_graph_enabled() is False
    assert namespaced_revision_nodes_enabled() is False
    assert recoverable_graph_feed_enabled() is False


def test_compile_rejects_non_authoritative() -> None:
    candidate = CandidateFact(
        fact_id="cf_x",
        project_id="proj_unit",
        source_revision_id="scrrev_x",
        source_revision_digest=_DIGEST,
        field_path="identity.display_name",
        claim=ClaimedText(
            text="苏晴",
            confidence=0.8,
            evidence_spans=[EvidenceSpan(start=0, end=2, quote="苏晴")],
        ),
        status=CandidateStatus.EXTRACTED_FROM_TEXT,
        entity_kind="character",
        entity_id="char_1",
    )
    with pytest.raises(TypeError, match="AuthoritativeScriptFact"):
        compile_authoritative_facts_to_graph_events([candidate])  # type: ignore[list-item]


def test_compile_emits_provenance_and_categories() -> None:
    char = _auth_fact()
    scene = _auth_fact(
        authoritative_fact_id="af_scene_1",
        source_candidate_fact_id="cf_2",
        entity_kind="scene",
        entity_id="scene_1",
        field_path="scenes[0].name",
        text="海边小屋",
    )
    events = compile_authoritative_facts_to_graph_events([char, scene])
    types = [e["type"] for e in events]
    assert types.count("node_upserted") == 3  # revision + char + scene
    assert types.count("relation_upserted") == 2

    nodes = {e["node"]["node_id"]: e["node"] for e in events if e["type"] == "node_upserted"}
    char_node = nodes[authoritative_fact_graph_node_id(char)]
    scene_node = nodes[authoritative_fact_graph_node_id(scene)]
    assert char_node["category"] == "entity"
    assert scene_node["category"] == "location"
    assert char_node["metadata"]["authoritative_fact_id"] == "af_char_1"
    assert char_node["metadata"]["source_candidate_fact_id"] == "cf_1"
    assert char_node["metadata"]["source_revision_id"] == "scrrev_abc"
    assert scene_node["metadata"]["authoritative_fact_id"] == "af_scene_1"


def test_namespaced_revision_node_prevents_m6_semantic_collision(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    monkeypatch.setenv(NAMESPACED_REVISION_NODES_ENV, "true")
    monkeypatch.setenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, "true")
    project_id = "proj_collision_fixed"
    truth_id = "scrrev_collision_fixed"
    truth_digest = hashlib.sha256(HOME.encode("utf-8")).hexdigest()
    preview = build_m6_script_plan_asset_bible(
        project_id,
        {
            "source_kind": "script",
            "source_text": HOME,
            "source_revision_id": truth_id,
            "source_revision_digest": truth_digest,
            "revision_instruction": "",
            "parent_candidate_digest": "",
        },
    )
    candidate = preview["candidate"]
    fact = _auth_fact(
        project_id=project_id,
        source_revision_id=truth_id,
        source_revision_digest=truth_digest,
    )
    source_node_id = authoritative_revision_graph_node_id(fact)
    assert source_node_id == f"scripttruth-revision-{truth_id}-{truth_digest[:16]}"
    different_content_fact = fact.model_copy(
        update={"source_revision_digest": "b" * 64}
    )
    assert authoritative_revision_graph_node_id(different_content_fact) != source_node_id
    assert candidate["script_revision"]["revision_id"] == truth_id
    assert candidate["script_revision"]["draft_text"] != HOME
    assert candidate["source_digest"] != truth_digest

    graph_store = ProductionGraphStore(RuntimeStore(tmp_path))
    feed_result = feed_authoritative_facts_to_production_graph(
        graph_store,
        project_id,
        [fact],
    )
    before_m6 = graph_store.load(project_id)
    graph_store.append(
        project_id,
        expected_version=before_m6["version"],
        idempotency_key="collision-fixed-m6",
        semantic_digest=canonical_digest(candidate),
        events=compile_film_candidate(project_id, candidate),
    )
    graph = graph_store.load(project_id)

    assert feed_result["fed"] is True
    assert truth_id in graph["nodes"]
    assert source_node_id in graph["nodes"]
    assert graph["nodes"][truth_id]["metadata"] == {
        "source_digest": candidate["source_digest"]
    }
    assert graph["nodes"][source_node_id]["metadata"]["source_revision_digest"] == truth_digest
    assert graph["nodes"][source_node_id]["metadata"]["node_identity_kind"] == (
        "script_truth_revision_for_authoritative_facts"
    )
    assert {
        "from_id": source_node_id,
        "to_id": authoritative_fact_graph_node_id(fact),
        "relation_type": "derived_from",
    } in graph["relations"]


def test_feed_skipped_when_flag_off_does_not_touch_graph(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(FEED_PRODUCTION_GRAPH_ENV, raising=False)
    store = RuntimeStore(tmp_path)
    graph_store = ProductionGraphStore(store)
    project_id = "proj_feed_off"
    before = graph_store.ensure(project_id)
    result = feed_authoritative_facts_to_production_graph(graph_store, project_id, [_auth_fact()])
    after = graph_store.load(project_id)
    assert result["fed"] is False
    assert result["skipped"] is True
    assert FEED_PRODUCTION_GRAPH_ENV in (result["reason"] or "")
    assert after["version"] == before["version"] == 0
    assert after["nodes"] == {}


def test_api_flag_off_accept_does_not_write_graph(tmp_path, monkeypatch) -> None:
    _enable_confirmation(monkeypatch)
    monkeypatch.delenv(FEED_PRODUCTION_GRAPH_ENV, raising=False)
    client = _client(tmp_path)
    project_id = "proj_api_off"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, SEA)
    refreshed = _refresh(client, project_id, revision)
    suqing = next(item for item in refreshed["bundle"]["items"] if item["text"] == "苏晴")

    accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": suqing["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert accept.status_code == 200, accept.text
    body = accept.json()
    assert body["affects_production_graph"] is False
    assert body["production_graph_feed_enabled"] is False
    assert body["graph_feed"]["fed"] is False
    assert body["graph_feed"]["skipped"] is True
    assert "operation_status" not in body
    assert "graph_feed_records" not in body

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).ensure(project_id)
    assert graph["version"] == 0
    assert not any(nid.startswith("authfact-") for nid in graph["nodes"])


def test_api_flag_on_authoritative_facts_feed_graph_with_provenance(tmp_path, monkeypatch) -> None:
    _enable_confirmation(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_api_on"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, PHOTO)
    refreshed = _refresh(client, project_id, revision)
    items = refreshed["bundle"]["items"]

    mother = next(item for item in items if item["text"] == "母亲" and item["entity_kind"] == "character")
    attic = next(item for item in items if item["text"] == "阁楼" and item["entity_kind"] == "scene")
    pending_left = [
        item
        for item in items
        if item["fact_id"] not in {mother["fact_id"], attic["fact_id"]} and not item["is_missing_slot"]
    ]
    missing = [item for item in items if item["is_missing_slot"]]
    assert pending_left, "need at least one still-pending candidate to assert non-write"

    # Reject junk — must not create graph nodes
    store = RuntimeStore(tmp_path)
    ledger = load_ledger(store, project_id)
    junk = inject_raw_junk_candidate(ledger, junk_text="苏晴没", evidence_quote="苏晴没说话")
    save_ledger(store, ledger)
    reject = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "reject",
            "fact_id": junk.fact_id,
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "reason": "fragment",
        },
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["affects_production_graph"] is False
    assert reject.json()["graph_feed"]["fed"] is False

    edit_char = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": mother["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": "周丽",
            "reason": "proper name",
        },
    )
    assert edit_char.status_code == 200, edit_char.text
    char_body = edit_char.json()
    assert char_body["affects_production_graph"] is True
    assert char_body["production_graph_feed_enabled"] is True
    assert char_body["graph_feed"]["fed"] is True
    assert len(char_body["graph_feed"]["node_ids"]) == 1

    accept_scene = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": attic["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert accept_scene.status_code == 200, accept_scene.text
    scene_body = accept_scene.json()
    assert scene_body["graph_feed"]["fed"] is True

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    authfact_nodes = {
        nid: node
        for nid, node in graph["nodes"].items()
        if nid.startswith("authfact-")
    }
    assert len(authfact_nodes) == 2

    by_text = {node["metadata"]["text"]: node for node in authfact_nodes.values()}
    assert set(by_text) == {"周丽", "阁楼"}
    for node in authfact_nodes.values():
        meta = node["metadata"]
        assert meta["source"] == "authoritative_script_fact_feed"
        assert meta["authoritative_fact_id"]
        assert meta["source_candidate_fact_id"]
        assert meta["source_revision_id"] == revision["revision_id"]

    assert by_text["周丽"]["category"] == "entity"
    assert by_text["周丽"]["metadata"]["source_candidate_fact_id"] == mother["fact_id"]
    assert by_text["阁楼"]["category"] == "location"
    assert by_text["阁楼"]["metadata"]["source_candidate_fact_id"] == attic["fact_id"]

    # Still-pending / missing / rejected must not appear as graph nodes
    graph_texts = {node["metadata"].get("text") for node in authfact_nodes.values()}
    for item in pending_left:
        assert item["text"] not in graph_texts
    for item in missing:
        assert item["text"] not in graph_texts
    assert "苏晴没" not in graph_texts
    assert "母亲" not in graph_texts  # edited away before feed

    # Revision node + derived_from edges
    assert revision["revision_id"] in graph["nodes"]
    assert graph["nodes"][revision["revision_id"]]["category"] == "revision"
    for nid in authfact_nodes:
        assert {
            "from_id": revision["revision_id"],
            "to_id": nid,
            "relation_type": "derived_from",
        } in graph["relations"]


def test_graph_feed_failure_is_durable_and_retryable_without_reconfirmation(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_confirmation(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    monkeypatch.setenv(NAMESPACED_REVISION_NODES_ENV, "true")
    monkeypatch.setenv(RECOVERABLE_GRAPH_FEED_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_recoverable_feed"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, SEA)
    refreshed = _refresh(client, project_id, revision)
    suqing = next(item for item in refreshed["bundle"]["items"] if item["text"] == "苏晴")

    attempts = 0

    def flaky_feed(graph_store, target_project_id, facts):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ProductionGraphError("forced graph failure")
        return feed_authoritative_facts_to_production_graph(
            graph_store,
            target_project_id,
            facts,
        )

    monkeypatch.setattr(
        "apps.api.runtime_candidate_confirmation.feed_authoritative_facts_to_production_graph",
        flaky_feed,
    )
    accepted = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": suqing["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert accepted.status_code == 200, accepted.text
    accepted_body = accepted.json()
    authoritative_fact_id = accepted_body["result"]["authoritative_fact_id"]
    assert accepted_body["operation_status"] == "partial_success"
    assert accepted_body["confirmation_status"] == "succeeded"
    assert accepted_body["graph_feed_status"] == "failed"
    assert accepted_body["retry_available"] is True
    assert accepted_body["graph_feed"]["error"] == "forced graph failure"

    store = RuntimeStore(tmp_path)
    failed_ledger = load_ledger(store, project_id)
    failed_record = next(
        record
        for record in failed_ledger.authoritative_records
        if record.fact.authoritative_fact_id == authoritative_fact_id
    )
    assert failed_ledger.review_decisions[suqing["fact_id"]].value == "accepted"
    assert failed_record.graph_feed_status == GraphFeedStatus.FAILED
    assert failed_record.graph_feed_attempt_count == 1
    assert failed_record.graph_feed_last_error == "forced graph failure"
    assert len(failed_ledger.authoritative_records) == 1

    review = client.get(f"/projects/{project_id}/candidate-facts/review")
    status_row = next(
        row
        for row in review.json()["graph_feed_records"]
        if row["authoritative_fact_id"] == authoritative_fact_id
    )
    assert status_row["status"] == "failed"
    assert status_row["retry_available"] is True

    retry_payload = {
        "authoritative_fact_id": authoritative_fact_id,
        "source_revision_id": revision["revision_id"],
        "source_revision_digest": revision["source_digest"],
    }
    retried = client.post(
        f"/projects/{project_id}/candidate-facts/graph-feed/retry",
        json=retry_payload,
    )
    assert retried.status_code == 200, retried.text
    retried_body = retried.json()
    assert retried_body["operation_status"] == "succeeded"
    assert retried_body["confirmation_status"] == "already_succeeded"
    assert retried_body["graph_feed_status"] == "succeeded"
    assert retried_body["retry_available"] is False
    assert retried_body["graph_feed"]["fed"] is True

    succeeded_ledger = load_ledger(store, project_id)
    succeeded_record = next(
        record
        for record in succeeded_ledger.authoritative_records
        if record.fact.authoritative_fact_id == authoritative_fact_id
    )
    assert succeeded_record.graph_feed_status == GraphFeedStatus.SUCCEEDED
    assert succeeded_record.graph_feed_attempt_count == 2
    assert succeeded_record.graph_feed_last_error is None
    assert len(succeeded_ledger.authoritative_records) == 1
    assert attempts == 2

    graph_before_replay = ProductionGraphStore(store).load(project_id)
    replayed = client.post(
        f"/projects/{project_id}/candidate-facts/graph-feed/retry",
        json=retry_payload,
    )
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["graph_feed"]["reason"] == "graph_feed_already_succeeded"
    graph_after_replay = ProductionGraphStore(store).load(project_id)
    assert graph_after_replay["version"] == graph_before_replay["version"]
    assert attempts == 2
