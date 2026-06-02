from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_feedback import (
    OPERATOR_FEEDBACK_EVENT_KIND,
    build_production_memory_operator_feedback_event,
)
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _operator_manifest(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T07:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    write_production_memory_operator_loop_run(result, tmp_path)
    return tmp_path / "production_memory_operator_loop_run.json"


def test_operator_feedback_capture_is_evidence_not_acceptance_or_memory(tmp_path: Path) -> None:
    manifest = json.loads(_operator_manifest(tmp_path).read_text(encoding="utf-8"))

    event = build_production_memory_operator_feedback_event(
        manifest,
        target_node_id="company_kb_feedback_candidate_packet",
        decision="accepted",
        summary="Operator reviewed the candidate packet shape for the next loop.",
        reviewer_role="operator",
        reviewed_at="2026-06-02T07:10:00+08:00",
    )

    assert event["kind"] == OPERATOR_FEEDBACK_EVENT_KIND
    assert event["target_node_id"] == "company_kb_feedback_candidate_packet"
    assert event["decision"] == "accepted"
    assert event["feedback_is_memory"] is False
    assert event["creates_memory_candidate"] is False
    assert event["creates_promotion_decision"] is False
    assert event["provider_calls_started"] is False
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
    assert event["claim_boundaries"]["human_acceptance"] == "not_claimed"
    assert event["claim_boundaries"]["business_validation"] == "not_validated"


def test_operator_feedback_capture_unknown_node_fails(tmp_path: Path) -> None:
    manifest = json.loads(_operator_manifest(tmp_path).read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="target_node_id does not exist"):
        build_production_memory_operator_feedback_event(
            manifest,
            target_node_id="missing_node",
            decision="note",
            summary="Missing node feedback should fail.",
            reviewer_role="operator",
            reviewed_at="2026-06-02T07:10:00+08:00",
        )


def test_operator_feedback_cli_writes_event_and_markdown_without_provider_or_memory_writes(tmp_path: Path) -> None:
    manifest_path = _operator_manifest(tmp_path / "operator_loop")
    output_dir = tmp_path / "operator_feedback"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-capture-operator-feedback",
            str(manifest_path),
            "--target-node",
            "company_kb_feedback_candidate_packet",
            "--decision",
            "accepted",
            "--summary",
            "Operator reviewed the candidate packet shape for the next loop.",
            "--reviewed-at",
            "2026-06-02T07:10:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator feedback: evidence_only" in result.stdout
    assert "Human acceptance: not claimed" in result.stdout
    assert (output_dir / "operator_feedback_event.json").exists()
    assert (output_dir / "operator_feedback_event.md").exists()
    event = json.loads((output_dir / "operator_feedback_event.json").read_text(encoding="utf-8"))
    assert event["kind"] == OPERATOR_FEEDBACK_EVENT_KIND
    assert event["feedback_is_memory"] is False
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
