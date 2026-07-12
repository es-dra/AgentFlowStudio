from __future__ import annotations

import json

from apps.api.runtime_errors import response_contains_unsafe_marker


def test_asset_auto_binding_algorithm_exports_contract() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import asset_auto_binding

    assert "asset_auto_binding" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert asset_auto_binding.ALGORITHM_ID == "afs.asset_auto_binding.v0.1"
    assert asset_auto_binding.INPUT_CONTRACT
    assert asset_auto_binding.OUTPUT_CONTRACT
    assert asset_auto_binding.FAILURE_MODES
    assert asset_auto_binding.EVIDENCE_BOUNDARY


def test_asset_auto_binding_establishes_reversible_explainable_graph_relationship() -> None:
    from agentflow.algorithms.asset_auto_binding import build_asset_auto_binding_graph

    graph = build_asset_auto_binding_graph(
        project_id="proj_auto_bind",
        asset_graph=_asset_graph(),
        fixed_visual_assets=[_fixed_asset()],
    )
    suggestion = graph["binding_suggestions"][0]
    relationship = graph["relationships"][0]
    serialized = json.dumps(graph, ensure_ascii=False).lower()

    assert graph["artifact_type"] == "agentflow_asset_auto_binding_graph"
    assert graph["binding_policy"]["fail_closed"] is True
    assert graph["summary"]["suggested_binding_count"] == 1
    assert graph["summary"]["established_binding_count"] == 1
    assert graph["summary"]["blocked_candidate_count"] == 0
    assert graph["writes_long_term_memory"] is False
    assert graph["writes_company_kb"] is False

    assert suggestion["binding_state"] == "bound"
    assert suggestion["binding_decision"] == "auto_established"
    assert suggestion["graph_asset_id"] == "graph:character:future_robot"
    assert suggestion["fixed_visual_asset_id"] == "vas_future_robot"
    assert suggestion["explainability"]["candidate_evidence_span_count"] == 1
    assert suggestion["explainability"]["fixed_source_evidence_available"] is True
    assert suggestion["reversal_plan"] == {
        "reversible": True,
        "action": "unbind",
        "restores_binding_state": "unbound",
        "preserve_lineage": True,
        "destructive_asset_write": False,
    }
    assert suggestion["safety_boundary"]["provider_calls_started"] is False

    assert relationship["relationship_type"] == "asset_auto_binding_established"
    assert relationship["from_node_id"] == "asset:graph:character:future_robot"
    assert relationship["to_node_id"] == "fixed_asset:vas_future_robot"
    assert relationship["reversible"] is True
    assert response_contains_unsafe_marker(graph) is False
    assert "api_key" not in serialized
    assert "data_base64" not in serialized


def test_asset_auto_binding_fails_closed_for_low_confidence_and_missing_evidence() -> None:
    from agentflow.algorithms.asset_auto_binding import build_asset_auto_binding_graph

    graph = build_asset_auto_binding_graph(
        project_id="proj_auto_bind",
        asset_graph=_asset_graph(confidence=0.61, evidence_spans=[]),
        fixed_visual_assets=[_fixed_asset(source_evidence={})],
    )
    blocked = graph["blocked_candidates"][0]

    assert graph["summary"]["established_binding_count"] == 0
    assert graph["summary"]["blocked_candidate_count"] == 1
    assert blocked["binding_state"] == "blocked"
    assert {
        "low_confidence_candidate",
        "missing_candidate_evidence",
        "missing_fixed_source_evidence",
    } <= set(blocked["block_reasons"])
    assert graph["relationships"] == []


def test_asset_auto_binding_blocks_ambiguous_or_review_required_graphs() -> None:
    from agentflow.algorithms.asset_auto_binding import build_asset_auto_binding_graph

    asset_graph = _asset_graph(unsupported_additions=[{"shot_id": "shot_01", "addition": "new object"}])
    graph = build_asset_auto_binding_graph(
        project_id="proj_auto_bind",
        asset_graph=asset_graph,
        fixed_visual_assets=[_fixed_asset(), _fixed_asset(asset_id="vas_future_robot_duplicate")],
    )
    reasons = set(graph["blocked_candidates"][0]["block_reasons"])

    assert graph["summary"]["established_binding_count"] == 0
    assert graph["summary"]["blocked_candidate_count"] == 1
    assert "ambiguous_fixed_asset_match" in reasons
    assert "unsupported_additions_require_review" in reasons
    assert graph["binding_policy"]["reversibility_required"] is True


def _asset_graph(*, confidence: float = 0.91, evidence_spans: list[dict] | None = None, unsupported_additions: list[dict] | None = None) -> dict:
    return {
        "artifact_type": "agentflow_asset_graph",
        "schema_version": "0.1.0",
        "asset_count": 1,
        "assets": [
            {
                "graph_asset_id": "graph:character:future_robot",
                "asset_id": "candidate:character:future_robot",
                "asset_type": "character",
                "label": "Future Robot",
                "status": "candidate",
                "review_state": "candidate_review_required",
                "confidence": confidence,
                "evidence_spans": evidence_spans
                if evidence_spans is not None
                else [{"shot_id": "shot_01", "source_span_id": "span_01", "text": "Future Robot watches the sky."}],
            }
        ],
        "relationships": [],
        "unsupported_additions": unsupported_additions or [],
        "merge_candidates": [],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _fixed_asset(*, asset_id: str = "vas_future_robot", source_evidence: dict | None = None) -> dict:
    return {
        "asset_id": asset_id,
        "asset_type": "character",
        "label": "Future Robot",
        "status": "fixed",
        "source_node_id": "node-ref-future-robot",
        "source_evidence": source_evidence
        if source_evidence is not None
        else {
            "source_contract": "fixed_asset_promotion_gate",
            "source_human_gate_id": "runtime-human-gate:robot:accepted",
            "source_asset_card_candidate_id": "asset_card_candidate:graph_character_future_robot",
            "source_stage": "asset_card_candidate_review",
            "result_asset_status": "fixed",
            "provider_calls_started": False,
            "generated_media_claimed": False,
            "human_creative_acceptance_claimed": False,
            "business_validation_claimed": False,
        },
    }
