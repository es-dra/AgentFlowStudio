from __future__ import annotations

import json
from pathlib import Path

from agentflow.harness.json_io import write_json
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_submit_idempotency import (
    begin_submit_idempotency,
    complete_submit_idempotency,
    submit_idempotency_error_detail,
)


def test_active_provider_free_lease_returns_pending(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    first = begin_submit_idempotency(
        store,
        project_id="lease-active",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="active-lease-001",
        request_id="req-1",
    )

    assert first.state == "reserved"
    assert first.ledger["provider_calls_started"] is False
    assert first.ledger["attempt_number"] == 1
    assert first.ledger["attempt_status"] == "active"
    assert first.ledger["lease"]["status"] == "active"
    assert first.ledger["lease"]["expires_at"]

    second = begin_submit_idempotency(
        store,
        project_id="lease-active",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="active-lease-001",
        request_id="req-2",
    )

    assert second.state == "pending"
    detail = submit_idempotency_error_detail(second, request_id="req-2", client_request_id="active-lease-001")
    assert detail["error"] == "idempotency_request_in_progress"
    assert detail["provider_calls_started"] is False
    assert detail["details"]["attempt_number"] == 1
    assert detail["details"]["lease_status"] == "active"


def test_stale_provider_free_lease_is_reclaimed_to_dlq_and_allows_new_attempt(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    first = begin_submit_idempotency(
        store,
        project_id="lease-stale",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="stale-lease-001",
        request_id="req-1",
    )
    old_attempt_id = str(first.ledger["attempt_id"])
    _make_stale(first.ledger_dir / "ledger.json")

    recovered = begin_submit_idempotency(
        store,
        project_id="lease-stale",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="stale-lease-001",
        request_id="req-2",
    )

    assert recovered.state == "reserved"
    assert recovered.ledger["attempt_number"] == 2
    assert recovered.ledger["attempt_id"] != old_attempt_id
    assert recovered.ledger["provider_calls_started"] is False
    assert recovered.ledger["reclaimed_attempts"] == [
        {
            "attempt_id": old_attempt_id,
            "attempt_number": 1,
            "status": "failed",
            "reason": "stale_provider_free_lease",
            "dlq_ref": f"dlq/{old_attempt_id}.json",
        }
    ]

    dlq_records = list((recovered.ledger_dir / "dlq").glob("*.json"))
    assert len(dlq_records) == 1
    dlq = json.loads(dlq_records[0].read_text(encoding="utf-8"))
    assert dlq["status"] == "failed"
    assert dlq["failure_reason"] == "stale_provider_free_lease"
    assert dlq["attempt_id"] == old_attempt_id
    assert dlq["provider_calls_started"] is False
    assert dlq["provider_calls_count"] == 0
    assert dlq["model_calls_count"] == 0
    assert dlq["media_calls_count"] == 0
    assert dlq["contains_provider_raw"] is False
    assert dlq["contains_secret"] is False
    assert dlq["contains_signed_url"] is False
    assert dlq["contains_media_bytes"] is False
    assert dlq["contains_private_absolute_asset_path"] is False
    assert dlq["request_payload_retained"] is False


def test_stale_provider_free_reclaimer_is_idempotent_after_recovery(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    first = begin_submit_idempotency(
        store,
        project_id="lease-idempotent",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="stale-lease-002",
        request_id="req-1",
    )
    _make_stale(first.ledger_dir / "ledger.json")

    recovered = begin_submit_idempotency(
        store,
        project_id="lease-idempotent",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="stale-lease-002",
        request_id="req-2",
    )
    pending = begin_submit_idempotency(
        store,
        project_id="lease-idempotent",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="stale-lease-002",
        request_id="req-3",
    )

    assert recovered.state == "reserved"
    assert pending.state == "pending"
    assert len(list((recovered.ledger_dir / "dlq").glob("*.json"))) == 1
    assert pending.ledger["attempt_number"] == 2
    assert pending.ledger["reclaimed_attempts"] == recovered.ledger["reclaimed_attempts"]


def test_completed_replay_and_payload_conflict_are_unchanged(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    first = begin_submit_idempotency(
        store,
        project_id="lease-completed",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="completed-001",
        request_id="req-1",
    )
    response = {"job": {"job_id": "job_001", "status": "blocked"}, "provider_calls_started": False}
    complete_submit_idempotency(first, job_id="job_001", response=response, provider_calls_started=False)

    replay = begin_submit_idempotency(
        store,
        project_id="lease-completed",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="completed-001",
        request_id="req-2",
    )
    conflict = begin_submit_idempotency(
        store,
        project_id="lease-completed",
        action="keyframe_generation",
        request=_request("changed prompt"),
        client_request_id="completed-001",
        request_id="req-3",
    )

    assert replay.state == "replay"
    assert replay.response == response
    assert conflict.state == "conflict"
    detail = submit_idempotency_error_detail(conflict, request_id="req-3", client_request_id="completed-001")
    assert detail["error"] == "idempotency_conflict"
    assert detail["retryable"] is False
    assert detail["details"]["existing_job_id"] == "job_001"


def test_stale_provider_started_attempt_is_not_reclaimed_or_retried(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    first = begin_submit_idempotency(
        store,
        project_id="lease-provider-started",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="provider-started-001",
        request_id="req-1",
    )
    _make_stale(first.ledger_dir / "ledger.json", provider_calls_started=True)

    second = begin_submit_idempotency(
        store,
        project_id="lease-provider-started",
        action="keyframe_generation",
        request=_request("same prompt"),
        client_request_id="provider-started-001",
        request_id="req-2",
    )

    assert second.state == "pending"
    assert not (second.ledger_dir / "dlq").exists()
    detail = submit_idempotency_error_detail(second, request_id="req-2", client_request_id="provider-started-001")
    assert detail["provider_calls_started"] is True
    assert detail["details"]["provider_calls_started"] is True
    assert detail["details"]["attempt_number"] == 1


def _request(prompt_text: str) -> dict[str, object]:
    return {
        "node_id": "recovery_node",
        "prompt_text": prompt_text,
        "optimized_prompt": "Stable local prompt.",
        "provider_service_id": "image_relay",
        "candidate_count": 1,
        "generated_at": "2026-07-03T10:00:00+00:00",
    }


def _make_stale(path: Path, *, provider_calls_started: bool = False) -> None:
    ledger = json.loads(path.read_text(encoding="utf-8"))
    ledger["updated_at"] = "2020-01-01T00:00:00+00:00"
    ledger["provider_calls_started"] = provider_calls_started
    ledger["lease"] = {
        **ledger["lease"],
        "expires_at": "2020-01-01T00:15:00+00:00",
    }
    write_json(path, ledger)
