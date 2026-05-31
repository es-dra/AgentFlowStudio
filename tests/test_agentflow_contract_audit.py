from __future__ import annotations

import json
from pathlib import Path


REGISTRY_PATH = Path("examples/agentflow/contract_registry.example.json")
AUDIT_REPORT_PATH = Path("examples/agentflow/contract_audit_report.example.json")
AGENTFLOW_EXAMPLE_GLOB = "examples/agentflow/*"
FORBIDDEN_EXAMPLE_FRAGMENTS = [
    "D:\\",
    "C:\\",
    "data/processed/runs",
    "data/raw/",
    ".mp4",
    ".mov",
    "api_key",
    "access_token",
    "refresh_token",
    "secret_key",
    "client_secret",
    "authorization:",
    "bearer ",
    "cookie=",
    "signed_url",
]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_agentflow_contract_audit_report_declares_static_gate() -> None:
    payload = _json(AUDIT_REPORT_PATH)

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_contract_audit_report"
    assert payload["audit_scope"] == "static_contract_examples"
    assert payload["source_registry"] == REGISTRY_PATH.as_posix()
    assert payload["runtime_status"] == "not_implemented"
    assert payload["does_not_execute"] is True
    assert payload["overall_status"] == "passed"


def test_agentflow_contract_audit_report_covers_registry_contracts() -> None:
    registry = _json(REGISTRY_PATH)
    report = _json(AUDIT_REPORT_PATH)

    registry_types = {contract["artifact_type"] for contract in registry["contracts"]}
    audited_types = {entry["artifact_type"] for entry in report["audited_contracts"]}

    assert registry_types <= audited_types
    assert all(entry["example_path_exists"] for entry in report["audited_contracts"])
    assert all(entry["doc_path_exists"] for entry in report["audited_contracts"])
    assert all(entry["schema_version"] == "0.1.0" for entry in report["audited_contracts"])
    assert all(Path(entry["example_path"]).exists() for entry in report["audited_contracts"])
    assert all(Path(entry["doc_path"]).exists() for entry in report["audited_contracts"])


def test_agentflow_contract_audit_report_records_boundary_checks() -> None:
    report = _json(AUDIT_REPORT_PATH)
    check_ids = {check["check_id"] for check in report["boundary_checks"]}

    assert {
        "no_private_paths_or_secrets",
        "no_generated_media_or_run_outputs",
        "router_decision_only",
        "memory_candidate_only",
        "feedback_signal_is_derived",
        "cost_quality_trace_is_evidence",
        "candidate_memory_not_reusable_asset",
        "reusable_asset_requires_promotion",
        "context_reuse_requires_promotion_decision",
        "context_reuse_does_not_write_memory",
        "loulan_decision_template_pending_only",
        "intermediate_asset_has_evidence",
    } <= check_ids
    assert all(check["status"] == "passed" for check in report["boundary_checks"])


def test_agentflow_contract_audit_report_does_not_claim_runtime_validation() -> None:
    report = _json(AUDIT_REPORT_PATH)
    forbidden_claims = {
        "router_runtime",
        "skill_runtime",
        "memory_runtime",
        "workflow_execution",
        "provider_call",
        "database_write",
    }

    assert not (forbidden_claims & set(report["validated_runtime_capabilities"]))
    assert report["validated_runtime_capabilities"] == []


def test_agentflow_contract_examples_do_not_include_private_or_generated_paths() -> None:
    for path in sorted(Path("examples/agentflow").glob("*")):
        raw_text = path.read_text(encoding="utf-8").lower()
        assert not any(fragment.lower() in raw_text for fragment in FORBIDDEN_EXAMPLE_FRAGMENTS)
