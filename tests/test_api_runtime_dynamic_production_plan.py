from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_dynamic_production_plan import (
    PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION,
    PROVIDER_CAPABILITY_SCHEMA_VERSION,
    STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
    story_plan_candidate_digest,
)
from apps.api.runtime_script_core_truth import ANALYSIS_CANDIDATE_SCHEMA_VERSION
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


def _create_revision(client: TestClient, project_id: str, text: str, headers: dict[str, str] | None = None) -> dict:
    response = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": text, "provenance": {"test": "dynamic_plan"}},
        headers=headers or {},
    )
    assert response.status_code == 200, response.text
    return response.json()["revision"]


def _span(text: str, quote: str) -> dict:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _analysis_candidate(project_id: str, revision: dict, text: str) -> dict:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
        "named_characters": [
            {
                "display_name": "Mira",
                "aliases": ["she"],
                "pronoun_links": [],
                "evidence_spans": [_span(text, "Mira")],
                "confidence": 0.94,
                "status": "candidate",
            },
            {
                "display_name": "Tao",
                "aliases": [],
                "pronoun_links": [],
                "evidence_spans": [_span(text, "Tao")],
                "confidence": 0.9,
                "status": "candidate",
            },
        ],
        "main_scenes": [
            {
                "name": "Observatory",
                "evidence_spans": [_span(text, "observatory")],
                "confidence": 0.92,
                "status": "candidate",
            },
            {
                "name": "Signal Room",
                "evidence_spans": [_span(text, "signal room")],
                "confidence": 0.91,
                "status": "candidate",
            },
        ],
        "style": "precise luminous animation",
        "genre": "short science drama",
        "tone": "focused",
        "actions": ["Mira calibrates the lens", "Tao opens the signal room"],
        "events": ["a distant signal arrives"],
        "beats": [{"summary": "signal setup"}, {"summary": "response"}],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _bootstrap_script_core_truth(
    client: TestClient,
    project_id: str,
    headers: dict[str, str] | None = None,
) -> tuple[dict, dict]:
    text = "Mira calibrates the lens in the observatory. Tao opens the signal room as a distant signal arrives."
    _create_project(client, project_id, headers)
    revision = _create_revision(client, project_id, text, headers)
    accepted = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json=_analysis_candidate(project_id, revision, text),
        headers=headers or {},
    )
    assert accepted.status_code == 200, accepted.text
    return revision, accepted.json()["projection"]


def _capability(durations: list[float], *, supports_i2v: bool = True) -> dict:
    return {
        "schema_version": PROVIDER_CAPABILITY_SCHEMA_VERSION,
        "provider_profile_id": "offline-contract-capability",
        "supports_t2v": True,
        "supports_i2v": supports_i2v,
        "supported_clip_durations": durations,
        "max_duration_seconds": max(durations),
        "supports_start_frame": True,
        "supports_end_frame": True,
        "aspect_ratios": ["9:16", "16:9"],
        "fps_values": [24],
    }


def _asset_ids(projection: dict) -> tuple[list[str], list[str]]:
    characters = [item["asset_id"] for item in projection["assets"] if item["asset_type"] == "character"]
    scenes = [item["asset_id"] for item in projection["assets"] if item["asset_type"] == "main_scene"]
    return characters, scenes


def _t2v(reason: str) -> dict:
    return {
        "strategy": "t2v",
        "strategy_reason": reason,
        "input_requirements": ["text_prompt_contract"],
        "reference_asset_refs": [],
        "user_constraints": {"explicit_reference_available": False},
    }


def _i2v(project_id: str, revision: dict, asset_id: str, reason: str) -> dict:
    return {
        "strategy": "i2v",
        "strategy_reason": reason,
        "input_requirements": ["reference_artifact_or_locked_keyframe"],
        "reference_asset_refs": [
            {
                "ref_id": "ref_lens_keyframe",
                "source_kind": "locked_keyframe",
                "asset_id": asset_id,
                "artifact_id": "artifact-lens-keyframe",
                "lineage": {
                    "project_id": project_id,
                    "script_revision_id": revision["revision_id"],
                    "source_digest": revision["source_digest"],
                    "asset_id": asset_id,
                    "artifact_id": "artifact-lens-keyframe",
                    "locked_keyframe_id": "locked-keyframe-lens",
                },
            }
        ],
        "user_constraints": {"explicit_reference_available": True},
    }


def _plan_candidate(
    project_id: str,
    revision: dict,
    projection: dict,
    *,
    shot_durations: list[float],
    capability: dict | None = None,
    strategy_mode: str = "mixed",
) -> dict:
    characters, scenes = _asset_ids(projection)
    beats = [
        {
            "beat_id": "beat_signal_setup",
            "order": 1,
            "summary": "Mira notices the signal and prepares the lens.",
            "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "Mira calibrates the lens"}],
            "narrative_purpose": "establish the incoming signal",
        },
        {
            "beat_id": "beat_signal_response",
            "order": 2,
            "summary": "Tao opens the response path in the signal room.",
            "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "Tao opens the signal room"}],
            "narrative_purpose": "move from discovery to response",
        },
    ]
    shots = []
    for index, duration in enumerate(shot_durations, start=1):
        beat_id = beats[0]["beat_id"] if index <= max(1, len(shot_durations) // 2) else beats[1]["beat_id"]
        strategy = _t2v("no explicit visual reference is required for this shot")
        if strategy_mode == "mixed" and index == 2:
            strategy = _i2v(project_id, revision, characters[0], "locked keyframe lineage is available for the lens move")
        if strategy_mode == "i2v_missing" and index == 1:
            strategy = {
                "strategy": "i2v",
                "strategy_reason": "user requested an image-guided shot but no reference has been attached",
                "input_requirements": ["reference_artifact_or_locked_keyframe"],
                "reference_asset_refs": [],
                "user_constraints": {"explicit_reference_available": False},
            }
        shots.append(
            {
                "shot_id": f"shot_dynamic_{index}",
                "beat_id": beat_id,
                "order": index,
                "intent": f"Dynamic shot {index} follows the signal without fixed timing.",
                "duration_seconds": duration,
                "character_refs": characters[: 1 if index == 1 else 2],
                "scene_refs": scenes[:1] if index != len(shot_durations) else scenes[-1:],
                "continuity_in": "previous lens pose" if index > 1 else "opening stillness",
                "continuity_out": "signal line continues" if index < len(shot_durations) else "response path holds",
                "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "distant signal arrives"}],
                "media_strategy": strategy,
            }
        )
    payload = {
        "project_id": project_id,
        "script_revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
        "candidate_digest": "",
        "beats": beats,
        "shots": shots,
        "capability_contract": capability or _capability([2.5, 3.0, 4.0]),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    payload["candidate_digest"] = story_plan_candidate_digest(payload)
    return payload


def _submit_and_confirm_plan(client: TestClient, project_id: str, candidate: dict, headers: dict[str, str] | None = None) -> dict:
    submitted = client.post(f"/projects/{project_id}/story-plan-candidates", json=candidate, headers=headers or {})
    assert submitted.status_code == 200, submitted.text
    confirmed = client.post(
        f"/projects/{project_id}/story-plan-candidates/{candidate['candidate_digest']}/confirm",
        json={
            "project_id": project_id,
            "script_revision_id": candidate["script_revision_id"],
            "source_digest": candidate["source_digest"],
            "candidate_digest": candidate["candidate_digest"],
            "schema_version": STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
        },
        headers=headers or {},
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def _plan_command(project_id: str, projection: dict, command_type: str, **overrides) -> dict:
    plan = projection["current_plan"]
    payload = {
        "project_id": project_id,
        "script_revision_id": plan["script_revision_id"],
        "source_digest": plan["source_digest"],
        "plan_id": plan["plan_id"],
        "plan_digest": plan["plan_digest"],
        "schema_version": PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION,
        "command_type": command_type,
        "target_shot_id": overrides.pop("target_shot_id", None),
        "target_chunk_id": overrides.pop("target_chunk_id", None),
        "patch": overrides.pop("patch", {}),
        "reason": overrides.pop("reason", "test_confirmed"),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    payload.update(overrides)
    return payload


def test_production_plan_auth_scope_and_empty_planning_required(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-plan,beta-plan")
    client = _client(tmp_path)
    alpha = _register(client, invite_code="alpha-plan", email="alpha-plan@example.com")
    beta = _register(client, invite_code="beta-plan", email="beta-plan@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])
    revision, projection = _bootstrap_script_core_truth(client, "alpha-dynamic-plan", alpha_headers)
    candidate = _plan_candidate("alpha-dynamic-plan", revision, projection, shot_durations=[2.5, 3.0, 6.5])

    assert client.get("/projects/alpha-dynamic-plan/production-plan-truth").status_code == 401
    assert client.get("/projects/alpha-dynamic-plan/production-plan-truth", headers=beta_headers).status_code == 403
    empty = client.get("/projects/alpha-dynamic-plan/production-plan-truth", headers=alpha_headers)
    assert empty.status_code == 200, empty.text
    assert empty.json()["projection"]["planning_state"] == "planning_required"

    blocked = client.post("/projects/alpha-dynamic-plan/story-plan-candidates", json=candidate, headers=beta_headers)
    assert blocked.status_code == 403
    accepted = _submit_and_confirm_plan(client, "alpha-dynamic-plan", candidate, alpha_headers)
    assert accepted["projection"]["planning_state"] == "planned"
    assert accepted["provider_dispatch_count"] == 0


def test_dynamic_story_plan_candidate_creates_variable_shots_strategies_chunks_and_concat(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "dynamic-plan-variable"
    revision, projection = _bootstrap_script_core_truth(client, project_id)
    candidate = _plan_candidate(project_id, revision, projection, shot_durations=[2.5, 3.0, 6.5], strategy_mode="mixed")
    confirmed = _submit_and_confirm_plan(client, project_id, candidate)
    plan = confirmed["projection"]

    assert plan["planning_state"] == "planned"
    assert [shot["duration_seconds"] for shot in plan["shots"]] == [2.5, 3.0, 6.5]
    assert [shot["order"] for shot in plan["shots"]] == [1, 2, 3]
    assert {shot["media_strategy"]["strategy"] for shot in plan["shots"]} == {"t2v", "i2v"}
    assert all(shot["media_strategy"]["strategy_reason"] for shot in plan["shots"])
    assert sum(chunk["target_duration_seconds"] for chunk in plan["chunks"] if chunk["shot_id"] == "shot_dynamic_3") == 6.5
    assert all(chunk["continuity_anchor_out"] for chunk in plan["chunks"])
    assert plan["concat_plan"]["state"] == "planned_not_executed"
    assert plan["concat_plan"]["shot_order"] == ["shot_dynamic_1", "shot_dynamic_2", "shot_dynamic_3"]
    assert plan["provider_dispatch_count"] == 0
    assert plan["remote_dispatch_count"] == 0


def test_story_plan_candidate_fail_closed_mismatches_and_pending_inputs(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "dynamic-plan-fail-closed"
    revision, projection = _bootstrap_script_core_truth(client, project_id)
    candidate = _plan_candidate(project_id, revision, projection, shot_durations=[2.25, 4.75], capability=_capability([3.0, 4.0]))

    for patch, expected_error in [
        ({"schema_version": "wrong.schema"}, "schema_version_mismatch"),
        ({"source_digest": "0" * 64}, "script_revision_contract_mismatch"),
        ({"project_id": "other-project"}, "project_identity_mismatch"),
    ]:
        body = {**candidate, **patch}
        if patch.get("schema_version") != "wrong.schema":
            body["candidate_digest"] = story_plan_candidate_digest(body)
        response = client.post(f"/projects/{project_id}/story-plan-candidates", json=body)
        assert response.status_code == 409
        assert response.json()["detail"]["error"] == expected_error

    bad_digest = {**candidate, "candidate_digest": "f" * 64}
    response = client.post(f"/projects/{project_id}/story-plan-candidates", json=bad_digest)
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "candidate_digest_mismatch"

    bad_ref = _plan_candidate(project_id, revision, projection, shot_durations=[2.5])
    bad_ref["shots"][0]["character_refs"] = ["missing-character"]
    bad_ref["candidate_digest"] = story_plan_candidate_digest(bad_ref)
    response = client.post(f"/projects/{project_id}/story-plan-candidates", json=bad_ref)
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "character_reference_mismatch"

    pending_input = _plan_candidate(project_id, revision, projection, shot_durations=[2.25], capability=_capability([3.0, 4.0]), strategy_mode="i2v_missing")
    confirmed = _submit_and_confirm_plan(client, project_id, pending_input)
    assert confirmed["projection"]["planning_state"] in {"pending_input", "pending_capability"}
    first = confirmed["projection"]["shots"][0]
    assert first["media_strategy"]["strategy"] == "i2v"
    assert first["media_input_state"] == "pending_input"
    assert first["status"] == "blocked"
    assert any(chunk["remainder_strategy"] == "pending_capability" for chunk in confirmed["projection"]["chunks"])


def test_production_plan_commands_preview_confirm_undo_split_merge_and_retry_only_failed(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "dynamic-plan-commands"
    revision, projection = _bootstrap_script_core_truth(client, project_id)
    candidate = _plan_candidate(project_id, revision, projection, shot_durations=[3.0, 4.0, 6.5], strategy_mode="mixed")
    confirmed = _submit_and_confirm_plan(client, project_id, candidate)
    plan_projection = confirmed["projection"]
    original_digest = plan_projection["current_plan"]["plan_digest"]

    edit_payload = _plan_command(
        project_id,
        plan_projection,
        "edit_shot_duration",
        target_shot_id="shot_dynamic_3",
        patch={"duration_seconds": 7.0},
    )
    preview = client.post(f"/projects/{project_id}/production-plan-commands/preview", json=edit_payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["command"]["status"] == "preview"
    assert "shot_dynamic_3" in preview.json()["command"]["affected_ids"]
    assert "shot_dynamic_1" in preview.json()["command"]["preserved_ids"]
    edited = client.post(f"/projects/{project_id}/production-plan-commands/confirm", json=edit_payload)
    assert edited.status_code == 200, edited.text
    assert next(shot for shot in edited.json()["projection"]["shots"] if shot["shot_id"] == "shot_dynamic_3")["duration_seconds"] == 7.0
    assert edited.json()["receipt"]["undo_available"] is True

    undo = client.post(
        f"/projects/{project_id}/production-plan-commands/undo",
        json={
            "project_id": project_id,
            "receipt_id": edited.json()["receipt"]["receipt_id"],
            "script_revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "plan_digest": edited.json()["projection"]["current_plan"]["plan_digest"],
            "schema_version": PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION,
        },
    )
    assert undo.status_code == 200, undo.text
    assert undo.json()["projection"]["current_plan"]["plan_digest"] == original_digest

    plan_projection = undo.json()["projection"]
    split_payload = _plan_command(project_id, plan_projection, "split_shot", target_shot_id="shot_dynamic_2", patch={"durations": [1.5, 2.5]})
    split = client.post(f"/projects/{project_id}/production-plan-commands/confirm", json=split_payload)
    assert split.status_code == 200, split.text
    assert [shot["shot_id"] for shot in split.json()["projection"]["shots"]] == ["shot_dynamic_1", "shot_dynamic_2a", "shot_dynamic_2b", "shot_dynamic_3"]

    merge_payload = _plan_command(project_id, split.json()["projection"], "merge_shot_next", target_shot_id="shot_dynamic_2a")
    merged = client.post(f"/projects/{project_id}/production-plan-commands/confirm", json=merge_payload)
    assert merged.status_code == 200, merged.text
    assert [shot["shot_id"] for shot in merged.json()["projection"]["shots"]] == ["shot_dynamic_1", "shot_dynamic_2a", "shot_dynamic_3"]

    chunk_id = next(chunk["chunk_id"] for chunk in merged.json()["projection"]["chunks"] if chunk["shot_id"] == "shot_dynamic_3")
    failed_payload = _plan_command(project_id, merged.json()["projection"], "mark_failed", target_chunk_id=chunk_id)
    failed = client.post(f"/projects/{project_id}/production-plan-commands/confirm", json=failed_payload)
    assert failed.status_code == 200, failed.text
    assert next(chunk for chunk in failed.json()["projection"]["chunks"] if chunk["chunk_id"] == chunk_id)["state"] == "failed"

    retry_payload = _plan_command(project_id, failed.json()["projection"], "retry_failed")
    retried = client.post(f"/projects/{project_id}/production-plan-commands/confirm", json=retry_payload)
    assert retried.status_code == 200, retried.text
    assert next(chunk for chunk in retried.json()["projection"]["chunks"] if chunk["chunk_id"] == chunk_id)["state"] == "ready"
    untouched_states = [
        chunk["state"]
        for chunk in retried.json()["projection"]["chunks"]
        if chunk["chunk_id"] != chunk_id
    ]
    assert "failed" not in untouched_states
    assert retried.json()["provider_dispatch_count"] == 0
