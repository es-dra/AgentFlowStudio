from __future__ import annotations

import json
from pathlib import Path

from agentflow.contracts.examples import AGENTFLOW_EXAMPLE_PATHS


def test_agentflow_contract_registry_example_indexes_current_contracts() -> None:
    payload = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_contract_registry"
    assert payload["registry_scope"] == "contract_discovery"
    assert payload["runtime_status"] == "not_implemented"
    assert payload["does_not_execute"] is True

    registered_types = {contract["artifact_type"] for contract in payload["contracts"]}
    expected_types = {
        "agentflow_project_manifest",
        "agentflow_artifact_map",
        "agentflow_feedback_event",
        "agentflow_memory_candidate",
        "agentflow_memory_promotion_decision",
        "agentflow_memory_evidence_reuse_review",
        "agentflow_production_memory_loop",
        "agentflow_run_trace",
        "agentflow_quality_report",
        "agentflow_guardrail_result",
        "agentflow_handoff_record",
        "agentflow_maintenance_audit_report",
        "agentflow_skill_invocation",
        "agentflow_skill_result",
        "agentflow_router_decision",
        "agentflow_intermediate_asset",
        "agentflow_reusable_asset_profile",
        "agentflow_asset_reuse_decision",
        "agentflow_production_asset_feedback_review",
        "agentflow_production_asset_feedback_review_validation",
        "agentflow_production_asset_feedback_review_gate",
        "agentflow_production_asset_reuse_dry_run_plan",
        "agentflow_production_asset_reuse_review",
    }
    assert expected_types <= registered_types
    assert all(contract["example_path"] for contract in payload["contracts"])
    assert all(contract["doc_path"] for contract in payload["contracts"])


def test_agentflow_contract_registry_examples_exist_and_match_artifact_types() -> None:
    payload = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))
    json_examples = {path.as_posix() for path in AGENTFLOW_EXAMPLE_PATHS if path.suffix == ".json"}
    jsonl_examples = {path.as_posix() for path in AGENTFLOW_EXAMPLE_PATHS if path.suffix == ".jsonl"}

    for contract in payload["contracts"]:
        example_path = contract["example_path"]
        assert example_path in json_examples | jsonl_examples
        if example_path in json_examples:
            example_payload = json.loads(Path(example_path).read_text(encoding="utf-8"))
            assert example_payload["artifact_type"] == contract["artifact_type"]
        else:
            events = [
                json.loads(line)
                for line in Path(example_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert events
            assert {event["artifact_type"] for event in events} == {contract["artifact_type"]}


def test_agentflow_contract_registry_declares_validation_rules_without_runtime() -> None:
    payload = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    rule_ids = {rule["rule_id"] for rule in payload["validation_rules"]}
    assert {
        "schema_version_0_1_0",
        "example_path_exists",
        "no_private_paths_or_secrets",
        "router_decision_only",
        "candidate_memory_only",
        "promotion_decision_required_for_context_reuse",
        "context_reuse_no_durable_write",
        "evidence_reuse_traceability_first",
        "production_memory_loop_no_provider_context_bundle",
        "local_agentops_non_claims",
        "local_agentops_no_company_write",
    } <= rule_ids
    assert "execute_workflow" not in rule_ids
    assert "call_remote_provider" not in rule_ids
