from __future__ import annotations

import base64
import copy
import json
import re
from pathlib import Path

from apps.api.runtime_errors import response_contains_unsafe_marker


def test_node_reference_stack_algorithm_exports_contract() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import node_reference_stack

    assert "node_reference_stack" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert node_reference_stack.ALGORITHM_ID == "afs.node_reference_stack.v0.1"
    assert node_reference_stack.INPUT_CONTRACT
    assert node_reference_stack.OUTPUT_CONTRACT
    assert node_reference_stack.FAILURE_MODES
    assert node_reference_stack.EVIDENCE_BOUNDARY


def test_node_reference_stack_resolves_priority_scope_and_type_precedence() -> None:
    from agentflow.algorithms.node_reference_stack import build_node_reference_stack

    stack = build_node_reference_stack(
        project_id="proj_refs",
        node_id="node-keyframe-01",
        references=[
            _reference("project-character", "project_asset", "project", "primary_character", "asset:future_robot", 80, "fixed"),
            _reference("node-upload", "reference_input", "node", "primary_character", "upload:future_robot", 90, "bound"),
            _reference("shot-keyframe", "keyframe_version", "shot", "lighting", "keyframe:v1", 50, "succeeded"),
            _reference("node-binding", "binding", "node", "lighting", "binding:fixed_rooftop", 50, "bound"),
            _reference("node-ref-style", "reference_input", "node", "style", "upload:style", 45, "bound"),
            _reference("node-binding-style", "binding", "node", "style", "binding:style", 45, "bound"),
        ],
    )

    selected_ids = {item["reference_id"] for item in stack["reference_stack"]}
    strategies = {item["conflict_key"]: item["resolution_strategy"] for item in stack["conflicts"]}

    assert selected_ids == {"node-upload", "node-binding", "node-binding-style"}
    assert stack["summary"]["selected_reference_count"] == 3
    assert strategies["primary_character"] == "resolved_by_priority"
    assert strategies["lighting"] == "resolved_by_scope_precedence"
    assert strategies["style"] == "resolved_by_type_precedence"
    assert any(item["reference_id"] == "project-character" and item["conflict_state"] == "shadowed" for item in stack["references"])
    assert any(item["reference_id"] == "shot-keyframe" and item["conflict_state"] == "shadowed" for item in stack["references"])
    assert all(item["reversal_plan"]["reversible"] is True for item in stack["reference_stack"])


def test_node_reference_stack_fails_closed_for_unusable_state_and_equal_rank_conflict() -> None:
    from agentflow.algorithms.node_reference_stack import build_node_reference_stack

    stack = build_node_reference_stack(
        project_id="proj_refs",
        node_id="node-keyframe-01",
        references=[
            _reference("unbound-ref", "reference_input", "node", "pose", "upload:pose_a", 100, "unbound"),
            _reference("pose-a", "reference_input", "node", "pose", "upload:pose_a", 90, "bound"),
            _reference("pose-b", "reference_input", "node", "pose", "upload:pose_b", 90, "bound"),
        ],
    )
    conflict = stack["conflicts"][0]
    blocked = {item["reference_id"]: set(item["block_reasons"]) for item in stack["references"] if item["conflict_state"] == "blocked"}

    assert stack["summary"]["selected_reference_count"] == 0
    assert conflict["resolution_strategy"] == "unresolved_equal_rank_conflict"
    assert conflict["requires_human_review"] is True
    assert "reference_state_not_usable" in blocked["unbound-ref"]
    assert "unresolved_equal_rank_conflict" in blocked["pose-a"]
    assert "unresolved_equal_rank_conflict" in blocked["pose-b"]


def test_node_reference_stack_imports_asset_auto_binding_suggestions_as_binding_refs() -> None:
    from agentflow.algorithms.asset_auto_binding import build_asset_auto_binding_graph
    from agentflow.algorithms.node_reference_stack import build_node_reference_stack

    binding_graph = build_asset_auto_binding_graph(
        project_id="proj_refs",
        asset_graph=_asset_graph(),
        fixed_visual_assets=[_fixed_asset()],
    )
    stack = build_node_reference_stack(
        project_id="proj_refs",
        node_id="node-keyframe-01",
        references=[],
        asset_auto_binding_graph=binding_graph,
    )
    selected = stack["reference_stack"][0]
    relationship = stack["relationships"][0]

    assert stack["asset_auto_binding_contract"]["algorithm_id"] == "afs.asset_auto_binding.v0.1"
    assert stack["asset_auto_binding_contract"]["relationship_type"] == "asset_auto_binding_established"
    assert selected["reference_type"] == "binding"
    assert selected["status"] == "bound"
    assert selected["priority"] == 91
    assert selected["source"] == "asset_auto_binding_graph"
    assert selected["source_relationship_type"] == "asset_auto_binding_established"
    assert selected["reversal_plan"]["action"] == "unbind"
    assert relationship["relationship_type"] == "node_reference_selected"
    assert relationship["to_ref"] == "fixed_asset:vas_future_robot"
    assert response_contains_unsafe_marker(stack) is False


def test_node_reference_stack_uses_existing_studio_vocabulary_and_safe_boundaries() -> None:
    from agentflow.algorithms.node_reference_stack import STUDIO_REFERENCE_ACTIONS, STUDIO_REFERENCE_ENTITIES, build_node_reference_stack

    studio_vocab = Path("apps/studio/src/studio-entity-status-vocabulary.js").read_text(encoding="utf-8")
    for entity_id in STUDIO_REFERENCE_ENTITIES:
        assert f'"{entity_id}"' in studio_vocab
    for action_id in STUDIO_REFERENCE_ACTIONS:
        assert f'action("{action_id}"' in studio_vocab

    stack = build_node_reference_stack(
        project_id="proj_refs",
        node_id="node-keyframe-01",
        references=[
            _reference(
                "unsafe-ref",
                "reference_input",
                "node",
                "primary_character",
                "https://example.test/signed?token=abc",
                100,
                "bound",
            )
        ],
    )
    serialized = json.dumps(stack, ensure_ascii=False).lower()
    blocked = stack["references"][0]

    assert blocked["conflict_state"] == "blocked"
    assert "unsafe_target_ref" in blocked["block_reasons"]
    assert stack["safety_boundary"]["provider_calls_started"] is False
    assert stack["writes_long_term_memory"] is False
    assert "token=abc" not in serialized
    assert "https://example.test" not in serialized


def test_node_reference_stack_reversal_actions_match_studio_applies_to() -> None:
    from agentflow.algorithms.node_reference_stack import build_node_reference_stack

    action_applies_to = _studio_action_applies_to()
    stack = build_node_reference_stack(
        project_id="proj_refs",
        node_id="node-keyframe-01",
        references=[
            _reference("project-asset-ref", "project_asset", "node", "slot_project_asset", "asset:future_robot", 10, "fixed"),
            _reference("reference-input-ref", "reference_input", "node", "slot_reference_input", "upload:future_robot", 10, "bound"),
            _reference("candidate-ref", "generation_candidate", "node", "slot_generation_candidate", "candidate:image:v1", 10, "succeeded"),
            _reference("keyframe-ref", "keyframe_version", "node", "slot_keyframe_version", "keyframe:v1", 10, "succeeded"),
            _reference("video-ref", "video_revision", "node", "slot_video_revision", "video:v1", 10, "succeeded"),
            _reference("binding-ref", "binding", "node", "slot_binding", "binding:future_robot", 10, "bound"),
            _reference("lineage-ref", "lineage", "node", "slot_lineage", "lineage:future_robot", 10, "available"),
        ],
    )

    assert stack["summary"]["selected_reference_count"] == 7
    for item in stack["reference_stack"]:
        action = item["reversal_plan"]["action"]
        assert item["reference_type"] in action_applies_to[action]
    candidate = next(item for item in stack["reference_stack"] if item["reference_type"] == "generation_candidate")
    assert candidate["reversal_plan"]["action"] == "reject"


def test_node_reference_stack_blocks_data_urls_and_media_byte_like_targets() -> None:
    from agentflow.algorithms.node_reference_stack import build_node_reference_stack

    long_base64_media = base64.b64encode(b"\x00" * 800).decode("ascii")
    stack = build_node_reference_stack(
        project_id="proj_refs",
        node_id="node-keyframe-01",
        references=[
            _reference("data-text", "reference_input", "node", "data_text", "data:text/plain,hello", 100, "bound"),
            _reference("data-image", "reference_input", "node", "data_image", "data:image/png;base64,iVBORw0KGgo=", 100, "bound"),
            _reference("raw-png-base64", "reference_input", "node", "raw_png", "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB", 100, "bound"),
            _reference("long-base64-media", "reference_input", "node", "long_media", long_base64_media, 100, "bound"),
        ],
    )
    blocked = {item["reference_id"]: item for item in stack["references"]}
    serialized = json.dumps(stack, ensure_ascii=False).lower()

    assert stack["summary"]["selected_reference_count"] == 0
    assert all(item["conflict_state"] == "blocked" for item in blocked.values())
    assert all("unsafe_target_ref" in item["block_reasons"] for item in blocked.values())
    assert all(item["target_ref"] == "unsafe_ref_redacted" for item in blocked.values())
    assert "data:image" not in serialized
    assert "data:text" not in serialized
    assert "ivborw0kggo" not in serialized


def test_node_reference_stack_fails_closed_for_malformed_asset_auto_binding_graph_imports() -> None:
    from agentflow.algorithms.asset_auto_binding import build_asset_auto_binding_graph
    from agentflow.algorithms.node_reference_stack import build_node_reference_stack

    binding_graph = build_asset_auto_binding_graph(
        project_id="proj_refs",
        asset_graph=_asset_graph(),
        fixed_visual_assets=[_fixed_asset()],
    )
    empty_fixed_asset_id = copy.deepcopy(binding_graph)
    empty_fixed_asset_id["binding_suggestions"][0]["fixed_visual_asset_id"] = ""
    missing_established_relationship = copy.deepcopy(binding_graph)
    missing_established_relationship["relationships"] = []
    missing_source_relationship = copy.deepcopy(binding_graph)
    missing_source_relationship["relationships"][0].pop("source")
    missing_source_relationship["relationships"][0].pop("from_node_id")

    cases = [
        (empty_fixed_asset_id, "asset_binding_missing_fixed_asset_id"),
        (missing_established_relationship, "asset_binding_missing_established_relationship"),
        (missing_source_relationship, "asset_binding_missing_source_relationship"),
    ]
    for graph, expected_reason in cases:
        stack = build_node_reference_stack(
            project_id="proj_refs",
            node_id="node-keyframe-01",
            references=[],
            asset_auto_binding_graph=graph,
        )
        imported = stack["references"][0]

        assert stack["summary"]["asset_auto_binding_reference_count"] == 1
        assert stack["summary"]["selected_reference_count"] == 0
        assert stack["reference_stack"] == []
        assert stack["relationships"] == []
        assert imported["conflict_state"] == "blocked"
        assert expected_reason in imported["block_reasons"]


def _studio_action_applies_to() -> dict[str, set[str]]:
    studio_vocab = Path("apps/studio/src/studio-entity-status-vocabulary.js").read_text(encoding="utf-8")
    action_pattern = re.compile(r'action\("([^"]+)",\s*"[^"]+",\s*\[([^\]]*)\]\)')
    actions: dict[str, set[str]] = {}
    for action_id, applies_to_source in action_pattern.findall(studio_vocab):
        actions[action_id] = set(re.findall(r'"([^"]+)"', applies_to_source))
    return actions


def _reference(reference_id: str, reference_type: str, scope: str, slot: str, target_ref: str, priority: int, status: str) -> dict:
    return {
        "reference_id": reference_id,
        "reference_type": reference_type,
        "scope": scope,
        "target_slot": slot,
        "target_ref": target_ref,
        "priority": priority,
        "status": status,
        "source": "focused_test",
    }


def _asset_graph() -> dict:
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
                "confidence": 0.91,
                "evidence_spans": [{"shot_id": "shot_01", "source_span_id": "span_01", "text": "Future Robot watches the sky."}],
            }
        ],
        "relationships": [],
        "unsupported_additions": [],
        "merge_candidates": [],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _fixed_asset() -> dict:
    return {
        "asset_id": "vas_future_robot",
        "asset_type": "character",
        "label": "Future Robot",
        "status": "fixed",
        "source_node_id": "node-ref-future-robot",
        "source_evidence": {
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
