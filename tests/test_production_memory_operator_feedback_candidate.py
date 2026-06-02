from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_feedback import build_production_memory_operator_feedback_event
from agentflow.memory.production_operator_feedback_candidate import (
    OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND,
    build_operator_feedback_candidate_packet,
)
from agentflow.memory.production_operator_loop import build_production_memory_operator_loop_run
from agentflow_studio.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _operator_feedback_event(*, decision: str = "accepted") -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T08:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    return build_production_memory_operator_feedback_event(
        result["manifest"],
        target_node_id="company_kb_feedback_candidate_packet",
        decision=decision,
        summary="Operator reviewed the candidate packet shape for the next loop.",
        reviewer_role="operator",
        reviewed_at="2026-06-02T08:10:00+08:00",
    )


def test_operator_feedback_candidate_packet_drafts_candidate_and_pending_template() -> None:
    packet = build_operator_feedback_candidate_packet(
        _operator_feedback_event(),
        generated_at="2026-06-02T08:20:00+08:00",
    )

    assert packet["kind"] == OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND
    assert packet["candidate_generation_status"] == "candidate_only"
    assert packet["provider_calls_started"] is False
    assert packet["writes_long_term_memory"] is False
    assert packet["writes_company_kb"] is False
    assert packet["feedback_is_memory"] is False
    assert packet["candidate_is_promoted_memory"] is False
    assert packet["source_target_node_id"] == "company_kb_feedback_candidate_packet"
    assert packet["claim_boundaries"]["human_acceptance"] == "not_claimed"
    assert packet["memory_candidate"]["status"] == "candidate"
    assert packet["memory_candidate"]["candidate_is_promoted_memory"] is False
    assert packet["memory_candidate"]["source_feedback_ids"] == [packet["source_feedback_event_id"]]
    assert packet["promotion_decision_template"]["decision"] == "pending"
    assert packet["promotion_decision_template"]["template_only"] is True
    assert packet["promotion_decision_template"]["writes_long_term_memory"] is False
    assert packet["promotion_decision_template"]["writes_company_kb"] is False


def test_rejected_operator_feedback_stays_blocked_from_candidate_use() -> None:
    packet = build_operator_feedback_candidate_packet(
        _operator_feedback_event(decision="rejected"),
        generated_at="2026-06-02T08:20:00+08:00",
    )

    assert packet["memory_candidate"]["status"] == "blocked"
    assert packet["promotion_decision_template"]["decision"] == "pending"
    assert "not promoted memory" in packet["non_claims"]


def test_operator_feedback_candidate_does_not_mutate_source_event() -> None:
    event = _operator_feedback_event()
    before = deepcopy(event)

    build_operator_feedback_candidate_packet(event, generated_at="2026-06-02T08:20:00+08:00")

    assert event == before


def test_operator_feedback_candidate_rejects_wrong_kind() -> None:
    event = _operator_feedback_event()
    event["kind"] = "agentflow_wrong_kind"

    with pytest.raises(ValueError, match="operator feedback candidate requires kind"):
        build_operator_feedback_candidate_packet(event, generated_at="2026-06-02T08:20:00+08:00")


def test_operator_feedback_candidate_rejects_feedback_that_created_promotion_decision() -> None:
    event = _operator_feedback_event()
    event["creates_promotion_decision"] = True

    with pytest.raises(ValueError, match="original event to create no promotion decision"):
        build_operator_feedback_candidate_packet(event, generated_at="2026-06-02T08:20:00+08:00")


def test_cli_drafts_operator_feedback_candidate_packet(tmp_path: Path) -> None:
    event_path = write_json(tmp_path / "operator_feedback_event.json", _operator_feedback_event())
    output_dir = tmp_path / "operator_feedback_candidate"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-draft-operator-feedback-candidate",
            str(event_path),
            "--generated-at",
            "2026-06-02T08:20:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator feedback candidate: candidate_only" in result.stdout
    assert "Promotion decision: pending" in result.stdout
    assert "Human acceptance: not claimed" in result.stdout
    packet = json.loads((output_dir / "operator_feedback_candidate_packet.json").read_text(encoding="utf-8"))
    candidate = json.loads((output_dir / "memory_candidate.json").read_text(encoding="utf-8"))
    decision = json.loads((output_dir / "promotion_decision_template.json").read_text(encoding="utf-8"))
    assert packet["kind"] == OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND
    assert candidate["candidate_is_promoted_memory"] is False
    assert decision["decision"] == "pending"
