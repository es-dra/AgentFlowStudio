"""Persisted candidate confirmation loop API — A/B/C acceptance via real routes."""

from __future__ import annotations

import json
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
SCRIPT_FORMAT_PROFILE_FIELD_PATHS = {
    "script_format_profile.format_style",
    "script_format_profile.cleaning_notes",
    "script_format_profile.scene_boundary_count",
}
SCRIPT_FORMAT_EXPECTATIONS = {
    "01": ("industry_heading", 2),
    "02": ("industry_heading", 3),
    "03": ("labeled", 2),
    "04": ("mixed", 2),
    "05": ("unclear", 0),
    "06": ("industry_heading", 2),
}
LABELED_SCRIPT_PROFILE = """主题：等待与释然
类型：悬疑、情感
受众：成年观众
叙事目标：让观众体会未送达的告别
风格：克制对白，冷暖光对比

""" + HOME
LABELED_BEAT_CONTROL = LABELED_SCRIPT_PROFILE.replace(
    "人物：陈浩（40多岁，疲惫，眼神坚定）\n\n陈浩独自",
    "人物：陈浩（40多岁，疲惫，眼神坚定）\n\n节拍1：等待列车\n陈浩独自",
).replace(
    "人物：陈浩、林秀（60多岁，陈浩的母亲）\n\n林秀站在门口",
    "人物：陈浩、林秀（60多岁，陈浩的母亲）\n\nBEAT 1: 归家重逢\n林秀站在门口",
)
LABELED_BEAT_FACET_CONTROL = LABELED_SCRIPT_PROFILE.replace(
    "人物：陈浩（40多岁，疲惫，眼神坚定）\n\n陈浩独自",
    (
        "人物：陈浩（40多岁，疲惫，眼神坚定）\n\n"
        "节拍1：等待列车\n"
        "冲突：与时间赛跑\n"
        "转折：火车进站\n"
        "信息释放：到站通知响起\n"
        "情绪从：疲惫\n"
        "情绪到：紧张\n"
        "情绪变化：由等待转为准备登车\n"
        "陈浩独自"
    ),
).replace(
    "人物：陈浩、林秀（60多岁，陈浩的母亲）\n\n林秀站在门口",
    (
        "人物：陈浩、林秀（60多岁，陈浩的母亲）\n\n"
        "BEAT 1: 归家重逢\n"
        "冲突：久别后的愧疚\n"
        "转折：母亲抱住他\n"
        "信息释放：终于回家了\n"
        "情绪从：克制\n"
        "情绪到：释然\n"
        "情绪变化：从压抑转为拥抱\n"
        "林秀站在门口"
    ),
)
BEAT_FACET_SUFFIXES = {
    "conflict",
    "turn",
    "info_release",
    "emotion_shift",
    "emotion_shift.from_state",
    "emotion_shift.to_state",
    "emotion_shift.change",
}


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
        "script_format_profile",
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
        "script_format_profile",
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


@pytest.mark.parametrize("script_path", SIX_SCRIPT_PATHS, ids=lambda path: path.stem)
def test_six_scripts_expose_expected_script_format_profile_via_api(
    script_path: Path,
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = f"proj_format_{script_path.stem[:2]}"
    _create_project(client, project_id)
    source_text = script_path.read_text(encoding="utf-8")
    revision = _create_revision(client, project_id, source_text)
    refreshed = _refresh(client, project_id, revision)
    format_items = [
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "script_format_profile"
    ]
    by_path = {item["field_path"]: item for item in format_items}
    expected_style, expected_count = SCRIPT_FORMAT_EXPECTATIONS[script_path.stem[:2]]

    assert len(format_items) == 3
    assert len({item["entity_id"] for item in format_items}) == 1
    assert set(by_path) == SCRIPT_FORMAT_PROFILE_FIELD_PATHS
    assert by_path["script_format_profile.format_style"]["text"] == expected_style
    assert by_path["script_format_profile.scene_boundary_count"]["text"] == str(
        expected_count
    )
    assert json.loads(by_path["script_format_profile.cleaning_notes"]["text"]) == []
    assert {item["status"] for item in format_items} == {"extracted_from_text"}
    assert all(not item["is_missing_slot"] for item in format_items)
    assert all(item["source_revision_id"] == revision["revision_id"] for item in format_items)
    assert all(
        item["source_revision_digest"] == revision["source_digest"]
        for item in format_items
    )
    for item in format_items:
        assert item["evidence_spans"]
        for span in item["evidence_spans"]:
            assert source_text[span["start"]:span["end"]] == span["quote"]

    review = client.get(f"/projects/{project_id}/candidate-facts/review")
    assert review.status_code == 200, review.text
    persisted = [
        item
        for item in review.json()["bundle"]["items"]
        if item["entity_kind"] == "script_format_profile"
    ]
    assert {
        item["field_path"]: item["text"] for item in persisted
    } == {item["field_path"]: item["text"] for item in format_items}


def test_script_format_profile_accept_repeat_refresh_supersedes_and_upserts_graph_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_format_repeat"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, PHOTO)

    first_refresh = _refresh(client, project_id, revision)
    first = next(
        item
        for item in first_refresh["bundle"]["items"]
        if item["field_path"] == "script_format_profile.format_style"
    )
    first_cleaning = next(
        item
        for item in first_refresh["bundle"]["items"]
        if item["field_path"] == "script_format_profile.cleaning_notes"
    )
    first_count = next(
        item
        for item in first_refresh["bundle"]["items"]
        if item["field_path"] == "script_format_profile.scene_boundary_count"
    )
    first_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": first["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert first_accept.status_code == 200, first_accept.text
    assert first_accept.json()["resolved"]["script_format_profile"] == {
        "format_style": "mixed"
    }
    cleaning_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": first_cleaning["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert cleaning_accept.status_code == 200, cleaning_accept.text
    count_edit = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": first_count["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": "003",
            "reason": "human corrected the detected Scene count",
        },
    )
    assert count_edit.status_code == 200, count_edit.text
    assert count_edit.json()["result"]["text"] == "3"
    assert count_edit.json()["resolved"]["script_format_profile"] == {
        "format_style": "mixed",
        "cleaning_notes": [],
        "scene_boundary_count": 3,
    }

    second_refresh = _refresh(client, project_id, revision)
    second = next(
        item
        for item in second_refresh["bundle"]["items"]
        if item["field_path"] == first["field_path"]
    )
    assert second["fact_id"] != first["fact_id"]
    assert second["entity_id"] == first["entity_id"]
    second_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": second["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert second_accept.status_code == 200, second_accept.text

    records = [
        record
        for record in load_ledger(RuntimeStore(tmp_path), project_id).authoritative_records
        if record.fact.entity_kind == "script_format_profile"
        and record.fact.field_path == first["field_path"]
    ]
    assert len(records) == 2
    assert [record.validity.value for record in records].count("active") == 1
    assert [record.validity.value for record in records].count("superseded") == 1
    active = next(record for record in records if record.validity.value == "active")

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    nodes = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("entity_kind") == "script_format_profile"
        and node.get("metadata", {}).get("field_path") == first["field_path"]
    ]
    assert len(nodes) == 1
    assert nodes[0]["category"] == "profile"
    assert nodes[0]["metadata"]["value"] == "mixed"
    assert nodes[0]["metadata"]["authoritative_fact_id"] == (
        active.fact.authoritative_fact_id
    )
    graph_profile = {
        node["metadata"]["profile_facet"]: node["metadata"]["value"]
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("entity_kind") == "script_format_profile"
    }
    assert graph_profile == {
        "format_style": "mixed",
        "cleaning_notes": [],
        "scene_boundary_count": 3,
    }


def test_script_format_profile_new_revision_changes_identity_and_graph_node_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_format_revision"
    _create_project(client, project_id)
    rev1 = _create_revision(client, project_id, HOME)
    first_refresh = _refresh(client, project_id, rev1)
    first = next(
        item
        for item in first_refresh["bundle"]["items"]
        if item["field_path"] == "script_format_profile.format_style"
    )
    first_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": first["fact_id"],
            "source_revision_id": rev1["revision_id"],
            "source_revision_digest": rev1["source_digest"],
        },
    )
    assert first_accept.status_code == 200, first_accept.text

    rev2 = _create_revision(
        client,
        project_id,
        HOME.replace("标题：归途", "标题：归途（修订）"),
        parent=rev1["revision_id"],
    )
    second_refresh = _refresh(client, project_id, rev2)
    assert second_refresh["authoritative"] == []
    second = next(
        item
        for item in second_refresh["bundle"]["items"]
        if item["field_path"] == first["field_path"]
    )
    assert second["entity_id"] != first["entity_id"]
    second_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": second["fact_id"],
            "source_revision_id": rev2["revision_id"],
            "source_revision_digest": rev2["source_digest"],
        },
    )
    assert second_accept.status_code == 200, second_accept.text

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    nodes = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("entity_kind") == "script_format_profile"
        and node.get("metadata", {}).get("field_path") == first["field_path"]
    ]
    assert len(nodes) == 2
    assert {node["metadata"]["source_revision_id"] for node in nodes} == {
        rev1["revision_id"],
        rev2["revision_id"],
    }


def test_script_format_profile_cleaning_notes_and_edit_evidence_are_source_backed_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_format_cleaning"
    _create_project(client, project_id)
    source_text = HOME + "\n异常字符：\ufffd\x00"
    revision = _create_revision(client, project_id, source_text)
    refreshed = _refresh(client, project_id, revision)
    cleaning = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["field_path"] == "script_format_profile.cleaning_notes"
    )
    assert json.loads(cleaning["text"]) == [
        "unicode_replacement_character_present",
        "unexpected_control_character_U+0000",
    ]
    assert {span["quote"] for span in cleaning["evidence_spans"]} == {"\ufffd", "\x00"}
    for span in cleaning["evidence_spans"]:
        assert source_text[span["start"]:span["end"]] == span["quote"]

    original_evidence = cleaning["evidence_spans"]
    edited = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": cleaning["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": '["人工确认的清洗说明"]',
            "reason": "human clarified cleaning diagnostics",
        },
    )
    assert edited.status_code == 200, edited.text
    authority = next(
        fact
        for fact in edited.json()["authoritative"]
        if fact["source_candidate_fact_id"] == cleaning["fact_id"]
    )
    assert authority["evidence_spans"] == original_evidence
    for span in authority["evidence_spans"]:
        assert source_text[span["start"]:span["end"]] == span["quote"]


def test_script_format_profile_rejects_invalid_typed_edits_before_authority_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_format_invalid_edits"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, PHOTO)
    refreshed = _refresh(client, project_id, revision)
    by_path = {
        item["field_path"]: item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "script_format_profile"
    }

    invalid_edits = {
        "script_format_profile.format_style": "screenplay",
        "script_format_profile.cleaning_notes": '{"note":"not a list"}',
        "script_format_profile.scene_boundary_count": "two",
    }
    for field_path, new_text in invalid_edits.items():
        response = client.post(
            f"/projects/{project_id}/candidate-facts/actions",
            json={
                "action": "edit_confirm",
                "fact_id": by_path[field_path]["fact_id"],
                "source_revision_id": revision["revision_id"],
                "source_revision_digest": revision["source_digest"],
                "new_text": new_text,
                "reason": "typed-contract negative control",
            },
        )
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["error"] == "candidate_action_rejected"

    review = client.get(f"/projects/{project_id}/candidate-facts/review")
    assert review.status_code == 200, review.text
    assert review.json()["authoritative"] == []
    assert all(
        item["review_decision"] == "pending"
        for item in review.json()["bundle"]["items"]
        if item["entity_kind"] == "script_format_profile"
    )
    graph = ProductionGraphStore(RuntimeStore(tmp_path)).ensure(project_id)
    assert not any(
        node.get("metadata", {}).get("entity_kind") == "script_format_profile"
        for node in graph["nodes"].values()
    )


def test_beat_labeled_control_coexists_confirms_and_feeds_graph_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_beat_control"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, LABELED_BEAT_CONTROL)
    refreshed = _refresh(client, project_id, revision)
    items = refreshed["bundle"]["items"]

    assert {item["entity_kind"] for item in items} == {
        "character",
        "scene",
        "script_profile",
        "script_format_profile",
        "beat",
    }
    scenes = {item["text"]: item for item in items if item["entity_kind"] == "scene"}
    beats = [
        item
        for item in items
        if item["entity_kind"] == "beat" and item["field_path"].endswith(".boundary")
    ]
    assert len(beats) == 2
    assert {item["text"] for item in beats} == {"等待列车", "归家重逢"}
    assert {item["status"] for item in beats} == {"extracted_from_text"}
    assert all(item["producer_method"] == "explicit_numbered_beat_label" for item in beats)

    # Without facet labels, each Beat still emits fail-closed missing facet slots.
    waiting = next(item for item in beats if item["text"] == "等待列车")
    waiting_facets = [
        item
        for item in items
        if item["entity_kind"] == "beat"
        and item["entity_id"] == waiting["entity_id"]
        and not item["field_path"].endswith(".boundary")
    ]
    assert {item["field_path"].rsplit(".", 1)[-1] for item in waiting_facets} >= {
        "conflict",
        "turn",
        "info_release",
        "emotion_shift",
    }
    assert all(item["status"] == "missing" for item in waiting_facets)
    assert all(item["text"] == "(missing)" for item in waiting_facets)

    reunion = next(item for item in beats if item["text"] == "归家重逢")
    station_id = scenes["小镇火车站"]["entity_id"]
    home_id = scenes["陈浩家中的老屋"]["entity_id"]
    assert waiting["entity_id"].startswith(f"{station_id}.beat_0000.")
    assert waiting["field_path"] == f"scene[{station_id}].beats[0].boundary"
    assert reunion["entity_id"].startswith(f"{home_id}.beat_0000.")
    assert reunion["field_path"] == f"scene[{home_id}].beats[0].boundary"
    assert waiting["entity_id"] != reunion["entity_id"]
    for beat in beats:
        span = beat["evidence_spans"][0]
        assert LABELED_BEAT_CONTROL[span["start"]:span["end"]] == span["quote"]

    accepted = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": waiting["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert accepted.status_code == 200, accepted.text
    edited = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": reunion["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": "重逢",
            "reason": "confirm concise Beat boundary label",
        },
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    beat_authority = [
        fact
        for fact in body["authoritative"]
        if fact["entity_kind"] == "beat" and fact["field_path"].endswith(".boundary")
    ]
    assert {fact["text"] for fact in beat_authority} == {"等待列车", "重逢"}
    assert {row["text"] for row in body["resolved"]["beats"]} == {"等待列车", "重逢"}
    assert all(
        item["review_decision"] == "pending"
        for item in body["bundle"]["items"]
        if item["entity_kind"]
        in {"character", "scene", "script_profile", "script_format_profile"}
    )

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    graph_beats = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("entity_kind") == "beat"
        and node.get("metadata", {}).get("beat_slot") == "boundary"
    ]
    assert len(graph_beats) == 2
    graph_by_text = {
        node["metadata"]["boundary_label"]: node for node in graph_beats
    }
    assert set(graph_by_text) == {"等待列车", "重逢"}
    assert graph_by_text["等待列车"]["category"] == "beat"
    assert graph_by_text["等待列车"]["metadata"]["parent_scene_id"] == station_id
    assert graph_by_text["等待列车"]["metadata"]["order_index"] == 0
    assert graph_by_text["重逢"]["metadata"]["parent_scene_id"] == home_id


def test_beat_edit_confirm_preserves_marker_evidence_when_text_is_not_in_source_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_beat_edit_evidence"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, LABELED_BEAT_CONTROL)
    refreshed = _refresh(client, project_id, revision)
    beat = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "beat"
        and item["field_path"].endswith(".boundary")
        and item["text"] == "等待列车"
    )
    original_evidence = beat["evidence_spans"]

    edited = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": beat["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": "人工改写且原文不存在",
            "reason": "human clarification outside the literal marker",
        },
    )
    assert edited.status_code == 200, edited.text
    authority = next(
        fact
        for fact in edited.json()["authoritative"]
        if fact["source_candidate_fact_id"] == beat["fact_id"]
    )
    assert authority["text"] == "人工改写且原文不存在"
    assert authority["evidence_spans"] == original_evidence
    for span in authority["evidence_spans"]:
        assert LABELED_BEAT_CONTROL[span["start"]:span["end"]] == span["quote"]


@pytest.mark.parametrize("script_path", SIX_SCRIPT_PATHS, ids=lambda path: path.stem)
def test_six_scripts_keep_beat_segmentation_missing_via_api(
    script_path: Path,
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = f"proj_beat_missing_{script_path.stem[:2]}"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, script_path.read_text(encoding="utf-8"))
    refreshed = _refresh(client, project_id, revision)

    assert [
        item for item in refreshed["bundle"]["items"] if item["entity_kind"] == "beat"
    ] == []
    beat_missing = [
        slot
        for slot in refreshed["bundle"]["missing_slots"]
        if slot["entity_kind"] == "beat"
    ]
    assert beat_missing
    assert all(slot["status"] == "missing" for slot in beat_missing)
    assert all(slot["field_path"].startswith("scene[") for slot in beat_missing)
    assert refreshed["authoritative"] == []

    review = client.get(f"/projects/{project_id}/candidate-facts/review")
    assert review.status_code == 200, review.text
    persisted = [
        slot
        for slot in review.json()["bundle"]["missing_slots"]
        if slot["entity_kind"] == "beat"
    ]
    assert [slot["field_path"] for slot in persisted] == [
        slot["field_path"] for slot in beat_missing
    ]


def test_beat_label_without_resolved_scene_fails_closed_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_beat_no_scene"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, "标题：孤立节拍\n\n节拍1：不能悬空\n动作继续。")
    refreshed = _refresh(client, project_id, revision)

    assert not any(
        item["entity_kind"] == "beat" for item in refreshed["bundle"]["items"]
    )
    assert "explicit_beat_labels_without_resolved_scene_ignored" in (
        refreshed["bundle"]["extraction_notes"]
    )
    assert any(
        slot["entity_kind"] == "beat"
        and slot["field_path"] == "scene[(missing)].beats"
        for slot in refreshed["bundle"]["missing_slots"]
    )


def test_beat_labels_in_duplicate_scene_names_fail_closed_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_beat_duplicate_scene_name"
    _create_project(client, project_id)
    source = """标题：同名场景

第一场 - 内景 - 厨房 - 夜
节拍1：第一次进入
她推开门。

第二场 - 内景 - 厨房 - 清晨
节拍1：再次进入
她重新推开门。
"""
    revision = _create_revision(client, project_id, source)
    refreshed = _refresh(client, project_id, revision)

    assert not any(
        item["entity_kind"] == "beat" for item in refreshed["bundle"]["items"]
    )
    assert "beat_scene_ownership_ambiguous; no Beat candidate emitted" in (
        refreshed["bundle"]["extraction_notes"]
    )
    assert any(
        slot["entity_kind"] == "beat"
        and slot["field_path"].endswith(".beats")
        for slot in refreshed["bundle"]["missing_slots"]
    )


def test_beat_repeat_refresh_accept_supersedes_and_upserts_graph_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_beat_repeat"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, LABELED_BEAT_CONTROL)

    first_refresh = _refresh(client, project_id, revision)
    first = next(
        item
        for item in first_refresh["bundle"]["items"]
        if item["entity_kind"] == "beat" and item["field_path"].endswith(".boundary") and item["text"] == "等待列车"
    )
    first_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": first["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert first_accept.status_code == 200, first_accept.text

    second_refresh = _refresh(client, project_id, revision)
    second = next(
        item
        for item in second_refresh["bundle"]["items"]
        if item["entity_kind"] == "beat" and item["field_path"] == first["field_path"]
    )
    assert second["fact_id"] != first["fact_id"]
    assert second["entity_id"] == first["entity_id"]
    second_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": second["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert second_accept.status_code == 200, second_accept.text

    records = [
        record
        for record in load_ledger(RuntimeStore(tmp_path), project_id).authoritative_records
        if record.fact.entity_kind == "beat" and record.fact.field_path == first["field_path"]
    ]
    assert len(records) == 2
    assert [record.validity.value for record in records].count("active") == 1
    assert [record.validity.value for record in records].count("superseded") == 1
    active = next(record for record in records if record.validity.value == "active")

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    graph_beats = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("entity_kind") == "beat"
        and node.get("metadata", {}).get("field_path") == first["field_path"]
    ]
    assert len(graph_beats) == 1
    assert graph_beats[0]["metadata"]["authoritative_fact_id"] == (
        active.fact.authoritative_fact_id
    )


def test_beat_new_revision_invalidates_authority_and_changes_identity_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_beat_revision"
    _create_project(client, project_id)
    rev1 = _create_revision(client, project_id, LABELED_BEAT_CONTROL)
    first_refresh = _refresh(client, project_id, rev1)
    first = next(
        item
        for item in first_refresh["bundle"]["items"]
        if item["entity_kind"] == "beat" and item["field_path"].endswith(".boundary") and item["text"] == "等待列车"
    )
    first_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": first["fact_id"],
            "source_revision_id": rev1["revision_id"],
            "source_revision_digest": rev1["source_digest"],
        },
    )
    assert first_accept.status_code == 200, first_accept.text

    text_v2 = LABELED_BEAT_CONTROL.replace("节拍1：等待列车", "节拍1：决定登车")
    rev2 = _create_revision(client, project_id, text_v2, parent=rev1["revision_id"])
    second_refresh = _refresh(client, project_id, rev2)
    assert second_refresh["authoritative"] == []
    second = next(
        item
        for item in second_refresh["bundle"]["items"]
        if item["entity_kind"] == "beat" and item["field_path"].endswith(".boundary") and item["text"] == "决定登车"
    )
    assert second["field_path"] == first["field_path"]
    assert second["entity_id"] != first["entity_id"]

    invalidated = [
        record
        for record in load_ledger(RuntimeStore(tmp_path), project_id).authoritative_records
        if record.fact.entity_kind == "beat"
        and record.validity.value == "invalidated_by_revision"
    ]
    assert len(invalidated) == 1
    assert invalidated[0].invalidated_by_revision_id == rev2["revision_id"]


def test_beat_facets_labeled_control_confirm_and_feed_graph_via_api(tmp_path, monkeypatch) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_beat_facets_control"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, LABELED_BEAT_FACET_CONTROL)
    refreshed = _refresh(client, project_id, revision)
    items = refreshed["bundle"]["items"]

    waiting = next(
        item
        for item in items
        if item["entity_kind"] == "beat"
        and item["field_path"].endswith(".boundary")
        and item["text"] == "等待列车"
    )
    facets = {
        item["field_path"].split("].", 1)[1]: item
        for item in items
        if item["entity_kind"] == "beat" and item["entity_id"] == waiting["entity_id"]
        and not item["field_path"].endswith(".boundary")
    }
    assert facets["beats[0].conflict"]["text"] == "与时间赛跑"
    assert facets["beats[0].turn"]["text"] == "火车进站"
    assert facets["beats[0].info_release"]["text"] == "到站通知响起"
    assert facets["beats[0].emotion_shift.from_state"]["text"] == "疲惫"
    assert facets["beats[0].emotion_shift.to_state"]["text"] == "紧张"
    assert facets["beats[0].emotion_shift.change"]["text"] == "由等待转为准备登车"
    assert "beats[0].emotion_shift" not in facets
    assert all(item["status"] == "extracted_from_text" for item in facets.values())
    for item in facets.values():
        span = item["evidence_spans"][0]
        assert LABELED_BEAT_FACET_CONTROL[span["start"]:span["end"]] == span["quote"] == item["text"]

    accepted_paths = []
    for item in facets.values():
        response = client.post(
            f"/projects/{project_id}/candidate-facts/actions",
            json={
                "action": "accept",
                "fact_id": item["fact_id"],
                "source_revision_id": revision["revision_id"],
                "source_revision_digest": revision["source_digest"],
            },
        )
        assert response.status_code == 200, response.text
        accepted_paths.append(item["field_path"])
        body = response.json()

    assert {row["text"] for row in body["resolved"]["beat_facets"]} >= {
        "与时间赛跑",
        "火车进站",
        "到站通知响起",
        "疲惫",
        "紧张",
        "由等待转为准备登车",
    }

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    graph_facets = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("entity_kind") == "beat"
        and node.get("metadata", {}).get("beat_slot") not in {None, "boundary"}
    ]
    assert len(graph_facets) == 6
    assert {node["metadata"]["value"] for node in graph_facets} >= {
        "与时间赛跑",
        "火车进站",
        "到站通知响起",
        "疲惫",
        "紧张",
        "由等待转为准备登车",
    }


def test_beat_emotion_partial_labels_fail_closed_as_missing_via_api(tmp_path, monkeypatch) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_beat_emotion_partial"
    text = LABELED_BEAT_CONTROL.replace(
        "节拍1：等待列车\n陈浩独自",
        "节拍1：等待列车\n情绪从：疲惫\n冲突：与时间赛跑\n陈浩独自",
    )
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, text)
    refreshed = _refresh(client, project_id, revision)
    waiting = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "beat"
        and item["field_path"].endswith(".boundary")
        and item["text"] == "等待列车"
    )
    facets = [
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_id"] == waiting["entity_id"] and not item["field_path"].endswith(".boundary")
    ]
    by_suffix = {item["field_path"].rsplit("].", 1)[-1]: item for item in facets}
    assert by_suffix["conflict"]["status"] == "extracted_from_text"
    assert by_suffix["conflict"]["text"] == "与时间赛跑"
    assert by_suffix["emotion_shift"]["status"] == "missing"
    assert by_suffix["emotion_shift"]["text"] == "(missing)"
    assert not any(key.startswith("emotion_shift.") for key in by_suffix)
    assert "partial emotion_shift" in (by_suffix["emotion_shift"]["uncertainty_note"] or "")


def test_beat_missing_facet_edit_confirm_requires_source_evidence_via_api(
    tmp_path,
    monkeypatch,
) -> None:
    """Missing facet edit must bind an exact source span — never fabricate one."""

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_beat_facet_edit_evidence"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, LABELED_BEAT_CONTROL)
    refreshed = _refresh(client, project_id, revision)
    waiting = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "beat"
        and item["field_path"].endswith(".boundary")
        and item["text"] == "等待列车"
    )
    conflict = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_id"] == waiting["entity_id"] and item["field_path"].endswith(".conflict")
    )
    assert conflict["status"] == "missing"
    assert conflict["evidence_spans"] == []

    fabricated = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": conflict["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": "原文完全不存在的冲突表述",
            "reason": "must fail closed without source span",
        },
    )
    assert fabricated.status_code == 409, fabricated.text
    assert "source-backed" in fabricated.json()["detail"]["message"]

    # Reuse an exact quote already present in the Beat range prose.
    source_quote = "陈浩独自坐在长椅上"
    assert source_quote in LABELED_BEAT_CONTROL
    edited = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "edit_confirm",
            "fact_id": conflict["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
            "new_text": source_quote,
            "reason": "human supplies labeled conflict from source",
        },
    )
    assert edited.status_code == 200, edited.text
    authority = next(
        fact
        for fact in edited.json()["authoritative"]
        if fact["source_candidate_fact_id"] == conflict["fact_id"]
    )
    assert authority["text"] == source_quote
    span = authority["evidence_spans"][0]
    assert LABELED_BEAT_CONTROL[span["start"]:span["end"]] == span["quote"] == source_quote


def test_beat_duplicate_conflict_labels_fail_closed_via_api(tmp_path, monkeypatch) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_beat_dup_conflict"
    text = LABELED_BEAT_CONTROL.replace(
        "节拍1：等待列车\n陈浩独自",
        "节拍1：等待列车\n冲突：与时间赛跑\n冲突：另一冲突\n陈浩独自",
    )
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, text)
    refreshed = _refresh(client, project_id, revision)
    waiting = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "beat"
        and item["field_path"].endswith(".boundary")
        and item["text"] == "等待列车"
    )
    conflict = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_id"] == waiting["entity_id"] and item["field_path"].endswith(".conflict")
    )
    assert conflict["status"] == "missing"
    assert "multiple explicit conflict labels" in (conflict["uncertainty_note"] or "")


def test_beat_facet_repeat_refresh_accept_supersedes_via_api(tmp_path, monkeypatch) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_beat_facet_repeat"
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, LABELED_BEAT_FACET_CONTROL)

    first_refresh = _refresh(client, project_id, revision)
    first = next(
        item
        for item in first_refresh["bundle"]["items"]
        if item["entity_kind"] == "beat" and item["field_path"].endswith(".conflict")
        and item["text"] == "与时间赛跑"
    )
    first_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": first["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert first_accept.status_code == 200, first_accept.text

    second_refresh = _refresh(client, project_id, revision)
    second = next(
        item
        for item in second_refresh["bundle"]["items"]
        if item["entity_kind"] == "beat" and item["field_path"] == first["field_path"]
    )
    second_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": second["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert second_accept.status_code == 200, second_accept.text

    records = [
        record
        for record in load_ledger(RuntimeStore(tmp_path), project_id).authoritative_records
        if record.fact.field_path == first["field_path"]
    ]
    assert [record.validity.value for record in records].count("active") == 1
    assert [record.validity.value for record in records].count("superseded") == 1

    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    nodes = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("field_path") == first["field_path"]
    ]
    assert len(nodes) == 1


SCENE_CAST_EXPECTATIONS = {
    "01": {
        "废弃灯塔": {"玛雅"},
        "灯塔阳台": {"玛雅"},
    },
    "02": {
        "老式邮局": {"苏晴", "老王"},
        "海边礁石": {"苏晴", "林悦"},
        "苏晴的房间": {"苏晴"},
    },
    "03": {
        "小镇火车站": {"陈浩"},
        "陈浩家中的老屋": {"陈浩", "林秀"},
    },
    "04": {
        "阁楼": {"周明"},
        "厨房": {"周明", "母亲"},
    },
    "05": {},
    "06": {
        "地下通道": {"沈岚", "阿拓"},
        "货运站台": {"阿拓"},
    },
}


def _scene_name_to_entity_id(items: list[dict]) -> dict[str, str]:
    return {
        item["text"]: item["entity_id"]
        for item in items
        if item["entity_kind"] == "scene" and item["field_path"] == "scene.name"
    }


@pytest.mark.parametrize("script_path", SIX_SCRIPT_PATHS, ids=lambda path: path.stem)
def test_six_scripts_emit_scene_cast_appearances_via_api(
    script_path: Path,
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = f"proj_cast_{script_path.stem[:2]}"
    _create_project(client, project_id)
    source_text = script_path.read_text(encoding="utf-8")
    revision = _create_revision(client, project_id, source_text)
    refreshed = _refresh(client, project_id, revision)
    items = refreshed["bundle"]["items"]
    expected = SCENE_CAST_EXPECTATIONS[script_path.stem[:2]]
    scene_ids = _scene_name_to_entity_id(items)

    appearances = [
        item
        for item in items
        if item["entity_kind"] == "character"
        and ".cast[" in item["field_path"]
        and item["field_path"].endswith(".appearance")
    ]
    if not expected:
        assert appearances == []
        return

    by_scene: dict[str, set[str]] = {}
    for item in appearances:
        assert item["status"] == "extracted_from_text"
        assert item["evidence_spans"]
        span = item["evidence_spans"][0]
        assert source_text[span["start"]:span["end"]] == span["quote"] == item["text"]
        scene_id = item["field_path"].split("scene[", 1)[1].split("]", 1)[0]
        scene_name = next(name for name, eid in scene_ids.items() if eid == scene_id)
        by_scene.setdefault(scene_name, set()).add(item["text"])
        identity = next(
            row
            for row in items
            if row["entity_kind"] == "character"
            and row["field_path"] == "identity.display_name"
            and row["text"] == item["text"]
        )
        assert item["entity_id"] == identity["entity_id"]

    assert by_scene == expected


def test_scene_cast_accept_feeds_graph_and_resolved_via_api(tmp_path, monkeypatch) -> None:
    _enable_both(monkeypatch)
    monkeypatch.setenv(FEED_PRODUCTION_GRAPH_ENV, "true")
    client = _client(tmp_path)
    project_id = "proj_cast_graph"
    _create_project(client, project_id)
    home = (SCRIPTS / "03_labeled_fields_homecoming.txt").read_text(encoding="utf-8")
    revision = _create_revision(client, project_id, home)
    refreshed = _refresh(client, project_id, revision)
    scene_ids = _scene_name_to_entity_id(refreshed["bundle"]["items"])
    station_id = scene_ids["小镇火车站"]
    appearance = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["field_path"].startswith(f"scene[{station_id}].cast[")
        and item["text"] == "陈浩"
    )
    response = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": appearance["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert any(
        row["text"] == "陈浩" and row["field_path"] == appearance["field_path"]
        for row in body["resolved"]["scene_cast"]
    )
    graph = ProductionGraphStore(RuntimeStore(tmp_path)).load(project_id)
    cast_nodes = [
        node
        for node in graph["nodes"].values()
        if node.get("metadata", {}).get("cast_slot") == "appearance"
    ]
    assert len(cast_nodes) == 1
    assert cast_nodes[0]["metadata"]["parent_scene_id"] == station_id
    assert cast_nodes[0]["metadata"]["display_name"] == "陈浩"


def test_entity_asset_binding_bidirectional_and_supersede_via_api(tmp_path, monkeypatch) -> None:
    from apps.api.runtime_script_core_truth import ANALYSIS_CANDIDATE_SCHEMA_VERSION

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_entity_asset_bind"
    _create_project(client, project_id)
    home = (SCRIPTS / "03_labeled_fields_homecoming.txt").read_text(encoding="utf-8")
    revision = _create_revision(client, project_id, home)

    def _span(quote: str) -> dict:
        start = home.index(quote)
        return {"start": start, "end": start + len(quote), "quote": quote}

    analysis = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
            "named_characters": [
                {
                    "display_name": "陈浩",
                    "aliases": [],
                    "pronoun_links": [],
                    "evidence_spans": [_span("陈浩")],
                    "confidence": 0.95,
                    "status": "candidate",
                }
            ],
            "main_scenes": [
                {
                    "name": "小镇火车站",
                    "evidence_spans": [_span("小镇火车站")],
                    "confidence": 0.95,
                    "status": "candidate",
                }
            ],
            "style": "x",
            "genre": "y",
            "tone": "z",
            "actions": ["a"],
            "events": ["b"],
            "beats": [{"summary": "c"}],
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert analysis.status_code == 200, analysis.text
    core_assets = analysis.json()["projection"]["assets"]
    char_asset = next(asset for asset in core_assets if asset["display_name"] == "陈浩")
    scene_asset = next(asset for asset in core_assets if asset["display_name"] == "小镇火车站")

    refreshed = _refresh(client, project_id, revision)
    identity = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "character"
        and item["field_path"] == "identity.display_name"
        and item["text"] == "陈浩"
    )
    scene = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "scene" and item["text"] == "小镇火车站"
    )

    first = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": identity["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert first.status_code == 200, first.text
    binding = first.json()["entity_asset_binding"]
    assert binding is not None
    assert binding["core_asset_id"] == char_asset["asset_id"]
    assert binding["entity_id"] == identity["entity_id"]
    assert binding["authoritative_fact_id"] == first.json()["result"]["authoritative_fact_id"]

    by_entity = client.get(
        f"/projects/{project_id}/entity-asset-bindings",
        params={"entity_id": identity["entity_id"]},
    )
    assert by_entity.status_code == 200, by_entity.text
    assert by_entity.json()["bindings"][0]["core_asset_id"] == char_asset["asset_id"]

    by_asset = client.get(
        f"/projects/{project_id}/entity-asset-bindings",
        params={"core_asset_id": char_asset["asset_id"]},
    )
    assert by_asset.status_code == 200, by_asset.text
    assert by_asset.json()["bindings"][0]["entity_id"] == identity["entity_id"]

    scene_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": scene["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert scene_accept.status_code == 200, scene_accept.text
    assert scene_accept.json()["entity_asset_binding"]["core_asset_id"] == scene_asset["asset_id"]

    second_refresh = _refresh(client, project_id, revision)
    identity2 = next(
        item
        for item in second_refresh["bundle"]["items"]
        if item["field_path"] == "identity.display_name" and item["text"] == "陈浩"
    )
    second = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": identity2["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert second.status_code == 200, second.text
    binding2 = second.json()["entity_asset_binding"]
    assert binding2["core_asset_id"] == char_asset["asset_id"]
    assert binding2["authoritative_fact_id"] == second.json()["result"]["authoritative_fact_id"]
    assert binding2["authoritative_fact_id"] != binding["authoritative_fact_id"]

    station_id = scene["entity_id"]
    appearance = next(
        item
        for item in second_refresh["bundle"]["items"]
        if item["field_path"].startswith(f"scene[{station_id}].cast[") and item["text"] == "陈浩"
    )
    appearance_accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": appearance["fact_id"],
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert appearance_accept.status_code == 200, appearance_accept.text
    assert appearance_accept.json()["entity_asset_binding"] is None


def test_entity_asset_binding_stale_on_revision_change_via_api(tmp_path, monkeypatch) -> None:
    from apps.api.runtime_entity_asset_bindings import load_bindings
    from apps.api.runtime_script_core_truth import ANALYSIS_CANDIDATE_SCHEMA_VERSION

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_entity_asset_stale"
    _create_project(client, project_id)
    home = (SCRIPTS / "03_labeled_fields_homecoming.txt").read_text(encoding="utf-8")
    rev1 = _create_revision(client, project_id, home)

    def _span(quote: str) -> dict:
        start = home.index(quote)
        return {"start": start, "end": start + len(quote), "quote": quote}

    analysis = client.post(
        f"/projects/{project_id}/script-revisions/{rev1['revision_id']}/analysis-candidates",
        json={
            "project_id": project_id,
            "revision_id": rev1["revision_id"],
            "source_digest": rev1["source_digest"],
            "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
            "named_characters": [
                {
                    "display_name": "陈浩",
                    "aliases": [],
                    "pronoun_links": [],
                    "evidence_spans": [_span("陈浩")],
                    "confidence": 0.95,
                    "status": "candidate",
                }
            ],
            "main_scenes": [],
            "style": "x",
            "genre": "y",
            "tone": "z",
            "actions": ["a"],
            "events": ["b"],
            "beats": [{"summary": "c"}],
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert analysis.status_code == 200, analysis.text

    refreshed = _refresh(client, project_id, rev1)
    identity = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["field_path"] == "identity.display_name" and item["text"] == "陈浩"
    )
    accept = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": identity["fact_id"],
            "source_revision_id": rev1["revision_id"],
            "source_revision_digest": rev1["source_digest"],
        },
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["entity_asset_binding"] is not None

    text_v2 = home.replace("小镇火车站", "北方小镇火车站")
    rev2 = _create_revision(client, project_id, text_v2, parent=rev1["revision_id"])
    _refresh(client, project_id, rev2)

    active = client.get(
        f"/projects/{project_id}/entity-asset-bindings",
        params={"entity_id": identity["entity_id"]},
    )
    assert active.status_code == 200, active.text
    assert active.json()["bindings"] == []

    store = RuntimeStore(tmp_path)
    rows = load_bindings(store, project_id).bindings
    assert rows
    assert all(row.status == "stale" for row in rows)
    assert all(row.revision_id == rev1["revision_id"] for row in rows)


def _accept_item(client: TestClient, project_id: str, revision: dict, fact_id: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/candidate-facts/actions",
        json={
            "action": "accept",
            "fact_id": fact_id,
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("script_path", SIX_SCRIPT_PATHS, ids=lambda path: path.stem)
def test_six_scripts_project_character_asset_requirements_from_confirmed_cast(
    script_path: Path,
    tmp_path,
    monkeypatch,
) -> None:
    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = f"proj_areq_{script_path.stem[:2]}"
    _create_project(client, project_id)
    source_text = script_path.read_text(encoding="utf-8")
    revision = _create_revision(client, project_id, source_text)
    refreshed = _refresh(client, project_id, revision)
    expected = SCENE_CAST_EXPECTATIONS[script_path.stem[:2]]

    empty = client.get(f"/projects/{project_id}/asset-requirements")
    assert empty.status_code == 200, empty.text
    assert empty.json()["requirements"] == []
    assert empty.json()["asset_kinds_included"] == ["character"]
    assert empty.json()["asset_kinds_omitted"][0]["asset_kind"] == "prop"

    appearances = [
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "character"
        and ".cast[" in item["field_path"]
        and item["field_path"].endswith(".appearance")
    ]
    scenes = [
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_kind"] == "scene" and item["field_path"] == "scene.name"
    ]
    for item in scenes:
        _accept_item(client, project_id, revision, item["fact_id"])
    last = None
    for item in appearances:
        last = _accept_item(client, project_id, revision, item["fact_id"])

    projected = client.get(f"/projects/{project_id}/asset-requirements")
    assert projected.status_code == 200, projected.text
    body = projected.json()
    requirements = body["requirements"]
    if not expected:
        assert requirements == []
        return

    by_scene: dict[str, set[str]] = {}
    for row in requirements:
        assert row["kind"] == "asset_requirement"
        assert row["scope_kind"] == "scene"
        assert row["asset_kind"] == "character"
        assert row["core_asset_binding_status"] == "unbound"
        assert row["core_asset_id"] is None
        assert row["core_asset_binding_note"] == "暂无 Core asset 绑定"
        assert row["source_revision_id"] == revision["revision_id"]
        by_scene.setdefault(row["scope_display_name"], set()).add(row["display_name"])
    assert by_scene == expected

    assert last is not None
    assert last["resolved"]["asset_requirements"] == requirements


def test_asset_requirements_bind_when_identity_bound_and_refresh_on_supersede(
    tmp_path,
    monkeypatch,
) -> None:
    from apps.api.runtime_script_core_truth import ANALYSIS_CANDIDATE_SCHEMA_VERSION

    _enable_both(monkeypatch)
    client = _client(tmp_path)
    project_id = "proj_areq_bind"
    _create_project(client, project_id)
    home = (SCRIPTS / "03_labeled_fields_homecoming.txt").read_text(encoding="utf-8")
    revision = _create_revision(client, project_id, home)

    def _span(quote: str) -> dict:
        start = home.index(quote)
        return {"start": start, "end": start + len(quote), "quote": quote}

    analysis = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
            "named_characters": [
                {
                    "display_name": "陈浩",
                    "aliases": [],
                    "pronoun_links": [],
                    "evidence_spans": [_span("陈浩")],
                    "confidence": 0.95,
                    "status": "candidate",
                }
            ],
            "main_scenes": [
                {
                    "name": "小镇火车站",
                    "evidence_spans": [_span("小镇火车站")],
                    "confidence": 0.95,
                    "status": "candidate",
                }
            ],
            "style": "x",
            "genre": "y",
            "tone": "z",
            "actions": ["a"],
            "events": ["b"],
            "beats": [{"summary": "c"}],
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert analysis.status_code == 200, analysis.text
    char_asset = next(
        asset
        for asset in analysis.json()["projection"]["assets"]
        if asset["display_name"] == "陈浩"
    )

    refreshed = _refresh(client, project_id, revision)
    scene_ids = _scene_name_to_entity_id(refreshed["bundle"]["items"])
    station_id = scene_ids["小镇火车站"]
    identity = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["field_path"] == "identity.display_name" and item["text"] == "陈浩"
    )
    scene = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["entity_id"] == station_id and item["field_path"] == "scene.name"
    )
    appearance = next(
        item
        for item in refreshed["bundle"]["items"]
        if item["field_path"].startswith(f"scene[{station_id}].cast[") and item["text"] == "陈浩"
    )

    _accept_item(client, project_id, revision, scene["fact_id"])
    _accept_item(client, project_id, revision, identity["fact_id"])
    accept_cast = _accept_item(client, project_id, revision, appearance["fact_id"])

    bound_rows = [
        row
        for row in accept_cast["resolved"]["asset_requirements"]
        if row["scope_entity_id"] == station_id and row["display_name"] == "陈浩"
    ]
    assert len(bound_rows) == 1
    assert bound_rows[0]["core_asset_binding_status"] == "bound"
    assert bound_rows[0]["core_asset_id"] == char_asset["asset_id"]
    assert bound_rows[0]["core_asset_binding_note"] is None

    # Supersede cast via re-accept after refresh → requirement tracks new authoritative id.
    refreshed2 = _refresh(client, project_id, revision)
    appearance2 = next(
        item
        for item in refreshed2["bundle"]["items"]
        if item["field_path"].startswith(f"scene[{station_id}].cast[") and item["text"] == "陈浩"
    )
    superseded = _accept_item(client, project_id, revision, appearance2["fact_id"])
    new_auth = superseded["result"]["authoritative_fact_id"]
    assert new_auth != bound_rows[0]["source_cast_authoritative_fact_id"]
    updated = next(
        row
        for row in superseded["resolved"]["asset_requirements"]
        if row["scope_entity_id"] == station_id and row["display_name"] == "陈浩"
    )
    assert updated["source_cast_authoritative_fact_id"] == new_auth
    assert updated["core_asset_id"] == char_asset["asset_id"]

    # New revision invalidates old authority → requirements empty for new rev.
    text_v2 = home.replace("小镇火车站", "北方小镇火车站")
    rev2 = _create_revision(client, project_id, text_v2, parent=revision["revision_id"])
    _refresh(client, project_id, rev2)
    after = client.get(
        f"/projects/{project_id}/asset-requirements",
        params={"source_revision_id": rev2["revision_id"]},
    )
    assert after.status_code == 200, after.text
    assert after.json()["requirements"] == []
