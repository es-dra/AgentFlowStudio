"""Persisted candidate confirmation loop API — A/B/C acceptance via real routes."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_candidate_confirmation import (
    CONFIRMATION_LOOP_ENV,
    load_ledger,
)
from apps.api.runtime_m6_script_plan_asset_bible import IMPROVED_EXTRACTION_ENV
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
