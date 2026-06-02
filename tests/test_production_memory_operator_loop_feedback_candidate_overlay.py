from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_feedback import build_production_memory_operator_feedback_event
from agentflow.memory.production_operator_feedback_candidate import build_operator_feedback_candidate_packet
from agentflow.memory.production_operator_feedback_candidate_promotion import (
    build_operator_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_operator_loop import (
    OPERATOR_LOOP_KIND,
    build_production_memory_operator_loop_run,
)
from agentflow_studio.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _loop_inputs(decision: str = "promoted") -> tuple[dict, dict, dict]:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    event = build_production_memory_operator_feedback_event(
        seed["manifest"],
        target_node_id="company_kb_feedback_candidate_packet",
        decision="accepted",
        summary="Operator selected the feedback candidate overlay for the next loop.",
        reviewer_role="operator",
        reviewed_at="2026-06-02T10:10:00+08:00",
    )
    packet = build_operator_feedback_candidate_packet(event, generated_at="2026-06-02T10:20:00+08:00")
    promotion_decision = build_operator_feedback_candidate_promotion_decision(
        packet,
        decision=decision,
        rationale="Traceable operator feedback candidate selected for the next context overlay.",
        reviewer_role="operator",
        decided_at="2026-06-02T10:30:00+08:00",
    )
    return loop, packet, promotion_decision


def test_operator_loop_can_include_operator_feedback_candidate_overlay() -> None:
    loop, packet, decision = _loop_inputs()

    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T10:40:00+08:00",
        source_kb_status="restructuring_or_unknown",
        operator_feedback_candidate_packet=packet,
        operator_feedback_candidate_promotion_decision=decision,
    )

    manifest = result["manifest"]
    node_ids = {node["node_id"] for node in manifest["operator_loop_nodes"]}
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert manifest["kind"] == OPERATOR_LOOP_KIND
    assert manifest["chain_status"] == "ready"
    assert "operator_feedback_candidate_promotion_decision" in node_ids
    assert "operator_feedback_candidate_promotion_overlay" in node_ids
    assert manifest["operator_feedback_candidate_promotion"]["decision"] == "promoted"
    assert manifest["operator_feedback_candidate_promotion"]["decision_effect"] == "included_in_context"
    assert result["operator_feedback_candidate_promotion_decision"]["decision"] == "promoted"
    assert result["operator_feedback_candidate_promotion_overlay"]["candidate_included_in_context"] is True
    assert result["operator_feedback_candidate_promotion_overlay"]["writes_company_kb"] is False
    assert result["operator_feedback_candidate_reviewed_feedback_run"]["provider_calls_started"] is False
    assert result["operator_feedback_candidate_reviewed_feedback_run"]["writes_long_term_memory"] is False
    assert "operator_feedback_candidate_promotion_decision/operator_feedback_candidate_promotion_decision.json" in artifact_paths
    assert "operator_feedback_candidate_reviewed_feedback/operator_feedback_candidate_promotion_overlay.json" in artifact_paths
    assert "operator_feedback_candidate_reviewed_feedback/context_bundle.json" in artifact_paths


@pytest.mark.parametrize(
    ("packet_present", "decision_present", "message"),
    [
        (True, False, "operator_feedback_candidate_packet requires operator_feedback_candidate_promotion_decision"),
        (False, True, "operator_feedback_candidate_promotion_decision requires operator_feedback_candidate_packet"),
    ],
)
def test_operator_loop_requires_feedback_candidate_packet_and_decision_pair(
    packet_present: bool,
    decision_present: bool,
    message: str,
) -> None:
    loop, packet, decision = _loop_inputs()

    with pytest.raises(ValueError, match=message):
        build_production_memory_operator_loop_run(
            loop,
            generated_at="2026-06-02T10:40:00+08:00",
            source_kb_status="restructuring_or_unknown",
            operator_feedback_candidate_packet=packet if packet_present else None,
            operator_feedback_candidate_promotion_decision=decision if decision_present else None,
        )


def test_operator_loop_rejects_feedback_candidate_packet_from_wrong_project() -> None:
    loop, packet, decision = _loop_inputs()
    packet["source_project_id"] = "wrong-project"
    decision["source_project_id"] = "wrong-project"

    with pytest.raises(ValueError, match="operator_feedback_candidate_packet source_project_id must match loop project_id"):
        build_production_memory_operator_loop_run(
            loop,
            generated_at="2026-06-02T10:40:00+08:00",
            source_kb_status="restructuring_or_unknown",
            operator_feedback_candidate_packet=packet,
            operator_feedback_candidate_promotion_decision=decision,
        )


def test_operator_loop_cli_writes_operator_feedback_candidate_overlay(tmp_path: Path) -> None:
    _loop, packet, decision = _loop_inputs()
    packet_path = write_json(tmp_path / "operator_feedback_candidate_packet.json", packet)
    decision_path = write_json(tmp_path / "operator_feedback_candidate_promotion_decision.json", decision)
    output_dir = tmp_path / "operator_loop"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-02T10:40:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--operator-feedback-candidate-packet",
            str(packet_path),
            "--operator-feedback-candidate-promotion-decision",
            str(decision_path),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in completed.stdout
    assert "Operator feedback candidate promotion: included_in_context" in completed.stdout
    assert (
        output_dir
        / "operator_feedback_candidate_promotion_decision"
        / "operator_feedback_candidate_promotion_decision.json"
    ).exists()
    assert (
        output_dir
        / "operator_feedback_candidate_reviewed_feedback"
        / "operator_feedback_candidate_promotion_overlay.json"
    ).exists()
    manifest = json.loads((output_dir / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert manifest["operator_feedback_candidate_promotion"]["decision"] == "promoted"
    assert "operator_feedback_candidate_reviewed_feedback/context_bundle.json" in artifact_paths
    assert "operator_feedback_candidate_reviewed_feedback/operator_feedback_candidate_promotion_overlay.json" in artifact_paths
