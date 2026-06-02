from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from agentflow.memory.production_operator_manifest_check import OPERATOR_MANIFEST_CHECK_KIND


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_operator_loop_writer_can_emit_manifest_check_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T16:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    written_paths = write_production_memory_operator_loop_run(result, output_dir, write_manifest_check=True)

    check_path = output_dir / "operator_manifest_check" / "operator_manifest_check.json"
    assert check_path in written_paths
    assert check_path.exists()
    check = json.loads(check_path.read_text(encoding="utf-8"))
    assert check["kind"] == OPERATOR_MANIFEST_CHECK_KIND
    assert check["check_status"] == "passed"
    assert check["checked_ref_count"] == 15
    assert check["missing_refs"] == []
    assert result["operator_manifest_check"]["check_status"] == "passed"


def test_operator_loop_cli_can_write_manifest_check_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-02T16:00:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--draft-next-pass-result",
            "--write-manifest-check",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in result.stdout
    assert "Operator manifest check: passed" in result.stdout
    assert (output_dir / "operator_manifest_check" / "operator_manifest_check.json").exists()
