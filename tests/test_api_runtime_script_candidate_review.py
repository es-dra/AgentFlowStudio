from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import apps.api.runtime_script_core_truth as script_truth
from apps.api.runtime_script_core_truth import (
    ANALYSIS_CANDIDATE_SCHEMA_VERSION,
    ANALYSIS_REVIEW_SCHEMA_VERSION,
    CORE_ASSET_COMMAND_SCHEMA_VERSION,
)
from apps.api.runtime_service import create_runtime_app


def _client(runtime_root) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=runtime_root))


def _span(text: str, quote: str) -> dict:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _seed_candidate(client: TestClient, project_id: str = "script-review") -> tuple[dict, dict, list[dict]]:
    created = client.post("/projects", json={"project_id": project_id, "goal": "Review script facts"})
    assert created.status_code == 200, created.text
    source_text = "Mira enters the Archive Hall. Rowan waits beside the brass door."
    revision_response = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": source_text, "provenance": {"fixture": "review"}},
    )
    assert revision_response.status_code == 200, revision_response.text
    revision = revision_response.json()["revision"]
    candidate_response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
            "named_characters": [
                {
                    "display_name": "Mira",
                    "aliases": [],
                    "pronoun_links": [],
                    "evidence_spans": [_span(source_text, "Mira")],
                    "confidence": 0.99,
                    "status": "candidate",
                    "evidence_status": "extracted_from_text",
                    "extraction_method": "fixture_exact_span",
                }
            ],
            "main_scenes": [
                {
                    "name": "Archive Hall",
                    "evidence_spans": [_span(source_text, "Archive Hall")],
                    "confidence": 0.99,
                    "status": "candidate",
                    "evidence_status": "extracted_from_text",
                    "extraction_method": "fixture_exact_span",
                }
            ],
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert candidate_response.status_code == 200, candidate_response.text
    payload = candidate_response.json()
    return revision, payload["candidate"], payload["projection"]["assets"]


def _review_body(
    project_id: str,
    revision: dict,
    candidate: dict,
    asset: dict,
    *,
    decision: str,
    key: str,
    graph_version: int,
) -> dict:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "candidate_id": candidate["candidate_id"],
        "asset_version_id": asset["version_id"],
        "expected_asset_version": asset["version"],
        "expected_graph_version": graph_version,
        "idempotency_key": key,
        "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
        "decision": decision,
        "reason": f"fixture {decision}",
    }


def test_candidate_edit_review_graph_write_and_restart_recovery(tmp_path) -> None:
    project_id = "script-review-lifecycle"
    client = _client(tmp_path)
    revision, candidate, assets = _seed_candidate(client, project_id)
    character = next(item for item in assets if item["asset_type"] == "character")
    scene = next(item for item in assets if item["asset_type"] == "main_scene")

    assert {item["status"] for item in assets} == {"candidate"}
    assert client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]["nodes"] == {}

    edited = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "edit_asset",
            "target_asset_id": character["asset_id"],
            "patch": {"display_name": "Mira Vale"},
            "expected_asset_version": character["version"],
            "idempotency_key": "edit-mira-v1",
        },
    )
    assert edited.status_code == 200, edited.text
    edited_character = next(
        item for item in edited.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"]
    )
    assert edited_character["status"] == "modified"
    assert edited_character["version"] == 2
    assert edited_character["parent_version_id"] == character["version_id"]
    assert edited_character["evidence_status"] == "human_edited"
    assert edited_character["extraction_method"] == "human_edit"
    assert edited_character["evidence_spans"] == character["evidence_spans"]

    confirmed = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            edited_character,
            decision="confirm",
            key="confirm-mira-v2",
            graph_version=0,
        ),
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_payload = confirmed.json()
    assert confirmed_payload["asset"]["status"] == "confirmed"
    assert confirmed_payload["review_decision"]["decision"] == "confirmed"
    assert confirmed_payload["receipt"]["production_graph_node_id"] == character["asset_id"]
    assert confirmed_payload["graph"]["version"] == 1
    graph_metadata = confirmed_payload["graph"]["nodes"][character["asset_id"]]["metadata"]
    assert graph_metadata["source_digest"] == revision["source_digest"]
    assert graph_metadata["asset_version_id"] == confirmed_payload["asset"]["version_id"]
    assert graph_metadata["lineage"]["evidence_status"] == "human_edited"
    assert graph_metadata["lineage"]["extraction_method"] == "human_edit"
    assert {
        (item["from_id"], item["to_id"], item["relation_type"])
        for item in confirmed_payload["graph"]["relations"]
    } >= {(f"script-revision:{revision['revision_id']}", character["asset_id"], "analysis_confirmed")}

    replay = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            edited_character,
            decision="confirm",
            key="confirm-mira-v2",
            graph_version=0,
        ),
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["receipt"]["receipt_id"] == confirmed_payload["receipt"]["receipt_id"]
    assert replay.json()["graph"]["version"] == 1

    wrong_route_replay = client.post(
        f"/projects/{project_id}/script-revisions/not-the-reviewed-revision/analysis-assets/{character['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            edited_character,
            decision="confirm",
            key="confirm-mira-v2",
            graph_version=0,
        ),
    )
    assert wrong_route_replay.status_code == 409
    assert wrong_route_replay.json()["detail"]["error"] == "analysis_review_idempotency_conflict"

    rejected = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{scene['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            scene,
            decision="reject",
            key="reject-scene-v1",
            graph_version=1,
        ),
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["asset"]["status"] == "rejected"
    assert scene["asset_id"] not in rejected.json()["graph"]["nodes"]

    restarted = _client(tmp_path)
    recovered = restarted.get(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates"
    )
    assert recovered.status_code == 200, recovered.text
    recovered_assets = {item["asset_id"]: item for item in recovered.json()["assets"]}
    assert recovered_assets[character["asset_id"]]["status"] == "confirmed"
    assert recovered_assets[scene["asset_id"]]["status"] == "rejected"
    assert len(recovered.json()["review_decisions"]) == 2
    assert restarted.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]["version"] == 1


def test_new_script_revision_expires_open_candidates_and_blocks_stale_review(tmp_path) -> None:
    project_id = "script-review-expiry"
    client = _client(tmp_path)
    revision, candidate, assets = _seed_candidate(client, project_id)
    character = next(item for item in assets if item["asset_type"] == "character")

    next_revision = client.post(
        f"/projects/{project_id}/script-revisions",
        json={
            "source_kind": "script",
            "source_text": "Mira leaves the Archive Hall.",
            "parent_revision_id": revision["revision_id"],
        },
    )
    assert next_revision.status_code == 200, next_revision.text

    expired = client.get(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates"
    )
    assert expired.status_code == 200, expired.text
    assert expired.json()["candidates"][0]["status"] == "expired"
    assert {item["status"] for item in expired.json()["assets"]} == {"expired"}

    stale = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            character,
            decision="confirm",
            key="stale-confirm",
            graph_version=0,
        ),
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["error"] in {"current_revision_mismatch", "analysis_asset_expired"}
    assert client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]["nodes"] == {}


def test_graph_first_confirmation_recovers_state_write_failure_without_duplicate_fact(tmp_path, monkeypatch) -> None:
    project_id = "script-review-recovery"
    client = _client(tmp_path)
    revision, candidate, assets = _seed_candidate(client, project_id)
    character = next(item for item in assets if item["asset_type"] == "character")
    body = _review_body(
        project_id,
        revision,
        candidate,
        character,
        decision="confirm",
        key="recover-confirm",
        graph_version=0,
    )
    original_write = script_truth._write_state
    failed = False

    def fail_once(store, scoped_project_id, state):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected truth-state write failure")
        return original_write(store, scoped_project_id, state)

    monkeypatch.setattr(script_truth, "_write_state", fail_once)
    with pytest.raises(RuntimeError, match="injected truth-state write failure"):
        client.post(
            f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
            json=body,
        )
    monkeypatch.setattr(script_truth, "_write_state", original_write)

    graph_after_failure = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert graph_after_failure["version"] == 1
    assert character["asset_id"] in graph_after_failure["nodes"]

    recovered = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json=body,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["graph"]["version"] == 1
    assert recovered.json()["graph_idempotent_replay"] is True
    assert recovered.json()["asset"]["status"] == "confirmed"


def test_merge_alias_graph_write_recovers_truth_state_failure_without_duplicate_fact(tmp_path, monkeypatch) -> None:
    project_id = "script-alias-graph-recovery"
    client = _client(tmp_path)
    revision, candidate, assets = _seed_candidate(client, project_id)
    character = next(item for item in assets if item["asset_type"] == "character")
    confirmed = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            character,
            decision="confirm",
            key="confirm-before-alias",
            graph_version=0,
        ),
    )
    assert confirmed.status_code == 200, confirmed.text
    command = {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        "command_type": "merge_alias",
        "target_asset_id": character["asset_id"],
        "patch": {"alias": "M"},
        "expected_asset_version": confirmed.json()["asset"]["version"],
        "idempotency_key": "merge-mira-alias-recovery",
    }
    original_write = script_truth._write_state
    failed = False

    def fail_once(store, scoped_project_id, state):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected alias truth-state write failure")
        return original_write(store, scoped_project_id, state)

    monkeypatch.setattr(script_truth, "_write_state", fail_once)
    with pytest.raises(RuntimeError, match="injected alias truth-state write failure"):
        client.post(f"/projects/{project_id}/core-assets/commands/confirm", json=command)
    monkeypatch.setattr(script_truth, "_write_state", original_write)

    graph_after_failure = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert graph_after_failure["version"] == 2
    assert graph_after_failure["nodes"][character["asset_id"]]["metadata"]["aliases"] == ["M"]
    truth_after_failure = client.get(f"/projects/{project_id}/script-truth").json()["projection"]
    stale_character = next(item for item in truth_after_failure["assets"] if item["asset_id"] == character["asset_id"])
    assert stale_character["aliases"] == []

    recovered = client.post(f"/projects/{project_id}/core-assets/commands/confirm", json=command)
    assert recovered.status_code == 200, recovered.text
    recovered_character = next(
        item for item in recovered.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"]
    )
    assert recovered_character["aliases"] == ["M"]
    assert recovered.json()["receipt"]["production_graph_version"] == 2
    graph_after_recovery = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert graph_after_recovery["version"] == 2
    assert graph_after_recovery["nodes"][character["asset_id"]]["metadata"]["asset_version_id"] == recovered_character["version_id"]


def test_alias_merge_after_confirmed_asset_edit_reenters_review_before_graph_projection(tmp_path) -> None:
    project_id = "script-alias-after-confirmed-edit"
    client = _client(tmp_path)
    revision, candidate, assets = _seed_candidate(client, project_id)
    character = next(item for item in assets if item["asset_type"] == "character")
    confirmed = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            character,
            decision="confirm",
            key="confirm-before-edit-and-alias",
            graph_version=0,
        ),
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_character = confirmed.json()["asset"]

    edited = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "edit_asset",
            "target_asset_id": character["asset_id"],
            "patch": {"display_name": "Mira Vale"},
            "expected_asset_version": confirmed_character["version"],
            "idempotency_key": "edit-confirmed-mira-before-alias",
        },
    )
    assert edited.status_code == 200, edited.text
    edited_character = next(
        item for item in edited.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"]
    )
    assert edited_character["status"] == "modified"

    merged = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "merge_alias",
            "target_asset_id": character["asset_id"],
            "patch": {"alias": "M"},
            "expected_asset_version": edited_character["version"],
            "idempotency_key": "merge-alias-after-confirmed-edit",
        },
    )
    assert merged.status_code == 200, merged.text
    merged_character = next(
        item for item in merged.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"]
    )
    assert merged_character["status"] == "modified"
    assert merged_character["aliases"] == ["M"]
    assert merged.json()["receipt"]["production_graph_version"] == 0
    graph_before_review = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert graph_before_review["version"] == 1
    assert graph_before_review["nodes"][character["asset_id"]]["metadata"]["aliases"] == []

    reconfirmed = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            merged_character,
            decision="confirm",
            key="reconfirm-after-edit-and-alias",
            graph_version=1,
        ),
    )
    assert reconfirmed.status_code == 200, reconfirmed.text
    assert reconfirmed.json()["asset"]["status"] == "confirmed"
    assert reconfirmed.json()["asset"]["aliases"] == ["M"]
    assert reconfirmed.json()["graph"]["version"] == 2
    assert reconfirmed.json()["graph"]["nodes"][character["asset_id"]]["metadata"]["aliases"] == ["M"]


def test_name_command_graph_projection_preserves_existing_alias_idempotency_keys() -> None:
    class CapturingGraphStore:
        def __init__(self) -> None:
            self.keys: list[str] = []

        def ensure(self, _project_id: str) -> dict:
            return {
                "version": len(self.keys),
                "nodes": {
                    "asset_1": {
                        "node_id": "asset_1",
                        "category": "character",
                        "state": "active",
                        "metadata": {
                            "kind": "script_core_asset",
                            "asset_version_id": "assetver_1",
                            "aliases": [],
                        },
                    }
                },
            }

        def append(self, _project_id: str, **kwargs) -> dict:
            self.keys.append(kwargs["idempotency_key"])
            return {"version": len(self.keys)}

    graph_store = CapturingGraphStore()
    before = {
        "asset_id": "asset_1",
        "asset_type": "character",
        "status": "confirmed",
        "version_id": "assetver_1",
        "aliases": [],
    }
    after = {**before, "version_id": "assetver_2", "aliases": ["Alias"]}
    script_truth._project_confirmed_name_command_to_graph(
        graph_store,
        project_id="p1",
        preview={
            "command_id": "command_alias",
            "command_type": "merge_alias",
            "before": before,
            "after": after,
        },
    )
    script_truth._project_confirmed_name_command_to_graph(
        graph_store,
        project_id="p1",
        preview={
            "command_id": "command_scene",
            "command_type": "merge_scene_name",
            "before": {**before, "asset_type": "main_scene"},
            "after": {**after, "asset_type": "main_scene"},
        },
    )

    assert graph_store.keys == [
        "core-asset-alias:command_alias",
        "core-asset-scene-name:command_scene",
    ]


def test_merge_scene_name_graph_write_recovers_truth_state_failure_without_duplicate_fact(
    tmp_path,
    monkeypatch,
) -> None:
    project_id = "script-scene-name-graph-recovery"
    client = _client(tmp_path)
    revision, candidate, assets = _seed_candidate(client, project_id)
    scene = next(item for item in assets if item["asset_type"] == "main_scene")
    confirmed = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{scene['asset_id']}/review",
        json=_review_body(
            project_id,
            revision,
            candidate,
            scene,
            decision="confirm",
            key="confirm-before-scene-name",
            graph_version=0,
        ),
    )
    assert confirmed.status_code == 200, confirmed.text
    command = {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        "command_type": "merge_scene_name",
        "target_asset_id": scene["asset_id"],
        "patch": {"alias": "The Archive Hall"},
        "expected_asset_version": confirmed.json()["asset"]["version"],
        "idempotency_key": "merge-archive-scene-name-recovery",
    }
    original_write = script_truth._write_state
    failed = False

    def fail_once(store, scoped_project_id, state):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected scene-name truth-state write failure")
        return original_write(store, scoped_project_id, state)

    monkeypatch.setattr(script_truth, "_write_state", fail_once)
    with pytest.raises(RuntimeError, match="injected scene-name truth-state write failure"):
        client.post(f"/projects/{project_id}/core-assets/commands/confirm", json=command)
    monkeypatch.setattr(script_truth, "_write_state", original_write)

    graph_after_failure = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert graph_after_failure["version"] == 2
    assert graph_after_failure["nodes"][scene["asset_id"]]["metadata"]["aliases"] == ["The Archive Hall"]
    truth_after_failure = client.get(f"/projects/{project_id}/script-truth").json()["projection"]
    stale_scene = next(item for item in truth_after_failure["assets"] if item["asset_id"] == scene["asset_id"])
    assert stale_scene["aliases"] == []

    recovered = client.post(f"/projects/{project_id}/core-assets/commands/confirm", json=command)
    assert recovered.status_code == 200, recovered.text
    recovered_scene = next(
        item for item in recovered.json()["projection"]["assets"] if item["asset_id"] == scene["asset_id"]
    )
    assert recovered_scene["aliases"] == ["The Archive Hall"]
    assert recovered.json()["receipt"]["production_graph_version"] == 2
    graph_after_recovery = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert graph_after_recovery["version"] == 2
    assert graph_after_recovery["nodes"][scene["asset_id"]]["metadata"]["asset_version_id"] == recovered_scene["version_id"]
