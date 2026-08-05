from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from apps.api.runtime_script_core_truth import (
    ANALYSIS_CANDIDATE_SCHEMA_VERSION,
    ANALYSIS_REVIEW_SCHEMA_VERSION,
    CORE_ASSET_COMMAND_SCHEMA_VERSION,
)
from apps.api.runtime_service import create_runtime_app


def _client(tmp_path) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=tmp_path))


def _auth_headers(session_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_token}"}


def _register(client: TestClient, *, invite_code: str, email: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": email.split("@", 1)[0],
            "invite_code": invite_code,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_project(client: TestClient, project_id: str, headers: dict[str, str] | None = None) -> None:
    response = client.post("/projects", json={"project_id": project_id, "goal": f"{project_id} story"}, headers=headers or {})
    assert response.status_code == 200, response.text


def _create_revision(client: TestClient, project_id: str, text: str, *, parent_revision_id: str = "") -> dict:
    payload = {"source_kind": "script", "source_text": text, "provenance": {"test": "script_core_truth"}}
    if parent_revision_id:
        payload["parent_revision_id"] = parent_revision_id
    response = client.post(f"/projects/{project_id}/script-revisions", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["revision"]


def _span(text: str, quote: str) -> dict:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _candidate(project_id: str, revision: dict, *, characters: list[dict], scenes: list[dict], **extra) -> dict:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
        "named_characters": characters,
        "main_scenes": scenes,
        "style": extra.get("style", "quiet observational"),
        "genre": extra.get("genre", "short drama"),
        "tone": extra.get("tone", "restrained"),
        "actions": extra.get("actions", ["opens the door"]),
        "events": extra.get("events", ["a choice is made"]),
        "beats": extra.get("beats", [{"summary": "setup"}]),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _character(text: str, name: str, quote: str, confidence: float = 0.91, aliases: list[str] | None = None) -> dict:
    return {
        "display_name": name,
        "aliases": aliases or [],
        "pronoun_links": [],
        "evidence_spans": [_span(text, quote)],
        "confidence": confidence,
        "status": "candidate",
    }


def _scene(text: str, name: str, quote: str, confidence: float = 0.9) -> dict:
    return {"name": name, "evidence_spans": [_span(text, quote)], "confidence": confidence, "status": "candidate"}


def test_script_core_truth_auth_scope_covers_revision_and_projection(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-invite,beta-invite")
    client = _client(tmp_path)
    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    beta = _register(client, invite_code="beta-invite", email="beta@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])
    _create_project(client, "alpha-script-truth", alpha_headers)

    assert client.get("/projects/alpha-script-truth/script-truth").status_code == 401
    assert client.get("/projects/alpha-script-truth/script-truth", headers=beta_headers).status_code == 403
    empty = client.get("/projects/alpha-script-truth/script-truth", headers=alpha_headers)
    assert empty.status_code == 200, empty.text
    assert empty.json()["projection"]["analysis_state"] == "analysis_required"

    created = client.post(
        "/projects/alpha-script-truth/script-revisions",
        json={"source_kind": "idea", "source_text": "A short idea enters a traceable revision."},
        headers=alpha_headers,
    )
    assert created.status_code == 200, created.text
    assert created.json()["revision"]["source_digest"] == hashlib.sha256(b"A short idea enters a traceable revision.").hexdigest()
    refreshed = client.get("/projects/alpha-script-truth/script-truth", headers=alpha_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["projection"]["current_revision"]["source_text"] == "A short idea enters a traceable revision."
    assert "source_text" not in refreshed.json()["projection"]["revision_history"][0]
    assert client.post(
        "/projects/alpha-script-truth/script-revisions",
        json={"source_kind": "idea", "source_text": "blocked"},
        headers=beta_headers,
    ).status_code == 403


def test_revision_candidate_contract_fails_closed_and_keeps_narrative_fields_out_of_assets(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "contract-fail-closed"
    _create_project(client, project_id)
    text = "Mira waits in the Observatory. Rowan enters with a folded map."
    revision = _create_revision(client, project_id, text)
    truth = client.get(f"/projects/{project_id}/script-truth").json()["projection"]
    assert truth["current_revision_id"] == revision["revision_id"]
    assert truth["analysis_state"] == "analysis_required"
    assert truth["assets"] == []

    good_candidate = _candidate(
        project_id,
        revision,
        characters=[
            _character(text, "Mira", "Mira", 0.93),
            _character(text, "Rowan", "Rowan", 0.88),
        ],
        scenes=[_scene(text, "Observatory", "Observatory", 0.91)],
    )
    for patch, expected_error in [
        ({"schema_version": "wrong.schema"}, "schema_version_mismatch"),
        ({"source_digest": "0" * 64}, "source_digest_mismatch"),
        ({"project_id": "other-project"}, "project_identity_mismatch"),
    ]:
        body = {**good_candidate, **patch}
        response = client.post(
            f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
            json=body,
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error"] == expected_error

    evidence_mismatch = {
        **good_candidate,
        "named_characters": [{**good_candidate["named_characters"][0], "evidence_spans": [{"start": 0, "end": 4, "quote": "Nope"}]}],
    }
    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json=evidence_mismatch,
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "evidence_span_mismatch"

    accepted = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json=good_candidate,
    )
    assert accepted.status_code == 200, accepted.text
    projection = accepted.json()["projection"]
    assert projection["analysis_state"] == "pending_confirmation"
    assert projection["asset_counts"] == {
        "characters": 2,
        "main_scenes": 1,
        "manual_props": 0,
        "auto_props": 0,
        "style_assets": 0,
        "action_event_assets": 0,
    }
    assert {item["asset_type"] for item in projection["assets"]} == {"character", "main_scene"}
    assert {item["status"] for item in projection["assets"]} == {"candidate"}
    assert projection["narrative_fields"]["promoted_to_assets"] is False
    assert projection["narrative_fields"]["actions_count"] == 1
    assert accepted.json()["provider_dispatch_count"] == 0


def test_structured_candidate_aliases_require_explicit_merge_alias(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "candidate-alias-authority-boundary"
    text = "Captain Vale, called V, waits in the archive."
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json=_candidate(
            project_id,
            revision,
            characters=[_character(text, "Captain Vale", "Captain Vale", aliases=["V"])],
            scenes=[_scene(text, "Archive", "archive")],
        ),
    )

    assert response.status_code == 422, response.text
    projection = client.get(f"/projects/{project_id}/script-truth").json()["projection"]
    assert projection["assets"] == []
    assert projection["current_revision"]["analysis_state"] == "analysis_required"


def test_legacy_candidate_alias_needs_merge_receipt_before_review_after_restart(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "legacy-candidate-alias-recovery"
    text = "Captain Vale waits in the archive."
    _create_project(client, project_id)
    revision = _create_revision(client, project_id, text)
    accepted = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json=_candidate(
            project_id,
            revision,
            characters=[_character(text, "Captain Vale", "Captain Vale")],
            scenes=[_scene(text, "Archive", "archive")],
        ),
    )
    assert accepted.status_code == 200, accepted.text
    candidate = accepted.json()["candidate"]
    character = next(
        item for item in accepted.json()["projection"]["assets"] if item["asset_type"] == "character"
    )

    state_path = tmp_path / "projects" / project_id / "script_core_truth" / "truth_state.json"
    legacy_state = json.loads(state_path.read_text(encoding="utf-8"))
    legacy_state["assets"][character["asset_id"]]["aliases"] = ["V"]
    state_path.write_text(json.dumps(legacy_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    restarted = _client(tmp_path)
    review_body = {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "candidate_id": candidate["candidate_id"],
        "asset_version_id": character["version_id"],
        "expected_asset_version": character["version"],
        "expected_graph_version": 0,
        "idempotency_key": "confirm-legacy-alias-without-merge",
        "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
        "decision": "confirm",
    }
    blocked = restarted.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json=review_body,
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["error"] == "candidate_aliases_require_merge_alias"
    blocked_projection = restarted.get(f"/projects/{project_id}/script-truth").json()["projection"]
    blocked_character = next(
        item for item in blocked_projection["assets"] if item["asset_id"] == character["asset_id"]
    )
    assert blocked_character["status"] == "candidate"
    assert blocked_character["version"] == character["version"]
    assert restarted.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]["nodes"] == {}

    merged = restarted.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_command(
                project_id,
                revision,
                "merge_alias",
                target_asset_id=character["asset_id"],
                patch={"alias": "V"},
            ),
            "expected_asset_version": character["version"],
            "idempotency_key": "authorize-legacy-alias-v",
        },
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["receipt"]["authorized_alias"] == "V"
    undone = restarted.post(
        f"/projects/{project_id}/core-assets/commands/undo",
        json={
            "project_id": project_id,
            "receipt_id": merged.json()["receipt"]["receipt_id"],
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        },
    )
    assert undone.status_code == 200, undone.text
    undone_character = next(
        item for item in undone.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"]
    )
    restarted = _client(tmp_path)
    duplicate_undo = restarted.post(
        f"/projects/{project_id}/core-assets/commands/undo",
        json={
            "project_id": project_id,
            "receipt_id": merged.json()["receipt"]["receipt_id"],
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        },
    )
    assert duplicate_undo.status_code == 409, duplicate_undo.text
    assert duplicate_undo.json()["detail"]["error"] == "core_asset_receipt_not_undoable"
    blocked_after_undo = restarted.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json={
            **review_body,
            "asset_version_id": undone_character["version_id"],
            "expected_asset_version": undone_character["version"],
            "idempotency_key": "confirm-legacy-alias-after-merge-undo",
        },
    )
    assert blocked_after_undo.status_code == 409, blocked_after_undo.text
    assert blocked_after_undo.json()["detail"]["error"] == "candidate_aliases_require_merge_alias"

    remerged = restarted.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_command(
                project_id,
                revision,
                "merge_alias",
                target_asset_id=character["asset_id"],
                patch={"alias": "V"},
            ),
            "expected_asset_version": undone_character["version"],
            "idempotency_key": "reauthorize-legacy-alias-v",
        },
    )
    assert remerged.status_code == 200, remerged.text
    remerged_character = next(
        item for item in remerged.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"]
    )
    confirmed = restarted.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json={
            **review_body,
            "asset_version_id": remerged_character["version_id"],
            "expected_asset_version": remerged_character["version"],
            "idempotency_key": "confirm-legacy-alias-after-remerge",
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["asset"]["status"] == "confirmed"
    assert confirmed.json()["asset"]["aliases"] == ["V"]


def test_varied_structured_candidates_cover_scenes_and_low_confidence(tmp_path) -> None:
    client = _client(tmp_path)
    cases = [
        (
            "single-lead-partner",
            "Iris repairs the radio while Niko keeps watch beside the ferry terminal.",
            lambda text, revision, project_id: _candidate(
                project_id,
                revision,
                characters=[_character(text, "Iris", "Iris"), _character(text, "Niko", "Niko")],
                scenes=[_scene(text, "Ferry Terminal", "ferry terminal")],
            ),
            "pending_confirmation",
            2,
            1,
        ),
        (
            "dual-leads",
            "Captain Vale, called V, argues with Dr. Sato before she unlocks the archive.",
            lambda text, revision, project_id: _candidate(
                project_id,
                revision,
                characters=[
                    _character(text, "Captain Vale", "Captain Vale"),
                    _character(text, "Dr. Sato", "Dr. Sato"),
                ],
                scenes=[_scene(text, "Archive", "archive")],
            ),
            "pending_confirmation",
            2,
            1,
        ),
        (
            "multi-scene",
            "At the clinic, Lena finds the file. On the rooftop, Omar burns the envelope.",
            lambda text, revision, project_id: _candidate(
                project_id,
                revision,
                characters=[_character(text, "Lena", "Lena"), _character(text, "Omar", "Omar")],
                scenes=[_scene(text, "Clinic", "clinic"), _scene(text, "Rooftop", "rooftop")],
            ),
            "pending_confirmation",
            2,
            2,
        ),
        (
            "low-confidence-empty",
            "A sound moves through the room, and no speaker is named.",
            lambda text, revision, project_id: _candidate(project_id, revision, characters=[], scenes=[]),
            "low_confidence_pending",
            0,
            0,
        ),
    ]
    for project_id, text, build_candidate, expected_state, expected_characters, expected_scenes in cases:
        _create_project(client, project_id)
        revision = _create_revision(client, project_id, text)
        response = client.post(
            f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
            json=build_candidate(text, revision, project_id),
        )
        assert response.status_code == 200, response.text
        projection = response.json()["projection"]
        assert projection["analysis_state"] == expected_state
        assert projection["asset_counts"]["characters"] == expected_characters
        assert projection["asset_counts"]["main_scenes"] == expected_scenes
        assert projection["asset_counts"]["auto_props"] == 0
        assert projection["asset_counts"]["style_assets"] == 0
        assert projection["asset_counts"]["action_event_assets"] == 0
        assert all(item["asset_type"] in {"character", "main_scene"} for item in projection["assets"])


def test_core_asset_commands_preview_confirm_receipt_undo_and_pollution_zero(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "core-asset-commands"
    _create_project(client, project_id)
    text = "Jun meets Asha in the editing suite."
    revision = _create_revision(client, project_id, text)
    accepted = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json=_candidate(
            project_id,
            revision,
            characters=[_character(text, "Jun", "Jun"), _character(text, "Asha", "Asha")],
            scenes=[_scene(text, "Editing Suite", "editing suite")],
        ),
    )
    assert accepted.status_code == 200, accepted.text
    character = next(item for item in accepted.json()["projection"]["assets"] if item["asset_type"] == "character")

    edit_payload = _command(project_id, revision, "edit_asset", target_asset_id=character["asset_id"], patch={"display_name": "Jun Park"})
    preview = client.post(f"/projects/{project_id}/core-assets/commands/preview", json=edit_payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["command"]["status"] == "preview"
    confirmed = client.post(f"/projects/{project_id}/core-assets/commands/confirm", json=edit_payload)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["receipt"]["undo_available"] is True
    assert any(item["display_name"] == "Jun Park" for item in confirmed.json()["projection"]["assets"])

    undo = client.post(
        f"/projects/{project_id}/core-assets/commands/undo",
        json={
            "project_id": project_id,
            "receipt_id": confirmed.json()["receipt"]["receipt_id"],
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        },
    )
    assert undo.status_code == 200, undo.text
    assert any(item["display_name"] == "Jun" for item in undo.json()["projection"]["assets"])

    alias = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json=_command(project_id, revision, "merge_alias", target_asset_id=character["asset_id"], patch={"alias": "J"}),
    )
    assert alias.status_code == 200, alias.text
    assert "J" in next(item for item in alias.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"])["aliases"]

    retired = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json=_command(project_id, revision, "retire_asset", target_asset_id=character["asset_id"]),
    )
    assert retired.status_code == 200, retired.text
    assert next(item for item in retired.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"])["status"] == "retired"

    restored = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json=_command(project_id, revision, "restore_asset", target_asset_id=character["asset_id"]),
    )
    assert restored.status_code == 200, restored.text
    assert next(item for item in restored.json()["projection"]["assets"] if item["asset_id"] == character["asset_id"])["status"] == "confirmed"

    manual = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json=_command(project_id, revision, "create_manual_prop", patch={"display_name": "brass key"}),
    )
    assert manual.status_code == 200, manual.text
    projection = manual.json()["projection"]
    assert projection["asset_counts"]["manual_props"] == 1
    assert projection["asset_counts"]["auto_props"] == 0
    assert any(item["asset_type"] == "prop" and item["source_mode"] == "manual" for item in projection["assets"])
    assert manual.json()["provider_dispatch_count"] == 0


def test_revision_history_selection_and_preserved_affected_sets(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "revision-history-lineage"
    _create_project(client, project_id)
    text_one = "Noa enters the print shop and sees the broken press."
    revision_one = _create_revision(client, project_id, text_one)
    body_one = _candidate(
        project_id,
        revision_one,
        characters=[_character(text_one, "Noa", "Noa")],
        scenes=[_scene(text_one, "Print Shop", "print shop")],
    )
    first = client.post(
        f"/projects/{project_id}/script-revisions/{revision_one['revision_id']}/analysis-candidates",
        json=body_one,
    )
    assert first.status_code == 200, first.text
    asset_id = first.json()["projection"]["assets"][0]["asset_id"]

    replay = client.post(
        f"/projects/{project_id}/script-revisions/{revision_one['revision_id']}/analysis-candidates",
        json=body_one,
    )
    assert replay.status_code == 200, replay.text
    assert asset_id in replay.json()["preserved_asset_ids"]

    text_two = "Noa enters the print shop and sees the repaired press."
    revision_two = _create_revision(client, project_id, text_two, parent_revision_id=revision_one["revision_id"])
    body_two = _candidate(
        project_id,
        revision_two,
        characters=[_character(text_two, "Noa", "Noa")],
        scenes=[_scene(text_two, "Print Shop", "print shop")],
    )
    second = client.post(
        f"/projects/{project_id}/script-revisions/{revision_two['revision_id']}/analysis-candidates",
        json=body_two,
    )
    assert second.status_code == 200, second.text
    assert asset_id in second.json()["affected_asset_ids"]
    assert len(second.json()["projection"]["revision_history"]) == 2

    select_old = client.post(f"/projects/{project_id}/script-revisions/{revision_one['revision_id']}/select")
    assert select_old.status_code == 200, select_old.text
    assert select_old.json()["current_revision_id"] == revision_one["revision_id"]
    stale = client.post(
        f"/projects/{project_id}/script-revisions/{revision_two['revision_id']}/analysis-candidates",
        json=body_two,
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["error"] == "current_revision_mismatch"


def _command(
    project_id: str,
    revision: dict,
    command_type: str,
    *,
    target_asset_id: str | None = None,
    patch: dict | None = None,
) -> dict:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        "command_type": command_type,
        "target_asset_id": target_asset_id,
        "patch": patch or {},
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
