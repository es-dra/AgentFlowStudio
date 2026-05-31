from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.contracts.examples import AGENTFLOW_EXAMPLE_PATHS, AGENTFLOW_EXAMPLE_TYPES
from agentflow.memory.loulan_decision_intake import (
    build_loulan_decision_intake_report,
    write_loulan_decision_intake_report,
)
from agentflow.memory.loulan_decision_review_pack import build_loulan_decision_review_pack
from agentflow.memory.loulan_decision_worksheet import build_loulan_decision_worksheet
from tests.test_loulan_decision_review_pack import _review_and_template


def test_loulan_decision_intake_reports_ready_filled_decisions(tmp_path: Path) -> None:
    worksheet, decisions = _worksheet_and_template(tmp_path)
    decisions["decisions"] = [
        _filled_decision(row, row["allowed_decisions"][0], ["evidence-ref"])
        for row in worksheet["decision_rows"]
    ]

    report = build_loulan_decision_intake_report(
        worksheet,
        decisions,
        created_at="2026-06-01T18:00:00+08:00",
    )

    assert report["artifact_type"] == "agentflow_loulan_decision_intake_report"
    assert report["provider_calls_started"] is False
    assert report["writes_long_term_memory"] is False
    assert report["human_acceptance_recorded"] is False
    assert report["intake_status"] == "ready_for_context_bundle"
    assert report["context_bundle_command_ready"] is True
    assert report["intake_summary"] == {
        "required_decisions": 3,
        "submitted_decisions": 3,
        "ready_count": 3,
        "pending_count": 0,
        "missing_count": 0,
        "invalid_count": 0,
        "unexpected_count": 0,
        "reusable_count": 3,
        "blocked_count": 0,
    }
    assert {row["intake_status"] for row in report["decision_rows"]} == {"ready_for_context_bundle"}
    assert report["next_action"] == "run_loulan_context_bundle_with_validated_decisions"
    assert report["claim_boundaries"]["human_acceptance"] == "decision_file_validated_not_product_acceptance"


def test_loulan_decision_intake_blocks_pending_manual_fields(tmp_path: Path) -> None:
    worksheet, decisions = _worksheet_and_template(tmp_path)

    report = build_loulan_decision_intake_report(
        worksheet,
        decisions,
        created_at="2026-06-01T18:00:00+08:00",
    )

    assert report["intake_status"] == "blocked_pending_manual_decisions"
    assert report["context_bundle_command_ready"] is False
    assert report["intake_summary"]["pending_count"] == 3
    assert report["decision_rows"][0]["reason"] == "pending_manual_decision"
    assert report["next_action"] == "fix_manual_decisions_before_context_bundle"


def test_loulan_decision_intake_blocks_invalid_and_unexpected_decisions(tmp_path: Path) -> None:
    worksheet, decisions = _worksheet_and_template(tmp_path)
    first, second, third = worksheet["decision_rows"]
    decisions["decisions"] = [
        _filled_decision(first, first["allowed_decisions"][0], ["evidence-ref"]),
        _filled_decision(second, "not_allowed", ["evidence-ref"]),
        _filled_decision(third, third["allowed_decisions"][0], []),
        {
            "decision_id": "unexpected_decision",
            "target_ref": "shot:UNEXPECTED",
            "decision": "approve_anchor",
            "allowed_decisions": ["approve_anchor"],
            "decided_by": "human",
            "evidence_refs": ["evidence-ref"],
            "review_note": "unexpected",
        },
    ]

    report = build_loulan_decision_intake_report(
        worksheet,
        decisions,
        created_at="2026-06-01T18:00:00+08:00",
    )

    assert report["intake_status"] == "blocked_invalid_decisions"
    assert report["intake_summary"]["invalid_count"] == 2
    assert report["intake_summary"]["unexpected_count"] == 1
    assert report["unexpected_decision_refs"] == ["shot:UNEXPECTED"]
    assert {row["reason"] for row in report["decision_rows"]} >= {
        "invalid_decision_value",
        "missing_evidence_refs",
    }


def test_loulan_decision_intake_rejects_worksheet_as_decisions(tmp_path: Path) -> None:
    worksheet, _decisions = _worksheet_and_template(tmp_path)

    try:
        build_loulan_decision_intake_report(
            worksheet,
            worksheet,
            created_at="2026-06-01T18:00:00+08:00",
        )
    except ValueError as exc:
        assert "requires decisions artifact_type agentflow_loulan_promotion_decisions" in str(exc)
    else:
        raise AssertionError("expected worksheet-as-decisions to be rejected")


def test_loulan_decision_intake_cli_writes_artifacts(tmp_path: Path) -> None:
    worksheet, decisions = _worksheet_and_template(tmp_path)
    worksheet_path = tmp_path / "worksheet.json"
    decisions_path = tmp_path / "decisions.json"
    worksheet_path.write_text(json.dumps(worksheet, ensure_ascii=False, indent=2), encoding="utf-8")
    decisions_path.write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "decision_intake"

    result = CliRunner().invoke(
        app,
        [
            "loulan-decision-intake",
            "--decision-worksheet",
            str(worksheet_path),
            "--decisions",
            str(decisions_path),
            "--created-at",
            "2026-06-01T18:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan decision intake" in result.output
    assert "Status: blocked_pending_manual_decisions" in result.output
    assert "Human acceptance: not recorded" in result.output
    assert "Provider calls: not started" in result.output
    assert (output / "loulan_decision_intake_report.json").is_file()
    assert (output / "loulan_decision_intake_report.md").is_file()


def test_loulan_decision_intake_write_returns_artifacts(tmp_path: Path) -> None:
    worksheet, decisions = _worksheet_and_template(tmp_path)
    report = build_loulan_decision_intake_report(
        worksheet,
        decisions,
        created_at="2026-06-01T18:00:00+08:00",
    )

    paths = write_loulan_decision_intake_report(report, tmp_path / "out")

    assert {path.name for path in paths} == {
        "loulan_decision_intake_report.json",
        "loulan_decision_intake_report.md",
    }


def test_loulan_decision_intake_contract_example_is_registered() -> None:
    example_path = Path("examples/agentflow/loulan_decision_intake_report.example.json")
    payload = json.loads(example_path.read_text(encoding="utf-8"))
    registry = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    assert example_path in AGENTFLOW_EXAMPLE_PATHS
    assert "agentflow_loulan_decision_intake_report" in AGENTFLOW_EXAMPLE_TYPES
    assert payload["artifact_type"] == "agentflow_loulan_decision_intake_report"
    assert payload["intake_status"] == "blocked_pending_manual_decisions"
    assert payload["context_bundle_command_ready"] is False
    assert payload["human_acceptance_recorded"] is False
    assert payload["writes_long_term_memory"] is False
    assert "agentflow_loulan_decision_intake_report" in {
        contract["artifact_type"] for contract in registry["contracts"]
    }
    assert "loulan_decision_intake_before_context_bundle" in {
        rule["rule_id"] for rule in registry["validation_rules"]
    }


def _worksheet_and_template(tmp_path: Path) -> tuple[dict, dict]:
    review_pack, decisions = _review_and_template(tmp_path)
    decision_review_pack = build_loulan_decision_review_pack(
        review_pack,
        decisions,
        created_at="2026-06-01T16:00:00+08:00",
    )
    worksheet = build_loulan_decision_worksheet(
        decision_review_pack,
        created_at="2026-06-01T16:30:00+08:00",
    )
    return worksheet, worksheet["manual_transfer_template"]


def _filled_decision(row: dict, decision: str, evidence_refs: list[str]) -> dict:
    return {
        "decision_id": row["decision_id"],
        "target_ref": row["target_ref"],
        "decision": decision,
        "allowed_decisions": row["allowed_decisions"],
        "decided_by": "human",
        "evidence_refs": evidence_refs,
        "suggested_evidence_refs": row["suggested_evidence_refs"],
        "review_note": "reviewed by human",
    }
