from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest


EVENT_LOG_PATH = Path("examples/agentflow/control_events_active_pending.example.jsonl")
REGISTER_PATH = Path("examples/agentflow/control_register_active_pending.example.json")


def _events() -> list[dict]:
    from agentflow.algorithms.control_event_register import load_control_event_log

    return load_control_event_log(EVENT_LOG_PATH)


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
