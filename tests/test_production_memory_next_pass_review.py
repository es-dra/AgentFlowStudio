from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import (
    build_production_memory_loop_run,
    load_production_memory_loop,
)
from agentflow.memory.production_next_context import build_next_context_handoff
from agentflow.memory.production_next_pass_review import (
    NEXT_PASS_RESULT_KIND,
    NEXT_PASS_REVIEW_KIND,
    build_next_pass_review,
    write_next_pass_review,
)
from agentflow.memory.production_next_task import build_next_task_packet, write_next_task_packet


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _ready_packet() -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at="2026-06-02T03:10:00+08:00")
    return build_next_task_packet(handoff, generated_at="2026-06-02T03:12:00+08:00")


def _result_for(packet: dict, *, used_refs: list[str] | None = None, provider_calls_started: bool = False) -> dict:
    allowed_id = packet["allowed_context_refs"][0]["ref_id"]
    return {
        "kind": NEXT_PASS_RESULT_KIND,
        "artifact_type": NEXT_PASS_RESULT_KIND,
        "schema_version": packet["schema_version"],
        "task_packet_id": packet["task_packet_id"],
        "provider_mode": "no-provider",
        "provider_calls_started": provider_calls_started,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "output_artifacts": [
            {
                "ref_id": "next-pass:artifact:draft-001",
                "title": "Second pass draft",
                "status": "draft",
                "used_context_refs": used_refs or [allowed_id],
            }
        ],
        "feedback_events": [
            {
                "feedback_id": "feedback:next-pass-001",
                "target_ref": "next-pass:artifact:draft-001",
                "decision": "needs_revision",
                "summary": "Second pass needs operator review before any memory promotion.",
            }
        ],
    }


def test_next_pass_review_accepts_only_allowed_context_refs_without_promoting_memory() -> None:
    packet = _ready_packet()
    allowed_ids = {ref["ref_id"] for ref in packet["allowed_context_refs"]}

    review = build_next_pass_review(
        packet,
        _result_for(packet, used_refs=sorted(allowed_ids)[:2]),
        reviewed_at="2026-06-02T03:30:00+08:00",
    )

    used_ids = {ref["ref_id"] for ref in review["used_allowed_refs"]}
    assert review["kind"] == NEXT_PASS_REVIEW_KIND
    assert review["review_status"] == "ready_for_operator_review"
    assert review["provider_mode"] == "no-provider"
    assert review["provider_calls_started"] is False
    assert review["writes_long_term_memory"] is False
    assert review["writes_company_kb"] is False
    assert used_ids <= allowed_ids
    assert review["blocked_or_unknown_refs"] == []
    assert review["feedback_candidates"]
    assert review["feedback_candidates"][0]["candidate_is_promoted_memory"] is False
    assert review["feedback_candidates"][0]["requires_promotion_decision"] is True
    assert review["promotion_decision_templates"][0]["decision"] == "pending"
    assert review["promotion_decision_templates"][0]["template_only"] is True
    assert "not durable memory" in review["non_claims"]
    controls = {control["control_id"]: control["status"] for control in review["controls"]}
    assert controls["source_packet_ready"] == "passed"
    assert controls["no_blocked_or_unknown_context_refs_used"] == "passed"
    assert controls["feedback_candidate_only"] == "passed"


def test_next_pass_review_blocks_blocked_context_ref_usage() -> None:
    packet = _ready_packet()
    blocked_id = packet["blocked_refs"][0]["ref_id"]

    review = build_next_pass_review(
        packet,
        _result_for(packet, used_refs=[blocked_id]),
        reviewed_at="2026-06-02T03:30:00+08:00",
    )

    assert review["review_status"] == "blocked"
    assert review["blocked_or_unknown_refs"] == [
        {
            "ref_id": blocked_id,
            "output_ref": "next-pass:artifact:draft-001",
            "reason": "blocked_ref_used",
        }
    ]
    controls = {control["control_id"]: control["status"] for control in review["controls"]}
    assert controls["no_blocked_or_unknown_context_refs_used"] == "failed"


def test_next_pass_review_blocks_unknown_context_ref_usage() -> None:
    packet = _ready_packet()

    review = build_next_pass_review(
        packet,
        _result_for(packet, used_refs=["memory:unknown"]),
        reviewed_at="2026-06-02T03:30:00+08:00",
    )

    assert review["review_status"] == "blocked"
    assert review["blocked_or_unknown_refs"] == [
        {
            "ref_id": "memory:unknown",
            "output_ref": "next-pass:artifact:draft-001",
            "reason": "unknown_ref_used",
        }
    ]


def test_next_pass_review_blocks_provider_started_result() -> None:
    packet = _ready_packet()

    review = build_next_pass_review(
        packet,
        _result_for(packet, provider_calls_started=True),
        reviewed_at="2026-06-02T03:30:00+08:00",
    )

    assert review["review_status"] == "blocked"
    controls = {control["control_id"]: control["status"] for control in review["controls"]}
    assert controls["provider_calls_not_started"] == "failed"


def test_next_pass_review_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    packet_dir = tmp_path / "packet"
    result_path = tmp_path / "next_pass_result.json"
    output_dir = tmp_path / "review"
    packet = _ready_packet()
    write_next_task_packet(packet, packet_dir)
    result_path.write_text(json.dumps(_result_for(packet), indent=2), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-review-next-pass",
            str(packet_dir / "next_task_packet.json"),
            str(result_path),
            "--reviewed-at",
            "2026-06-02T03:30:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory next pass review: ready_for_operator_review" in result.stdout
    assert "Provider calls: not started" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    review = json.loads((output_dir / "next_pass_review.json").read_text(encoding="utf-8"))
    assert review["kind"] == NEXT_PASS_REVIEW_KIND
    assert (output_dir / "next_pass_review.md").exists()
