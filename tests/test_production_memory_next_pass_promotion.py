from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from agentflow.memory.production_loop import build_production_memory_loop_run, load_production_memory_loop
from agentflow.memory.production_next_context import build_next_context_handoff
from agentflow.memory.production_next_pass_promotion import (
    NEXT_PASS_PROMOTION_DECISION_KIND,
    build_loop_with_next_pass_reviewed_feedback,
    build_next_pass_promotion_decision,
    build_next_pass_reviewed_feedback_run,
)
from agentflow.memory.production_next_pass_review import NEXT_PASS_RESULT_KIND, build_next_pass_review, write_next_pass_review
from agentflow.memory.production_next_task import build_next_task_packet


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _ready_review() -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at="2026-06-02T05:00:00+08:00")
    packet = build_next_task_packet(handoff, generated_at="2026-06-02T05:02:00+08:00")
    used_refs = [ref["ref_id"] for ref in packet["allowed_context_refs"][:2]]
    result = {
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
                "summary": "Keep the second-pass feedback as a candidate until explicit review.",
            }
        ],
    }
    return build_next_pass_review(packet, result, reviewed_at="2026-06-02T05:05:00+08:00")


def _decision(review: dict, decision: str = "promoted") -> dict:
    return build_next_pass_promotion_decision(
        review,
        candidate_id=review["feedback_candidates"][0]["candidate_id"],
        decision=decision,
        rationale="Traceable next-pass feedback selected by the operator.",
        reviewer_role="operator",
        decided_at="2026-06-02T05:10:00+08:00",
    )


def test_next_pass_promotion_decision_is_explicit_and_no_write() -> None:
    review = _ready_review()

    decision = _decision(review)

    assert decision["kind"] == NEXT_PASS_PROMOTION_DECISION_KIND
    assert decision["decision"] == "promoted"
    assert decision["candidate_id"] == review["feedback_candidates"][0]["candidate_id"]
    assert decision["source_review_id"] == review["review_id"]
    assert decision["template_only"] is False
    assert decision["review_mode"] == "explicit_operator_decision"
    assert decision["provider_mode"] == "no-provider"
    assert decision["provider_calls_started"] is False
    assert decision["writes_long_term_memory"] is False
    assert decision["writes_company_kb"] is False


def test_promoted_next_pass_feedback_enters_followup_context_without_mutating_source() -> None:
    base_loop = load_production_memory_loop(EXAMPLE_PATH)
    before = deepcopy(base_loop)
    review = _ready_review()
    decision = _decision(review, "promoted")

    derived_loop = build_loop_with_next_pass_reviewed_feedback(base_loop, review, decision)
    run = build_production_memory_loop_run(derived_loop)
    candidate_id = decision["candidate_id"]

    assert base_loop == before
    assert candidate_id in derived_loop["next_pass_request"]["requested_refs"]
    assert candidate_id in {ref["candidate_id"] for ref in derived_loop["memory_candidates"]}
    assert "next-pass:artifact:draft-001" in {ref["ref_id"] for ref in derived_loop["artifact_ledger"]}
    assert "feedback:next-pass-001" in {ref["feedback_id"] for ref in derived_loop["feedback_events"]}
    assert candidate_id in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert candidate_id in {ref["ref_id"] for ref in run["next_pass_bundle"]["context_refs"]}


def test_pending_next_pass_template_cannot_be_used_as_reviewed_decision() -> None:
    review = _ready_review()
    template = review["promotion_decision_templates"][0]

    try:
        build_loop_with_next_pass_reviewed_feedback(load_production_memory_loop(EXAMPLE_PATH), review, template)
    except ValueError as exc:
        assert "explicit next-pass promotion decision" in str(exc)
    else:
        raise AssertionError("pending next-pass promotion template was accepted")


def test_rejected_next_pass_feedback_is_blocked_from_followup_context() -> None:
    review = _ready_review()
    decision = _decision(review, "rejected")

    _derived_loop, run, overlay = build_next_pass_reviewed_feedback_run(
        load_production_memory_loop(EXAMPLE_PATH),
        review,
        decision,
    )
    candidate_id = decision["candidate_id"]
    blocked = {ref["ref_id"]: ref["reason"] for ref in run["context_bundle"]["blocked_refs"]}

    assert candidate_id not in {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    assert blocked[candidate_id] == "promotion_decision_rejected"
    assert overlay["decision_effect"] == "blocked_from_context"
    assert overlay["provider_calls_started"] is False
    assert overlay["writes_long_term_memory"] is False


def test_cli_reviews_next_pass_feedback_and_runs_no_provider_overlay(tmp_path: Path) -> None:
    review_dir = tmp_path / "review"
    decision_dir = tmp_path / "decision"
    output_dir = tmp_path / "run"
    review = _ready_review()
    write_next_pass_review(review, review_dir)

    decided = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-review-next-pass-promotion",
            str(review_dir / "next_pass_review.json"),
            "--candidate-id",
            review["feedback_candidates"][0]["candidate_id"],
            "--decision",
            "promoted",
            "--rationale",
            "Traceable next-pass feedback selected by the operator.",
            "--decided-at",
            "2026-06-02T05:10:00+08:00",
            "--output",
            str(decision_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Production memory next pass promotion decision: promoted" in decided.stdout
    assert (decision_dir / "next_pass_promotion_decision.json").exists()

    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-next-pass-reviewed-feedback-no-provider",
            str(EXAMPLE_PATH),
            "--next-pass-review",
            str(review_dir / "next_pass_review.json"),
            "--promotion-decision",
            str(decision_dir / "next_pass_promotion_decision.json"),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory next pass reviewed feedback run: ready" in run.stdout
    run_payload = json.loads((output_dir / "production_memory_loop_run.json").read_text(encoding="utf-8"))
    overlay = json.loads((output_dir / "next_pass_promotion_overlay.json").read_text(encoding="utf-8"))
    candidate_id = json.loads((decision_dir / "next_pass_promotion_decision.json").read_text(encoding="utf-8"))["candidate_id"]
    assert candidate_id in {ref["ref_id"] for ref in run_payload["context_bundle"]["included_refs"]}
    assert overlay["decision_effect"] == "included_in_context"
