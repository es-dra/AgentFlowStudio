from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.memory.loulan_api_workbench import build_loulan_api_workbench_plan
from agentflow.memory.loulan_context_bundle import (
    build_loulan_context_bundle_projection,
    write_loulan_context_bundle_projection,
)
from agentflow.memory.loulan_human_review_pack import build_loulan_human_review_pack
from agentflow.memory.loulan_package import build_loulan_memory_package
from tests.test_loulan_human_review_pack import _loulan_review_fixture


def test_loulan_context_bundle_projection_uses_only_human_decisions(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    decisions = _decisions(review_pack, omit_last=False)

    projection = build_loulan_context_bundle_projection(
        review_pack,
        decisions,
        created_at="2026-06-01T12:00:00+08:00",
    )

    assert projection["artifact_type"] == "agentflow_loulan_context_bundle_projection"
    assert projection["provider_calls_started"] is False
    assert projection["writes_long_term_memory"] is False
    assert projection["decision_audit"]["status"] == "partial_ready"
    assert projection["context_bundle"]["memory_refs"] == ["character:guan_pingping_v2"]
    assert projection["context_bundle"]["shot_anchor_refs"] == ["shot:B01-S01"]
    assert projection["context_bundle"]["blocked_refs"] == ["shot:B01-S02"]
    assert projection["next_prompt_draft"]["status"] == "partial_ready"
    assert "character:guan_pingping_v2" in projection["next_prompt_draft"]["memory_refs"]


def test_loulan_context_bundle_projection_blocks_missing_decisions(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    decisions = _decisions(review_pack, omit_last=True)

    projection = build_loulan_context_bundle_projection(
        review_pack,
        decisions,
        created_at="2026-06-01T12:00:00+08:00",
    )

    assert projection["decision_audit"]["status"] == "blocked_missing_decisions"
    assert projection["context_bundle"]["status"] == "blocked"
    assert projection["decision_audit"]["missing_decision_refs"] == ["character:guan_pingping_v2"]


def test_loulan_context_bundle_projection_supports_asset_refs(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    review_pack["next_pass_readiness"]["required_decisions"] = ["asset:character_guan_pingping_target"]
    decisions = {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_loulan_promotion_decisions",
        "review_pack_id": review_pack["review_pack_id"],
        "decisions": [
            {
                "decision_id": "loulan_decision_asset_guan_pingping_target",
                "target_ref": "asset:character_guan_pingping_target",
                "decision": "promoted",
                "decided_by": "human",
                "evidence_refs": ["asset:character_guan_pingping_target"],
            }
        ],
        "writes_long_term_memory": False,
    }

    projection = build_loulan_context_bundle_projection(
        review_pack,
        decisions,
        created_at="2026-06-01T12:00:00+08:00",
    )

    assert projection["decision_audit"]["status"] == "ready"
    assert projection["context_bundle"]["memory_refs"] == ["asset:character_guan_pingping_target"]
    assert projection["context_bundle"]["shot_anchor_refs"] == []


def test_loulan_context_bundle_cli_writes_projection_artifacts(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    decisions = _decisions(review_pack, omit_last=False)
    review_path = tmp_path / "review_pack.json"
    decisions_path = tmp_path / "decisions.json"
    review_path.write_text(json.dumps(review_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    decisions_path.write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "context_bundle"

    result = CliRunner().invoke(
        app,
        [
            "loulan-context-bundle",
            "--review-pack",
            str(review_path),
            "--decisions",
            str(decisions_path),
            "--created-at",
            "2026-06-01T12:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan context bundle projection" in result.output
    assert "Provider calls: not started" in result.output
    for name in [
        "loulan_context_bundle_projection.json",
        "context_bundle.json",
        "next_prompt_draft.json",
        "decision_audit.json",
        "loulan_context_bundle_projection.md",
    ]:
        assert (output / name).is_file()


def test_loulan_context_bundle_contract_example_is_registered() -> None:
    payload = json.loads(Path("examples/agentflow/loulan_context_bundle_projection.example.json").read_text(encoding="utf-8"))
    registry = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    assert payload["artifact_type"] == "agentflow_loulan_context_bundle_projection"
    assert payload["writes_long_term_memory"] is False
    assert payload["context_bundle"]["writes_long_term_memory"] is False
    assert "agentflow_loulan_context_bundle_projection" in {contract["artifact_type"] for contract in registry["contracts"]}
    assert "loulan_context_bundle_decisions_only" in {rule["rule_id"] for rule in registry["validation_rules"]}


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


def _decisions(review_pack: dict, *, omit_last: bool) -> dict:
    decisions = [
        {
            "decision_id": "loulan_decision_b01_s01",
            "target_ref": "shot:B01-S01",
            "decision": "approve_anchor",
            "decided_by": "human",
            "evidence_refs": ["B01-S01-h1"],
        },
        {
            "decision_id": "loulan_decision_b01_s02",
            "target_ref": "shot:B01-S02",
            "decision": "request_repair",
            "decided_by": "human",
            "evidence_refs": ["B01-S02-h1"],
        },
        {
            "decision_id": "loulan_decision_guan_pingping_v2",
            "target_ref": "character:guan_pingping_v2",
            "decision": "promoted",
            "decided_by": "human",
            "evidence_refs": ["reviews/guan_pingping_v2/refinement_card.md"],
        },
    ]
    if omit_last:
        decisions = decisions[:-1]
    return {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_loulan_promotion_decisions",
        "review_pack_id": review_pack["review_pack_id"],
        "decisions": decisions,
        "writes_long_term_memory": False,
    }
