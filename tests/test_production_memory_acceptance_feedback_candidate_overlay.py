from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import build_acceptance_feedback_candidate_packet
from agentflow.memory.production_acceptance_feedback_candidate_overlay import (
    ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
    build_acceptance_feedback_candidate_reviewed_run,
    build_loop_with_acceptance_feedback_candidate_reviewed_feedback,
)
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    build_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_action_result_acceptance_feedback import (
    build_production_memory_action_result_acceptance_feedback_event,
)
from agentflow.memory.production_loop import build_production_memory_loop_run, load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from agentflow_studio.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _acceptance_feedback_candidate_packet(tmp_path: Path, *, feedback_decision: str = "accepted") -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T03:00:00+08:00",
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
        reviewed_at="2026-06-03T03:05:00+08:00",
    )
    return build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T03:10:00+08:00")


def _promotion_decision(packet: dict, decision: str = "promoted") -> dict:
    return build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision=decision,
        rationale="Traceable acceptance feedback selected for the next context overlay.",
        reviewer_role="operator",
        decided_at="2026-06-03T03:15:00+08:00",
    )


def test_promoted_acceptance_feedback_candidate_enters_context_without_mutating_source(tmp_path: Path) -> None:
    base_loop = load_production_memory_loop(EXAMPLE_PATH)
    before = deepcopy(base_loop)
    packet = _acceptance_feedback_candidate_packet(tmp_path)
    decision = _promotion_decision(packet, "promoted")

    derived_loop = build_loop_with_acceptance_feedback_candidate_reviewed_feedback(base_loop, packet, decision)
    run = build_production_memory_loop_run(derived_loop)
    candidate_id = packet["memory_candidate"]["candidate_id"]
    target_ref = packet["memory_candidate"]["target_ref"]

    assert base_loop == before
    assert candidate_id in derived_loop["next_pass_request"]["requested_refs"]
    assert target_ref in {ref["ref_id"] for ref in derived_loop["artifact_ledger"]}
    assert packet["source_acceptance_feedback_event_id"] in {
        ref["feedback_id"] for ref in derived_loop["feedback_events"]
    }
    assert candidate_id in {ref["candidate_id"] for ref in derived_loop["memory_candidates"]}
    assert decision["decision_id"] in {ref["decision_id"] for ref in derived_loop["promotion_decisions"]}
    assert candidate_id in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert candidate_id in {ref["ref_id"] for ref in run["next_pass_bundle"]["context_refs"]}


def test_action_result_acceptance_candidate_overlay_preserves_source_target(
    tmp_path: Path,
) -> None:
    packet = _action_result_acceptance_feedback_candidate_packet(tmp_path)
    decision = _promotion_decision(packet, "promoted")

    derived_loop, run, overlay = build_acceptance_feedback_candidate_reviewed_run(
        load_production_memory_loop(EXAMPLE_PATH),
        packet,
        decision,
    )
    candidate_id = packet["memory_candidate"]["candidate_id"]
    target_ref = packet["memory_candidate"]["target_ref"]
    artifact = next(ref for ref in derived_loop["artifact_ledger"] if ref["ref_id"] == target_ref)

    assert artifact["artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert artifact["status"] == "accepted"
    assert "next operator action result" in artifact["title"].lower()
    assert candidate_id in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert overlay["source_artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert overlay["source_artifact_status"] == "action_completed"
    assert overlay["source_target_ref"].startswith("next-operator-action-result:")
    assert overlay["decision_effect"] == "included_in_context"
    assert overlay["candidate_included_in_context"] is True
    assert overlay["provider_calls_started"] is False
    assert overlay["writes_company_kb"] is False


def test_action_result_overlay_allows_local_run_source_path(tmp_path: Path) -> None:
    packet = _action_result_acceptance_feedback_candidate_packet(tmp_path)
    packet["source_artifact_path"] = (
        "data/processed/runs/production_memory_loop/operator_loop/next_operator_action_result/"
        "next_operator_action_result.json"
    )
    decision = _promotion_decision(packet, "promoted")

    derived_loop, _run, overlay = build_acceptance_feedback_candidate_reviewed_run(
        load_production_memory_loop(EXAMPLE_PATH),
        packet,
        decision,
    )
    decision_record = next(
        item for item in derived_loop["promotion_decisions"] if item["decision_id"] == decision["decision_id"]
    )

    assert overlay["source_artifact_path"].startswith("data/processed/runs/")
    assert decision_record["source_artifact_path"] == "next_operator_action_result/next_operator_action_result.json"
    assert overlay["source_artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert overlay["provider_calls_started"] is False
    assert overlay["writes_company_kb"] is False


def test_rejected_acceptance_feedback_candidate_is_blocked_from_context(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)
    decision = _promotion_decision(packet, "rejected")

    _derived_loop, run, overlay = build_acceptance_feedback_candidate_reviewed_run(
        load_production_memory_loop(EXAMPLE_PATH),
        packet,
        decision,
    )
    candidate_id = packet["memory_candidate"]["candidate_id"]
    blocked = {ref["ref_id"]: ref["reason"] for ref in run["context_bundle"]["blocked_refs"]}

    assert candidate_id not in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert blocked[candidate_id] == "promotion_decision_rejected"
    assert overlay["kind"] == ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND
    assert overlay["decision_effect"] == "blocked_from_context"
    assert overlay["candidate_blocked_from_context"] is True
    assert overlay["provider_calls_started"] is False
    assert overlay["writes_company_kb"] is False


def test_rejected_action_result_acceptance_candidate_is_blocked_from_context(tmp_path: Path) -> None:
    packet = _action_result_acceptance_feedback_candidate_packet(tmp_path)
    decision = _promotion_decision(packet, "rejected")

    _derived_loop, run, overlay = build_acceptance_feedback_candidate_reviewed_run(
        load_production_memory_loop(EXAMPLE_PATH),
        packet,
        decision,
    )
    candidate_id = packet["memory_candidate"]["candidate_id"]
    blocked = {ref["ref_id"]: ref["reason"] for ref in run["context_bundle"]["blocked_refs"]}

    assert candidate_id not in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert blocked[candidate_id] == "promotion_decision_rejected"
    assert overlay["source_artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert overlay["candidate_blocked_from_context"] is True
    assert overlay["decision_effect"] == "blocked_from_context"


def test_acceptance_feedback_pending_template_cannot_drive_overlay(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)
    template = packet["promotion_decision_template"]

    with pytest.raises(ValueError, match="explicit acceptance feedback candidate promotion decision"):
        build_loop_with_acceptance_feedback_candidate_reviewed_feedback(
            load_production_memory_loop(EXAMPLE_PATH),
            packet,
            template,
        )


def test_acceptance_feedback_candidate_overlay_rejects_mismatched_decision_packet(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)
    decision = _promotion_decision(packet)
    decision["source_packet_id"] = "wrong-packet"

    with pytest.raises(ValueError, match="source_packet_id must match"):
        build_loop_with_acceptance_feedback_candidate_reviewed_feedback(
            load_production_memory_loop(EXAMPLE_PATH),
            packet,
            decision,
        )


def test_cli_builds_acceptance_feedback_candidate_overlay(tmp_path: Path) -> None:
    packet = _acceptance_feedback_candidate_packet(tmp_path)
    decision = _promotion_decision(packet)
    packet_path = write_json(tmp_path / "acceptance_feedback_candidate_packet.json", packet)
    decision_path = write_json(tmp_path / "acceptance_feedback_candidate_promotion_decision.json", decision)
    output_dir = tmp_path / "overlay"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-acceptance-feedback-candidate-reviewed-no-provider",
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

    assert "Production memory acceptance feedback candidate reviewed run: ready" in result.stdout
    assert "Decision effect: included_in_context" in result.stdout
    run_payload = json.loads((output_dir / "production_memory_loop_run.json").read_text(encoding="utf-8"))
    overlay = json.loads((output_dir / "acceptance_feedback_candidate_promotion_overlay.json").read_text(encoding="utf-8"))
    candidate_id = packet["memory_candidate"]["candidate_id"]
    assert candidate_id in {ref["ref_id"] for ref in run_payload["context_bundle"]["included_refs"]}
    assert candidate_id in {ref["ref_id"] for ref in run_payload["next_pass_bundle"]["context_refs"]}
    assert overlay["candidate_id"] == candidate_id
    assert overlay["source_acceptance_decision"] == "accepted"
    assert overlay["decision_effect"] == "included_in_context"
    assert overlay["provider_calls_started"] is False
    assert overlay["writes_long_term_memory"] is False
    assert overlay["writes_company_kb"] is False


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
