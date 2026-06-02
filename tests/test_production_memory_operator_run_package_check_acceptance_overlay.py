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
from agentflow.memory.production_operator_run_package_check import check_operator_run_package


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_operator_run_package_check_records_acceptance_feedback_candidate_promotion_consistency(
    tmp_path: Path,
) -> None:
    output_root = _operator_loop_with_acceptance_feedback_overlay(tmp_path)
    package_path = output_root / "operator_run_package" / "operator_run_package.json"

    check = check_operator_run_package(package_path)

    acceptance_check = check["acceptance_feedback_candidate_promotion_check"]
    assert check["check_status"] == "passed"
    assert acceptance_check["status"] == "passed"
    assert acceptance_check["decision"] == "promoted"
    assert acceptance_check["decision_effect"] == "included_in_context"
    assert acceptance_check["candidate_included_in_context"] is True
    assert acceptance_check["handoff_matches_package"] is True
    assert check["failed_controls"] == []


def test_operator_run_package_check_fails_when_acceptance_context_action_lacks_promotion_summary(
    tmp_path: Path,
) -> None:
    output_root = _operator_loop_with_acceptance_feedback_overlay(tmp_path)
    package_path = output_root / "operator_run_package" / "operator_run_package.json"
    package = _read_json(package_path)
    package.pop("acceptance_feedback_candidate_promotion")
    _write_json(package_path, package)

    check = check_operator_run_package(package_path)

    acceptance_check = check["acceptance_feedback_candidate_promotion_check"]
    failed_controls = {item["control_id"] for item in check["failed_controls"]}
    assert check["check_status"] == "failed"
    assert acceptance_check["status"] == "failed"
    assert acceptance_check["requires_acceptance_context"] is True
    assert "missing package acceptance feedback candidate promotion summary" in acceptance_check["reasons"]
    assert "acceptance_feedback_candidate_promotion_required_for_context_action" in failed_controls


def test_operator_run_package_check_fails_when_acceptance_promotion_differs_from_handoff(
    tmp_path: Path,
) -> None:
    output_root = _operator_loop_with_acceptance_feedback_overlay(tmp_path)
    package_path = output_root / "operator_run_package" / "operator_run_package.json"
    package = _read_json(package_path)
    package["acceptance_feedback_candidate_promotion"]["decision"] = "rejected"
    _write_json(package_path, package)

    check = check_operator_run_package(package_path)

    acceptance_check = check["acceptance_feedback_candidate_promotion_check"]
    failed_controls = {item["control_id"] for item in check["failed_controls"]}
    assert check["check_status"] == "failed"
    assert acceptance_check["status"] == "failed"
    assert acceptance_check["handoff_matches_package"] is False
    assert "acceptance feedback candidate promotion summary differs from handoff" in acceptance_check["reasons"]
    assert "acceptance_feedback_candidate_promotion_matches_handoff" in failed_controls


def test_operator_run_package_check_fails_when_handoff_has_acceptance_promotion_but_package_does_not(
    tmp_path: Path,
) -> None:
    output_root = _operator_loop_with_acceptance_feedback_overlay(tmp_path)
    package_path = output_root / "operator_run_package" / "operator_run_package.json"
    package = _read_json(package_path)
    package.pop("acceptance_feedback_candidate_promotion")
    package["next_operator_action"]["action"] = "run_next_ai_task_with_context_bundle"
    _write_json(package_path, package)

    check = check_operator_run_package(package_path)

    acceptance_check = check["acceptance_feedback_candidate_promotion_check"]
    failed_controls = {item["control_id"] for item in check["failed_controls"]}
    assert check["check_status"] == "failed"
    assert acceptance_check["status"] == "failed"
    assert acceptance_check["requires_acceptance_context"] is False
    assert "missing package acceptance feedback candidate promotion summary" in acceptance_check["reasons"]
    assert "acceptance_feedback_candidate_promotion_matches_handoff" in failed_controls


def _operator_loop_with_acceptance_feedback_overlay(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed_result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T07:00:00+08:00",
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
        reviewed_at="2026-06-03T07:05:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T07:10:00+08:00")
    promotion_decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable acceptance feedback candidate selected for package consistency checking.",
        reviewer_role="operator",
        decided_at="2026-06-03T07:15:00+08:00",
    )
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T07:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=promotion_decision,
    )
    output_root = tmp_path / "operator_loop_with_acceptance_check"
    write_production_memory_operator_loop_run(
        result,
        output_root,
        write_run_package=True,
        write_run_package_check=True,
    )
    return output_root


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
