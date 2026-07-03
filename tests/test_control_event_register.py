from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest


EVENT_LOG_PATH = Path("examples/agentflow/control_events_active_pending.example.jsonl")
WORKER_FINAL_EVENT_LOG_PATH = Path("examples/agentflow/control_events_worker_final_ingest.example.jsonl")
REGISTER_PATH = Path("examples/agentflow/control_register_active_pending.example.json")


def _events() -> list[dict]:
    from agentflow.algorithms.control_event_register import load_control_event_log

    return load_control_event_log(EVENT_LOG_PATH)


def _worker_final_events() -> list[dict]:
    from agentflow.algorithms.control_event_register import load_control_event_log

    return load_control_event_log(WORKER_FINAL_EVENT_LOG_PATH)


def test_control_event_register_algorithm_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import control_event_register

    assert "control_event_register" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert control_event_register.ALGORITHM_ID == "afs.control_event_register.v0.1"
    assert control_event_register.INPUT_CONTRACT
    assert control_event_register.OUTPUT_CONTRACT
    assert control_event_register.EVIDENCE_BOUNDARY


def test_active_pending_event_log_reconstructs_checked_register_fixture() -> None:
    from agentflow.algorithms.control_event_register import materialize_control_register, validate_active_pending_register

    register = materialize_control_register(_events())
    expected = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))

    assert register == expected
    validate_active_pending_register(register)
    assert register["active_pending_lane_ids"] == [
        "EVAL-P1-AFS-CONTROL-EVENT-LOG-REGISTER-ADAPTER",
        "IMP-P1-AFS-CONTROL-EVENT-LOG-REGISTER-ADAPTER",
    ]
    implementation_lane = next(
        lane for lane in register["lanes"] if lane["lane_id"] == "IMP-P1-AFS-CONTROL-EVENT-LOG-REGISTER-ADAPTER"
    )
    assert implementation_lane["implementation_artifact_handles"][0]["durability"] == {
        "is_durable": True,
        "storage_medium": "git_local_branch",
        "durability_state": "branch_created_pending_local_commit",
        "ref": "codex/control-event-log-register-adapter-20260703",
    }
    assert implementation_lane["claim_states"]["artifact_handle_durability"]["state"] == "claimed"
    assert implementation_lane["non_claims"]["provider_smoke"] is False
    assert implementation_lane["ack"] == {
        "ack_required": True,
        "ack_state": "no_ack",
        "ack_delivery_confirmed": False,
        "no_ack": True,
    }
    assert implementation_lane["archive_policy"]["archive_execution_allowed"] is False
    assert set(implementation_lane["fixed_role_surfaces"]) == {
        "dispatcher",
        "cto_disposition",
        "implementation_worker",
    }
    assert {source["source_class"] for source in implementation_lane["evidence_sources"]} == {
        "dispatcher_instruction",
        "local_artifact",
    }


def test_append_only_event_file_round_trips_jsonl(tmp_path: Path) -> None:
    from agentflow.algorithms.control_event_register import append_control_event, load_control_event_log

    target = tmp_path / "control_events.jsonl"
    events = _events()
    for event in events:
        append_control_event(target, event)

    assert load_control_event_log(target) == events
    assert len(target.read_text(encoding="utf-8").splitlines()) == len(events)


def test_active_implementation_lane_requires_durable_implementation_artifact() -> None:
    from agentflow.algorithms.control_event_register import materialize_control_register, validate_control_event

    events = [event for event in _events() if event["event_id"] != "evt-control-register-005"]
    with pytest.raises(ValueError, match="implementation artifact handle missing"):
        materialize_control_register(events)

    event_with_empty_uri = copy.deepcopy(_events()[4])
    event_with_empty_uri["payload"]["artifact_handle"]["uri"] = ""
    with pytest.raises(ValueError, match="missing required field: uri"):
        validate_control_event(event_with_empty_uri)

    event_with_empty_ref = copy.deepcopy(_events()[4])
    event_with_empty_ref["payload"]["artifact_handle"]["durability"]["ref"] = ""
    with pytest.raises(ValueError, match="missing required field: ref"):
        validate_control_event(event_with_empty_ref)


def test_claim_state_and_non_claim_events_stay_separate() -> None:
    from agentflow.algorithms.control_event_register import validate_control_event

    claim_event = copy.deepcopy(_events()[5])
    claim_event["payload"]["non_claims"] = {"provider_smoke": False}
    with pytest.raises(ValueError, match="non_claims must use non_claim_recorded"):
        validate_control_event(claim_event)

    non_claim_event = copy.deepcopy(_events()[6])
    non_claim_event["payload"]["non_claims"]["provider_smoke"] = True
    with pytest.raises(ValueError, match="explicit false boundaries"):
        validate_control_event(non_claim_event)


def test_archive_execution_requires_policy_evaluation_before_archive_and_ack_confirmation() -> None:
    from agentflow.algorithms.control_event_register import materialize_control_register

    archive_execute = copy.deepcopy(_events()[8])
    archive_execute["event_id"] = "evt-control-register-archive-exec-too-early"
    archive_execute["event_type"] = "archive_executed"
    archive_execute["payload"] = {"archive_execution_confirmed": True}

    with pytest.raises(ValueError, match="prior allowed archive policy evaluation"):
        materialize_control_register(_events()[:8] + [archive_execute])

    events = copy.deepcopy(_events())
    policy = events[8]["payload"]["archive_policy"]
    policy["archive_execution_allowed"] = True
    policy["evaluation_state"] = "allowed"

    with pytest.raises(ValueError, match="before ack delivery confirmation"):
        materialize_control_register(events)


def test_invalid_evidence_source_classification_is_rejected() -> None:
    from agentflow.algorithms.control_event_register import validate_control_event

    event = copy.deepcopy(_events()[0])
    event["evidence_source"]["source_class"] = "unknown_review_surface"

    with pytest.raises(ValueError, match="unsupported evidence source classification"):
        validate_control_event(event)


def test_control_scheduler_linter_accepts_explicitly_reasoned_state() -> None:
    from agentflow.algorithms.control_event_register import lint_control_scheduler_state

    state = {
        "scheduler_policy": {
            "fan_in_mode": "join_all",
            "join_all_reason": "both bounded lanes must return before evaluator handoff",
        },
        "processed_bottom_up_feedback_ids": ["BU-DONE-001"],
        "post_closeout_next_action": {
            "monitor": {
                "mechanism": "codex_thread_monitor",
                "ref": "monitor:control-scheduler-eval",
            }
        },
        "lanes": [
            {
                "lane_id": "IMP-P1-CONTROL-A",
                "state": "active",
                "stale_after": "2026-07-03T15:00:00Z",
            },
            {
                "lane_id": "IMP-P1-CONTROL-B",
                "state": "active",
                "stale_after": "2026-07-03T15:00:00Z",
            },
            {
                "lane_id": "IMP-P1-CONTROL-DONE",
                "state": "completed",
                "bottom_up_feedback_id": "BU-DONE-001",
            },
        ],
    }

    assert lint_control_scheduler_state(state, now="2026-07-03T14:00:00Z") == []


def test_control_scheduler_linter_reports_minimal_redispatch_rules() -> None:
    from agentflow.algorithms.control_event_register import (
        COMPLETED_BU_NOT_PROCESSED,
        JOIN_ALL_WITHOUT_REASON,
        LANE_PAST_STALE_AFTER_WITHOUT_RECOVERY_OUTCOME,
        POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR,
        SINGLE_ACTIVE_LANE_WITHOUT_DEPENDENCY_REASON,
        lint_control_scheduler_state,
    )

    state = {
        "scheduler_policy": {"fan_in_mode": "join_all"},
        "lanes": [
            {
                "lane_id": "IMP-P1-CONTROL-A",
                "state": "active",
                "stale_after": "2026-07-03T13:00:00Z",
                "post_closeout_next_action": "check with evaluator later",
            },
            {
                "lane_id": "IMP-P1-CONTROL-DONE",
                "state": "completed",
                "bottom_up_feedback_id": "BU-DONE-002",
            },
        ],
    }

    findings = lint_control_scheduler_state(state, now="2026-07-03T14:00:00Z")

    assert {finding["code"] for finding in findings} == {
        COMPLETED_BU_NOT_PROCESSED,
        JOIN_ALL_WITHOUT_REASON,
        SINGLE_ACTIVE_LANE_WITHOUT_DEPENDENCY_REASON,
        LANE_PAST_STALE_AFTER_WITHOUT_RECOVERY_OUTCOME,
        POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR,
    }
    assert all(finding["severity"] == "error" for finding in findings)

    placeholder_only = {"post_closeout_next_action": {"monitor_ref": "monitor:placeholder"}}
    assert [finding["code"] for finding in lint_control_scheduler_state(placeholder_only)] == [
        POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR
    ]

    pseudo_delegation_response = {
        "post_closeout_next_action": {
            "mechanism": "current_codex_delegation_response",
            "monitor_ref": "codex_thread:019f25c8-37c9-7e30-8c57-279e40a3a1fc",
        }
    }
    assert [finding["code"] for finding in lint_control_scheduler_state(pseudo_delegation_response)] == [
        POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR
    ]


def test_control_scheduler_linter_is_read_only() -> None:
    from agentflow.algorithms.control_event_register import lint_control_scheduler_state

    state = {
        "scheduler_policy": {
            "fan_in_mode": "single_lane",
            "dependency_reason": "dependent evaluator has not accepted the implementation BU",
        },
        "lanes": [
            {
                "lane_id": "IMP-P1-CONTROL-A",
                "state": "active",
                "dependency_reason": "depends on evaluator lane creation",
                "stale_after": "2026-07-03T13:00:00Z",
                "recovery_outcome": "redispatched with explicit evaluator wakeup",
            }
        ],
        "post_closeout_next_action": {
            "mechanism": "codex_thread_wakeup",
            "ref": "wakeup:control-scheduler-eval",
        },
    }
    before = copy.deepcopy(state)

    lint_control_scheduler_state(state, now="2026-07-03T14:00:00Z")

    assert state == before


def test_worker_final_ingest_fixture_materializes_recovery_sources_and_no_ack_archive_block() -> None:
    from agentflow.algorithms.control_event_register import (
        WORKER_FINAL_INGEST_CONTRACT,
        WORKER_FINAL_RECOVERY_SOURCES,
        materialize_control_register,
    )

    register = materialize_control_register(_worker_final_events())

    assert register["materialized_from_event_count"] == 2
    assert register["active_pending_lane_ids"] == ["SPEC-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH"]
    lane = register["lanes"][0]
    assert lane["lane_kind"] == "worker_final_ingest"
    assert lane["route_basis"] == "readback_accepted_reaffirm_parallel_architecture_redispatch"
    assert {source["source_class"] for source in lane["evidence_sources"]} == {
        "dispatcher_instruction",
        "repo_fixture",
    }
    ingest = lane["worker_final_ingests"][0]
    assert ingest["ingest_contract"] == WORKER_FINAL_INGEST_CONTRACT
    assert (
        ingest["top_down_dispatch_id"]
        == "TD-AFS-V02-SPEC-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH-20260703-001"
    )
    assert (
        ingest["bottom_up_feedback_id"]
        == "BU-AFS-V02-SPEC-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH-20260703-001"
    )
    assert ingest["close_state"] == "control_event_bus_worker_final_ingest_redispatch_completed"
    assert set(lane["worker_final_recovery_sources"]) == WORKER_FINAL_RECOVERY_SOURCES
    assert lane["ack"] == {
        "ack_required": True,
        "ack_state": "no_ack",
        "ack_delivery_confirmed": False,
        "no_ack": True,
    }
    assert lane["archive_policy"]["policy"] == "agent_created_archive_when_useless"
    assert lane["archive_policy"]["archive_after_ack_delivery_confirmed"] is True
    assert lane["archive_policy"]["archive_execution_allowed"] is False
    assert lane["non_claims"]["full_historical_replay"] is False


def test_worker_final_ingest_exact_duplicate_is_idempotently_deduped() -> None:
    from agentflow.algorithms.control_event_register import materialize_control_register

    events = _worker_final_events()
    register = materialize_control_register(events + [copy.deepcopy(events[1])])

    lane = register["lanes"][0]
    assert register["materialized_from_event_count"] == 2
    assert lane["event_ids"] == ["evt-worker-final-ingest-redispatch-lane-001", "evt-worker-final-ingest-redispatch-001"]
    assert len(lane["worker_final_ingests"]) == 1


def test_worker_final_ingest_rejects_duplicate_td_bu_with_different_event_id() -> None:
    from agentflow.algorithms.control_event_register import materialize_control_register

    events = _worker_final_events()
    conflicting_event = copy.deepcopy(events[1])
    conflicting_event["event_id"] = "evt-worker-final-ingest-conflict"
    worker_final = conflicting_event["payload"]["worker_final_ingest"]
    worker_final["canonical_event_id"] = "evt-worker-final-ingest-conflict"
    worker_final["idempotency"]["dedupe_keys"]["event_id"] = "evt-worker-final-ingest-conflict"

    with pytest.raises(ValueError, match="duplicate worker-final TD/BU ingest"):
        materialize_control_register(events + [conflicting_event])


def test_worker_final_ingest_requires_known_recovery_sources() -> None:
    from agentflow.algorithms.control_event_register import validate_control_event

    event = copy.deepcopy(_worker_final_events()[1])
    event["payload"]["worker_final_ingest"]["recovery_sources"][0]["source_type"] = "unknown_source"

    with pytest.raises(ValueError, match="unsupported worker-final recovery source"):
        validate_control_event(event)


def test_worker_final_ingest_materialization_fails_without_payload_contract() -> None:
    from agentflow.algorithms.control_event_register import materialize_control_register

    event = copy.deepcopy(_worker_final_events()[1])
    event["payload"] = {}

    with pytest.raises(ValueError, match="missing required object: worker_final_ingest"):
        materialize_control_register([_worker_final_events()[0], event])


def test_worker_final_ingest_blocks_archive_allowed_before_ack_confirmation() -> None:
    from agentflow.algorithms.control_event_register import validate_control_event

    event = copy.deepcopy(_worker_final_events()[1])
    archive_policy = event["payload"]["worker_final_ingest"]["archive_policy"]
    archive_policy["archive_execution_allowed"] = True
    archive_policy["evaluation_state"] = "allowed"

    with pytest.raises(ValueError, match="archive cannot be allowed before ack delivery confirmation"):
        validate_control_event(event)
