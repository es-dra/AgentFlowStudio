from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import apps.api.runtime_script_core_truth as script_truth
from apps.api.runtime_script_core_truth import (
    ANALYSIS_CANDIDATE_SCHEMA_VERSION,
    ANALYSIS_REVIEW_SCHEMA_VERSION,
    CORE_ASSET_COMMAND_SCHEMA_VERSION,
    SCENE_OWNERSHIP_REVIEW_SCHEMA_VERSION,
)
from apps.api.runtime_service import create_runtime_app


def _span(text: str, quote: str, *, occurrence: int = 0) -> dict:
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(quote, start + 1)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _seed(
    client: TestClient,
    project_id: str,
    *,
    review_assets: bool = True,
    create_prop: bool = True,
) -> tuple[dict, dict, dict[str, dict]]:
    source = (
        "INT. ARCHIVE HALL - NIGHT\n"
        "Mira enters carrying the brass key.\n\n"
        "INT. ROOFTOP - DAWN\n"
        "Rowan waits."
    )
    assert client.post("/projects", json={"project_id": project_id, "goal": "scene ownership"}).status_code == 200
    created = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": source},
    )
    assert created.status_code == 200, created.text
    revision = created.json()["revision"]
    submitted = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
            "named_characters": [
                {
                    "display_name": name,
                    "evidence_spans": [_span(source, name)],
                    "confidence": 1.0,
                    "evidence_status": "extracted_from_text",
                    "extraction_method": "fixture_exact_span",
                }
                for name in ("Mira", "Rowan")
            ],
            "main_scenes": [
                {
                    "name": heading,
                    "evidence_spans": [_span(source, heading)],
                    "confidence": 1.0,
                    "evidence_status": "extracted_from_text",
                    "extraction_method": "fixture_scene_heading",
                }
                for heading in ("INT. ARCHIVE HALL - NIGHT", "INT. ROOFTOP - DAWN")
            ],
        },
    )
    assert submitted.status_code == 200, submitted.text
    candidate = submitted.json()["candidate"]
    assets = submitted.json()["projection"]["assets"]
    graph_version = 0
    confirmed: dict[str, dict] = {asset["display_name"]: asset for asset in assets}
    for asset in assets if review_assets else []:
        reviewed = client.post(
            f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{asset['asset_id']}/review",
            json={
                "project_id": project_id,
                "revision_id": revision["revision_id"],
                "source_digest": revision["source_digest"],
                "candidate_id": candidate["candidate_id"],
                "asset_version_id": asset["version_id"],
                "expected_asset_version": asset["version"],
                "expected_graph_version": graph_version,
                "idempotency_key": f"confirm-{asset['asset_id']}",
                "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
                "decision": "confirm",
            },
        )
        assert reviewed.status_code == 200, reviewed.text
        graph_version = reviewed.json()["graph"]["version"]
        confirmed[asset["display_name"]] = reviewed.json()["asset"]
        assert reviewed.json()["receipt"]["production_graph_node_id"] == asset["asset_id"]

    if create_prop:
        prop = client.post(
            f"/projects/{project_id}/core-assets/commands/confirm",
            json={
                "project_id": project_id,
                "revision_id": revision["revision_id"],
                "source_digest": revision["source_digest"],
                "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
                "command_type": "create_manual_prop",
                "patch": {"display_name": "brass key"},
                "idempotency_key": "create-brass-key",
            },
        )
        assert prop.status_code == 200, prop.text
        confirmed["brass key"] = next(
            item for item in prop.json()["projection"]["assets"] if item["display_name"] == "brass key"
        )
        confirmed["_prop_receipt"] = prop.json()["receipt"]
    return revision, candidate, confirmed


def _extract(client: TestClient, project_id: str, revision: dict):
    return client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-relationships/extract"
    )


def _review(client: TestClient, project_id: str, revision: dict, relationship: dict, graph_version: int, key: str):
    return client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-relationships/"
        f"{relationship['relationship_id']}/review",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "relationship_version_id": relationship["version_id"],
            "expected_relationship_version": relationship["version"],
            "expected_graph_version": graph_version,
            "idempotency_key": key,
            "schema_version": SCENE_OWNERSHIP_REVIEW_SCHEMA_VERSION,
            "decision": "confirm",
        },
    )


def test_scene_ownership_uses_asset_ids_preserves_review_and_invalidates_on_endpoint_edit(tmp_path) -> None:
    project_id = "scene-ownership-lifecycle"
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    revision, _candidate, assets = _seed(client, project_id)

    extracted = _extract(client, project_id, revision)
    assert extracted.status_code == 200, extracted.text
    relationships = extracted.json()["relationships"]
    assert len(relationships) == 6
    archive = assets["INT. ARCHIVE HALL - NIGHT"]
    mira = assets["Mira"]
    brass_key = assets["brass key"]
    archive_mira = next(
        item
        for item in relationships
        if item["scene_asset_id"] == archive["asset_id"] and item["member_asset_id"] == mira["asset_id"]
    )
    archive_key = next(
        item
        for item in relationships
        if item["scene_asset_id"] == archive["asset_id"] and item["member_asset_id"] == brass_key["asset_id"]
    )
    assert archive_mira["status"] == "candidate"
    assert archive_mira["evidence_status"] == "extracted_from_text"
    assert archive_key["relation_type"] == "scene_core_prop"
    missing = next(
        item
        for item in relationships
        if item["scene_asset_id"] == assets["INT. ROOFTOP - DAWN"]["asset_id"]
        and item["member_asset_id"] == mira["asset_id"]
    )
    assert missing["status"] == "missing"
    assert missing["evidence_status"] == "missing"
    assert missing["evidence_spans"] == []

    graph = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    confirmed = _review(client, project_id, revision, archive_mira, graph["version"], "confirm-archive-mira")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["relationship"]["status"] == "confirmed"
    assert confirmed.json()["relationship"]["scene_asset_id"] == archive["asset_id"]
    assert confirmed.json()["relationship"]["member_asset_id"] == mira["asset_id"]
    assert {
        (item["from_id"], item["to_id"], item["relation_type"])
        for item in confirmed.json()["graph"]["relations"]
    } >= {(archive["asset_id"], mira["asset_id"], "scene_cast")}
    assert confirmed.json()["graph"]["nodes"][archive["asset_id"]]["metadata"]["candidate_id"]

    replay_extract = _extract(client, project_id, revision)
    assert replay_extract.status_code == 200, replay_extract.text
    preserved = next(
        item for item in replay_extract.json()["relationships"] if item["relationship_id"] == archive_mira["relationship_id"]
    )
    assert preserved["status"] == "confirmed"
    assert preserved["review_decision_id"] == confirmed.json()["review_decision"]["review_decision_id"]

    edited = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "edit_asset",
            "target_asset_id": mira["asset_id"],
            "patch": {"display_name": "Mira Vale"},
            "expected_asset_version": mira["version"],
            "idempotency_key": "edit-mira-after-relationship",
        },
    )
    assert edited.status_code == 200, edited.text
    queried = client.get(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates"
    ).json()
    expired = next(item for item in queried["relationships"] if item["relationship_id"] == archive_mira["relationship_id"])
    assert expired["status"] == "expired"
    graph_after_edit = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert (archive["asset_id"], mira["asset_id"], "scene_cast") not in {
        (item["from_id"], item["to_id"], item["relation_type"])
        for item in graph_after_edit["relations"]
    }

    confirmed_prop = _review(
        client,
        project_id,
        revision,
        archive_key,
        graph_after_edit["version"],
        "confirm-archive-key",
    )
    assert confirmed_prop.status_code == 200, confirmed_prop.text
    assert brass_key["asset_id"] in confirmed_prop.json()["graph"]["nodes"]
    undone_prop = client.post(
        f"/projects/{project_id}/core-assets/commands/undo",
        json={
            "project_id": project_id,
            "receipt_id": assets["_prop_receipt"]["receipt_id"],
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        },
    )
    assert undone_prop.status_code == 200, undone_prop.text
    graph_after_undo = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert (archive["asset_id"], brass_key["asset_id"], "scene_core_prop") not in {
        (item["from_id"], item["to_id"], item["relation_type"])
        for item in graph_after_undo["relations"]
    }


def test_scene_ownership_fails_closed_and_recovers_graph_first_state_failure(tmp_path, monkeypatch) -> None:
    project_id = "scene-ownership-recovery"
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    revision, _candidate, assets = _seed(client, project_id)
    extracted = _extract(client, project_id, revision)
    assert extracted.status_code == 200, extracted.text
    relationships = extracted.json()["relationships"]
    archive = assets["INT. ARCHIVE HALL - NIGHT"]
    mira = assets["Mira"]
    explicit = next(
        item
        for item in relationships
        if item["scene_asset_id"] == archive["asset_id"] and item["member_asset_id"] == mira["asset_id"]
    )
    missing = next(item for item in relationships if item["status"] == "missing")
    graph = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    blocked = _review(client, project_id, revision, missing, graph["version"], "cannot-confirm-missing")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["error"] == "scene_ownership_evidence_missing"

    original_write = script_truth._write_state
    failed = False

    def fail_once(store, scoped_project_id, state):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected scene ownership state failure")
        return original_write(store, scoped_project_id, state)

    monkeypatch.setattr(script_truth, "_write_state", fail_once)
    with pytest.raises(RuntimeError, match="injected scene ownership state failure"):
        _review(client, project_id, revision, explicit, graph["version"], "recover-scene-cast")
    monkeypatch.setattr(script_truth, "_write_state", original_write)
    graph_after_failure = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert (archive["asset_id"], mira["asset_id"], "scene_cast") in {
        (item["from_id"], item["to_id"], item["relation_type"])
        for item in graph_after_failure["relations"]
    }

    recovered = _review(client, project_id, revision, explicit, graph["version"], "recover-scene-cast")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["graph_idempotent_replay"] is True
    assert recovered.json()["relationship"]["status"] == "confirmed"

    revision_body = {
        "source_kind": "script",
        "source_text": "INT. ARCHIVE HALL - DAY\nThe hall is empty.",
        "parent_revision_id": revision["revision_id"],
    }
    failed = False
    monkeypatch.setattr(script_truth, "_write_state", fail_once)
    with pytest.raises(RuntimeError, match="injected scene ownership state failure"):
        client.post(f"/projects/{project_id}/script-revisions", json=revision_body)
    monkeypatch.setattr(script_truth, "_write_state", original_write)
    graph_after_revision_failure = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert (archive["asset_id"], mira["asset_id"], "scene_cast") not in {
        (item["from_id"], item["to_id"], item["relation_type"])
        for item in graph_after_revision_failure["relations"]
    }

    next_revision = client.post(f"/projects/{project_id}/script-revisions", json=revision_body)
    assert next_revision.status_code == 200, next_revision.text
    old = client.get(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates"
    ).json()
    assert next(item for item in old["relationships"] if item["relationship_id"] == explicit["relationship_id"])[
        "status"
    ] == "expired"
    graph_after_revision = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert (archive["asset_id"], mira["asset_id"], "scene_cast") not in {
        (item["from_id"], item["to_id"], item["relation_type"])
        for item in graph_after_revision["relations"]
    }


def test_scene_ownership_requires_authoritative_endpoints_and_expires_on_reject(tmp_path) -> None:
    project_id = "scene-ownership-endpoint-review"
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    revision, candidate, assets = _seed(
        client,
        project_id,
        review_assets=False,
        create_prop=False,
    )
    extracted = _extract(client, project_id, revision)
    assert extracted.status_code == 200, extracted.text
    relationship = next(
        item
        for item in extracted.json()["relationships"]
        if item["scene_asset_id"] == assets["INT. ARCHIVE HALL - NIGHT"]["asset_id"]
        and item["member_asset_id"] == assets["Mira"]["asset_id"]
    )
    blocked = _review(client, project_id, revision, relationship, 0, "unconfirmed-endpoint")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["error"] == "scene_ownership_endpoint_not_authoritative"

    mira = assets["Mira"]
    rejected = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{mira['asset_id']}/review",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "candidate_id": candidate["candidate_id"],
            "asset_version_id": mira["version_id"],
            "expected_asset_version": mira["version"],
            "expected_graph_version": 0,
            "idempotency_key": "reject-mira-endpoint",
            "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
            "decision": "reject",
        },
    )
    assert rejected.status_code == 200, rejected.text
    queried = client.get(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates"
    ).json()
    assert next(
        item for item in queried["relationships"] if item["relationship_id"] == relationship["relationship_id"]
    )["status"] == "expired"
