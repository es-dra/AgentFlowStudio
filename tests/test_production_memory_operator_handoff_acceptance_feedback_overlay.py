from __future__ import annotations

import json
from pathlib import Path

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import build_acceptance_feedback_candidate_packet
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    build_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_operator_handoff_and_run_package_surface_acceptance_feedback_candidate_overlay(tmp_path: Path) -> None:
    loop, packet, promotion_decision = _acceptance_feedback_candidate_inputs(tmp_path / "seed")
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T05:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=promotion_decision,
    )

    write_production_memory_operator_loop_run(
        result,
        tmp_path / "operator_loop",
        write_run_package=True,
        write_run_package_check=True,
    )

    handoff = _read_json(tmp_path / "operator_loop" / "operator_handoff" / "operator_handoff_packet.json")
    package = _read_json(tmp_path / "operator_loop" / "operator_run_package" / "operator_run_package.json")
    package_check = _read_json(tmp_path / "operator_loop" / "operator_run_package_check" / "operator_run_package_check.json")
    handoff_markdown = (tmp_path / "operator_loop" / "operator_handoff" / "operator_handoff_packet.md").read_text(
        encoding="utf-8"
    )
    package_markdown = (tmp_path / "operator_loop" / "operator_run_package" / "operator_run_package.md").read_text(
        encoding="utf-8"
    )

    summary = handoff["acceptance_feedback_candidate_promotion"]
    assert summary["decision"] == "promoted"
    assert summary["decision_effect"] == "included_in_context"
    assert summary["candidate_included_in_context"] is True
    assert summary["context_bundle_id"].startswith("context:")
    assert handoff["next_operator_action"]["action"] == "run_next_ai_task_with_acceptance_feedback_context"
    assert "Acceptance feedback candidate promotion" in handoff["handoff_prompt"]
    assert "## Acceptance Feedback Candidate Promotion" in handoff_markdown
    assert "Decision: promoted" in handoff_markdown

    assert package["acceptance_feedback_candidate_promotion"] == summary
    assert package["next_operator_action"] == handoff["next_operator_action"]
    assert "## Acceptance Feedback Candidate Promotion" in package_markdown
    assert "Decision effect: included_in_context" in package_markdown
    assert package_check["check_status"] == "passed"


def _acceptance_feedback_candidate_inputs(tmp_path: Path) -> tuple[dict, dict, dict]:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed_result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T05:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        seed_result,
        tmp_path / "operator_loop_seed",
        write_run_package=True,
        write_run_package_check=True,
    )
    package_check = _read_json(
        tmp_path / "operator_loop_seed" / "operator_run_package_check" / "operator_run_package_check.json"
    )
    event = build_production_memory_acceptance_feedback_event(
        package_check,
        decision="accepted",
        summary="Human operator accepted the package for the next production-memory iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T05:05:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T05:10:00+08:00")
    promotion_decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable acceptance feedback candidate selected for reviewed context assembly.",
        reviewer_role="operator",
        decided_at="2026-06-03T05:15:00+08:00",
    )
    return loop, packet, promotion_decision


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
