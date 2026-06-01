from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_loop import (
    build_production_memory_loop_run,
    load_production_memory_loop,
)
from agentflow.memory.production_next_context import build_next_context_handoff
from agentflow.memory.production_next_pass_result import (
    NEXT_PASS_RESULT_KIND,
    build_next_pass_result_scaffold,
    write_next_pass_result_scaffold,
)
from agentflow.memory.production_next_pass_review import build_next_pass_review
from agentflow.memory.production_next_task import build_next_task_packet, write_next_task_packet


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _ready_packet() -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at="2026-06-02T03:10:00+08:00")
    return build_next_task_packet(handoff, generated_at="2026-06-02T03:12:00+08:00")


def test_next_pass_result_scaffold_uses_allowed_refs_without_provider_or_feedback() -> None:
    packet = _ready_packet()
    allowed_ids = [ref["ref_id"] for ref in packet["allowed_context_refs"]]

    result = build_next_pass_result_scaffold(
        packet,
        generated_at="2026-06-02T11:00:00+08:00",
        output_ref="next-pass:artifact:operator-draft-001",
        title="Second pass operator draft",
        summary="Operator-supplied scaffold for the second pass.",
        used_context_refs=allowed_ids[:2],
    )

    assert result["kind"] == NEXT_PASS_RESULT_KIND
    assert result["artifact_type"] == NEXT_PASS_RESULT_KIND
    assert result["schema_version"] == packet["schema_version"]
    assert result["task_packet_id"] == packet["task_packet_id"]
    assert result["result_status"] == "scaffolded_for_operator_completion"
    assert result["provider_mode"] == "no-provider"
    assert result["provider_calls_started"] is False
    assert result["writes_long_term_memory"] is False
    assert result["writes_company_kb"] is False
    assert result["feedback_events"] == []
    assert result["output_artifacts"][0]["used_context_refs"] == allowed_ids[:2]
    assert result["output_artifacts"][0]["status"] == "scaffolded"
    assert "not generated content" in result["non_claims"]
    assert "not human acceptance" in result["non_claims"]
    controls = {control["control_id"]: control["status"] for control in result["controls"]}
    assert controls["source_packet_ready"] == "passed"
    assert controls["used_refs_allowed"] == "passed"
    assert controls["provider_calls_not_started"] == "passed"
    assert controls["feedback_not_auto_created"] == "passed"


def test_next_pass_result_scaffold_rejects_blocked_or_unknown_refs() -> None:
    packet = _ready_packet()
    blocked_ref = packet["blocked_refs"][0]["ref_id"]

    with pytest.raises(ValueError, match="used_context_refs must be allowed"):
        build_next_pass_result_scaffold(
            packet,
            generated_at="2026-06-02T11:00:00+08:00",
            used_context_refs=[blocked_ref, "memory:unknown"],
        )


def test_next_pass_result_scaffold_blocks_unready_packet() -> None:
    packet = _ready_packet()
    packet["packet_status"] = "blocked"

    with pytest.raises(ValueError, match="next task packet must be ready"):
        build_next_pass_result_scaffold(packet, generated_at="2026-06-02T11:00:00+08:00")


def test_next_pass_result_scaffold_cli_writes_outputs_and_enters_review(tmp_path: Path) -> None:
    packet_dir = tmp_path / "packet"
    result_dir = tmp_path / "result"
    packet = _ready_packet()
    write_next_task_packet(packet, packet_dir)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-draft-next-pass-result-no-provider",
            str(packet_dir / "next_task_packet.json"),
            "--generated-at",
            "2026-06-02T11:00:00+08:00",
            "--output-ref",
            "next-pass:artifact:operator-draft-001",
            "--title",
            "Second pass operator draft",
            "--summary",
            "Operator-supplied scaffold for the second pass.",
            "--output",
            str(result_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory next pass result scaffold: scaffolded_for_operator_completion" in completed.stdout
    assert "Provider calls: not started" in completed.stdout
    assert "Writes Company KB: false" in completed.stdout
    result = json.loads((result_dir / "next_pass_result.json").read_text(encoding="utf-8"))
    assert result["kind"] == NEXT_PASS_RESULT_KIND
    assert result["feedback_events"] == []
    assert (result_dir / "next_pass_result.md").exists()

    review = build_next_pass_review(packet, result, reviewed_at="2026-06-02T11:10:00+08:00")

    assert review["review_status"] == "ready_for_operator_review"
    assert review["feedback_candidates"] == []
    assert review["provider_calls_started"] is False
