from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_feedback import build_production_memory_feedback_capture
from agentflow.memory.production_loop import build_production_memory_loop_run
from agentflow.memory.production_promotion import (
    build_production_memory_promotion_decision,
    build_reviewed_feedback_run,
)
from agentflow.memory.production_session import build_production_memory_session_report
from agentflow.memory.company_kb_feedback import (
    COMPANY_KB_FEEDBACK_PACKET_KIND,
    build_company_kb_feedback_candidate_packet,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def build_report_with_reviewed_feedback() -> dict:
    loop = load_example()
    capture = build_production_memory_feedback_capture(
        loop,
        target_ref="artifact:approved_storyboard:v1",
        decision="accepted",
        summary="Carry the reviewed storyboard structure into the next pass.",
        reviewer_role="operator",
        created_at="2026-06-02T00:00:00+08:00",
    )
    promotion = build_production_memory_promotion_decision(
        capture,
        decision="promoted",
        rationale="Candidate is traceable to reviewed feedback.",
        reviewer_role="operator",
        decided_at="2026-06-02T00:05:00+08:00",
    )
    _derived_loop, run = build_reviewed_feedback_run(loop, capture, promotion)
    return build_production_memory_session_report(
        run,
        feedback_capture=capture,
        promotion_decision=promotion,
        generated_at="2026-06-02T00:10:00+08:00",
    )


def test_candidate_packet_is_candidate_only_and_does_not_write_company_kb() -> None:
    report = build_report_with_reviewed_feedback()

    packet = build_company_kb_feedback_candidate_packet(
        report,
        generated_at="2026-06-02T00:20:00+08:00",
        source_kb_status="restructuring",
    )

    assert packet["kind"] == COMPANY_KB_FEEDBACK_PACKET_KIND
    assert packet["promotion_status"] == "candidate_only"
    assert packet["requires_human_review"] is True
    assert packet["writes_company_kb"] is False
    assert packet["writes_long_term_memory"] is False
    assert packet["source_kb_status"] == "restructuring"
    assert packet["target"]["write_status"] == "not_written"
    assert packet["target"]["promotion_required"] == "explicit_human_review"
    assert packet["source_report"]["session_id"] == report["session_id"]
    assert len(packet["candidate_items"]) >= 3
    assert all(item["status"] == "candidate" for item in packet["candidate_items"])
    assert all(item["writes_company_kb"] is False for item in packet["candidate_items"])
    assert all(item["requires_human_review"] is True for item in packet["candidate_items"])


def test_candidate_packet_preserves_context_and_claim_boundaries_without_raw_private_paths() -> None:
    report = build_report_with_reviewed_feedback()

    packet = build_company_kb_feedback_candidate_packet(
        report,
        generated_at="2026-06-02T00:20:00+08:00",
    )
    item_ids = {item["candidate_id"] for item in packet["candidate_items"]}
    serialized = json.dumps(packet, ensure_ascii=False)

    assert "company-kb:candidate:context-bundle-audit:v1" in item_ids
    assert "company-kb:candidate:claim-boundary-discipline:v1" in item_ids
    assert "company-kb:candidate:promotion-decision-overlay:v1" in item_ids
    assert packet["context_signal"]["included_ref_count"] == 4
    assert packet["context_signal"]["blocked_ref_count"] == 3
    assert packet["non_claim_boundaries"]["human_acceptance"] == "not_reviewed"
    assert "D:\\" not in serialized
    assert "C:\\" not in serialized
    assert "api_key" not in serialized.lower()
    assert "secret_key" not in serialized.lower()


def test_candidate_packet_rejects_non_session_report_payload() -> None:
    with pytest.raises(ValueError, match="session report"):
        build_company_kb_feedback_candidate_packet(
            {"kind": "not_a_session_report"},
            generated_at="2026-06-02T00:20:00+08:00",
        )


def test_candidate_packet_example_is_registered_candidate_only_contract() -> None:
    example = json.loads(
        Path("examples/agentflow/company_kb_feedback_candidate_packet.example.json").read_text(encoding="utf-8")
    )
    registry = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))
    registered_types = {contract["artifact_type"] for contract in registry["contracts"]}
    rule_ids = {rule["rule_id"] for rule in registry["validation_rules"]}

    assert example["kind"] == COMPANY_KB_FEEDBACK_PACKET_KIND
    assert example["artifact_type"] == COMPANY_KB_FEEDBACK_PACKET_KIND
    assert example["schema_version"] == "company-kb-feedback-candidate-packet/v1"
    assert example["promotion_status"] == "candidate_only"
    assert example["requires_human_review"] is True
    assert example["writes_company_kb"] is False
    assert example["writes_long_term_memory"] is False
    assert example["target"]["write_status"] == "not_written"
    assert example["target"]["promotion_required"] == "explicit_human_review"
    assert example["candidate_items"]
    assert all(item["status"] == "candidate" for item in example["candidate_items"])
    assert COMPANY_KB_FEEDBACK_PACKET_KIND in registered_types
    assert "company_kb_feedback_candidates_not_written" in rule_ids


@pytest.mark.legacy(reason="production-memory CLI surface is retired from the product command registry")
def test_cli_company_kb_feedback_candidate_packet_writes_json_and_markdown(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    report_dir = tmp_path / "report"
    packet_dir = tmp_path / "company_kb_packet"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-no-provider",
            str(EXAMPLE_PATH),
            "--output",
            str(run_dir),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-session-report",
            str(run_dir / "production_memory_loop_run.json"),
            "--generated-at",
            "2026-06-02T00:10:00+08:00",
            "--output",
            str(report_dir),
        ],
        check=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-company-kb-candidates",
            str(report_dir / "production_memory_session_report.json"),
            "--generated-at",
            "2026-06-02T00:20:00+08:00",
            "--source-kb-status",
            "restructuring",
            "--output",
            str(packet_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Company KB feedback candidates: candidate_only" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    assert "Requires human review: true" in result.stdout
    packet = json.loads((packet_dir / "company_kb_feedback_candidate_packet.json").read_text(encoding="utf-8"))
    markdown = (packet_dir / "company_kb_feedback_candidate_packet.md").read_text(encoding="utf-8")
    assert packet["kind"] == COMPANY_KB_FEEDBACK_PACKET_KIND
    assert packet["source_kb_status"] == "restructuring"
    assert "Do not auto-promote" in markdown
    assert "Writes Company KB: false" in markdown
