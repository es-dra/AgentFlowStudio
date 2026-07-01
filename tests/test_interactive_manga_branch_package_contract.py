from __future__ import annotations

import copy
from pathlib import Path

import pytest


FIXTURE_PATH = Path("tests/fixtures/interactive_manga_branch_package/branch_package_fixture.json")


def test_interactive_manga_branch_package_algorithm_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import interactive_manga_branch_package

    assert "interactive_manga_branch_package" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert interactive_manga_branch_package.ALGORITHM_ID == "afs.interactive_manga_branch_package.v0.1"
    assert interactive_manga_branch_package.INPUT_CONTRACT
    assert interactive_manga_branch_package.OUTPUT_CONTRACT
    assert interactive_manga_branch_package.FAILURE_MODES
    assert interactive_manga_branch_package.EVIDENCE_BOUNDARY


def test_branch_package_fixture_loads_with_one_choice_and_two_paths() -> None:
    from agentflow.algorithms.interactive_manga_branch_package import load_branch_package_fixture

    report = load_branch_package_fixture(FIXTURE_PATH)

    assert report["fixture_id"] == "interactive_manga_branch_package_fixture_v0"
    assert report["fixture_claim_level"] == "deterministic_branch_package_structure_only"
    assert report["summary"] == {
        "choice_point_count": 1,
        "branch_path_count": 2,
        "branch_shot_count": 4,
        "asset_need_count": 3,
        "shared_asset_need_count": 1,
        "branch_specific_asset_need_count": 2,
        "continuity_constraint_count": 3,
        "evidence_requirement_count": 4,
    }
    assert report["branch_paths"] == {
        "branch_path:reveal": ["branch_shot:reveal-001", "branch_shot:reveal-002"],
        "branch_path:hide": ["branch_shot:hide-001", "branch_shot:hide-002"],
    }


def test_branch_shots_map_to_base_storyboard_and_branch_specific_refs() -> None:
    from agentflow.algorithms.interactive_manga_branch_package import load_branch_package_fixture

    report = load_branch_package_fixture(FIXTURE_PATH)

    for mapping in report["branch_shot_mappings"]:
        assert mapping["base_storyboard_ref"] == "storyboard:demo-001"
        assert mapping["base_shot_ref"].startswith("shot:base-")
        assert mapping["branch_specific_shot_ref"].startswith("shot:branch-")
        assert mapping["branch_specific_shot_ref"] != mapping["base_shot_ref"]


def test_asset_and_continuity_scopes_are_explicit() -> None:
    from agentflow.algorithms.interactive_manga_branch_package import load_branch_package_fixture

    report = load_branch_package_fixture(FIXTURE_PATH)

    assert report["asset_need_scopes"] == {
        "branch_specific": 2,
        "shared_across_package": 1,
    }
    assert report["continuity_scopes"] == {
        "branch_specific": 1,
        "shared_across_paths": 2,
    }
    assert report["all_paths_have_shared_and_branch_specific_assets"] is True
    assert report["all_paths_have_continuity_constraints"] is True


def test_evidence_requirements_map_to_safe_ref_families_without_graph_writes() -> None:
    from agentflow.algorithms.interactive_manga_branch_package import load_branch_package_fixture

    report = load_branch_package_fixture(FIXTURE_PATH)

    assert report["evidence_mapping_fields"] == [
        "asset_refs",
        "evidence_refs",
        "handoff_envelope_refs",
        "production_graph_artifact_refs",
        "storyboard_refs",
    ]
    assert report["production_graph_boundary"] == {
        "reference_policy": "reference_only_no_node_write",
        "graph_node_writes_required": False,
        "graph_artifact_refs": ["artifact_production_graph_snapshot_demo"],
    }


def test_fixture_rejects_unresolved_branch_refs() -> None:
    from agentflow.algorithms.interactive_manga_branch_package import load_json_fixture, validate_branch_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    payload["branch_package"]["branch_paths"][0]["branch_shot_refs"].append("branch_shot:missing")

    with pytest.raises(ValueError, match="unresolved reference"):
        validate_branch_package_fixture(payload)


def test_fixture_rejects_unsafe_payload_markers() -> None:
    from agentflow.algorithms.interactive_manga_branch_package import load_json_fixture, validate_branch_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    unsafe_key = "_".join(["signed", "url"])
    payload["branch_package"]["evidence_requirements"][0][unsafe_key] = "https://example.invalid/private"

    with pytest.raises(ValueError, match="unsafe marker"):
        validate_branch_package_fixture(payload)


def test_fixture_preserves_protected_non_claims_fail_closed() -> None:
    from agentflow.algorithms.interactive_manga_branch_package import load_json_fixture, validate_branch_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    mutated = copy.deepcopy(payload)
    mutated["non_claims"]["provider_prompt_inclusion"] = True

    with pytest.raises(ValueError, match="protected non-claim"):
        validate_branch_package_fixture(mutated)


def test_fixture_carries_t52_and_stage1_residual_boundaries() -> None:
    from agentflow.algorithms.interactive_manga_branch_package import load_branch_package_fixture

    report = load_branch_package_fixture(FIXTURE_PATH)

    assert report["source_boundary_refs"] == [
        "handoff:stage1-shared-contract",
        "shared_object_evidence:fixture_v0",
        "docs/handoff/AFS-T52-SHARED-OBJECT-EVIDENCE-FIXTURE-20260701.md",
    ]
    assert report["stage1_residuals"] == ["stage1_evaluator_system_error_residual"]
    assert report["non_claims"]["final_schema_acceptance"] is False
    assert report["non_claims"]["product_readiness"] is False
    assert report["non_claims"]["reader_playback"] is False
