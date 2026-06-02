from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import (
    ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND,
    build_acceptance_feedback_candidate_packet,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from narratocut.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _acceptance_feedback_event(tmp_path: Path, *, decision: str = "accepted") -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T01:00:00+08:00",
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
    if decision != "accepted":
        check["check_status"] = "failed"
        check["ready_for_handoff"] = False
    return build_production_memory_acceptance_feedback_event(
        check,
        decision=decision,
        summary="Human operator reviewed the package for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T01:05:00+08:00",
    )


def test_acceptance_feedback_candidate_packet_drafts_candidate_and_pending_template(tmp_path: Path) -> None:
    packet = build_acceptance_feedback_candidate_packet(
        _acceptance_feedback_event(tmp_path),
        generated_at="2026-06-03T01:10:00+08:00",
    )

    assert packet["kind"] == ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND
    assert packet["candidate_generation_status"] == "candidate_only"
    assert packet["source_acceptance_decision"] == "accepted"
    assert packet["source_human_acceptance_recorded"] is True
    assert packet["business_validation"] == "not_validated"
    assert packet["provider_calls_started"] is False
    assert packet["writes_long_term_memory"] is False
    assert packet["writes_company_kb"] is False
    assert packet["feedback_is_memory"] is False
    assert packet["candidate_is_promoted_memory"] is False
    assert packet["claim_boundaries"]["human_acceptance"] == "accepted"
    assert packet["claim_boundaries"]["business_validation"] == "not_validated"
    assert packet["memory_candidate"]["status"] == "candidate"
    assert packet["memory_candidate"]["candidate_is_promoted_memory"] is False
    assert packet["memory_candidate"]["source_feedback_ids"] == [packet["source_acceptance_feedback_event_id"]]
    assert packet["promotion_decision_template"]["decision"] == "pending"
    assert packet["promotion_decision_template"]["template_only"] is True
    assert packet["promotion_decision_template"]["writes_long_term_memory"] is False
    assert packet["promotion_decision_template"]["writes_company_kb"] is False


def test_rejected_or_revision_acceptance_feedback_stays_blocked_from_candidate_use(tmp_path: Path) -> None:
    for decision in ("rejected", "needs_revision"):
        packet = build_acceptance_feedback_candidate_packet(
            _acceptance_feedback_event(tmp_path / decision, decision=decision),
            generated_at="2026-06-03T01:10:00+08:00",
        )
        assert packet["source_acceptance_decision"] == decision
        assert packet["memory_candidate"]["status"] == "blocked"
        assert packet["promotion_decision_template"]["decision"] == "pending"
        assert "not promoted memory" in packet["non_claims"]


def test_acceptance_feedback_candidate_does_not_mutate_source_event(tmp_path: Path) -> None:
    event = _acceptance_feedback_event(tmp_path)
    before = deepcopy(event)

    build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T01:10:00+08:00")

    assert event == before


def test_acceptance_feedback_candidate_rejects_wrong_kind(tmp_path: Path) -> None:
    event = _acceptance_feedback_event(tmp_path)
    event["kind"] = "agentflow_wrong_kind"

    with pytest.raises(ValueError, match="acceptance feedback candidate requires kind"):
        build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T01:10:00+08:00")


def test_acceptance_feedback_candidate_rejects_event_that_created_memory_candidate(tmp_path: Path) -> None:
    event = _acceptance_feedback_event(tmp_path)
    event["creates_memory_candidate"] = True

    with pytest.raises(ValueError, match="original event to create no memory candidate"):
        build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T01:10:00+08:00")


def test_cli_drafts_acceptance_feedback_candidate_packet(tmp_path: Path) -> None:
    event_path = write_json(tmp_path / "acceptance_feedback_event.json", _acceptance_feedback_event(tmp_path))
    output_dir = tmp_path / "acceptance_feedback_candidate"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-draft-acceptance-feedback-candidate",
            str(event_path),
            "--generated-at",
            "2026-06-03T01:10:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory acceptance feedback candidate: candidate_only" in result.stdout
    assert "Source human acceptance: accepted" in result.stdout
    assert "Promotion decision: pending" in result.stdout
    packet = json.loads((output_dir / "acceptance_feedback_candidate_packet.json").read_text(encoding="utf-8"))
    candidate = json.loads((output_dir / "memory_candidate.json").read_text(encoding="utf-8"))
    decision = json.loads((output_dir / "promotion_decision_template.json").read_text(encoding="utf-8"))
    assert packet["kind"] == ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND
    assert candidate["candidate_is_promoted_memory"] is False
    assert decision["decision"] == "pending"
