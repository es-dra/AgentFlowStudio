from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import (
    build_production_memory_loop_run,
    load_production_memory_loop,
)
from agentflow.memory.production_next_context import build_next_context_handoff, write_next_context_handoff
from agentflow.memory.production_next_task import (
    NEXT_TASK_PACKET_KIND,
    build_next_task_packet,
    write_next_task_packet,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _ready_handoff() -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    return build_next_context_handoff(run, generated_at="2026-06-02T03:10:00+08:00")


def test_next_task_packet_consumes_ready_handoff_without_promoting_or_executing() -> None:
    handoff = _ready_handoff()

    packet = build_next_task_packet(handoff, generated_at="2026-06-02T03:12:00+08:00")

    included_ids = {ref["ref_id"] for ref in handoff["next_context_refs"]}
    blocked_ids = {ref["ref_id"] for ref in handoff["blocked_refs"]}
    packet_ids = {ref["ref_id"] for ref in packet["allowed_context_refs"]}

    assert packet["kind"] == NEXT_TASK_PACKET_KIND
    assert packet["packet_status"] == "ready"
    assert packet["provider_mode"] == "no-provider"
    assert packet["provider_calls_started"] is False
    assert packet["writes_long_term_memory"] is False
    assert packet["writes_company_kb"] is False
    assert packet_ids == included_ids
    assert not (packet_ids & blocked_ids)
    assert packet["blocked_refs"] == handoff["blocked_refs"]
    assert packet["source_handoff_id"] == handoff["handoff_id"]
    assert "Use only allowed_context_refs" in packet["task_instructions"]
    assert "Do not use blocked_refs" in packet["task_instructions"]
    assert "feedback is not memory" in packet["task_instructions"]
    assert "memory candidate is not promoted memory" in packet["task_instructions"]
    assert "not human acceptance" in packet["non_claims"]
    assert "not business validation" in packet["non_claims"]
    controls = {control["control_id"]: control["status"] for control in packet["controls"]}
    assert controls["handoff_ready"] == "passed"
    assert controls["next_context_refs_present"] == "passed"
    assert controls["blocked_refs_excluded"] == "passed"
    assert controls["provider_calls_not_started"] == "passed"
    assert controls["company_kb_write_disabled"] == "passed"


def test_next_task_packet_blocks_unready_handoff() -> None:
    handoff = _ready_handoff()
    handoff["handoff_status"] = "blocked"

    packet = build_next_task_packet(handoff, generated_at="2026-06-02T03:12:00+08:00")

    assert packet["packet_status"] == "blocked"
    assert packet["allowed_context_refs"] == []
    assert len(packet["blocked_refs"]) >= len(handoff["blocked_refs"])
    assert any(ref["ref_id"] == "handoff:blocked" for ref in packet["blocked_refs"])
    controls = {control["control_id"]: control["status"] for control in packet["controls"]}
    assert controls["handoff_ready"] == "failed"
    assert "Resolve handoff blockers" in packet["task_instructions"]


def test_next_task_packet_writes_json_and_markdown(tmp_path: Path) -> None:
    packet = build_next_task_packet(_ready_handoff(), generated_at="2026-06-02T03:12:00+08:00")

    written = write_next_task_packet(packet, tmp_path)

    assert tmp_path / "next_task_packet.json" in written
    assert tmp_path / "next_task_packet.md" in written
    markdown = (tmp_path / "next_task_packet.md").read_text(encoding="utf-8")
    assert "Next Task Packet" in markdown
    assert "Allowed context refs" in markdown
    assert "Blocked refs" in markdown
    assert "Provider calls: not started" in markdown
    assert "Company KB write: disabled" in markdown


def test_next_task_packet_cli_reads_handoff_and_writes_outputs(tmp_path: Path) -> None:
    handoff_dir = tmp_path / "handoff"
    output_dir = tmp_path / "task"
    write_next_context_handoff(_ready_handoff(), handoff_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-next-task-packet",
            str(handoff_dir / "next_context_handoff.json"),
            "--generated-at",
            "2026-06-02T03:12:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory next task packet: ready" in result.stdout
    assert "Provider calls: not started" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    packet = json.loads((output_dir / "next_task_packet.json").read_text(encoding="utf-8"))
    assert packet["kind"] == NEXT_TASK_PACKET_KIND
    assert (output_dir / "next_task_packet.md").exists()
