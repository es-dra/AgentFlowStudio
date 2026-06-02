from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_loop import build_production_memory_loop_run
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_feedback_candidate_overlay import (
    OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
    build_loop_with_operator_feedback_candidate_reviewed_feedback,
    build_operator_feedback_candidate_reviewed_run,
)
from agentflow.memory.production_operator_feedback import build_production_memory_operator_feedback_event
from agentflow.memory.production_operator_feedback_candidate import build_operator_feedback_candidate_packet
from agentflow.memory.production_operator_feedback_candidate_promotion import (
    build_operator_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_operator_loop import build_production_memory_operator_loop_run
from narratocut.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _operator_feedback_candidate_packet() -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T09:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    event = build_production_memory_operator_feedback_event(
        result["manifest"],
        target_node_id="company_kb_feedback_candidate_packet",
        decision="accepted",
        summary="Operator reviewed the candidate packet shape for the next loop.",
        reviewer_role="operator",
        reviewed_at="2026-06-02T09:10:00+08:00",
    )
    return build_operator_feedback_candidate_packet(event, generated_at="2026-06-02T09:20:00+08:00")


def _promotion_decision(packet: dict, decision: str = "promoted") -> dict:
    return build_operator_feedback_candidate_promotion_decision(
        packet,
        decision=decision,
        rationale="Traceable operator feedback selected for the next context overlay.",
        reviewer_role="operator",
        decided_at="2026-06-02T09:30:00+08:00",
    )


def test_promoted_operator_feedback_candidate_enters_context_without_mutating_source() -> None:
    base_loop = load_production_memory_loop(EXAMPLE_PATH)
    before = deepcopy(base_loop)
    packet = _operator_feedback_candidate_packet()
    decision = _promotion_decision(packet, "promoted")

    derived_loop = build_loop_with_operator_feedback_candidate_reviewed_feedback(base_loop, packet, decision)
    run = build_production_memory_loop_run(derived_loop)
    candidate_id = packet["memory_candidate"]["candidate_id"]
    target_ref = packet["memory_candidate"]["target_ref"]

    assert base_loop == before
    assert candidate_id in derived_loop["next_pass_request"]["requested_refs"]
    assert target_ref in {ref["ref_id"] for ref in derived_loop["artifact_ledger"]}
    assert packet["source_feedback_event_id"] in {ref["feedback_id"] for ref in derived_loop["feedback_events"]}
    assert candidate_id in {ref["candidate_id"] for ref in derived_loop["memory_candidates"]}
    assert decision["decision_id"] in {ref["decision_id"] for ref in derived_loop["promotion_decisions"]}
    assert candidate_id in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert candidate_id in {ref["ref_id"] for ref in run["next_pass_bundle"]["context_refs"]}


def test_rejected_operator_feedback_candidate_is_blocked_from_context() -> None:
    packet = _operator_feedback_candidate_packet()
    decision = _promotion_decision(packet, "rejected")

    _derived_loop, run, overlay = build_operator_feedback_candidate_reviewed_run(
        load_production_memory_loop(EXAMPLE_PATH),
        packet,
        decision,
    )
    candidate_id = packet["memory_candidate"]["candidate_id"]
    blocked = {ref["ref_id"]: ref["reason"] for ref in run["context_bundle"]["blocked_refs"]}

    assert candidate_id not in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert blocked[candidate_id] == "promotion_decision_rejected"
    assert overlay["kind"] == OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND
    assert overlay["decision_effect"] == "blocked_from_context"
    assert overlay["candidate_blocked_from_context"] is True
    assert overlay["provider_calls_started"] is False
    assert overlay["writes_company_kb"] is False


def test_operator_feedback_pending_template_cannot_drive_overlay() -> None:
    packet = _operator_feedback_candidate_packet()
    template = packet["promotion_decision_template"]

    with pytest.raises(ValueError, match="explicit operator feedback candidate promotion decision"):
        build_loop_with_operator_feedback_candidate_reviewed_feedback(
            load_production_memory_loop(EXAMPLE_PATH),
            packet,
            template,
        )


def test_operator_feedback_candidate_overlay_rejects_mismatched_decision_packet() -> None:
    packet = _operator_feedback_candidate_packet()
    decision = _promotion_decision(packet)
    decision["source_packet_id"] = "wrong-packet"

    with pytest.raises(ValueError, match="source_packet_id must match"):
        build_loop_with_operator_feedback_candidate_reviewed_feedback(
            load_production_memory_loop(EXAMPLE_PATH),
            packet,
            decision,
        )


def test_cli_builds_operator_feedback_candidate_overlay(tmp_path: Path) -> None:
    packet = _operator_feedback_candidate_packet()
    decision = _promotion_decision(packet)
    packet_path = write_json(tmp_path / "operator_feedback_candidate_packet.json", packet)
    decision_path = write_json(tmp_path / "operator_feedback_candidate_promotion_decision.json", decision)
    output_dir = tmp_path / "overlay"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-feedback-candidate-reviewed-no-provider",
            str(EXAMPLE_PATH),
            "--candidate-packet",
            str(packet_path),
            "--promotion-decision",
            str(decision_path),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator feedback candidate reviewed run: ready" in result.stdout
    assert "Decision effect: included_in_context" in result.stdout
    run_payload = json.loads((output_dir / "production_memory_loop_run.json").read_text(encoding="utf-8"))
    overlay = json.loads((output_dir / "operator_feedback_candidate_promotion_overlay.json").read_text(encoding="utf-8"))
    candidate_id = packet["memory_candidate"]["candidate_id"]
    assert candidate_id in {ref["ref_id"] for ref in run_payload["context_bundle"]["included_refs"]}
    assert candidate_id in {ref["ref_id"] for ref in run_payload["next_pass_bundle"]["context_refs"]}
    assert overlay["candidate_id"] == candidate_id
    assert overlay["decision_effect"] == "included_in_context"
    assert overlay["provider_calls_started"] is False
    assert overlay["writes_long_term_memory"] is False
    assert overlay["writes_company_kb"] is False
