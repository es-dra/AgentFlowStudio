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
from agentflow.memory.production_operator_start_packet import build_next_operator_start_packet_from_check_path
from agentflow.memory.production_next_operator_start_event import (
    NEXT_OPERATOR_START_EVENT_KIND,
    build_next_operator_start_event,
    load_next_operator_start_event,
    render_next_operator_start_event_markdown,
    write_next_operator_start_event_report,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_next_operator_start_event_records_started_packet_without_claiming_acceptance(tmp_path: Path) -> None:
    packet = _next_operator_start_packet(tmp_path)

    event = build_next_operator_start_event(
        packet,
        decision="started",
        summary="Next operator received the start packet and began the recorded action.",
        operator_role="next_operator",
        recorded_at="2026-06-03T09:45:00+08:00",
    )

    assert event["kind"] == NEXT_OPERATOR_START_EVENT_KIND
    assert event["event_status"] == "operator_started"
    assert event["start_decision"] == "started"
    assert event["source_start_packet_status"] == "ready"
    assert event["source_ready_for_next_operator"] is True
    assert event["source_next_operator_action"] == "review_or_complete_next_pass_result"
    assert event["operator_prompt_excerpt"]
    assert len(event["start_requirements"]) == 5
    assert event["provider_calls_started"] is False
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
    assert event["start_event_is_memory"] is False
    assert event["start_event_is_acceptance"] is False
    assert event["start_event_is_execution"] is False
    assert event["creates_memory_candidate"] is False
    assert event["creates_promotion_decision"] is False
    assert event["claim_boundaries"]["human_acceptance"] == "not_claimed"
    assert event["claim_boundaries"]["next_pass_execution"] == "not_claimed"
    assert "not human acceptance" in event["non_claims"]
    assert "not next-pass execution result" in event["non_claims"]


def test_next_operator_start_event_rejects_started_decision_for_blocked_packet(tmp_path: Path) -> None:
    packet = _next_operator_start_packet(tmp_path)
    packet["start_packet_status"] = "blocked"
    packet["ready_for_next_operator"] = False
    packet["blocked_items"] = [{"ref": "operator_run_package_check", "reason": "not ready"}]

    with pytest.raises(ValueError, match="started start event requires ready next operator start packet"):
        build_next_operator_start_event(
            packet,
            decision="started",
            summary="Start was attempted before the packet was ready.",
            operator_role="next_operator",
            recorded_at="2026-06-03T09:45:00+08:00",
        )


def test_next_operator_start_event_records_blocked_packet_without_memory_promotion(tmp_path: Path) -> None:
    packet = _next_operator_start_packet(tmp_path)
    packet["start_packet_status"] = "blocked"
    packet["ready_for_next_operator"] = False
    packet["blocked_items"] = [{"ref": "operator_run_package_check", "reason": "not ready"}]

    event = build_next_operator_start_event(
        packet,
        decision="blocked",
        summary="Next operator could not start because the start packet was not ready.",
        operator_role="next_operator",
        recorded_at="2026-06-03T09:45:00+08:00",
    )

    assert event["event_status"] == "start_blocked"
    assert event["source_ready_for_next_operator"] is False
    assert event["source_blocked_items"] == packet["blocked_items"]
    assert event["start_event_is_memory"] is False
    assert event["creates_memory_candidate"] is False
    assert event["claim_boundaries"]["memory_promotion"] == "not_performed"


def test_next_operator_start_event_writes_json_and_markdown(tmp_path: Path) -> None:
    packet = _next_operator_start_packet(tmp_path)
    event = build_next_operator_start_event(
        packet,
        decision="started",
        summary="Next operator received the start packet.",
        operator_role="next_operator",
        recorded_at="2026-06-03T09:45:00+08:00",
    )

    written = write_next_operator_start_event_report(event, tmp_path / "start_event")

    json_path = tmp_path / "start_event" / "next_operator_start_event.json"
    markdown_path = tmp_path / "start_event" / "next_operator_start_event.md"
    assert written == [json_path, markdown_path]
    assert _read_json(json_path)["kind"] == NEXT_OPERATOR_START_EVENT_KIND
    markdown = render_next_operator_start_event_markdown(event)
    assert "# Production Memory Next Operator Start Event" in markdown
    assert "Decision: started" in markdown
    assert "Human acceptance: not_claimed" in markdown
    assert "Next-pass execution: not_claimed" in markdown
    assert "Provider calls: not started" in markdown


def test_next_operator_start_event_cli_writes_started_event(tmp_path: Path) -> None:
    packet = _next_operator_start_packet(tmp_path)
    packet_path = tmp_path / "next_operator_start_packet.json"
    _write_json(packet_path, packet)
    output_dir = tmp_path / "start_event"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-record-next-operator-start",
            str(packet_path),
            "--decision",
            "started",
            "--summary",
            "Next operator received the start packet.",
            "--operator-role",
            "next_operator",
            "--recorded-at",
            "2026-06-03T09:45:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Next operator start event: operator_started" in result.stdout
    assert "Human acceptance: not claimed" in result.stdout
    assert "Next-pass execution: not claimed" in result.stdout
    assert "Provider calls: not started" in result.stdout
    event = load_next_operator_start_event(output_dir / "next_operator_start_event.json")
    assert event["kind"] == NEXT_OPERATOR_START_EVENT_KIND
    assert (output_dir / "next_operator_start_event.md").exists()


def _next_operator_start_packet(tmp_path: Path) -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T09:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    output_root = tmp_path / "operator_loop"
    write_production_memory_operator_loop_run(
        result,
        output_root,
        write_run_package=True,
        write_run_package_check=True,
    )
    return build_next_operator_start_packet_from_check_path(
        output_root / "operator_run_package_check" / "operator_run_package_check.json",
        generated_at="2026-06-03T09:30:00+08:00",
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
