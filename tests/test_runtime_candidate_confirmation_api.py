"""Persisted candidate confirmation loop API — A/B/C acceptance via real routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_authoritative_facts_graph import FEED_PRODUCTION_GRAPH_ENV
from apps.api.runtime_candidate_confirmation import (
    CONFIRMATION_LOOP_ENV,
    load_ledger,
)
from apps.api.runtime_m6_script_plan_asset_bible import IMPROVED_EXTRACTION_ENV
from apps.api.runtime_production_graph import ProductionGraphStore
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


SCRIPTS = Path(__file__).resolve().parents[1] / "docs" / "internal-notes" / "test-scripts-character-scene"
SEA = (SCRIPTS / "02_industry_standard_letter_by_the_sea.txt").read_text(encoding="utf-8")
PHOTO = (SCRIPTS / "04_mixed_format_old_photo.txt").read_text(encoding="utf-8")
HOME = (SCRIPTS / "03_labeled_fields_homecoming.txt").read_text(encoding="utf-8")
SIX_SCRIPT_PATHS = tuple(sorted(SCRIPTS.glob("[0-9][0-9]_*.txt")))
SCRIPT_PROFILE_FIELD_PATHS = {
    "script_profile.theme",
    "script_profile.genre",
    "script_profile.audience",
    "script_profile.narrative_goals",
    "script_profile.style_requirements",
}
LABELED_SCRIPT_PROFILE = """主题：等待与释然
类型：悬疑、情感
受众：成年观众
叙事目标：让观众体会未送达的告别
风格：克制对白，冷暖光对比

""" + HOME


def _client(tmp_path) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=tmp_path))


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post("/projects", json={"project_id": project_id, "goal": f"{project_id} story"})
    assert response.status_code == 200, response.text


def _create_revision(client: TestClient, project_id: str, text: str, *, parent: str = "") -> dict:
    payload = {"source_kind": "script", "source_text": text}
    if parent:
        payload["parent_revision_id"] = parent
    response = client.post(f"/projects/{project_id}/script-revisions", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["revision"]


def _enable_both(monkeypatch) -> None:
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


def test_routes_404_when_confirmation_flag_off(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(CONFIRMATION_LOOP_ENV, raising=False)
    monkeypatch.delenv(IMPROVED_EXTRACTION_ENV, raising=False)
    client = _client(tmp_path)
    _create_project(client, "proj_off")
    response = client.get("/projects/proj_off/candidate-facts/review")
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "candidate_confirmation_disabled"


def test_refresh_requires_improved_extraction_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(CONFIRMATION_LOOP_ENV, "true")
    monkeypatch.delenv(IMPROVED_EXTRACTION_ENV, raising=False)
    client = _client(tmp_path)
    _create_project(client, "proj_half")
    revision = _create_revision(client, "proj_half", SEA)
    response = client.post(
        "/projects/proj_half/candidate-facts/review/refresh",
        json={
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "improved_extraction_required"


def test_scenario_a_junk_never_authoritative_via_api(tmp_path, monkeypatch) -> None:
    """A: 苏晴没 cannot become authoritative; reject persists; real 苏晴 can."""

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_loop_a"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, SEA)
    refreshed = _refresh(client, project_id, revision)
    items = refreshed["bundle"]["items"]
    texts = {item["text"]: item for item in items}
    assert "苏晴" in texts
    assert "苏晴没" not in texts

    # Inject junk via store then reject
    store = RuntimeStore(tmp_path)
    ledger = load_ledger(store, project_id)
    from apps.api.runtime_candidate_confirmation import inject_raw_junk_candidate, save_ledger

    junk = inject_raw_junk_candidate(ledger, junk_text="苏晴没", evidence_quote="苏晴没说话")
    save_ledger(store, ledger)

    reject = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "reject",
            "fact_id": junk.fact_id,
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "reason": "fragment not a name",
        },
    )
    assert reject.status_code == 200, reject.text
    assert all(row["text"] != "苏晴没" for row in reject.json()["authoritative"])

    accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": texts["苏晴"]["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert accept.status_code == 200, accept.text
    auth_texts = [row["text"] for row in accept.json()["authoritative"]]
    assert "苏晴" in auth_texts
    assert "苏晴没" not in auth_texts
    # Persistence: ledger file exists and reloads
    ledger2 = load_ledger(store, project_id)
    assert any(r.fact.text == "苏晴" for r in ledger2.authoritative_records if r.validity.value == "active")


def test_scenario_b_edit_confirm_wins_on_resolve(tmp_path, monkeypatch) -> None:
    """B: human edit persists; resolve returns corrected value not raw extract label."""

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_loop_b"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, PHOTO)
    refreshed = _refresh(client, project_id, revision)
    mother = next(item for item in refreshed["bundle"]["items"] if item["text"] == "母亲")
    attic = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["text"] == "阁楼" and item["entity_kind"] == "scene"
    )

    edit = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": mother["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": "周丽",
            "reason": "role label → proper name",
        },
    )
    assert edit.status_code == 200, edit.text
    resolved = edit.json()["resolved"]
    assert "周丽" in resolved["characters"]
    assert "母亲" not in resolved["characters"]

    edit_scene = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": attic["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": "老宅阁楼",
            "reason": "more specific place",
        },
    )
    assert edit_scene.status_code == 200, edit_scene.text
    resolved2 = edit_scene.json()["resolved"]
    assert "老宅阁楼" in resolved2["scenes"]
    assert "阁楼" not in resolved2["scenes"]

    # GET review still sees decisions after reload
    review = client.get(f"/projects/{project_id}/candidate-facts/review")
    assert review.status_code == 200
    decisions = {item["fact_id"]: item["review_decision"] for item in review.json()["bundle"]["items"]}
    assert decisions[mother["fact_id"]] == "edited_and_confirmed"
    assert decisions[attic["fact_id"]] == "edited_and_confirmed"


def test_scenario_c_new_revision_invalidates_old_authority(tmp_path, monkeypatch) -> None:
    """C: new Script Truth revision invalidates prior active authoritative facts."""

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_loop_c"
    _create_project(client, project_id)
    rev1 = _create_revision(client, project_id, HOME)
    refreshed = _refresh(client, project_id, rev1)
    for item in refreshed["bundle"]["items"]:
        if item["is_missing_slot"]:
            continue
        response = client.post(
            f"/projects/{project_id}/candidate-facts/actions",
            json={
                "action": "accept",
                "fact_id": item["fact_id"],
                "source_revision_id": rev1["revision_id"],
                "source_revision_digest": rev1["source_digest"],
            },
        )
        assert response.status_code == 200, response.text

    store = RuntimeStore(tmp_path)
    before = [r for r in load_ledger(store, project_id).authoritative_records if r.validity.value == "active"]
    assert len(before) >= 2

    text_v2 = HOME.replace("小镇火车站", "北方小镇火车站")
    rev2 = _create_revision(client, project_id, text_v2, parent=rev1["revision_id"])
    refreshed2 = _refresh(client, project_id, rev2)
    assert refreshed2["authoritative"] == []

    ledger = load_ledger(store, project_id)
    invalidated = [r for r in ledger.authoritative_records if r.validity.value == "invalidated_by_revision"]
    assert len(invalidated) == len(before)
    assert all(r.invalidated_by_revision_id == rev2["revision_id"] for r in invalidated)

    station = next(item for item in refreshed2["bundle"]["items"] if "火车站" in item["text"])
    accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": station["fact_id"],
            "source_revision_id": rev2["revision_id"],
            "source_revision_digest": rev2["source_digest"],
        },
    )
    assert accept.status_code == 200, accept.text
    current = [row["text"] for row in accept.json()["authoritative"]]
    assert current == ["北方小镇火车站"]
    assert "小镇火车站" not in current

    # Ledger file on disk
    assert (tmp_path / "projects" / project_id / "candidate_facts" / "ledger.json").is_file()


def test_revision_refresh_accumulates_change_log(tmp_path, monkeypatch) -> None:
    """Human accept/edit/reject audit rows survive a later revision refresh."""

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_loop_changelog"
    _create_project(client, project_id)
    rev1 = _create_revision(client, project_id, PHOTO)
    refreshed = _refresh(client, project_id, rev1)
    items = refreshed["bundle"]["items"]
    mother = next(item for item in items if item["text"] == "母亲" and item["entity_kind"] == "character")
    attic = next(item for item in items if item["text"] == "阁楼" and item["entity_kind"] == "scene")
    other = next(
        item
        for item in items
        if item["fact_id"] not in {mother["fact_id"], attic["fact_id"]} and not item["is_missing_slot"]
    )

    accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": attic["fact_id"],
            "source_revision_id": rev1["revision_id"],
            "source_revision_digest": rev1["source_digest"],
            "reason": "keep attic label",
        },
    )
    assert accept.status_code == 200, accept.text

    edit = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": mother["fact_id"],
            "source_revision_id": rev1["revision_id"],
            "source_revision_digest": rev1["source_digest"],
            "new_text": "周丽",
            "reason": "role label → proper name",
        },
    )
    assert edit.status_code == 200, edit.text

    reject = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "reject",
            "fact_id": other["fact_id"],
            "source_revision_id": rev1["revision_id"],
            "source_revision_digest": rev1["source_digest"],
            "reason": "not needed for this cut",
        },
    )
    assert reject.status_code == 200, reject.text

    store = RuntimeStore(tmp_path)
    before_log = load_ledger(store, project_id).change_log
    before_reasons = [row.reason for row in before_log]
    assert "human_accept" in before_reasons or "keep attic label" in before_reasons
    assert "role label → proper name" in before_reasons
    assert "not needed for this cut" in before_reasons
    before_ids = [row.change_id for row in before_log]
    assert len(before_ids) >= 4  # initial extract + accept + edit + reject

    text_v2 = PHOTO + "\n\n周丽转身离开阁楼。"
    rev2 = _create_revision(client, project_id, text_v2, parent=rev1["revision_id"])
    refreshed2 = _refresh(client, project_id, rev2)
    assert refreshed2["enabled"] is True

    after_log = load_ledger(store, project_id).change_log
    after_ids = [row.change_id for row in after_log]
    after_reasons = [row.reason for row in after_log]

    # Prior human decisions remain; revision-change + new extraction are appended.
    for change_id in before_ids:
        assert change_id in after_ids
    assert "role label → proper name" in after_reasons
    assert "not needed for this cut" in after_reasons
    assert "script_revision_changed" in after_reasons
    assert after_reasons.count("initial_extract") >= 2
    assert len(after_log) > len(before_log)


def test_script_profile_scenario_a_labeled_control_accepts_and_feeds_graph(
    tmp_path,
    monkeypatch,
) -> None:
    """A: five explicit labels coexist with Character/Scene and accept into Graph."""

    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_profile_a"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, LABELED_SCRIPT_PROFILE)

    refreshed = _refresh(client, project_id, revision)
    items = refreshed["bundle"]["items"]
    assert {item["entity_kind"] for item in items} == {
        "character",
        "scene",
        "script_profile",
    }
    profile_items = [item for item in items if item["entity_kind"] == "script_profile"]
    assert len(profile_items) == 5
    assert {item["field_path"] for item in profile_items} == SCRIPT_PROFILE_FIELD_PATHS
    assert {item["status"] for item in profile_items} == {"extracted_from_text"}
    assert len({item["entity_id"] for item in profile_items}) == 1
    assert len({item["entity_id"] for item in items if item["entity_kind"] == "character"}) > 1
    assert len({item["entity_id"] for item in items if item["entity_kind"] == "scene"}) > 1

    theme = next(
        item for item in profile_items if item["field_path"] == "script_profile.theme"
    )
    accepted = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": theme["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    authority = next(
        fact for fact in body["authoritative"] if fact["source_candidate_fact_id"] == theme["fact_id"]
    )
    assert authority["entity_kind"] == "script_profile"
    assert authority["field_path"] == "script_profile.theme"
    assert authority["text"] == "等待与释然"
    assert body["resolved"]["script_profile"] == {"theme": "等待与释然"}
    assert body["graph_feed"]["fed"] is True

    review = client.get(f"/projects/{project_id}/candidate-facts/review")
    assert review.status_code == 200, review.text
    review_body = review.json()
    assert {item["entity_kind"] for item in review_body["bundle"]["items"]} == {
        "character",
        "scene",
        "script_profile",
    }
    assert any(
        fact["entity_kind"] == "script_profile" and fact["text"] == "等待与释然"
        for fact in review_body["authoritative"]
    )

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    node = next(
        node
        for node_id, node in graph["nodes"].items()
        if node_id.startswith("authfact-script_profile-")
    )
    assert node["category"] == "profile"
    assert node["metadata"]["entity_kind"] == "script_profile"
    assert node["metadata"]["field_path"] == "script_profile.theme"
    assert node["metadata"]["value"] == "等待与释然"


def test_script_profile_scenario_b_missing_requires_edit_confirm_and_feeds_graph(
    tmp_path,
    monkeypatch,
) -> None:
    """B: an unlabeled facet cannot be accepted, but edit_confirm reaches authority."""

    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_profile_b"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, SEA)
    refreshed = _refresh(client, project_id, revision)
    profile_items = [
        item for item in refreshed["bundle"]["items"] if item["entity_kind"] == "script_profile"
    ]
    assert len(profile_items) == 5
    assert all(item["status"] == "missing" and item["is_missing_slot"] for item in profile_items)
    genre = next(
        item for item in profile_items if item["field_path"] == "script_profile.genre"
    )
    assert "accept" not in genre["allowed_actions"]

    rejected_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": genre["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert rejected_accept.status_code == 409
    assert rejected_accept.json()["detail"]["error"] == "candidate_action_rejected"

    edited = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": genre["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": "悬疑",
            "reason": "human supplied genre",
        },
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    authority = next(
        fact for fact in body["authoritative"] if fact["source_candidate_fact_id"] == genre["fact_id"]
    )
    assert authority["entity_kind"] == "script_profile"
    assert authority["field_path"] == "script_profile.genre"
    assert authority["promotion_kind"] == "human_confirmation"
    assert authority["text"] == "悬疑"
    assert body["resolved"]["script_profile"] == {"genre": "悬疑"}
    assert body["graph_feed"]["fed"] is True

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    profile_nodes = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("entity_kind") == "script_profile"
    ]
    assert len(profile_nodes) == 1
    assert profile_nodes[0]["metadata"]["value"] == "悬疑"


def test_script_profile_empty_label_does_not_consume_the_next_label_line_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_profile_line_boundary"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, "主题：\n类型：悬疑\n\n" + HOME)
    refreshed = _refresh(client, project_id, revision)
    by_path = {
        item["field_path"]: item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "script_profile"
    }

    assert by_path["script_profile.theme"]["status"] == "missing"
    assert by_path["script_profile.theme"]["text"] == "(missing)"
    assert by_path["script_profile.genre"]["status"] == "extracted_from_text"
    assert by_path["script_profile.genre"]["text"] == "悬疑"


def test_script_profile_repeat_refresh_accept_supersedes_authority_and_upserts_graph(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_profile_repeat_accept"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, LABELED_SCRIPT_PROFILE)

    first_refresh = _refresh(client, project_id, revision)
    first_theme = next(
        item
        for item in first_refresh["bundle"]["items"]
        if item["field_path"] == "script_profile.theme"
    )
    first_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": first_theme["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert first_accept.status_code == 200, first_accept.text

    second_refresh = _refresh(client, project_id, revision)
    second_theme = next(
        item
        for item in second_refresh["bundle"]["items"]
        if item["field_path"] == "script_profile.theme"
    )
    assert second_theme["fact_id"] != first_theme["fact_id"]
    assert second_theme["entity_id"] == first_theme["entity_id"]
    second_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": second_theme["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert second_accept.status_code == 200, second_accept.text
    current = [
        fact
        for fact in second_accept.json()["authoritative"]
        if fact["entity_kind"] == "script_profile"
        and fact["field_path"] == "script_profile.theme"
    ]
    assert len(current) == 1
    assert current[0]["source_candidate_fact_id"] == second_theme["fact_id"]

    records = [
        record
        for record in load_ledger(RuntimeStore(tmp_path), project_id).authoritative_records
        if record.fact.entity_kind == "script_profile"
        and record.fact.field_path == "script_profile.theme"
    ]
    assert len(records) == 2
    assert [record.validity.value for record in records].count("active") == 1
    assert [record.validity.value for record in records].count("superseded") == 1
    active = next(record for record in records if record.validity.value == "active")
    prior = next(record for record in records if record.validity.value == "superseded")
    assert active.supersedes_record_id == prior.record_id
    assert prior.superseded_by_record_id == active.record_id

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    profile_nodes = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("entity_kind") == "script_profile"
        and node.get("metadata", {}).get("field_path") == "script_profile.theme"
    ]
    assert len(profile_nodes) == 1
    assert profile_nodes[0]["metadata"]["authoritative_fact_id"] == (
        active.fact.authoritative_fact_id
    )


def test_script_profile_scenario_c_new_revision_invalidates_profile_authority(
    tmp_path,
    monkeypatch,
) -> None:
    """C: a revision gets a new single profile and invalidates old profile authority."""

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_profile_c"
    _create_project(client, project_id)
    rev1 = _create_revision(client, project_id, LABELED_SCRIPT_PROFILE)
    first = _refresh(client, project_id, rev1)
    first_profile = [
        item for item in first["bundle"]["items"] if item["entity_kind"] == "script_profile"
    ]
    first_profile_id = first_profile[0]["entity_id"]
    theme1 = next(
        item for item in first_profile if item["field_path"] == "script_profile.theme"
    )
    accepted1 = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": theme1["fact_id"],
            "source_revision_id": rev1["revision_id"],
            "source_revision_digest": rev1["source_digest"],
        },
    )
    assert accepted1.status_code == 200, accepted1.text

    text_v2 = LABELED_SCRIPT_PROFILE.replace("主题：等待与释然", "主题：重逢与和解")
    rev2 = _create_revision(client, project_id, text_v2, parent=rev1["revision_id"])
    second = _refresh(client, project_id, rev2)
    assert second["authoritative"] == []
    second_profile = [
        item for item in second["bundle"]["items"] if item["entity_kind"] == "script_profile"
    ]
    assert len(second_profile) == 5
    assert len({item["entity_id"] for item in second_profile}) == 1
    assert second_profile[0]["entity_id"] != first_profile_id

    store = RuntimeStore(tmp_path)
    invalidated = [
        record
        for record in load_ledger(store, project_id).authoritative_records
        if record.fact.entity_kind == "script_profile"
        and record.validity.value == "invalidated_by_revision"
    ]
    assert len(invalidated) == 1
    assert invalidated[0].invalidated_by_revision_id == rev2["revision_id"]

    theme2 = next(
        item for item in second_profile if item["field_path"] == "script_profile.theme"
    )
    accepted2 = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": theme2["fact_id"],
            "source_revision_id": rev2["revision_id"],
            "source_revision_digest": rev2["source_digest"],
        },
    )
    assert accepted2.status_code == 200, accepted2.text
    current_profile = [
        fact
        for fact in accepted2.json()["authoritative"]
        if fact["entity_kind"] == "script_profile"
    ]
    assert [fact["text"] for fact in current_profile] == ["重逢与和解"]


@pytest.mark.parametrize("script_path", SIX_SCRIPT_PATHS, ids=lambda path: path.stem)
def test_six_scripts_keep_all_script_profile_facets_missing_via_api(
    script_path: Path,
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = f"proj_profile_missing_{script_path.stem[:2]}"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, script_path.read_text(encoding="utf-8"))
    refreshed = _refresh(client, project_id, revision)
    profile_items = [
        item for item in refreshed["bundle"]["items"] if item["entity_kind"] == "script_profile"
    ]

    assert len(profile_items) == 5
    assert len({item["entity_id"] for item in profile_items}) == 1
    assert {item["field_path"] for item in profile_items} == SCRIPT_PROFILE_FIELD_PATHS
    assert all(item["status"] == "missing" for item in profile_items)
    assert all(item["is_missing_slot"] for item in profile_items)
    assert all(item["text"] == "(missing)" for item in profile_items)
    assert all(item["evidence_spans"] == [] for item in profile_items)
    assert all("accept" not in item["allowed_actions"] for item in profile_items)
    assert refreshed["authoritative"] == []
