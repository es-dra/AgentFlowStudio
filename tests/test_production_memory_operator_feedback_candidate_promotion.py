from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_feedback import build_production_memory_operator_feedback_event
from agentflow.memory.production_operator_feedback_candidate import build_operator_feedback_candidate_packet
from agentflow.memory.production_operator_feedback_candidate_promotion import (
    OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
    build_operator_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_operator_loop import build_production_memory_operator_loop_run
from narratocut.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _operator_feedback_candidate_packet(*, feedback_decision: str = "accepted") -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T08:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    event = build_production_memory_operator_feedback_event(
        result["manifest"],
        target_node_id="company_kb_feedback_candidate_packet",
        decision=feedback_decision,
        summary="Operator reviewed the candidate packet shape for the next loop.",
        reviewer_role="operator",
        reviewed_at="2026-06-02T08:10:00+08:00",
    )
    return build_operator_feedback_candidate_packet(event, generated_at="2026-06-02T08:20:00+08:00")


def _decision(packet: dict, decision: str = "promoted") -> dict:
    return build_operator_feedback_candidate_promotion_decision(
        packet,
        decision=decision,
        rationale="Traceable operator feedback selected for the next context overlay.",
        reviewer_role="operator",
        decided_at="2026-06-02T08:30:00+08:00",
    )


def test_operator_feedback_candidate_promotion_decision_is_explicit_and_no_write() -> None:
    packet = _operator_feedback_candidate_packet()

    decision = _decision(packet)

    assert decision["kind"] == OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND
    assert decision["decision"] == "promoted"
    assert decision["review_mode"] == "explicit_operator_decision"
    assert decision["template_only"] is False
    assert decision["source_packet_id"] == packet["packet_id"]
    assert decision["source_promotion_decision_template_id"] == packet["promotion_decision_template"]["decision_id"]
    assert decision["candidate_id"] == packet["memory_candidate"]["candidate_id"]
    assert decision["source_candidate_status"] == "candidate"
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


def test_rejected_operator_feedback_candidate_decision_blocks_reuse() -> None:
    packet = _operator_feedback_candidate_packet()

    decision = _decision(packet, "rejected")

    assert decision["decision_effect"] == "blocked_by_operator_rejection"
    assert decision["candidate_reuse_allowed"] is False
    assert decision["next_context_eligibility"] == "blocked_by_explicit_operator_decision"
    assert decision["provider_calls_started"] is False
    assert decision["writes_long_term_memory"] is False


def test_blocked_operator_feedback_candidate_cannot_be_promoted_or_merged() -> None:
    packet = _operator_feedback_candidate_packet(feedback_decision="rejected")
    assert packet["memory_candidate"]["status"] == "blocked"

    with pytest.raises(ValueError, match="blocked operator feedback candidate cannot be promoted"):
        _decision(packet, "promoted")
    with pytest.raises(ValueError, match="blocked operator feedback candidate cannot be promoted"):
        _decision(packet, "merged")


def test_operator_feedback_candidate_promotion_rejects_non_pending_template() -> None:
    packet = _operator_feedback_candidate_packet()
    packet["promotion_decision_template"]["decision"] = "promoted"

    with pytest.raises(ValueError, match="requires pending promotion template"):
        _decision(packet)


def test_operator_feedback_candidate_promotion_does_not_mutate_source_packet() -> None:
    packet = _operator_feedback_candidate_packet()
    before = deepcopy(packet)

    _decision(packet)

    assert packet == before


def test_operator_feedback_candidate_promotion_rejects_wrong_kind() -> None:
    packet = _operator_feedback_candidate_packet()
    packet["kind"] = "agentflow_wrong_kind"

    with pytest.raises(ValueError, match="operator feedback candidate promotion requires kind"):
        _decision(packet)


def test_cli_reviews_operator_feedback_candidate_promotion(tmp_path: Path) -> None:
    packet_path = write_json(tmp_path / "operator_feedback_candidate_packet.json", _operator_feedback_candidate_packet())
    output_dir = tmp_path / "decision"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-review-operator-feedback-candidate",
            str(packet_path),
            "--decision",
            "promoted",
            "--rationale",
            "Traceable operator feedback selected for the next context overlay.",
            "--decided-at",
            "2026-06-02T08:30:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator feedback candidate decision: promoted" in result.stdout
    assert "Candidate reuse: allowed" in result.stdout
    assert "Writes long-term memory: false" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    assert "Human acceptance: not claimed" in result.stdout
    decision = json.loads((output_dir / "operator_feedback_candidate_promotion_decision.json").read_text(encoding="utf-8"))
    assert decision["kind"] == "agentflow_production_memory_operator_feedback_candidate_promotion_decision"
    assert decision["decision"] == "promoted"
    assert decision["decision_effect"] == "eligible_for_next_context_overlay"
    assert decision["candidate_reuse_allowed"] is True
    assert decision["provider_calls_started"] is False
    assert decision["writes_long_term_memory"] is False
    assert decision["writes_company_kb"] is False
    assert decision["decision_is_durable_memory_write"] is False
    assert decision["decision_writes_company_kb"] is False
    assert decision["claim_boundaries"]["human_acceptance"] == "not_claimed"
    assert (output_dir / "operator_feedback_candidate_promotion_decision.md").exists()
