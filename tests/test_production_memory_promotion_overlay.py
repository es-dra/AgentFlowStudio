from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from agentflow.memory.production_feedback import build_production_memory_feedback_capture
from agentflow.memory.production_loop import build_production_memory_loop_run
from agentflow.memory.production_promotion import (
    build_loop_with_reviewed_feedback,
    build_production_memory_promotion_decision,
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


def test_reviewed_promotion_decision_is_explicit_and_no_write() -> None:
    capture = build_capture()
    decision = build_production_memory_promotion_decision(
        capture,
        decision="promoted",
        rationale="Candidate is traceable to reviewed feedback.",
        reviewer_role="operator",
        decided_at="2026-06-02T00:05:00+08:00",
    )

    assert decision["decision"] == "promoted"
    assert decision["candidate_id"] == capture["memory_candidate"]["candidate_id"]
    assert decision["source_candidate_id"] == capture["memory_candidate"]["candidate_id"]
    assert decision["template_only"] is False
    assert decision["writes_long_term_memory"] is False
    assert decision["review_mode"] == "explicit_operator_decision"


def test_promoted_reviewed_feedback_enters_next_context_without_mutating_source() -> None:
    base_loop = load_example()
    before = deepcopy(base_loop)
    capture = build_capture()
    decision = build_production_memory_promotion_decision(
        capture,
        decision="promoted",
        rationale="Candidate is traceable to reviewed feedback.",
        reviewer_role="operator",
        decided_at="2026-06-02T00:05:00+08:00",
    )

    derived_loop = build_loop_with_reviewed_feedback(base_loop, capture, decision)
    run = build_production_memory_loop_run(derived_loop)
    candidate_id = capture["memory_candidate"]["candidate_id"]

    assert base_loop == before
    assert candidate_id in derived_loop["next_pass_request"]["requested_refs"]
    assert candidate_id in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert candidate_id in {ref["ref_id"] for ref in run["next_pass_bundle"]["context_refs"]}


def test_rejected_reviewed_feedback_is_blocked_from_next_context() -> None:
    capture = build_capture()
    decision = build_production_memory_promotion_decision(
        capture,
        decision="rejected",
        rationale="Candidate is too narrow for reuse.",
        reviewer_role="operator",
        decided_at="2026-06-02T00:05:00+08:00",
    )

    derived_loop = build_loop_with_reviewed_feedback(load_example(), capture, decision)
    run = build_production_memory_loop_run(derived_loop)
    candidate_id = capture["memory_candidate"]["candidate_id"]
    blocked = {ref["ref_id"]: ref["reason"] for ref in run["context_bundle"]["blocked_refs"]}

    assert candidate_id not in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert blocked[candidate_id] == "promotion_decision_rejected"


def test_cli_review_and_run_reviewed_feedback_overlay(tmp_path: Path) -> None:
    capture_dir = tmp_path / "capture"
    decision_dir = tmp_path / "decision"
    output_dir = tmp_path / "reviewed_run"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-draft-feedback",
            str(EXAMPLE_PATH),
            "--target-ref",
            "artifact:approved_storyboard:v1",
            "--decision",
            "accepted",
            "--summary",
            "Carry the reviewed storyboard structure into the next pass.",
            "--created-at",
            "2026-06-02T00:00:00+08:00",
            "--output",
            str(capture_dir),
        ],
        check=True,
    )
    review = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-review-promotion",
            str(capture_dir / "production_memory_feedback_capture.json"),
            "--decision",
            "promoted",
            "--rationale",
            "Candidate is traceable to reviewed feedback.",
            "--decided-at",
            "2026-06-02T00:05:00+08:00",
            "--output",
            str(decision_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Production memory promotion decision: promoted" in review.stdout

    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-reviewed-feedback-no-provider",
            str(EXAMPLE_PATH),
            "--feedback-capture",
            str(capture_dir / "production_memory_feedback_capture.json"),
            "--promotion-decision",
            str(decision_dir / "promotion_decision.json"),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory reviewed feedback run: ready" in run.stdout
    run_payload = json.loads((output_dir / "production_memory_loop_run.json").read_text(encoding="utf-8"))
    derived_loop = json.loads((output_dir / "derived_production_memory_loop.json").read_text(encoding="utf-8"))
    candidate_id = json.loads((decision_dir / "promotion_decision.json").read_text(encoding="utf-8"))["candidate_id"]
    assert candidate_id in derived_loop["next_pass_request"]["requested_refs"]
    assert candidate_id in {ref["ref_id"] for ref in run_payload["context_bundle"]["included_refs"]}
