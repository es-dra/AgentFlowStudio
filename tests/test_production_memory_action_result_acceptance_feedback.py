from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_acceptance_feedback import ACCEPTANCE_FEEDBACK_EVENT_KIND
from agentflow.memory.production_action_result_acceptance_feedback import (
    build_production_memory_action_result_acceptance_feedback_event,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_acceptance_feedback_records_human_decision_from_action_result(tmp_path: Path) -> None:
    action_result = _next_operator_action_result(tmp_path)

    event = build_production_memory_action_result_acceptance_feedback_event(
        action_result,
        decision="accepted",
        summary="Human operator accepted the completed action result for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T12:05:00+08:00",
    )

    assert event["kind"] == ACCEPTANCE_FEEDBACK_EVENT_KIND
    assert event["feedback_scope"] == "next_operator_action_result"
    assert event["acceptance_scope"] == "next_operator_action_result"
    assert event["acceptance_decision"] == "accepted"
    assert event["status"] == "human_recorded"
    assert event["source_artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert event["source_artifact_status"] == "action_completed"
    assert event["source_action_result_status"] == "action_completed"
    assert event["source_action_decision"] == "completed"
    assert event["source_result_ref_count"] == 1
    assert event["source_ready_for_acceptance"] is True
    assert event["human_acceptance_recorded"] is True
    assert event["claim_boundaries"]["human_acceptance"] == "accepted"
    assert event["claim_boundaries"]["business_validation"] == "not_validated"
    assert event["feedback_is_memory"] is False
    assert event["creates_memory_candidate"] is False
    assert event["creates_promotion_decision"] is False
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
    assert event["provider_calls_started"] is False


def test_accepted_action_result_feedback_requires_completed_result(tmp_path: Path) -> None:
    action_result = _next_operator_action_result(tmp_path)
    action_result["result_status"] = "action_blocked"
    action_result["action_decision"] = "blocked"
    action_result["result_refs"] = []

    with pytest.raises(ValueError, match="accepted action result feedback requires completed action result"):
        build_production_memory_action_result_acceptance_feedback_event(
            action_result,
            decision="accepted",
            summary="Human operator accepted the action result.",
            reviewer_role="operator",
            reviewed_at="2026-06-03T12:05:00+08:00",
        )

    event = build_production_memory_action_result_acceptance_feedback_event(
        action_result,
        decision="needs_revision",
        summary="Human operator needs a revised action result before reuse.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T12:06:00+08:00",
    )
    assert event["acceptance_decision"] == "needs_revision"
    assert event["source_ready_for_acceptance"] is False


def test_cli_records_action_result_acceptance_feedback(tmp_path: Path) -> None:
    action_result_path = _next_operator_action_result_path(tmp_path / "operator_loop")
    output_dir = tmp_path / "action_result_acceptance"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-record-action-result-acceptance-feedback",
            str(action_result_path),
            "--decision",
            "accepted",
            "--summary",
            "Human operator accepted the completed action result for the next local iteration.",
            "--reviewed-at",
            "2026-06-03T12:05:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory action-result acceptance feedback: accepted" in result.stdout
    assert "Source action result: action_completed" in result.stdout
    assert "Business validation: not validated" in result.stdout
    event = json.loads((output_dir / "acceptance_feedback_event.json").read_text(encoding="utf-8"))
    assert event["kind"] == ACCEPTANCE_FEEDBACK_EVENT_KIND
    assert event["feedback_scope"] == "next_operator_action_result"
    assert event["writes_company_kb"] is False


def _next_operator_action_result(tmp_path: Path) -> dict:
    return json.loads(_next_operator_action_result_path(tmp_path).read_text(encoding="utf-8"))


def _next_operator_action_result_path(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T12:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path,
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
        write_next_operator_start_event=True,
        next_operator_start_event_decision="started",
        next_operator_start_event_summary="Next operator started from the checked no-provider package.",
        write_next_operator_action_result=True,
        next_operator_action_result_decision="completed",
        next_operator_action_result_summary="Next operator completed the recorded no-provider action.",
        next_operator_action_result_refs=["next_pass_result/next_pass_result.json"],
    )
    return tmp_path / "next_operator_action_result" / "next_operator_action_result.json"
