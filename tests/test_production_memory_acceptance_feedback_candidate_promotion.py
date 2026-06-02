from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import build_acceptance_feedback_candidate_packet
from agentflow.memory.production_action_result_acceptance_feedback import (
    build_production_memory_action_result_acceptance_feedback_event,
)
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
    build_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from narratocut.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _acceptance_feedback_candidate_packet(tmp_path: Path, *, feedback_decision: str = "accepted") -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T02:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path / "operator_loop",
        write_run_package=True,
        write_run_package_check=True,
    )
    check_path = tmp_path / "operator_loop" / "operator_run_package_check" / "operator_run_package_check.json"
    check = json.loads(check_path.read_text(encoding="utf-8"))
    if feedback_decision != "accepted":
        check["check_status"] = "failed"
        check["ready_for_handoff"] = False
    event = build_production_memory_acceptance_feedback_event(
        check,
        decision=feedback_decision,
        summary="Human operator reviewed the package for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T02:05:00+08:00",
    )
    return build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T02:10:00+08:00")


def _decision(packet: dict, decision: str = "promoted") -> dict:
    return build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision=decision,
        rationale="Traceable acceptance feedback selected for the next context overlay.",
        reviewer_role="operator",
        decided_at="2026-06-03T02:15:00+08:00",
    )


def test_acceptance_feedback_candidate_promotion_decision_is_explicit_and_no_write(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)

    decision = _decision(packet)

    assert decision["kind"] == ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND
    assert decision["decision"] == "promoted"
    assert decision["review_mode"] == "explicit_operator_decision"
    assert decision["template_only"] is False
    assert decision["source_packet_id"] == packet["packet_id"]
    assert decision["source_acceptance_feedback_event_id"] == packet["source_acceptance_feedback_event_id"]
    assert decision["source_promotion_decision_template_id"] == packet["promotion_decision_template"]["decision_id"]
    assert decision["candidate_id"] == packet["memory_candidate"]["candidate_id"]
    assert decision["source_candidate_status"] == "candidate"
    assert decision["source_acceptance_decision"] == "accepted"
    assert decision["source_human_acceptance_recorded"] is True
    assert decision["decision_effect"] == "eligible_for_next_context_overlay"
    assert decision["candidate_reuse_allowed"] is True
    assert decision["next_context_eligibility"] == "eligible_by_explicit_operator_decision"
    assert decision["provider_mode"] == "no-provider"
    assert decision["provider_calls_started"] is False
    assert decision["writes_long_term_memory"] is False
    assert decision["writes_company_kb"] is False
    assert decision["decision_is_durable_memory_write"] is False
    assert decision["decision_writes_company_kb"] is False
    assert decision["candidate_is_durable_memory"] is False
    assert decision["claim_boundaries"]["human_acceptance"] == "accepted"
    assert decision["claim_boundaries"]["business_validation"] == "not_validated"


def test_action_result_acceptance_feedback_candidate_promotion_preserves_source_artifact(
    tmp_path: Path,
) -> None:
    packet = _action_result_acceptance_feedback_candidate_packet(tmp_path)

    decision = _decision(packet)

    assert decision["source_artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert decision["source_artifact_status"] == "action_completed"
    assert decision["source_artifact_path"] == "next_operator_action_result/next_operator_action_result.json"
    assert decision["source_ready_for_acceptance"] is True
    assert decision["source_target_ref"].startswith("next-operator-action-result:")
    assert decision["source_target_artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert decision["claim_boundaries"]["human_acceptance"] == "accepted"
    assert decision["provider_calls_started"] is False
    assert decision["writes_company_kb"] is False


def test_action_result_promotion_allows_local_run_source_path(tmp_path: Path) -> None:
    packet = _action_result_acceptance_feedback_candidate_packet(tmp_path)
    packet["source_artifact_path"] = (
        "data/processed/runs/production_memory_loop/operator_loop/next_operator_action_result/"
        "next_operator_action_result.json"
    )

    decision = _decision(packet)

    assert decision["source_artifact_path"].startswith("data/processed/runs/")
    assert decision["provider_calls_started"] is False
    assert decision["writes_company_kb"] is False


def test_rejected_acceptance_feedback_candidate_decision_blocks_reuse(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)

    decision = _decision(packet, "rejected")

    assert decision["decision_effect"] == "blocked_by_operator_rejection"
    assert decision["candidate_reuse_allowed"] is False
    assert decision["next_context_eligibility"] == "blocked_by_explicit_operator_decision"
    assert decision["provider_calls_started"] is False
    assert decision["writes_long_term_memory"] is False


def test_blocked_acceptance_feedback_candidate_cannot_be_promoted_or_merged(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path, feedback_decision="needs_revision")
    assert packet["memory_candidate"]["status"] == "blocked"

    with pytest.raises(ValueError, match="blocked acceptance feedback candidate cannot be promoted"):
        _decision(packet, "promoted")
    with pytest.raises(ValueError, match="blocked acceptance feedback candidate cannot be promoted"):
        _decision(packet, "merged")


def test_acceptance_feedback_candidate_promotion_rejects_non_pending_template(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)
    packet["promotion_decision_template"]["decision"] = "promoted"

    with pytest.raises(ValueError, match="requires pending promotion template"):
        _decision(packet)


def test_acceptance_feedback_candidate_promotion_does_not_mutate_source_packet(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)
    before = deepcopy(packet)

    _decision(packet)

    assert packet == before


def test_acceptance_feedback_candidate_promotion_rejects_wrong_kind(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)
    packet["kind"] = "agentflow_wrong_kind"

    with pytest.raises(ValueError, match="acceptance feedback candidate promotion requires kind"):
        _decision(packet)


def test_cli_reviews_acceptance_feedback_candidate_promotion(tmp_path: Path) -> None:
    packet_path = write_json(tmp_path / "acceptance_feedback_candidate_packet.json", _acceptance_feedback_candidate_packet(tmp_path))
    output_dir = tmp_path / "decision"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-review-acceptance-feedback-candidate",
            str(packet_path),
            "--decision",
            "promoted",
            "--rationale",
            "Traceable acceptance feedback selected for the next context overlay.",
            "--decided-at",
            "2026-06-03T02:15:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory acceptance feedback candidate decision: promoted" in result.stdout
    assert "Candidate reuse: allowed" in result.stdout
    assert "Source human acceptance: accepted" in result.stdout
    assert "Writes long-term memory: false" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    decision = json.loads((output_dir / "acceptance_feedback_candidate_promotion_decision.json").read_text(encoding="utf-8"))
    assert decision["kind"] == ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND
    assert decision["decision"] == "promoted"
    assert decision["decision_effect"] == "eligible_for_next_context_overlay"
    assert decision["candidate_reuse_allowed"] is True
    assert decision["provider_calls_started"] is False
    assert decision["writes_long_term_memory"] is False
    assert decision["writes_company_kb"] is False
    assert decision["decision_is_durable_memory_write"] is False
    assert decision["decision_writes_company_kb"] is False
    assert decision["claim_boundaries"]["human_acceptance"] == "accepted"
    assert decision["claim_boundaries"]["business_validation"] == "not_validated"
    assert (output_dir / "acceptance_feedback_candidate_promotion_decision.md").exists()


def _action_result_acceptance_feedback_candidate_packet(tmp_path: Path) -> dict:
    action_result = _next_operator_action_result(tmp_path)
    event = build_production_memory_action_result_acceptance_feedback_event(
        action_result,
        decision="accepted",
        summary="Human operator accepted the completed action result for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T12:05:00+08:00",
        action_result_path="next_operator_action_result/next_operator_action_result.json",
    )
    return build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T12:10:00+08:00")


def _next_operator_action_result(tmp_path: Path) -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T12:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path / "operator_loop_with_action_result",
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
    action_result_path = (
        tmp_path
        / "operator_loop_with_action_result"
        / "next_operator_action_result"
        / "next_operator_action_result.json"
    )
    return json.loads(action_result_path.read_text(encoding="utf-8"))
