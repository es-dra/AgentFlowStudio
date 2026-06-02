from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_acceptance_feedback import (
    ACCEPTANCE_FEEDBACK_EVENT_KIND,
    build_production_memory_acceptance_feedback_event,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _operator_run_package_check(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T23:55:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path,
        write_run_package=True,
        write_run_package_check=True,
    )
    return tmp_path / "operator_run_package_check" / "operator_run_package_check.json"


def test_acceptance_feedback_records_human_decision_without_business_or_memory_claims(tmp_path: Path) -> None:
    check = json.loads(_operator_run_package_check(tmp_path).read_text(encoding="utf-8"))

    event = build_production_memory_acceptance_feedback_event(
        check,
        decision="accepted",
        summary="Human operator accepted the package for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T00:05:00+08:00",
    )

    assert event["kind"] == ACCEPTANCE_FEEDBACK_EVENT_KIND
    assert event["acceptance_decision"] == "accepted"
    assert event["status"] == "human_recorded"
    assert event["source_check_status"] == "passed"
    assert event["source_ready_for_handoff"] is True
    assert event["human_acceptance_recorded"] is True
    assert event["claim_boundaries"]["human_acceptance"] == "accepted"
    assert event["claim_boundaries"]["business_validation"] == "not_validated"
    assert event["feedback_is_memory"] is False
    assert event["creates_memory_candidate"] is False
    assert event["creates_promotion_decision"] is False
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False


def test_acceptance_feedback_accepted_requires_passed_ready_package_check(tmp_path: Path) -> None:
    check = json.loads(_operator_run_package_check(tmp_path).read_text(encoding="utf-8"))
    check["check_status"] = "failed"
    check["ready_for_handoff"] = False

    with pytest.raises(ValueError, match="accepted acceptance feedback requires passed ready package check"):
        build_production_memory_acceptance_feedback_event(
            check,
            decision="accepted",
            summary="Human operator accepted the package for the next local iteration.",
            reviewer_role="operator",
            reviewed_at="2026-06-03T00:05:00+08:00",
        )

    event = build_production_memory_acceptance_feedback_event(
        check,
        decision="needs_revision",
        summary="Human operator requests revisions before the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T00:06:00+08:00",
    )
    assert event["acceptance_decision"] == "needs_revision"
    assert event["claim_boundaries"]["human_acceptance"] == "needs_revision"


def test_acceptance_feedback_allows_ignored_runtime_source_refs(tmp_path: Path) -> None:
    check = json.loads(_operator_run_package_check(tmp_path).read_text(encoding="utf-8"))
    check["package_path"] = (
        "data/processed/runs/production_memory_loop/operator_loop/"
        "operator_run_package/operator_run_package.json"
    )
    check["artifact_root"] = "data/processed/runs/production_memory_loop/operator_loop"

    event = build_production_memory_acceptance_feedback_event(
        check,
        decision="accepted",
        summary="Human operator accepted the package for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T00:07:00+08:00",
    )

    assert event["source_package_path"].startswith("data/processed/runs/")
    assert event["acceptance_decision"] == "accepted"
    assert event["writes_company_kb"] is False


def test_acceptance_feedback_cli_writes_event_and_markdown_without_side_effects(tmp_path: Path) -> None:
    check_path = _operator_run_package_check(tmp_path / "operator_loop")
    output_dir = tmp_path / "acceptance_feedback"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-record-acceptance-feedback",
            str(check_path),
            "--decision",
            "accepted",
            "--summary",
            "Human operator accepted the package for the next local iteration.",
            "--reviewed-at",
            "2026-06-03T00:05:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory acceptance feedback: accepted" in result.stdout
    assert "Business validation: not validated" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    assert (output_dir / "acceptance_feedback_event.json").exists()
    assert (output_dir / "acceptance_feedback_event.md").exists()
    event = json.loads((output_dir / "acceptance_feedback_event.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "acceptance_feedback_event.md").read_text(encoding="utf-8")
    assert event["kind"] == ACCEPTANCE_FEEDBACK_EVENT_KIND
    assert event["acceptance_decision"] == "accepted"
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
    assert "Human acceptance: accepted" in markdown
    assert "Business validation: not_validated" in markdown
