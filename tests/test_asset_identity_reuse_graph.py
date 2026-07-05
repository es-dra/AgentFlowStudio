from __future__ import annotations

import json
from pathlib import Path


FIXTURE = Path("tests/fixtures/asset_identity_reuse_graph/asset_identity_reuse_graph_contract_fixture.json")
FORBIDDEN_FIELDS = {
    "raw_provider_response",
    "provider_raw_payload",
    "signed_url",
    "image_path",
    "output_path",
    "request_path",
    "local_path",
    "media_bytes",
    "data_base64",
    "api_key",
    "token",
    "cookie",
    "authorization",
    "provider_key",
}


def test_same_asset_across_shots_auto_links_with_signature_and_safe_asset_id_evidence() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import asset_identity_reuse_graph as reuse_graph

    fixture = _fixture()
    graph = reuse_graph.build_asset_identity_reuse_graph(
        project_id=fixture["project_id"],
        observed_assets=fixture["same_asset_across_shots"],
    )
    node = graph["canonical_asset_nodes"][0]
    edge = graph["auto_link_edges"][0]

    assert "asset_identity_reuse_graph" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert reuse_graph.ALGORITHM_ID == "afs.asset_identity_reuse_graph.v0.1"
    assert reuse_graph.INPUT_CONTRACT
    assert reuse_graph.OUTPUT_CONTRACT
    assert reuse_graph.FAILURE_MODES
    assert graph["artifact_type"] == "agentflow_asset_identity_reuse_graph"
    assert graph["graph_state"] == "ready"
    assert graph["summary"]["canonical_asset_node_count"] == 1
    assert graph["summary"]["auto_link_edge_count"] == 1
    assert graph["summary"]["blocked_observation_count"] == 0
    assert node["canonical_asset_node_id"].startswith(
        "asset_identity:proj_identity:character:asset:character:mira_fixed_01:"
    )
    assert node["identity_key_fields"] == [
        "asset_type",
        "descriptive_signature",
        "safe_asset_id_evidence",
    ]
    assert node["label_policy"]["display_name_used_as_identity_key"] is False
    assert edge["relationship_type"] == "asset_identity_reuse_auto_link"
    assert edge["review_required"] is False
    assert edge["observation_ids"] == ["obs_shot_001_mira", "obs_shot_002_mira"]
    _assert_boundary(graph)


def test_display_name_only_never_auto_links() -> None:
    from agentflow.algorithms.asset_identity_reuse_graph import build_asset_identity_reuse_graph

    fixture = _fixture()
    graph = build_asset_identity_reuse_graph(
        project_id=fixture["project_id"],
        observed_assets=fixture["display_name_only"],
    )

    assert graph["summary"]["canonical_asset_node_count"] == 0
    assert graph["summary"]["auto_link_edge_count"] == 0
    assert graph["canonical_asset_nodes"] == []
    assert graph["auto_link_edges"] == []
    assert {reason for item in graph["blocked_observations"] for reason in item["block_reasons"]} >= {
        "display_name_only_not_identity_key",
        "missing_descriptive_signature",
        "missing_safe_asset_id_evidence",
    }
    _assert_boundary(graph)


def test_alias_suggestions_are_review_only_and_stay_below_autolink_range() -> None:
    from agentflow.algorithms import asset_identity_reuse_graph as reuse_graph

    fixture = _fixture()
    graph = reuse_graph.build_asset_identity_reuse_graph(
        project_id=fixture["project_id"],
        observed_assets=fixture["alias_candidate"],
    )
    suggestion = graph["alias_suggestions"][0]
    alias = suggestion["suggested_aliases"][0]

    assert graph["summary"]["auto_link_edge_count"] == 1
    assert graph["summary"]["alias_suggestion_count"] == 1
    assert suggestion["suggestion_state"] == "review_required"
    assert suggestion["review_only"] is True
    assert suggestion["auto_link_authorized"] is False
    assert reuse_graph.ALIAS_SUGGESTION_MIN_CONFIDENCE <= alias["confidence"] <= reuse_graph.ALIAS_SUGGESTION_MAX_CONFIDENCE
    assert alias["confidence"] < reuse_graph.MIN_AUTOLINK_CONFIDENCE
    assert "display_name" not in graph["canonical_asset_nodes"][0]["identity_key_fields"]
    _assert_boundary(graph)


def test_conflict_or_reversal_blocks_auto_link() -> None:
    from agentflow.algorithms.asset_identity_reuse_graph import build_asset_identity_reuse_graph

    fixture = _fixture()
    conflict_case = [
        fixture["same_asset_across_shots"][0],
        {**fixture["same_asset_across_shots"][1], "conflict_state": "conflicted"},
    ]
    reversal_case = [
        fixture["same_asset_across_shots"][0],
        {**fixture["same_asset_across_shots"][1], "reversal_state": "reversed"},
    ]

    for observed_assets in (conflict_case, reversal_case):
        graph = build_asset_identity_reuse_graph(project_id=fixture["project_id"], observed_assets=observed_assets)
        reasons = {reason for item in graph["blocked_observations"] for reason in item["block_reasons"]}
        assert graph["graph_state"] == "blocked_conflict"
        assert graph["summary"]["auto_link_edge_count"] == 0
        assert graph["auto_link_edges"] == []
        assert "identity_group_contains_conflict_or_reversal" in reasons
        _assert_boundary(graph)


def test_generic_or_provisional_names_do_not_become_identity_keys() -> None:
    from agentflow.algorithms.asset_identity_reuse_graph import build_asset_identity_reuse_graph

    graph = build_asset_identity_reuse_graph(
        project_id="proj_identity",
        observed_assets=[
            {"observation_id": "generic_1", "shot_id": "shot_001", "asset_type": "character", "display_name": "Character A"},
            {"observation_id": "generic_2", "shot_id": "shot_002", "asset_type": "character", "display_name": "Unnamed Hero"},
        ],
    )
    reasons = {reason for item in graph["blocked_observations"] for reason in item["block_reasons"]}

    assert graph["canonical_asset_nodes"] == []
    assert graph["auto_link_edges"] == []
    assert graph["summary"]["generic_or_provisional_name_rejected_count"] == 2
    assert "generic_or_provisional_name_not_identity_key" in reasons
    _assert_boundary(graph)


def test_proper_name_evidence_strengthens_signature_backed_matches_but_name_only_does_not_link() -> None:
    from agentflow.algorithms.asset_identity_reuse_graph import build_asset_identity_reuse_graph

    fixture = _fixture()
    proper_name_only = [
        {
            "observation_id": "proper_name_only_1",
            "shot_id": "shot_001",
            "asset_type": "character",
            "display_name": "Mira Vale",
            "proper_name_evidence": [{"name": "Mira Vale", "source_ref_id": "script_span:mira_name"}],
        },
        {
            "observation_id": "proper_name_only_2",
            "shot_id": "shot_002",
            "asset_type": "character",
            "display_name": "Mira Vale",
            "proper_name_evidence": [{"name": "Mira Vale", "source_ref_id": "script_span:mira_name"}],
        },
    ]
    name_only_graph = build_asset_identity_reuse_graph(project_id=fixture["project_id"], observed_assets=proper_name_only)
    base_graph = build_asset_identity_reuse_graph(
        project_id=fixture["project_id"],
        observed_assets=fixture["same_asset_across_shots"],
    )
    strengthened_graph = build_asset_identity_reuse_graph(
        project_id=fixture["project_id"],
        observed_assets=fixture["proper_name_signature_backed"],
    )

    assert name_only_graph["summary"]["auto_link_edge_count"] == 0
    assert "proper_name_only_not_identity_key" in {
        reason for item in name_only_graph["blocked_observations"] for reason in item["block_reasons"]
    }
    assert strengthened_graph["summary"]["auto_link_edge_count"] == 1
    assert strengthened_graph["canonical_asset_nodes"][0]["evidence_strength"]["proper_name_evidence"] is True
    assert "proper_name_evidence_strengthened_match" in strengthened_graph["auto_link_edges"][0]["matched_evidence"]
    assert strengthened_graph["auto_link_edges"][0]["confidence"] > base_graph["auto_link_edges"][0]["confidence"]
    _assert_boundary(name_only_graph)
    _assert_boundary(strengthened_graph)


def test_unsafe_payload_rejection_fails_closed_without_echoing_values() -> None:
    from agentflow.algorithms.asset_identity_reuse_graph import build_asset_identity_reuse_graph

    graph = build_asset_identity_reuse_graph(
        project_id="proj_identity",
        observed_assets=[
            {
                "observation_id": "unsafe_1",
                "shot_id": "shot_001",
                "asset_type": "character",
                "display_name": "Mira",
                "descriptive_signature": "silver braid",
                "asset_id_evidence": [{"asset_id": "asset:character:mira_fixed_01"}],
                "raw_provider_response": {"signed_url": "https://private.example.test/out.png?token=secret-token-value"},
            }
        ],
    )
    serialized = json.dumps(graph, ensure_ascii=False).lower()

    assert graph["graph_state"] == "blocked_unsafe"
    assert graph["summary"]["unsafe_input_rejected"] is True
    assert graph["canonical_asset_nodes"] == []
    assert graph["auto_link_edges"] == []
    assert "private.example" not in serialized
    assert "secret-token-value" not in serialized
    _assert_boundary(graph)


def test_algorithm_has_no_provider_media_or_runtime_dependency() -> None:
    from agentflow.algorithms.asset_identity_reuse_graph import build_asset_identity_reuse_graph

    source = Path("agentflow/algorithms/asset_identity_reuse_graph/__init__.py").read_text(encoding="utf-8")
    banned_import_markers = (
        "import httpx",
        "import requests",
        "import openai",
        "apps.api",
        "agentflow_studio.model_gateway",
        "provider_adapter",
        "import subprocess",
        "import PIL",
        "import cv2",
    )
    graph = build_asset_identity_reuse_graph(project_id="proj_identity", observed_assets=_fixture()["same_asset_across_shots"])

    assert all(marker not in source for marker in banned_import_markers)
    assert graph["audit_metadata"]["provider_calls_started"] is False
    assert graph["audit_metadata"]["generated_media_claimed"] is False
    assert graph["audit_metadata"]["writes_long_term_memory"] is False
    assert graph["audit_metadata"]["writes_company_kb"] is False
    _assert_boundary(graph)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _assert_boundary(graph: dict) -> None:
    serialized = json.dumps(graph, ensure_ascii=False).lower()
    assert graph["provider_calls_started"] is False
    assert graph["generated_media_claimed"] is False
    assert graph["writes_long_term_memory"] is False
    assert graph["writes_company_kb"] is False
    assert graph["audit_metadata"]["provider_calls_started"] is False
    assert graph["audit_metadata"]["generated_media_claimed"] is False
    assert graph["audit_metadata"]["writes_long_term_memory"] is False
    assert graph["audit_metadata"]["writes_company_kb"] is False
    for field in FORBIDDEN_FIELDS:
        assert field not in serialized
