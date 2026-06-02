from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import build_acceptance_feedback_candidate_packet
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    build_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_action_result_acceptance_feedback import (
    build_production_memory_action_result_acceptance_feedback_event,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    OPERATOR_LOOP_KIND,
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from narratocut.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _loop_inputs(tmp_path: Path, decision: str = "promoted") -> tuple[dict, dict, dict]:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T04:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        seed,
        tmp_path / "operator_loop_seed",
        write_run_package=True,
        write_run_package_check=True,
    )
    check_path = tmp_path / "operator_loop_seed" / "operator_run_package_check" / "operator_run_package_check.json"
    package_check = json.loads(check_path.read_text(encoding="utf-8"))
    event = build_production_memory_acceptance_feedback_event(
        package_check,
        decision="accepted",
        summary="Human operator accepted the package for the next production-memory iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T04:05:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T04:10:00+08:00")
    promotion_decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision=decision,
        rationale="Traceable acceptance feedback candidate selected for reviewed context assembly.",
        reviewer_role="operator",
        decided_at="2026-06-03T04:15:00+08:00",
    )
    return loop, packet, promotion_decision


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
    return json.loads(
        (
            tmp_path
            / "operator_loop_with_action_result"
            / "next_operator_action_result"
            / "next_operator_action_result.json"
        ).read_text(encoding="utf-8")
    )


def test_operator_loop_can_include_acceptance_feedback_candidate_overlay(tmp_path: Path) -> None:
    loop, packet, decision = _loop_inputs(tmp_path)

    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T04:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=decision,
    )

    manifest = result["manifest"]
    node_ids = {node["node_id"] for node in manifest["operator_loop_nodes"]}
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert manifest["kind"] == OPERATOR_LOOP_KIND
    assert manifest["chain_status"] == "ready"
    assert "acceptance_feedback_candidate_promotion_decision" in node_ids
    assert "acceptance_feedback_candidate_promotion_overlay" in node_ids
    assert manifest["acceptance_feedback_candidate_promotion"]["decision"] == "promoted"
    assert manifest["acceptance_feedback_candidate_promotion"]["decision_effect"] == "included_in_context"
    assert result["acceptance_feedback_candidate_promotion_decision"]["decision"] == "promoted"
    assert result["acceptance_feedback_candidate_promotion_overlay"]["candidate_included_in_context"] is True
    assert result["acceptance_feedback_candidate_promotion_overlay"]["writes_company_kb"] is False
    assert result["acceptance_feedback_candidate_reviewed_feedback_run"]["provider_calls_started"] is False
    assert result["acceptance_feedback_candidate_reviewed_feedback_run"]["writes_long_term_memory"] is False
    assert "acceptance_feedback_candidate_promotion_decision/acceptance_feedback_candidate_promotion_decision.json" in artifact_paths
    assert "acceptance_feedback_candidate_reviewed_feedback/acceptance_feedback_candidate_promotion_overlay.json" in artifact_paths
    assert "acceptance_feedback_candidate_reviewed_feedback/context_bundle.json" in artifact_paths


def test_operator_loop_acceptance_overlay_preserves_action_result_source_summary(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    packet = _action_result_acceptance_feedback_candidate_packet(tmp_path)
    decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable action-result acceptance feedback selected for reviewed context assembly.",
        reviewer_role="operator",
        decided_at="2026-06-03T12:15:00+08:00",
    )

    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T12:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=decision,
    )

    summary = result["manifest"]["acceptance_feedback_candidate_promotion"]
    node = next(
        item
        for item in result["manifest"]["operator_loop_nodes"]
        if item["node_id"] == "acceptance_feedback_candidate_promotion_decision"
    )
    assert summary["source_artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert summary["source_artifact_status"] == "action_completed"
    assert summary["source_artifact_path"] == "next_operator_action_result/next_operator_action_result.json"
    assert summary["source_target_artifact_type"] == "agentflow_production_memory_next_operator_action_result"
    assert summary["source_ready_for_acceptance"] is True
    assert node["detail"] == "agentflow_production_memory_next_operator_action_result:action_completed"


@pytest.mark.parametrize(
    ("packet_present", "decision_present", "message"),
    [
        (True, False, "acceptance_feedback_candidate_packet requires acceptance_feedback_candidate_promotion_decision"),
        (False, True, "acceptance_feedback_candidate_promotion_decision requires acceptance_feedback_candidate_packet"),
    ],
)
def test_operator_loop_requires_acceptance_feedback_candidate_packet_and_decision_pair(
    tmp_path: Path,
    packet_present: bool,
    decision_present: bool,
    message: str,
) -> None:
    loop, packet, decision = _loop_inputs(tmp_path)

    with pytest.raises(ValueError, match=message):
        build_production_memory_operator_loop_run(
            loop,
            generated_at="2026-06-03T04:20:00+08:00",
            source_kb_status="restructuring_or_unknown",
            acceptance_feedback_candidate_packet=packet if packet_present else None,
            acceptance_feedback_candidate_promotion_decision=decision if decision_present else None,
        )


def test_operator_loop_rejects_acceptance_feedback_candidate_packet_from_wrong_project(tmp_path: Path) -> None:
    loop, packet, decision = _loop_inputs(tmp_path)
    packet["source_project_id"] = "wrong-project"
    decision["source_project_id"] = "wrong-project"

    with pytest.raises(ValueError, match="acceptance_feedback_candidate_packet source_project_id must match loop project_id"):
        build_production_memory_operator_loop_run(
            loop,
            generated_at="2026-06-03T04:20:00+08:00",
            source_kb_status="restructuring_or_unknown",
            acceptance_feedback_candidate_packet=packet,
            acceptance_feedback_candidate_promotion_decision=decision,
        )


def test_operator_loop_cli_writes_acceptance_feedback_candidate_overlay(tmp_path: Path) -> None:
    _loop, packet, decision = _loop_inputs(tmp_path)
    packet_path = write_json(tmp_path / "acceptance_feedback_candidate_packet.json", packet)
    decision_path = write_json(tmp_path / "acceptance_feedback_candidate_promotion_decision.json", decision)
    output_dir = tmp_path / "operator_loop"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-03T04:20:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--acceptance-feedback-candidate-packet",
            str(packet_path),
            "--acceptance-feedback-candidate-promotion-decision",
            str(decision_path),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in completed.stdout
    assert "Acceptance feedback candidate promotion: included_in_context" in completed.stdout
    assert (
        output_dir
        / "acceptance_feedback_candidate_promotion_decision"
        / "acceptance_feedback_candidate_promotion_decision.json"
    ).exists()
    assert (
        output_dir
        / "acceptance_feedback_candidate_reviewed_feedback"
        / "acceptance_feedback_candidate_promotion_overlay.json"
    ).exists()
    manifest = json.loads((output_dir / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert manifest["acceptance_feedback_candidate_promotion"]["decision"] == "promoted"
    assert "acceptance_feedback_candidate_reviewed_feedback/context_bundle.json" in artifact_paths
    assert "acceptance_feedback_candidate_reviewed_feedback/acceptance_feedback_candidate_promotion_overlay.json" in artifact_paths
