from __future__ import annotations

import copy
from pathlib import Path

import pytest


FIXTURE_PATH = Path("tests/fixtures/shared_object_evidence/stage1_contract_fixture.json")


def test_shared_object_evidence_algorithm_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import shared_object_evidence

    assert "shared_object_evidence" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert shared_object_evidence.ALGORITHM_ID == "afs.shared_object_evidence.v0.1"
    assert shared_object_evidence.INPUT_CONTRACT
    assert shared_object_evidence.OUTPUT_CONTRACT
    assert shared_object_evidence.FAILURE_MODES
    assert shared_object_evidence.EVIDENCE_BOUNDARY


def test_stage1_fixture_loads_with_stable_refs_and_boundaries() -> None:
    from agentflow.algorithms.shared_object_evidence import load_shared_object_evidence_fixture

    report = load_shared_object_evidence_fixture(FIXTURE_PATH)

    assert report["fixture_id"] == "shared_object_evidence_contract_fixture_v0"
    assert report["fixture_claim_level"] == "deterministic_local_contract_only"
    assert report["summary"] == {
        "object_count": 18,
        "evidence_reference_count": 3,
        "handoff_envelope_count": 1,
        "production_graph_node_count": 2,
        "production_graph_reference_count": 1,
        "proposed_graph_extension_count": 1,
    }
    assert report["object_type_counts"]["branch_shot"] == 1
    assert report["object_type_counts"]["production_graph_node"] == 2
    assert report["sorted_ref_ids"] == sorted(report["sorted_ref_ids"])
    assert report["non_claims"]["provider_smoke"] is False
    assert report["non_claims"]["generated_media_quality"] is False
    assert report["non_claims"]["human_creative_acceptance"] is False
    assert report["non_claims"]["business_validation"] is False
    assert report["non_claims"]["deploy_runtime_health"] is False
    assert report["stage1_residual"] == "evaluator_system_error_residual_carried"


def test_fixture_keeps_production_graph_node_and_reference_split() -> None:
    from agentflow.algorithms.shared_object_evidence import load_shared_object_evidence_fixture

    report = load_shared_object_evidence_fixture(FIXTURE_PATH)

    assert report["production_graph_boundary"] == {
        "current_allowed_node_types": ["asset", "fixed_visual_asset", "quality_report", "script", "shot"],
        "reference_policy": "reference_only_no_node_write",
        "proposed_extensions_require_evaluator": True,
    }


def test_fixture_rejects_unapproved_graph_extension_node() -> None:
    from agentflow.algorithms.shared_object_evidence import load_json_fixture, validate_shared_object_evidence_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    branch_node = _object(payload, "production_graph_node:branch-choice-reveal")
    branch_node["graph_stage"] = "storyboard_candidate_graph"
    branch_node["allowed_node_policy"] = "current_allowed"

    with pytest.raises(ValueError, match="unapproved production graph node"):
        validate_shared_object_evidence_fixture(payload)


def test_fixture_rejects_unresolved_references() -> None:
    from agentflow.algorithms.shared_object_evidence import load_json_fixture, validate_shared_object_evidence_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _object(payload, "handoff:stage1-shared-contract")["target_refs"].append("shot:missing")

    with pytest.raises(ValueError, match="unresolved reference"):
        validate_shared_object_evidence_fixture(payload)


def test_fixture_rejects_unsafe_payload_markers() -> None:
    from agentflow.algorithms.shared_object_evidence import load_json_fixture, validate_shared_object_evidence_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    unsafe_key = "_".join(["signed", "url"])
    _object(payload, "evidence:storyboard-safe-manifest")[unsafe_key] = "https://example.invalid/private"

    with pytest.raises(ValueError, match="unsafe marker"):
        validate_shared_object_evidence_fixture(payload)


def test_fixture_requires_evidence_gap_for_partial_state() -> None:
    from agentflow.algorithms.shared_object_evidence import load_json_fixture, validate_shared_object_evidence_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _object(payload, "branch_path:choice-reveal").pop("evidence_gap_reason")

    with pytest.raises(ValueError, match="partial evidence requires evidence_gap_reason"):
        validate_shared_object_evidence_fixture(payload)


def test_fixture_preserves_non_claims_fail_closed() -> None:
    from agentflow.algorithms.shared_object_evidence import load_json_fixture, validate_shared_object_evidence_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    mutated = copy.deepcopy(payload)
    mutated["non_claims"]["provider_smoke"] = True

    with pytest.raises(ValueError, match="protected non-claim"):
        validate_shared_object_evidence_fixture(mutated)


def _object(payload: dict, ref_id: str) -> dict:
    for item in payload["objects"]:
        if item["ref_id"] == ref_id:
            return item
    raise AssertionError(ref_id)
