from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentflow.contracts.agentops import AGENTOPS_ARTIFACT_TYPES, validate_agentops_artifact


def test_agentops_examples_validate_and_stay_candidate_evidence_only() -> None:
    example_paths = [
        Path("examples/agentflow/agentops_run_trace.example.json"),
        Path("examples/agentflow/agentops_quality_report.example.json"),
        Path("examples/agentflow/agentops_guardrail_result.example.json"),
        Path("examples/agentflow/agentops_handoff_record.example.json"),
        Path("examples/agentflow/agentops_maintenance_audit_report.example.json"),
    ]

    seen_types = set()
    for path in example_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_agentops_artifact(payload)
        seen_types.add(payload["artifact_type"])
        assert payload["writes_long_term_memory"] is False
        assert payload["writes_company_kb"] is False

    assert seen_types == AGENTOPS_ARTIFACT_TYPES


def test_agentops_artifact_rejects_private_paths() -> None:
    payload = json.loads(Path("examples/agentflow/agentops_run_trace.example.json").read_text(encoding="utf-8"))
    payload["input_refs"].append({"role": "unsafe", "ref": "D:\\private\\asset.png"})

    with pytest.raises(ValueError, match="private path"):
        validate_agentops_artifact(payload)


def test_agentops_artifact_requires_non_claim_boundaries() -> None:
    payload = json.loads(Path("examples/agentflow/agentops_run_trace.example.json").read_text(encoding="utf-8"))
    payload["non_claims"] = ["not human acceptance"]

    with pytest.raises(ValueError, match="missing non_claims"):
        validate_agentops_artifact(payload)
