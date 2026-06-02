from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import build_acceptance_feedback_candidate_packet
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    build_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from agentflow.memory.production_operator_start_packet import (
    NEXT_OPERATOR_START_PACKET_KIND,
    build_next_operator_start_packet,
    build_next_operator_start_packet_from_check_path,
    render_next_operator_start_packet_markdown,
    write_next_operator_start_packet_report,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_next_operator_start_packet_builds_from_passed_run_package_check(tmp_path: Path) -> None:
    output_root = _operator_loop_with_run_package_check(tmp_path)
    check_path = output_root / "operator_run_package_check" / "operator_run_package_check.json"

    packet = build_next_operator_start_packet_from_check_path(
        check_path,
        generated_at="2026-06-03T09:30:00+08:00",
    )

    assert packet["kind"] == NEXT_OPERATOR_START_PACKET_KIND
    assert packet["start_packet_status"] == "ready"
    assert packet["ready_for_next_operator"] is True
    assert packet["package_check_status"] == "passed"
    assert packet["package_status"] == "ready"
    assert packet["handoff_status"] == "ready"
    assert packet["next_operator_action"]["action"] == "review_or_complete_next_pass_result"
    assert packet["checked_package_item_count"] == 18
    assert len(packet["checked_package_items"]) == 18
    assert "Do not call remote providers" in packet["operator_prompt"]
    assert packet["provider_calls_started"] is False
    assert packet["writes_long_term_memory"] is False
    assert packet["writes_company_kb"] is False
    assert packet["claim_boundaries"]["human_acceptance"] == "not_claimed"
    assert packet["claim_boundaries"]["business_validation"] == "not_claimed"
    assert packet["claim_boundaries"]["durable_memory"] == "not_written"


def test_next_operator_start_packet_rejects_failed_run_package_check(tmp_path: Path) -> None:
    output_root = _operator_loop_with_run_package_check(tmp_path)
    check_path = output_root / "operator_run_package_check" / "operator_run_package_check.json"
    check = _read_json(check_path)
    check["check_status"] = "failed"
    check["ready_for_handoff"] = False
    check["failed_controls"] = [{"control_id": "package_status_ready", "status": "failed"}]
    _write_json(check_path, check)
    package = _read_json(output_root / "operator_run_package" / "operator_run_package.json")
    handoff = _read_json(output_root / "operator_handoff" / "operator_handoff_packet.json")

    with pytest.raises(ValueError, match="requires passed operator run package check"):
        build_next_operator_start_packet(
            check,
            package,
            handoff,
            generated_at="2026-06-03T09:30:00+08:00",
        )


def test_next_operator_start_packet_writes_json_and_markdown(tmp_path: Path) -> None:
    output_root = _operator_loop_with_run_package_check(tmp_path)
    packet = build_next_operator_start_packet_from_check_path(
        output_root / "operator_run_package_check" / "operator_run_package_check.json",
        generated_at="2026-06-03T09:30:00+08:00",
    )

    written = write_next_operator_start_packet_report(packet, tmp_path / "start_packet")

    json_path = tmp_path / "start_packet" / "next_operator_start_packet.json"
    markdown_path = tmp_path / "start_packet" / "next_operator_start_packet.md"
    assert written == [json_path, markdown_path]
    assert _read_json(json_path)["kind"] == NEXT_OPERATOR_START_PACKET_KIND
    markdown = render_next_operator_start_packet_markdown(packet)
    assert "# Production Memory Next Operator Start Packet" in markdown
    assert "Status: ready" in markdown
    assert "Next operator action: review_or_complete_next_pass_result" in markdown
    assert "Provider calls: not started" in markdown
    assert "Company KB write: disabled" in markdown
    assert "not human acceptance" in markdown


def test_next_operator_start_packet_cli_writes_ready_packet(tmp_path: Path) -> None:
    output_root = _operator_loop_with_run_package_check(tmp_path)
    start_packet_dir = tmp_path / "start_packet"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-next-operator-start-packet",
            str(output_root / "operator_run_package_check" / "operator_run_package_check.json"),
            "--generated-at",
            "2026-06-03T09:30:00+08:00",
            "--output",
            str(start_packet_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Next operator start packet: ready" in result.stdout
    assert "Package check: passed" in result.stdout
    assert "Next operator action: review_or_complete_next_pass_result" in result.stdout
    packet = _read_json(start_packet_dir / "next_operator_start_packet.json")
    assert packet["kind"] == NEXT_OPERATOR_START_PACKET_KIND
    assert (start_packet_dir / "next_operator_start_packet.md").exists()


def test_next_operator_start_packet_cli_rejects_failed_check(tmp_path: Path) -> None:
    output_root = _operator_loop_with_run_package_check(tmp_path)
    check_path = output_root / "operator_run_package_check" / "operator_run_package_check.json"
    check = _read_json(check_path)
    check["check_status"] = "failed"
    check["ready_for_handoff"] = False
    _write_json(check_path, check)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-next-operator-start-packet",
            str(check_path),
            "--generated-at",
            "2026-06-03T09:30:00+08:00",
            "--output",
            str(tmp_path / "start_packet"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "requires passed operator run package check" in result.stderr
    assert not (tmp_path / "start_packet" / "next_operator_start_packet.json").exists()


def test_next_operator_start_packet_preserves_acceptance_feedback_context_summary(tmp_path: Path) -> None:
    output_root = _operator_loop_with_acceptance_feedback_overlay(tmp_path)

    packet = build_next_operator_start_packet_from_check_path(
        output_root / "operator_run_package_check" / "operator_run_package_check.json",
        generated_at="2026-06-03T09:30:00+08:00",
    )

    acceptance_check = packet["acceptance_feedback_candidate_promotion_check"]
    assert packet["next_operator_action"]["action"] == "run_next_ai_task_with_acceptance_feedback_context"
    assert acceptance_check["status"] == "passed"
    assert acceptance_check["decision_effect"] == "included_in_context"
    assert acceptance_check["candidate_included_in_context"] is True
    assert acceptance_check["handoff_matches_package"] is True


def _operator_loop_with_run_package_check(tmp_path: Path) -> Path:
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
    return output_root


def _operator_loop_with_acceptance_feedback_overlay(tmp_path: Path) -> Path:
    seed_root = _operator_loop_with_run_package_check(tmp_path / "seed")
    package_check = _read_json(seed_root / "operator_run_package_check" / "operator_run_package_check.json")
    event = build_production_memory_acceptance_feedback_event(
        package_check,
        decision="accepted",
        summary="Human operator accepted the package for the next production-memory iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T09:05:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T09:10:00+08:00")
    decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable acceptance feedback candidate selected for next-operator context startup.",
        reviewer_role="operator",
        decided_at="2026-06-03T09:15:00+08:00",
    )
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T09:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=decision,
    )
    output_root = tmp_path / "operator_loop_with_acceptance"
    write_production_memory_operator_loop_run(
        result,
        output_root,
        write_run_package=True,
        write_run_package_check=True,
    )
    return output_root


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
