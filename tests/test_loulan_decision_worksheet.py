from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.contracts.examples import AGENTFLOW_EXAMPLE_PATHS, AGENTFLOW_EXAMPLE_TYPES
from agentflow.memory.loulan_decision_review_pack import build_loulan_decision_review_pack
from agentflow.memory.loulan_decision_worksheet import (
    build_loulan_decision_worksheet,
    write_loulan_decision_worksheet,
)
from tests.test_loulan_decision_review_pack import _review_and_template


def test_loulan_decision_worksheet_exports_manual_fill_rows(tmp_path: Path) -> None:
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

    assert worksheet["artifact_type"] == "agentflow_loulan_decision_worksheet"
    assert worksheet["decision_review_pack_id"] == decision_review_pack["decision_review_pack_id"]
    assert worksheet["review_pack_id"] == decision_review_pack["review_pack_id"]
    assert worksheet["provider_calls_started"] is False
    assert worksheet["writes_long_term_memory"] is False
    assert worksheet["human_acceptance_recorded"] is False
    assert worksheet["worksheet_status"] == "awaiting_manual_decisions"
    assert worksheet["decision_summary"] == decision_review_pack["decision_summary"]
    assert worksheet["worksheet_groups"] == [
        {
            "target_type": "character",
            "count": 1,
            "pending_count": 1,
            "missing_count": 0,
            "invalid_count": 0,
            "ready_count": 0,
        },
        {
            "target_type": "shot",
            "count": 2,
            "pending_count": 2,
            "missing_count": 0,
            "invalid_count": 0,
            "ready_count": 0,
        },
    ]
    first_row = worksheet["decision_rows"][0]
    assert first_row["target_ref"] == "shot:B01-S01"
    assert first_row["manual_fill_required"] is True
    assert first_row["decision_to_fill"] == ""
    assert first_row["decided_by_to_fill"] == ""
    assert first_row["evidence_refs_to_fill"] == []
    assert first_row["review_note_to_fill"] == ""
    assert first_row["copy_target_json"] == {
        "decision_id": first_row["decision_id"],
        "target_ref": "shot:B01-S01",
        "decision": "",
        "allowed_decisions": ["approve_anchor", "reject", "request_repair"],
        "decided_by": "",
        "evidence_refs": [],
        "suggested_evidence_refs": first_row["suggested_evidence_refs"],
        "review_note": "",
    }
    assert worksheet["manual_transfer_template"]["artifact_type"] == "agentflow_loulan_promotion_decisions"
    assert worksheet["manual_transfer_template"]["human_acceptance_recorded"] is False
    assert worksheet["manual_transfer_template"]["decisions"][0]["decision"] == ""


def test_loulan_decision_worksheet_preserves_ready_status_without_approval_claim(tmp_path: Path) -> None:
    review_pack, decisions = _review_and_template(tmp_path)
    decisions["decisions"] = [
        {
            "decision_id": "loulan_decision_b01_s01",
            "target_ref": "shot:B01-S01",
            "decision": "approve_anchor",
            "allowed_decisions": ["approve_anchor", "reject", "request_repair"],
            "decided_by": "human",
            "evidence_refs": ["B01-S01-h1"],
            "suggested_evidence_refs": ["B01-S01-h1"],
            "review_note": "usable anchor",
        }
    ]
    decision_review_pack = build_loulan_decision_review_pack(
        review_pack,
        decisions,
        created_at="2026-06-01T16:00:00+08:00",
    )

    worksheet = build_loulan_decision_worksheet(
        decision_review_pack,
        created_at="2026-06-01T16:30:00+08:00",
    )

    assert worksheet["worksheet_status"] == "awaiting_manual_decisions"
    assert worksheet["worksheet_groups"] == [
        {
            "target_type": "character",
            "count": 1,
            "pending_count": 0,
            "missing_count": 1,
            "invalid_count": 0,
            "ready_count": 0,
        },
        {
            "target_type": "shot",
            "count": 2,
            "pending_count": 0,
            "missing_count": 1,
            "invalid_count": 0,
            "ready_count": 1,
        },
    ]
    ready_row = worksheet["decision_rows"][0]
    assert ready_row["status"] == "ready_for_context_projection"
    assert ready_row["manual_fill_required"] is False
    assert ready_row["decision_to_fill"] == ""
    assert ready_row["copy_target_json"]["decision"] == ""
    assert worksheet["claim_boundaries"]["human_acceptance"] == "not_recorded"


def test_loulan_decision_worksheet_rejects_unsafe_or_accepted_review_pack(tmp_path: Path) -> None:
    review_pack, decisions = _review_and_template(tmp_path)
    decision_review_pack = build_loulan_decision_review_pack(
        review_pack,
        decisions,
        created_at="2026-06-01T16:00:00+08:00",
    )
    decision_review_pack["human_acceptance_recorded"] = True

    try:
        build_loulan_decision_worksheet(
            decision_review_pack,
            created_at="2026-06-01T16:30:00+08:00",
        )
    except ValueError as exc:
        assert "must not record human acceptance" in str(exc)
    else:
        raise AssertionError("expected accepted review pack to be rejected")


def test_loulan_decision_worksheet_cli_writes_artifacts(tmp_path: Path) -> None:
    review_pack, decisions = _review_and_template(tmp_path)
    decision_review_pack = build_loulan_decision_review_pack(
        review_pack,
        decisions,
        created_at="2026-06-01T16:00:00+08:00",
    )
    review_path = tmp_path / "decision_review_pack.json"
    review_path.write_text(json.dumps(decision_review_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "decision_worksheet"

    result = CliRunner().invoke(
        app,
        [
            "loulan-decision-worksheet",
            "--decision-review-pack",
            str(review_path),
            "--created-at",
            "2026-06-01T16:30:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan decision worksheet" in result.output
    assert "Human acceptance: not recorded" in result.output
    assert "Provider calls: not started" in result.output
    assert (output / "loulan_decision_worksheet.json").is_file()
    assert (output / "loulan_decision_worksheet.md").is_file()


def test_loulan_decision_worksheet_write_returns_artifacts(tmp_path: Path) -> None:
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

    paths = write_loulan_decision_worksheet(worksheet, tmp_path / "out")

    assert {path.name for path in paths} == {
        "loulan_decision_worksheet.json",
        "loulan_decision_worksheet.md",
    }


def test_loulan_decision_worksheet_contract_example_is_registered() -> None:
    example_path = Path("examples/agentflow/loulan_decision_worksheet.example.json")
    payload = json.loads(example_path.read_text(encoding="utf-8"))
    registry = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    assert example_path in AGENTFLOW_EXAMPLE_PATHS
    assert "agentflow_loulan_decision_worksheet" in AGENTFLOW_EXAMPLE_TYPES
    assert payload["artifact_type"] == "agentflow_loulan_decision_worksheet"
    assert payload["worksheet_status"] == "awaiting_manual_decisions"
    assert payload["human_acceptance_recorded"] is False
    assert payload["writes_long_term_memory"] is False
    assert "agentflow_loulan_decision_worksheet" in {
        contract["artifact_type"] for contract in registry["contracts"]
    }
    assert "loulan_decision_worksheet_manual_fill_only" in {
        rule["rule_id"] for rule in registry["validation_rules"]
    }
