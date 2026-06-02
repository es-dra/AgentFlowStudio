from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_next_operator_action_result import (
    NEXT_OPERATOR_ACTION_RESULT_KIND,
    build_next_operator_action_result,
)
from agentflow.memory.production_next_operator_start_event import build_next_operator_start_event
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_next_operator_action_result_cli_records_completed_result(tmp_path: Path) -> None:
    event_path = _write_started_event(tmp_path)
    output_dir = tmp_path / "action_result"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-record-next-operator-action-result",
            str(event_path),
            "--decision",
            "completed",
            "--summary",
            "Next operator completed the recorded action and produced a local result ref.",
            "--result-ref",
            "next_pass_result/next_pass_result.json",
            "--operator-role",
            "next_operator",
            "--recorded-at",
            "2026-06-03T10:30:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Next operator action result: action_completed" in result.stdout
    assert "Next-pass execution: not claimed" in result.stdout
    result_path = output_dir / "next_operator_action_result.json"
    markdown_path = output_dir / "next_operator_action_result.md"
    assert result_path.exists()
    assert markdown_path.exists()

    action_result = _read_json(result_path)
    assert action_result["kind"] == NEXT_OPERATOR_ACTION_RESULT_KIND
    assert action_result["result_status"] == "action_completed"
    assert action_result["action_decision"] == "completed"
    assert action_result["source_start_event_status"] == "operator_started"
    assert action_result["source_next_operator_action"] == "review_or_complete_next_pass_result"
    assert action_result["result_refs"] == ["next_pass_result/next_pass_result.json"]
    assert action_result["provider_calls_started"] is False
    assert action_result["writes_long_term_memory"] is False
    assert action_result["writes_company_kb"] is False
    assert action_result["action_result_is_acceptance"] is False
    assert action_result["action_result_is_execution"] is False
    assert action_result["action_result_is_memory"] is False
    assert action_result["creates_memory_candidate"] is False
    assert action_result["creates_promotion_decision"] is False


def test_completed_action_result_requires_started_start_event(tmp_path: Path) -> None:
    blocked_event = _blocked_start_event(tmp_path)

    with pytest.raises(ValueError, match="completed action result requires started next operator start event"):
        build_next_operator_action_result(
            blocked_event,
            decision="completed",
            summary="Attempted completion from a blocked start event.",
            result_refs=["next_pass_result/next_pass_result.json"],
            operator_role="next_operator",
            recorded_at="2026-06-03T10:30:00+08:00",
        )


def test_completed_action_result_requires_result_refs(tmp_path: Path) -> None:
    event = _read_json(_write_started_event(tmp_path))

    with pytest.raises(ValueError, match="completed action result requires result_refs"):
        build_next_operator_action_result(
            event,
            decision="completed",
            summary="Completion without result refs should stay blocked.",
            operator_role="next_operator",
            recorded_at="2026-06-03T10:30:00+08:00",
        )


def _write_started_event(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    output_dir = tmp_path / "operator_loop"
    write_production_memory_operator_loop_run(
        result,
        output_dir,
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
        write_next_operator_start_event=True,
        next_operator_start_event_decision="started",
        next_operator_start_event_summary="Next operator received the checked no-provider start packet.",
    )
    return output_dir / "next_operator_start_event" / "next_operator_start_event.json"


def _blocked_start_event(tmp_path: Path) -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    output_dir = tmp_path / "operator_loop_blocked"
    write_production_memory_operator_loop_run(
        result,
        output_dir,
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
    )
    start_packet = _read_json(output_dir / "next_operator_start_packet" / "next_operator_start_packet.json")
    return build_next_operator_start_event(
        start_packet,
        decision="blocked",
        summary="Next operator start was blocked before action execution.",
        operator_role="next_operator",
        recorded_at="2026-06-03T10:20:00+08:00",
        start_packet_path="next_operator_start_packet/next_operator_start_packet.json",
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
