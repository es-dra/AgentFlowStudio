from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_next_operator_start_event import NEXT_OPERATOR_START_EVENT_KIND
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_operator_loop_cli_writes_post_check_next_operator_start_event(tmp_path: Path) -> None:
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
            "--write-next-operator-start-event",
            "--next-operator-start-decision",
            "started",
            "--next-operator-start-summary",
            "Next operator received the checked no-provider start packet.",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in result.stdout
    assert "Next operator start packet: ready" in result.stdout
    assert "Next operator start event: operator_started" in result.stdout
    event_path = output_dir / "next_operator_start_event" / "next_operator_start_event.json"
    markdown_path = output_dir / "next_operator_start_event" / "next_operator_start_event.md"
    assert event_path.exists()
    assert markdown_path.exists()

    event = _read_json(event_path)
    manifest = _read_json(output_dir / "production_memory_operator_loop_run.json")
    package_check = _read_json(output_dir / "operator_run_package_check" / "operator_run_package_check.json")
    output_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    post_check_paths = {artifact["path"] for artifact in manifest["post_check_artifacts"]}
    checked_package_paths = {item["path"] for item in package_check["checked_items"]}

    assert event["kind"] == NEXT_OPERATOR_START_EVENT_KIND
    assert event["event_status"] == "operator_started"
    assert event["start_decision"] == "started"
    assert event["source_start_packet_status"] == "ready"
    assert event["source_ready_for_next_operator"] is True
    assert event["start_event_is_acceptance"] is False
    assert event["start_event_is_execution"] is False
    assert event["start_event_is_memory"] is False
    assert event["provider_calls_started"] is False
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
    assert manifest["next_operator_start_event"]["event_status"] == "operator_started"
    assert manifest["next_operator_start_event"]["path"] == "next_operator_start_event/next_operator_start_event.json"
    assert manifest["next_operator_start_event"]["start_event_is_acceptance"] is False
    assert "next_operator_start_event/next_operator_start_event.json" in post_check_paths
    assert "next_operator_start_event/next_operator_start_event.md" in post_check_paths
    assert "next_operator_start_event/next_operator_start_event.json" not in output_paths
    assert "next_operator_start_event/next_operator_start_event.json" not in checked_package_paths


def test_operator_loop_writer_requires_start_packet_for_start_event(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    with pytest.raises(ValueError, match="write_next_operator_start_event requires write_next_operator_start_packet"):
        write_production_memory_operator_loop_run(
            result,
            tmp_path / "operator_loop",
            write_run_package=True,
            write_run_package_check=True,
            write_next_operator_start_event=True,
            next_operator_start_event_decision="started",
            next_operator_start_event_summary="Next operator received the checked no-provider start packet.",
        )


def test_operator_loop_writer_requires_start_event_summary(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    with pytest.raises(ValueError, match="next_operator_start_event_summary is required"):
        write_production_memory_operator_loop_run(
            result,
            tmp_path / "operator_loop",
            write_run_package=True,
            write_run_package_check=True,
            write_next_operator_start_packet=True,
            write_next_operator_start_event=True,
            next_operator_start_event_decision="started",
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
