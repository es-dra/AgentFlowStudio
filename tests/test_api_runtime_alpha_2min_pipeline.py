from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from agentflow.harness.json_io import write_json
from apps.api.runtime_episode_alpha_2min import ALPHA_ACTION
from apps.api.runtime_episode_domain_store import EpisodeDomainAggregateStore
from apps.api.runtime_service import create_runtime_app


PROJECT_ID = "alpha-2min-pipeline"
STAMP = "2026-07-16T00:00:00+00:00"


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_ASR", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "false")
    return TestClient(create_runtime_app(runtime_root=tmp_path))


def _register(client: TestClient, email: str = "owner@example.com") -> dict[str, Any]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": email.split("@", 1)[0],
            "invite_code": "",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _headers(session: dict[str, Any], key: str = "alpha-2min-001") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {session['session_token']}",
        "Idempotency-Key": key,
    }


def _create_project(client: TestClient, headers: dict[str, str], project_id: str = PROJECT_ID) -> None:
    response = client.post(
        "/projects",
        headers=headers,
        json={
            "project_id": project_id,
            "project_type": "short_video_campaign",
            "goal": "Alpha 2-minute provider-free pipeline",
        },
    )
    assert response.status_code == 200, response.text
    assert "episode_bootstrap" not in response.json()


def _brief(
    title: str = "Signal Kitchen",
    *,
    brief_id: str = "alpha-brief-001",
) -> dict[str, Any]:
    return {
        "expected_aggregate_version": 0,
        "created_at": STAMP,
        "brief": {
            "brief_id": brief_id,
            "project_title": title,
            "logline": "A night-shift cook must choose whether to expose a false emergency signal.",
            "target_audience": "internal alpha reviewer",
            "tone": "tense but humane",
            "genre": "near-future workplace drama",
            "core_theme": "truth under operational pressure",
            "must_include": ["visible timer", "manual override"],
            "constraints": ["no external provider calls", "metadata-only placeholders"],
            "target_duration_seconds": 96,
        },
    }


def _post_alpha(
    client: TestClient,
    headers: dict[str, str],
    body: dict[str, Any],
    *,
    project_id: str = PROJECT_ID,
    crash_after: str | None = None,
):
    request_headers = dict(headers)
    if crash_after:
        request_headers["X-AFS-Crash-After"] = crash_after
    return client.post(
        f"/projects/{project_id}/episode-production-aggregate/alpha-2min",
        headers=request_headers,
        json=body,
    )


def test_alpha_2min_pipeline_executes_brief_to_export_provider_free(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client)
    headers = _headers(owner)
    _create_project(client, headers)

    response = _post_alpha(client, headers, _brief())
    assert response.status_code == 200, response.text
    packet = response.json()

    assert packet["schema_version"] == "afs.alpha_2min.pipeline_response.v0.1"
    assert packet["missing_link"] == "brief_to_provider_free_alpha_2min_episode_pipeline"
    assert packet["truth_chain"]["story_bible_ref"]["entity_id"] == "alpha-bible-001"
    assert packet["truth_chain"]["arc_ref"]["entity_id"] == "alpha-arc-001"
    assert packet["truth_chain"]["episode_ref"]["entity_id"] == "alpha-episode-001"
    assert packet["truth_chain"]["reference_set_ref"]["entity_id"] == "alpha-reference-set-001"
    assert len(packet["truth_chain"]["shot_refs"]) == 6
    assert packet["production_recipe"]["target_duration_seconds"] == 96
    assert packet["production_recipe"]["provider_policy"] == {
        "allow_remote_llm": False,
        "allow_remote_image": False,
        "allow_remote_video": False,
        "allow_remote_audio": False,
        "allow_external_download": False,
    }
    assert packet["candidate_inventory"]["total"] == 18
    assert packet["candidate_inventory"]["image"] == 6
    assert packet["candidate_inventory"]["video"] == 6
    assert packet["candidate_inventory"]["audio"] == 6
    assert packet["projections"]["creator_counts"]["reference_sets"] == 1
    assert packet["projections"]["workspace_truth"]["shot_count"] == 6
    assert packet["projections"]["workspace_truth"]["duration_seconds"] == 96
    assert packet["projections"]["workspace_truth"]["generation_dispatch_count"] == 18
    assert packet["projections"]["workspace_truth"]["playable_preview_available"] is False
    assert packet["review"] == {
        "status": "pending_fixture_review",
        "retry_enabled": True,
        "delivery_lifecycle_state": "candidate",
        "delivery_review_state": "needs_review",
    }
    assert packet["call_counters"] == {
        "provider_calls": 0,
        "model_calls": 0,
        "media_calls": 0,
        "external_downloads": 0,
    }
    assert packet["provider_dispatch_count"] == 0
    assert packet["production_control"]["provider_dispatch_count"] == 0
    assert packet["production_control"]["artifact_count"] == 18
    assert packet["export_manifest"]["compose"]["contains_media_bytes"] is False
    assert packet["export_manifest"]["compose"]["contains_private_path"] is False
    assert packet["export_manifest"]["compose"]["contains_signed_url"] is False
    assert packet["non_claims"]["human_acceptance"] is False
    assert packet["non_claims"]["generated_media_quality"] is False
    assert packet["non_claims"]["alpha_readiness"] is False

    aggregate = EpisodeDomainAggregateStore(tmp_path).load(
        org_id=owner["user"]["user_id"],
        project_id=PROJECT_ID,
    )
    assert len(aggregate.story_bibles) == 1
    assert len(aggregate.arcs) == 1
    assert len(aggregate.scenes) == 3
    assert len(aggregate.shots) == 6
    assert len(aggregate.reference_sets) == 1
    assert len(aggregate.asset_candidates) == 18
    assert len(aggregate.selections) == 18
    assert len(aggregate.deliveries) == 1
    assert {candidate.job_state for candidate in aggregate.asset_candidates} == {"succeeded"}
    assert all(candidate.control_provenance is not None for candidate in aggregate.asset_candidates)

    ledger = json.loads(
        (
            tmp_path
            / "projects"
            / PROJECT_ID
            / "production_control"
            / "ledger.json"
        ).read_text(encoding="utf-8")
    )
    assert ledger["provider_dispatch_count"] == 0
    event_types = [event["event_type"] for event in ledger["events"]]
    assert event_types.count("ArtifactWrittenBack") == 18
    assert event_types.count("RunCompleted") == 18

    replay = _post_alpha(client, headers, _brief())
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["job"] == packet["job"]

    conflict = _post_alpha(client, headers, _brief(title="Changed Title"))
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error"] == "idempotency_conflict"

    new_key_changed = _post_alpha(
        client,
        _headers(owner, key="alpha-2min-new-key-changed-brief"),
        _brief(brief_id="alpha-brief-CHANGED"),
    )
    assert new_key_changed.status_code == 409
    assert new_key_changed.json()["detail"]["error"] == "alpha_2min_brief_conflict"
    assert "production_recipe" not in new_key_changed.json()

    after_changed = EpisodeDomainAggregateStore(tmp_path).load(
        org_id=owner["user"]["user_id"],
        project_id=PROJECT_ID,
    )
    assert after_changed.aggregate_version == aggregate.aggregate_version
    assert [item.entity_id for item in after_changed.deliveries] == [
        item.entity_id for item in aggregate.deliveries
    ]
    ledger_after_changed = json.loads(
        (
            tmp_path
            / "projects"
            / PROJECT_ID
            / "production_control"
            / "ledger.json"
        ).read_text(encoding="utf-8")
    )
    assert len(ledger_after_changed["events"]) == len(ledger["events"])
    assert ledger_after_changed["provider_dispatch_count"] == 0


def test_alpha_2min_pipeline_recovers_provider_free_stale_lease_without_duplicate_writeback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client)
    headers = _headers(owner, key="alpha-2min-crash-001")
    _create_project(client, headers)

    crashed = _post_alpha(client, headers, _brief(), crash_after="candidates")
    assert crashed.status_code == 500
    assert crashed.json()["detail"]["error"] == "alpha_2min_injected_crash"
    _make_alpha_lease_stale(tmp_path)

    restarted = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = _post_alpha(restarted, headers, _brief())
    assert recovered.status_code == 200, recovered.text
    packet = recovered.json()
    assert packet["recovery"]["attempt_number"] == 2
    assert packet["recovery"]["reclaimed_attempts"][0]["reason"] == "stale_provider_free_lease"
    assert packet["candidate_inventory"]["total"] == 18
    assert packet["production_control"]["artifact_count"] == 18
    assert packet["production_control"]["provider_dispatch_count"] == 0
    assert packet["call_counters"]["provider_calls"] == 0
    assert packet["call_counters"]["model_calls"] == 0
    assert packet["call_counters"]["media_calls"] == 0

    ledger = json.loads(
        (
            tmp_path
            / "projects"
            / PROJECT_ID
            / "production_control"
            / "ledger.json"
        ).read_text(encoding="utf-8")
    )
    event_types = [event["event_type"] for event in ledger["events"]]
    assert event_types.count("ArtifactWrittenBack") == 18
    assert event_types.count("RunCompleted") == 18
    assert ledger["provider_dispatch_count"] == 0

    dlq_records = list(
        (tmp_path / "submit_idempotency" / PROJECT_ID / ALPHA_ACTION).glob("*/dlq/*.json")
    )
    assert len(dlq_records) == 1
    dlq = json.loads(dlq_records[0].read_text(encoding="utf-8"))
    assert dlq["provider_calls_started"] is False
    assert dlq["provider_calls_count"] == 0
    assert dlq["model_calls_count"] == 0
    assert dlq["media_calls_count"] == 0
    assert dlq["contains_provider_raw"] is False
    assert dlq["contains_media_bytes"] is False
    assert dlq["contains_private_absolute_asset_path"] is False


def _make_alpha_lease_stale(tmp_path: Path) -> None:
    ledgers = list((tmp_path / "submit_idempotency" / PROJECT_ID / ALPHA_ACTION).glob("*/ledger.json"))
    assert len(ledgers) == 1
    ledger = json.loads(ledgers[0].read_text(encoding="utf-8"))
    ledger["updated_at"] = "2020-01-01T00:00:00+00:00"
    ledger["provider_calls_started"] = False
    ledger["lease"] = {
        **ledger["lease"],
        "expires_at": "2020-01-01T00:15:00+00:00",
    }
    write_json(ledgers[0], ledger)
