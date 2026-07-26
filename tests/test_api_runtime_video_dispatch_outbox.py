from __future__ import annotations

import json

import pytest

from apps.api.runtime_video_dispatch_outbox import (
    load_dispatch_outbox,
    mark_network_may_have_started,
    mark_reconcile_required,
    prepare_dispatch_outbox,
    record_provider_task,
    recover_provider_task,
)


def test_dispatch_outbox_distinguishes_never_started_from_may_have_dispatched(tmp_path) -> None:
    prepared = prepare_dispatch_outbox(
        tmp_path,
        project_id="project-a",
        job_id="job-a",
        manifest_id="manifest-a",
        manifest_hash="a" * 64,
        item_id="item-a",
    )
    assert prepared["network_disposition"] == "never_started"
    assert prepared["provider_calls_started"] is False
    assert prepared["provider_task"] is None
    assert prepared["lease"]["status"] == "prepared"
    assert prepared["lease"]["ttl_seconds"] == 900

    started = mark_network_may_have_started(tmp_path)
    assert started["network_disposition"] == "may_have_dispatched"
    assert started["reconcile_required"] is True
    assert started["lease"]["status"] == "network_claimed"
    with pytest.raises(ValueError, match="reconciliation"):
        recover_provider_task(tmp_path)

    ambiguous = mark_reconcile_required(tmp_path, "submit_connection_lost")
    assert ambiguous["state"] == "reconcile_required"
    assert ambiguous["network_disposition"] == "may_have_dispatched"
    assert ambiguous["lease"]["status"] == "reconcile_required"
    with pytest.raises(ValueError, match="transition"):
        mark_network_may_have_started(tmp_path)


def test_dispatch_outbox_persists_private_task_before_recovery(tmp_path) -> None:
    prepare_dispatch_outbox(
        tmp_path,
        project_id="project-b",
        job_id="job-b",
        manifest_id="manifest-b",
        manifest_hash="b" * 64,
        item_id="item-b",
    )
    mark_network_may_have_started(tmp_path)
    recorded = record_provider_task(
        tmp_path,
        {
            "service_id": "seedance_i2v",
            "capability": "video",
            "task": {
                "status": "submitted",
                "task_id": "provider-task-private",
                "query_url_template": (
                    "https://relay.test/volc/v1/contents/generations/tasks/{id}"
                ),
            },
        },
    )
    assert recorded["network_disposition"] == "dispatched_with_task_identity"
    assert recorded["lease"]["status"] == "task_recorded"
    assert recorded["provider_task_fingerprint"]
    assert recover_provider_task(tmp_path)["task"]["task_id"] == "provider-task-private"
    serialized_public_fields = json.dumps(
        {
            "network_disposition": recorded["network_disposition"],
            "provider_task_fingerprint": recorded["provider_task_fingerprint"],
        }
    )
    assert "provider-task-private" not in serialized_public_fields
    assert load_dispatch_outbox(tmp_path)["provider_task"]["task"]["task_id"] == "provider-task-private"
