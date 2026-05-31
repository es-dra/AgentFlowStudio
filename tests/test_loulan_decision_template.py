from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.contracts.examples import AGENTFLOW_EXAMPLE_PATHS, AGENTFLOW_EXAMPLE_TYPES
from agentflow.memory.loulan_api_workbench import build_loulan_api_workbench_plan
from agentflow.memory.loulan_context_bundle import build_loulan_context_bundle_projection
from agentflow.memory.loulan_decision_template import (
    build_loulan_decision_template,
    write_loulan_decision_template,
)
from agentflow.memory.loulan_human_review_pack import build_loulan_human_review_pack
from agentflow.memory.loulan_package import build_loulan_memory_package
from tests.test_loulan_human_review_pack import _loulan_review_fixture


def test_loulan_decision_template_lists_required_human_decisions(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)

    template = build_loulan_decision_template(review_pack, created_at="2026-06-01T12:30:00+08:00")

    assert template["artifact_type"] == "agentflow_loulan_promotion_decisions"
    assert template["template_status"] == "pending_human_input"
    assert template["provider_calls_started"] is False
    assert template["writes_long_term_memory"] is False
    assert template["human_acceptance_recorded"] is False
    assert [item["target_ref"] for item in template["decisions"]] == [
        "shot:B01-S01",
        "shot:B01-S02",
        "character:guan_pingping_v2",
    ]
    assert template["decisions"][0]["allowed_decisions"] == ["approve_anchor", "reject", "request_repair"]
    assert template["decisions"][2]["allowed_decisions"] == ["promoted", "merged", "rejected", "expired"]
    assert {item["decision"] for item in template["decisions"]} == {"pending_human_review"}
    assert {item["decided_by"] for item in template["decisions"]} == {""}
    assert all(item["evidence_refs"] == [] for item in template["decisions"])

    projection = build_loulan_context_bundle_projection(
        review_pack,
        template,
        created_at="2026-06-01T12:45:00+08:00",
    )
    assert projection["decision_audit"]["status"] == "blocked_invalid_decisions"
    assert projection["context_bundle"]["status"] == "blocked"


def test_loulan_decision_template_cli_writes_template_artifacts(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    review_path = tmp_path / "review_pack.json"
    review_path.write_text(json.dumps(review_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "decision_template"

    result = CliRunner().invoke(
        app,
        [
            "loulan-decision-template",
            "--review-pack",
            str(review_path),
            "--created-at",
            "2026-06-01T12:30:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan decision template" in result.output
    assert "Human acceptance: not recorded" in result.output
    assert (output / "loulan_decisions.template.json").is_file()
    assert (output / "loulan_decisions.template.md").is_file()


def test_loulan_decision_template_write_returns_artifacts(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    template = build_loulan_decision_template(review_pack, created_at="2026-06-01T12:30:00+08:00")

    paths = write_loulan_decision_template(template, tmp_path / "out")

    assert {path.name for path in paths} == {
        "loulan_decisions.template.json",
        "loulan_decisions.template.md",
    }


def test_loulan_decision_template_contract_example_is_registered() -> None:
    example_path = Path("examples/agentflow/loulan_promotion_decisions_template.example.json")
    payload = json.loads(example_path.read_text(encoding="utf-8"))
    registry = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    assert example_path in AGENTFLOW_EXAMPLE_PATHS
    assert "agentflow_loulan_promotion_decisions" in AGENTFLOW_EXAMPLE_TYPES
    assert payload["artifact_type"] == "agentflow_loulan_promotion_decisions"
    assert payload["template_status"] == "pending_human_input"
    assert {item["decision"] for item in payload["decisions"]} == {"pending_human_review"}
    assert {item["decided_by"] for item in payload["decisions"]} == {""}
    assert payload["human_acceptance_recorded"] is False
    assert any(
        contract["artifact_type"] == "agentflow_loulan_promotion_decisions"
        for contract in registry["contracts"]
    )
    assert "loulan_decision_template_pending_only" in {
        rule["rule_id"] for rule in registry["validation_rules"]
    }


def _review_pack(tmp_path: Path) -> dict:
    root = _loulan_review_fixture(tmp_path)
    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")
    api_plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")
    return build_loulan_human_review_pack(
        package,
        api_plan,
        project_root=root,
        block_id="B01",
        created_at="2026-06-01T11:00:00+08:00",
    )
