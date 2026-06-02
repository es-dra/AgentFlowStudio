from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from agentflow.memory.production_operator_start_packet import NEXT_OPERATOR_START_PACKET_KIND


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_operator_loop_cli_writes_post_check_next_operator_start_packet(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-03T10:00:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--draft-next-pass-result",
            "--write-run-package",
            "--write-run-package-check",
            "--write-next-operator-start-packet",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in result.stdout
    assert "Operator run package check: passed" in result.stdout
    assert "Next operator start packet: ready" in result.stdout
    packet_path = output_dir / "next_operator_start_packet" / "next_operator_start_packet.json"
    markdown_path = output_dir / "next_operator_start_packet" / "next_operator_start_packet.md"
    assert packet_path.exists()
    assert markdown_path.exists()

    packet = _read_json(packet_path)
    manifest = _read_json(output_dir / "production_memory_operator_loop_run.json")
    package_check = _read_json(output_dir / "operator_run_package_check" / "operator_run_package_check.json")
    output_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    post_check_paths = {artifact["path"] for artifact in manifest["post_check_artifacts"]}
    checked_package_paths = {item["path"] for item in package_check["checked_items"]}

    assert packet["kind"] == NEXT_OPERATOR_START_PACKET_KIND
    assert packet["start_packet_status"] == "ready"
    assert packet["ready_for_next_operator"] is True
    assert packet["package_check_status"] == "passed"
    assert packet["checked_package_item_count"] == 18
    assert packet["provider_calls_started"] is False
    assert packet["writes_long_term_memory"] is False
    assert packet["writes_company_kb"] is False
    assert manifest["next_operator_start_packet"]["start_packet_status"] == "ready"
    assert manifest["next_operator_start_packet"]["path"] == "next_operator_start_packet/next_operator_start_packet.json"
    assert "next_operator_start_packet/next_operator_start_packet.json" in post_check_paths
    assert "next_operator_start_packet/next_operator_start_packet.md" in post_check_paths
    assert "next_operator_start_packet/next_operator_start_packet.json" not in output_paths
    assert "next_operator_start_packet/next_operator_start_packet.json" not in checked_package_paths


def test_operator_loop_writer_requires_run_package_check_for_start_packet(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    with pytest.raises(ValueError, match="write_next_operator_start_packet requires write_run_package_check"):
        write_production_memory_operator_loop_run(
            result,
            tmp_path / "operator_loop",
            write_run_package=True,
            write_next_operator_start_packet=True,
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
