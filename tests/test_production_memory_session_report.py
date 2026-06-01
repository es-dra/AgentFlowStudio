from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_feedback import build_production_memory_feedback_capture
from agentflow.memory.production_loop import build_production_memory_loop_run
from agentflow.memory.production_promotion import (
    build_production_memory_promotion_decision,
    build_reviewed_feedback_run,
)
from agentflow.memory.production_session import (
    SESSION_REPORT_KIND,
    build_production_memory_session_report,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def build_capture() -> dict:
    return build_production_memory_feedback_capture(
        load_example(),
        target_ref="artifact:approved_storyboard:v1",
        decision="accepted",
        summary="Carry the reviewed storyboard structure into the next pass.",
        reviewer_role="operator",
        created_at="2026-06-02T00:00:00+08:00",
    )


def build_promotion(capture: dict, decision: str = "promoted") -> dict:
    return build_production_memory_promotion_decision(
        capture,
        decision=decision,
        rationale="Candidate is traceable to reviewed feedback.",
        reviewer_role="operator",
        decided_at="2026-06-02T00:05:00+08:00",
    )


def test_session_report_summarizes_ready_run_without_provider_or_memory_writes() -> None:
    run = build_production_memory_loop_run(load_example())

    report = build_production_memory_session_report(run, generated_at="2026-06-02T00:10:00+08:00")

    assert report["kind"] == SESSION_REPORT_KIND
    assert report["session_status"] == "ready"
    assert report["provider_mode"] == "no-provider"
    assert report["provider_calls_started"] is False
    assert report["writes_long_term_memory"] is False
    assert report["context_summary"]["included_ref_count"] == 3
    assert report["context_summary"]["blocked_ref_count"] == 3
    assert report["claim_boundaries"]["human_acceptance"] == "not_reviewed"
    assert report["next_operator_action"]["action"] == "prepare_next_pass"


def test_session_report_keeps_blocked_refs_out_of_next_context_refs() -> None:
    run = build_production_memory_loop_run(load_example())

    report = build_production_memory_session_report(run, generated_at="2026-06-02T00:10:00+08:00")
    included = {ref["ref_id"] for ref in report["context_summary"]["included_refs"]}
    blocked = {ref["ref_id"]: ref["reason"] for ref in report["context_summary"]["blocked_refs"]}
    next_context = {ref["ref_id"] for ref in report["next_context_refs"]}

    assert "artifact:draft_storyboard:v1" not in included
    assert blocked["artifact:draft_storyboard:v1"] == "artifact_status_rejected"
    assert next_context == included
    assert not (next_context & set(blocked))


def test_session_report_links_feedback_capture_and_promotion_decision() -> None:
    capture = build_capture()
    promotion = build_promotion(capture)
    _derived_loop, run = build_reviewed_feedback_run(load_example(), capture, promotion)

    report = build_production_memory_session_report(
        run,
        feedback_capture=capture,
        promotion_decision=promotion,
        generated_at="2026-06-02T00:10:00+08:00",
    )
    candidate_id = capture["memory_candidate"]["candidate_id"]

    assert report["feedback_capture"]["target_ref"] == "artifact:approved_storyboard:v1"
    assert report["feedback_capture"]["candidate_id"] == candidate_id
    assert report["promotion_decision"]["decision"] == "promoted"
    assert report["promotion_decision"]["candidate_id"] == candidate_id
    assert candidate_id in {ref["ref_id"] for ref in report["next_context_refs"]}
    assert report["next_operator_action"]["action"] == "prepare_next_pass"


def test_session_report_rejected_promotion_points_to_blocker_resolution() -> None:
    capture = build_capture()
    promotion = build_promotion(capture, decision="rejected")
    _derived_loop, run = build_reviewed_feedback_run(load_example(), capture, promotion)

    report = build_production_memory_session_report(
        run,
        feedback_capture=capture,
        promotion_decision=promotion,
        generated_at="2026-06-02T00:10:00+08:00",
    )
    candidate_id = capture["memory_candidate"]["candidate_id"]
    blocked = {ref["ref_id"]: ref["reason"] for ref in report["context_summary"]["blocked_refs"]}

    assert blocked[candidate_id] == "promotion_decision_rejected"
    assert report["promotion_decision"]["decision"] == "rejected"
    assert report["next_operator_action"]["action"] == "resolve_blocked_refs"


def test_session_report_rejects_non_run_payload() -> None:
    with pytest.raises(ValueError, match="production memory loop run"):
        build_production_memory_session_report({"kind": "not_a_run"}, generated_at="2026-06-02T00:10:00+08:00")


def test_cli_session_report_writes_json_and_markdown(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    report_dir = tmp_path / "report"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-no-provider",
            str(EXAMPLE_PATH),
            "--output",
            str(run_dir),
        ],
        check=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-session-report",
            str(run_dir / "production_memory_loop_run.json"),
            "--generated-at",
            "2026-06-02T00:10:00+08:00",
            "--output",
            str(report_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory session report: ready" in result.stdout
    report = json.loads((report_dir / "production_memory_session_report.json").read_text(encoding="utf-8"))
    markdown = (report_dir / "production_memory_session_report.md").read_text(encoding="utf-8")
    assert report["kind"] == SESSION_REPORT_KIND
    assert report["context_summary"]["included_ref_count"] == 3
    assert "Provider calls: not started" in markdown
    assert "Human acceptance: not_reviewed" in markdown
