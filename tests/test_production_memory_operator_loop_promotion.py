from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_next_pass_promotion import build_next_pass_promotion_decision
from agentflow.memory.production_next_pass_review import NEXT_PASS_RESULT_KIND
from agentflow.memory.production_operator_loop import (
    OPERATOR_LOOP_KIND,
    build_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _next_pass_result_for(packet: dict) -> dict:
    used_refs = [ref["ref_id"] for ref in packet["allowed_context_refs"][:2]]
    return {
        "kind": NEXT_PASS_RESULT_KIND,
        "artifact_type": NEXT_PASS_RESULT_KIND,
        "schema_version": packet["schema_version"],
        "task_packet_id": packet["task_packet_id"],
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "output_artifacts": [
            {
                "ref_id": "next-pass:artifact:draft-001",
                "title": "Second pass draft",
                "status": "draft",
                "used_context_refs": used_refs,
            }
        ],
        "feedback_events": [
            {
                "feedback_id": "feedback:next-pass-001",
                "target_ref": "next-pass:artifact:draft-001",
                "decision": "needs_revision",
                "summary": "Second pass needs operator review before memory promotion.",
            }
        ],
    }


def _loop_inputs() -> tuple[dict, dict, dict]:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T06:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    next_pass_result = _next_pass_result_for(seed["next_task_packet"])
    reviewed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T06:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        next_pass_result=next_pass_result,
    )
    decision = build_next_pass_promotion_decision(
        reviewed["next_pass_review"],
        candidate_id=reviewed["next_pass_review"]["feedback_candidates"][0]["candidate_id"],
        decision="promoted",
        rationale="Traceable next-pass feedback selected by the operator.",
        reviewer_role="operator",
        decided_at="2026-06-02T06:10:00+08:00",
    )
    return loop, next_pass_result, decision


def test_operator_loop_can_include_next_pass_promotion_overlay() -> None:
    loop, next_pass_result, decision = _loop_inputs()

    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T06:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        next_pass_result=next_pass_result,
        next_pass_promotion_decision=decision,
    )

    manifest = result["manifest"]
    node_ids = {node["node_id"] for node in manifest["operator_loop_nodes"]}
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert manifest["kind"] == OPERATOR_LOOP_KIND
    assert manifest["chain_status"] == "ready"
    assert "next_pass_review" in node_ids
    assert "next_pass_promotion_decision" in node_ids
    assert "next_pass_promotion_overlay" in node_ids
    assert manifest["next_pass_promotion"]["decision"] == "promoted"
    assert manifest["next_pass_promotion"]["decision_effect"] == "included_in_context"
    assert result["next_pass_promotion_decision"]["decision"] == "promoted"
    assert result["next_pass_promotion_overlay"]["candidate_included_in_context"] is True
    assert result["next_pass_reviewed_feedback_run"]["provider_calls_started"] is False
    assert result["next_pass_reviewed_feedback_run"]["writes_long_term_memory"] is False
    assert "next_pass_promotion_decision/next_pass_promotion_decision.json" in artifact_paths
    assert "next_pass_reviewed_feedback/next_pass_promotion_overlay.json" in artifact_paths
    assert "next_pass_reviewed_feedback/context_bundle.json" in artifact_paths


def test_operator_loop_requires_next_pass_result_for_promotion_decision() -> None:
    loop, _next_pass_result, decision = _loop_inputs()

    try:
        build_production_memory_operator_loop_run(
            loop,
            generated_at="2026-06-02T06:00:00+08:00",
            source_kb_status="restructuring_or_unknown",
            next_pass_promotion_decision=decision,
        )
    except ValueError as exc:
        assert "next_pass_promotion_decision requires next_pass_result" in str(exc)
    else:
        raise AssertionError("promotion decision was accepted without next_pass_result")


def test_operator_loop_cli_writes_next_pass_promotion_overlay(tmp_path: Path) -> None:
    loop, next_pass_result, decision = _loop_inputs()
    result_path = tmp_path / "next_pass_result.json"
    decision_path = tmp_path / "next_pass_promotion_decision.json"
    output_dir = tmp_path / "operator_loop"
    result_path.write_text(json.dumps(next_pass_result, indent=2), encoding="utf-8")
    decision_path.write_text(json.dumps(decision, indent=2), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-02T06:00:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--next-pass-result",
            str(result_path),
            "--next-pass-promotion-decision",
            str(decision_path),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in completed.stdout
    assert "Next pass review: ready_for_operator_review" in completed.stdout
    assert "Next pass promotion: included_in_context" in completed.stdout
    assert (output_dir / "next_pass_promotion_decision" / "next_pass_promotion_decision.json").exists()
    assert (output_dir / "next_pass_reviewed_feedback" / "next_pass_promotion_overlay.json").exists()
    manifest = json.loads((output_dir / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert manifest["next_pass_promotion"]["decision"] == "promoted"
    assert "next_pass_reviewed_feedback/context_bundle.json" in artifact_paths
    assert "next_pass_reviewed_feedback/next_pass_promotion_overlay.json" in artifact_paths
