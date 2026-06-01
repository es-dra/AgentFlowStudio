from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import (
    build_production_memory_loop_run,
    load_production_memory_loop,
    write_production_memory_loop_run,
)
from agentflow.memory.production_next_context import (
    NEXT_CONTEXT_HANDOFF_KIND,
    build_next_context_handoff,
    write_next_context_handoff,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_next_context_handoff_uses_only_included_refs_and_records_blocked_refs() -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)

    handoff = build_next_context_handoff(run, generated_at="2026-06-02T01:40:00+08:00")

    included_ids = {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    blocked_ids = {ref["ref_id"] for ref in run["context_bundle"]["blocked_refs"]}
    handoff_ids = {ref["ref_id"] for ref in handoff["next_context_refs"]}

    assert handoff["kind"] == NEXT_CONTEXT_HANDOFF_KIND
    assert handoff["handoff_status"] == "ready"
    assert handoff["provider_mode"] == "no-provider"
    assert handoff["provider_calls_started"] is False
    assert handoff["writes_long_term_memory"] is False
    assert handoff["writes_company_kb"] is False
    assert handoff_ids == included_ids
    assert not (handoff_ids & blocked_ids)
    assert {ref["ref_id"] for ref in handoff["blocked_refs"]} == blocked_ids
    assert "Use only the listed next_context_refs" in handoff["task_prompt"]
    assert "Do not use blocked_refs" in handoff["task_prompt"]
    assert "not human acceptance" in handoff["non_claims"]
    assert "not business validation" in handoff["non_claims"]
    assert "not durable Memory OS" in handoff["non_claims"]
    assert "not provider success" in handoff["non_claims"]
    controls = {control["control_id"]: control["status"] for control in handoff["controls"]}
    assert controls["blocked_refs_excluded"] == "passed"
    assert controls["provider_calls_not_started"] == "passed"
    assert controls["long_term_memory_write_disabled"] == "passed"
    assert controls["company_kb_write_disabled"] == "passed"


def test_next_context_handoff_writes_json_and_markdown(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at="2026-06-02T01:40:00+08:00")

    written = write_next_context_handoff(handoff, tmp_path)

    assert tmp_path / "next_context_handoff.json" in written
    assert tmp_path / "next_context_handoff.md" in written
    markdown = (tmp_path / "next_context_handoff.md").read_text(encoding="utf-8")
    assert "Next Context Handoff" in markdown
    assert "Included refs" in markdown
    assert "Blocked refs" in markdown
    assert "No-provider" in markdown
    assert "Company KB write: disabled" in markdown


def test_next_context_handoff_cli_reads_run_artifact_and_writes_outputs(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    run_dir = tmp_path / "run"
    output_dir = tmp_path / "handoff"
    write_production_memory_loop_run(run, run_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-next-context-handoff",
            str(run_dir / "production_memory_loop_run.json"),
            "--generated-at",
            "2026-06-02T01:40:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory next context handoff: ready" in result.stdout
    assert "Provider calls: not started" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    handoff = json.loads((output_dir / "next_context_handoff.json").read_text(encoding="utf-8"))
    assert handoff["kind"] == NEXT_CONTEXT_HANDOFF_KIND
    assert (output_dir / "next_context_handoff.md").exists()
