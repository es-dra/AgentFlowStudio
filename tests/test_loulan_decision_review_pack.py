from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.contracts.examples import AGENTFLOW_EXAMPLE_PATHS, AGENTFLOW_EXAMPLE_TYPES
from agentflow.memory.loulan_api_workbench import build_loulan_api_workbench_plan
from agentflow.memory.loulan_decision_review_pack import (
    build_loulan_decision_review_pack,
    write_loulan_decision_review_pack,
)
from agentflow.memory.loulan_decision_template import build_loulan_decision_template
from agentflow.memory.loulan_human_review_pack import build_loulan_human_review_pack
from agentflow.memory.loulan_package import build_loulan_memory_package
from tests.test_loulan_human_review_pack import _loulan_review_fixture


def test_loulan_decision_review_pack_summarizes_pending_slots(tmp_path: Path) -> None:
    review_pack, decisions = _review_and_template(tmp_path)

    pack = build_loulan_decision_review_pack(review_pack, decisions, created_at="2026-06-01T16:00:00+08:00")

    assert pack["artifact_type"] == "agentflow_loulan_decision_review_pack"
    assert pack["provider_calls_started"] is False
    assert pack["writes_long_term_memory"] is False
    assert pack["human_acceptance_recorded"] is False
    assert pack["review_status"] == "blocked_pending_human_input"
    assert pack["decision_summary"] == {
        "required_decisions": 3,
        "decision_slots": 3,
        "pending_count": 3,
        "missing_slot_count": 0,
        "invalid_count": 0,
        "ready_count": 0,
    }
    assert pack["decision_groups"] == [
        {"target_type": "character", "count": 1, "pending_count": 1},
        {"target_type": "shot", "count": 2, "pending_count": 2},
    ]
    assert pack["decision_cards"][0]["target_ref"] == "shot:B01-S01"
    assert pack["decision_cards"][0]["status"] == "needs_human_input"
    assert pack["decision_cards"][0]["required_fields"] == ["decision", "decided_by", "evidence_refs", "review_note"]
    assert pack["decision_cards"][0]["suggested_evidence_refs"]
    assert "approve_anchor" in pack["decision_cards"][0]["allowed_decisions"]


def test_loulan_decision_review_pack_reports_missing_and_ready_decisions(tmp_path: Path) -> None:
    review_pack, decisions = _review_and_template(tmp_path)
    decisions["decisions"] = [
        {
            "decision_id": "loulan_decision_b01_s01",
            "target_ref": "shot:B01-S01",
            "decision": "approve_anchor",
            "decided_by": "human",
            "evidence_refs": ["B01-S01-h1"],
            "review_note": "approved by human",
        }
    ]

    pack = build_loulan_decision_review_pack(review_pack, decisions, created_at="2026-06-01T16:00:00+08:00")

    assert pack["review_status"] == "blocked_missing_decisions"
    assert pack["decision_summary"]["ready_count"] == 1
    assert pack["decision_summary"]["missing_slot_count"] == 2
    assert [card["status"] for card in pack["decision_cards"]] == [
        "ready_for_context_projection",
        "missing_decision_slot",
        "missing_decision_slot",
    ]


def test_loulan_decision_review_pack_supports_asset_slots(tmp_path: Path) -> None:
    review_pack, decisions = _review_and_template(tmp_path)
    review_pack["next_pass_readiness"]["required_decisions"].append("asset:character_guan_pingping_target")
    review_pack["asset_review"]["cards"].append(
        {
            "memory_ref": "asset:character_guan_pingping_target",
            "asset_id": "character_guan_pingping_target",
            "allowed_decisions": ["promoted", "merged", "rejected", "expired"],
        }
    )
    decisions["decisions"].append(
        {
            "decision_id": "loulan_decision_asset_guan_pingping_target",
            "target_ref": "asset:character_guan_pingping_target",
            "decision": "pending_human_review",
            "allowed_decisions": [],
            "decided_by": "",
            "evidence_refs": [],
            "suggested_evidence_refs": [],
            "review_note": "",
        }
    )

    pack = build_loulan_decision_review_pack(review_pack, decisions, created_at="2026-06-01T16:00:00+08:00")

    asset_card = pack["decision_cards"][-1]
    assert asset_card["target_type"] == "asset"
    assert asset_card["allowed_decisions"] == ["promoted", "merged", "rejected", "expired"]
    assert asset_card["suggested_evidence_refs"] == [
        "asset:character_guan_pingping_target",
        "character_guan_pingping_target",
    ]


def test_loulan_decision_review_pack_cli_writes_artifacts(tmp_path: Path) -> None:
    review_pack, decisions = _review_and_template(tmp_path)
    review_path = tmp_path / "review_pack.json"
    decisions_path = tmp_path / "decisions.json"
    review_path.write_text(json.dumps(review_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    decisions_path.write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "decision_review"

    result = CliRunner().invoke(
        app,
        [
            "loulan-decision-review-pack",
            "--review-pack",
            str(review_path),
            "--decisions",
            str(decisions_path),
            "--created-at",
            "2026-06-01T16:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan decision review pack" in result.output
    assert "Human acceptance: not recorded" in result.output
    assert (output / "loulan_decision_review_pack.json").is_file()
    assert (output / "loulan_decision_review_pack.md").is_file()


def test_loulan_decision_review_pack_write_returns_artifacts(tmp_path: Path) -> None:
    review_pack, decisions = _review_and_template(tmp_path)
    pack = build_loulan_decision_review_pack(review_pack, decisions, created_at="2026-06-01T16:00:00+08:00")

    paths = write_loulan_decision_review_pack(pack, tmp_path / "out")

    assert {path.name for path in paths} == {
        "loulan_decision_review_pack.json",
        "loulan_decision_review_pack.md",
    }


def test_loulan_decision_review_pack_contract_example_is_registered() -> None:
    example_path = Path("examples/agentflow/loulan_decision_review_pack.example.json")
    payload = json.loads(example_path.read_text(encoding="utf-8"))
    registry = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    assert example_path in AGENTFLOW_EXAMPLE_PATHS
    assert "agentflow_loulan_decision_review_pack" in AGENTFLOW_EXAMPLE_TYPES
    assert payload["artifact_type"] == "agentflow_loulan_decision_review_pack"
    assert payload["review_status"] == "blocked_pending_human_input"
    assert payload["human_acceptance_recorded"] is False
    assert payload["writes_long_term_memory"] is False
    assert "agentflow_loulan_decision_review_pack" in {
        contract["artifact_type"] for contract in registry["contracts"]
    }
    assert "loulan_decision_review_no_approval" in {
        rule["rule_id"] for rule in registry["validation_rules"]
    }


def _review_and_template(tmp_path: Path) -> tuple[dict, dict]:
    root = _loulan_review_fixture(tmp_path)
    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")
    api_plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")
    review_pack = build_loulan_human_review_pack(
        package,
        api_plan,
        project_root=root,
        block_id="B01",
        created_at="2026-06-01T11:00:00+08:00",
    )
    decisions = build_loulan_decision_template(review_pack, created_at="2026-06-01T12:30:00+08:00")
    return review_pack, decisions
