from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.memory.loulan_api_workbench import (
    build_loulan_api_workbench_plan,
    write_loulan_api_workbench_plan,
)
from agentflow.memory.loulan_context_bundle import build_loulan_context_bundle_projection
from agentflow.memory.loulan_human_review_pack import build_loulan_human_review_pack
from agentflow.memory.loulan_package import build_loulan_memory_package
from tests.test_loulan_human_review_pack import _loulan_review_fixture
from tests.test_loulan_memory_package import _loulan_fixture
from tests.test_loulan_memory_package_registry import _loulan_registry_fixture


def test_loulan_api_workbench_plan_builds_dry_run_request_preview(tmp_path: Path) -> None:
    package = build_loulan_memory_package(_loulan_fixture(tmp_path), created_at="2026-06-01T09:00:00+08:00")

    plan = build_loulan_api_workbench_plan(
        package,
        created_at="2026-06-01T10:00:00+08:00",
        provider_adapter_id="openai_compatible_image",
    )

    assert plan["artifact_type"] == "agentflow_loulan_api_workbench_plan"
    assert plan["dry_run_only"] is True
    assert plan["provider_calls_started"] is False
    assert plan["writes_long_term_memory"] is False
    assert plan["provider_adapter"]["required_gate"] == "NARRATOCUT_ALLOW_REMOTE_IMAGE"
    assert plan["provider_adapter"]["live_call_authorized"] is False
    assert plan["reference_pack"]["status"] == "ready"
    assert plan["reference_pack"]["references"] == [
        {
            "memory_ref": "character:zhou_tong_school_v1",
            "asset_id": "zhou_tong_school_v1",
            "label": "Zhou Tong school uniform",
            "sha256": "sha-approved",
            "source_status": "approved",
        }
    ]
    assert plan["prompt_compiler"]["status"] == "ready"
    assert "character:zhou_tong_school_v1" in plan["prompt_compiler"]["compiled_prompt_preview"]
    assert plan["request_manifest"]["status"] == "ready"
    assert plan["request_manifest"]["requests"][0]["body_preview"]["reference_images"][0] == {
        "memory_ref": "character:zhou_tong_school_v1",
        "sha256": "sha-approved",
        "runtime_image_loader": "deferred",
    }
    assert plan["response_ledger"]["status"] == "not_submitted"
    assert plan["qa_gate"]["status"] == "pending_response"
    assert plan["promotion_gate"]["status"] == "blocked_until_human_review"
    assert "character:guan_pingping_v2" in plan["promotion_gate"]["blocked_memory_refs"]

    serialized = json.dumps(plan, ensure_ascii=False)
    for forbidden in ["D:\\", "C:\\", "file://", ".mp4", ".mov", "api_key", "secret_key", "Bearer ", "signed_url"]:
        assert forbidden not in serialized


def test_loulan_api_workbench_plan_uses_registry_approved_anchors(tmp_path: Path) -> None:
    package = build_loulan_memory_package(_loulan_registry_fixture(tmp_path), created_at="2026-06-01T09:00:00+08:00")

    plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")

    assert plan["reference_pack"]["status"] == "ready"
    assert plan["reference_pack"]["references"] == [
        {
            "memory_ref": "asset:character_zhou_tong_school_v1",
            "asset_id": "character_zhou_tong_school_v1",
            "label": "Zhou Tong approved school-phase anchor",
            "sha256": "sha-approved",
            "source_status": "approved_anchor",
        }
    ]
    assert "asset:keyframe_b01_s01_h1" in plan["promotion_gate"]["blocked_memory_refs"]
    assert "asset:prop_chitu_bag_v1_failed" in plan["promotion_gate"]["blocked_memory_refs"]


def test_loulan_api_workbench_plan_blocks_without_approved_reference(tmp_path: Path) -> None:
    package = build_loulan_memory_package(_loulan_fixture(tmp_path), created_at="2026-06-01T09:00:00+08:00")
    package["asset_summary"]["assets"][0]["status"] = "candidate_pending_human_review"
    package["asset_summary"]["assets"][0]["eligible_for_context"] = False
    package["next_context_bundle_draft"]["eligible_memory_refs"] = []
    package["next_context_bundle_draft"]["blocked_memory_refs"].append("character:zhou_tong_school_v1")

    plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")

    assert plan["reference_pack"]["status"] == "blocked"
    assert plan["request_manifest"]["status"] == "blocked"
    assert plan["request_manifest"]["requests"] == []
    assert "no_approved_reference_hashes" in plan["blocking_reasons"]


def test_loulan_api_workbench_plan_uses_context_projection_decisions(tmp_path: Path) -> None:
    package, projection = _package_with_context_projection(tmp_path)

    plan = build_loulan_api_workbench_plan(
        package,
        context_projection=projection,
        created_at="2026-06-01T13:00:00+08:00",
    )

    assert plan["source_context_projection_id"] == projection["projection_id"]
    assert plan["context_projection"]["status"] == "partial_ready"
    assert plan["reference_pack"]["references"] == [
        {
            "memory_ref": "character:guan_pingping_v2",
            "asset_id": "guan_pingping_v2",
            "label": "Guan Pingping school uniform",
            "sha256": "sha-guan-human-approved",
            "source_status": "candidate_pending_human_review",
            "decision_source": projection["projection_id"],
        }
    ]
    assert "character:zhou_tong_school_v1" not in plan["prompt_compiler"]["compiled_prompt_preview"]
    assert plan["request_manifest"]["requests"][0]["source_context_projection_id"] == projection["projection_id"]
    assert plan["promotion_gate"]["blocked_memory_refs"] == ["shot:B01-S02"]


def test_loulan_api_workbench_plan_blocks_on_unready_context_projection(tmp_path: Path) -> None:
    package, projection = _package_with_context_projection(tmp_path, omit_last_decision=True)

    plan = build_loulan_api_workbench_plan(
        package,
        context_projection=projection,
        created_at="2026-06-01T13:00:00+08:00",
    )

    assert plan["context_projection"]["status"] == "blocked_missing_decisions"
    assert plan["reference_pack"]["status"] == "blocked"
    assert plan["request_manifest"]["requests"] == []
    assert "context_projection_not_ready" in plan["blocking_reasons"]
    assert "character:zhou_tong_school_v1" not in json.dumps(plan, ensure_ascii=False)


def test_loulan_api_workbench_cli_writes_preview_artifacts(tmp_path: Path) -> None:
    package = build_loulan_memory_package(_loulan_fixture(tmp_path), created_at="2026-06-01T09:00:00+08:00")
    package_path = tmp_path / "loulan_memory_package.json"
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "api_workbench"

    result = CliRunner().invoke(
        app,
        [
            "loulan-api-workbench-plan",
            "--package",
            str(package_path),
            "--created-at",
            "2026-06-01T10:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan API workbench plan" in result.output
    assert "Provider calls: not started" in result.output
    assert "Requests previewed: 1" in result.output
    for name in [
        "loulan_api_workbench_plan.json",
        "reference_pack.json",
        "prompt_compiler_preview.json",
        "request_manifest.json",
        "response_ledger.json",
        "qa_promotion_gates.json",
        "loulan_api_workbench_plan.md",
    ]:
        assert (output / name).is_file()

    written = json.loads((output / "loulan_api_workbench_plan.json").read_text(encoding="utf-8"))
    assert written["provider_calls_started"] is False
    assert written["request_manifest"]["requests"][0]["live_call_authorized"] is False


def test_loulan_api_workbench_cli_accepts_context_projection(tmp_path: Path) -> None:
    package, projection = _package_with_context_projection(tmp_path)
    package_path = tmp_path / "loulan_memory_package.json"
    projection_path = tmp_path / "loulan_context_bundle_projection.json"
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    projection_path.write_text(json.dumps(projection, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "api_workbench"

    result = CliRunner().invoke(
        app,
        [
            "loulan-api-workbench-plan",
            "--package",
            str(package_path),
            "--context-projection",
            str(projection_path),
            "--created-at",
            "2026-06-01T13:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Context projection: partial_ready" in result.output
    written = json.loads((output / "loulan_api_workbench_plan.json").read_text(encoding="utf-8"))
    assert written["source_context_projection_id"] == projection["projection_id"]
    assert written["reference_pack"]["references"][0]["memory_ref"] == "character:guan_pingping_v2"


def test_loulan_api_workbench_write_returns_artifacts(tmp_path: Path) -> None:
    package = build_loulan_memory_package(_loulan_fixture(tmp_path), created_at="2026-06-01T09:00:00+08:00")
    plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")

    paths = write_loulan_api_workbench_plan(plan, tmp_path / "out")

    assert {path.name for path in paths} == {
        "loulan_api_workbench_plan.json",
        "reference_pack.json",
        "prompt_compiler_preview.json",
        "request_manifest.json",
        "response_ledger.json",
        "qa_promotion_gates.json",
        "loulan_api_workbench_plan.md",
    }


def test_loulan_api_workbench_contract_example_is_dry_run_only() -> None:
    payload = json.loads(Path("examples/agentflow/loulan_api_workbench_plan.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_loulan_api_workbench_plan"
    assert payload["dry_run_only"] is True
    assert payload["provider_calls_started"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["source_context_projection_id"] is None
    assert payload["context_projection"]["status"] == "not_provided"
    assert payload["provider_adapter"]["live_call_authorized"] is False
    assert payload["reference_pack"]["references"][0]["sha256"] == "sha-approved"
    assert payload["request_manifest"]["requests"][0]["live_call_authorized"] is False
    assert payload["response_ledger"]["status"] == "not_submitted"
    assert payload["qa_gate"]["automatic_promotion_allowed"] is False
    assert payload["promotion_gate"]["writes_long_term_memory"] is False


def test_loulan_api_workbench_contract_is_registered() -> None:
    registry = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    registered_types = {contract["artifact_type"] for contract in registry["contracts"]}
    rule_ids = {rule["rule_id"] for rule in registry["validation_rules"]}
    assert "agentflow_loulan_api_workbench_plan" in registered_types
    assert "loulan_api_workbench_dry_run_only" in rule_ids


def _package_with_context_projection(tmp_path: Path, *, omit_last_decision: bool = False) -> tuple[dict, dict]:
    root = _loulan_review_fixture(tmp_path)
    characters_path = root / "manifests" / "character_assets.json"
    characters = json.loads(characters_path.read_text(encoding="utf-8"))
    characters["assets"][1]["sha256"] = "sha-guan-human-approved"
    characters_path.write_text(json.dumps(characters, ensure_ascii=False, indent=2), encoding="utf-8")
    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")
    api_plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")
    review_pack = build_loulan_human_review_pack(
        package,
        api_plan,
        project_root=root,
        block_id="B01",
        created_at="2026-06-01T11:00:00+08:00",
    )
    decisions = _context_decisions(review_pack, omit_last_decision=omit_last_decision)
    projection = build_loulan_context_bundle_projection(
        review_pack,
        decisions,
        created_at="2026-06-01T12:00:00+08:00",
    )
    return package, projection


def _context_decisions(review_pack: dict, *, omit_last_decision: bool) -> dict:
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
    if omit_last_decision:
        decisions = decisions[:-1]
    return {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_loulan_promotion_decisions",
        "review_pack_id": review_pack["review_pack_id"],
        "decisions": decisions,
        "writes_long_term_memory": False,
    }
