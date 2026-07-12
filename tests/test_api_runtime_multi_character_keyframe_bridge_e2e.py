from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app
from tests.runtime_main_loop_e2e_support import (
    benchmark_case,
    create_feedback_context_overlay,
    keyframe_preflight,
    promote_fixed_asset,
    storyboard_breakdown,
    upload_image,
)


def test_multi_character_benchmark_reaches_keyframe_bridge_source_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_multi_character_keyframe_bridge"
    client.post("/projects", json={"project_id": project_id, "goal": "Multi-character bridge baseline"}).raise_for_status()
    case = benchmark_case("multi_character_restaurant_note")
    zhou = _promote_character(client, project_id, label="周岚", node_id="node-ref-zhou-lan")
    chen = _promote_character(client, project_id, label="陈默", node_id="node-ref-chen-mo")
    storyboard_payload = storyboard_breakdown(
        client,
        project_id,
        case,
        node_id="script_multi_character_bridge_001",
        generated_at="2026-07-01T00:10:00+08:00",
    )
    overlay_state = create_feedback_context_overlay(
        client,
        project_id,
        storyboard_payload,
        node_id="script_multi_character_bridge_001",
        generated_at="2026-07-01T00:11:00+08:00",
        decisions=[
            {"graph_asset_id": "graph:character:周岚", "decision": "confirm", "label": "周岚", "note": "Keep Zhou Lan identity stable during the letter handoff."},
            {"graph_asset_id": "graph:character:陈默", "decision": "confirm", "label": "陈默", "note": "Keep Chen Mo identity stable during the chase to the doorway."},
        ],
        rationale="Use both character confirmations as local context evidence only.",
        reviewed_at="2026-07-01T00:12:00+08:00",
        overlay_intent="Keep two-character handoff continuity as bounded local evidence.",
        overlay_generated_at="2026-07-01T00:13:00+08:00",
    )
    overlay = overlay_state["overlay"]
    request_payload = _keyframe_request(zhou["asset_id"], chen["asset_id"], overlay["overlay_id"])

    preflight_payload = keyframe_preflight(client, project_id, request_payload)
    generation = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={**request_payload, "preflight_token": preflight_payload["preflight_token"]},
    )

    generation.raise_for_status()
    payload = generation.json()
    bridge = payload["generation_bridge"]
    request_plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()[
        "payload"
    ]
    request_context = request_plan["context_bundle"]
    source_refs = bridge["context_evidence"]["included_asset_source_evidence_refs"]
    source_candidate_ids = {item["source_asset_card_candidate_id"] for item in source_refs}
    source_human_gate_ids = {item["source_human_gate_id"] for item in source_refs}
    fixed_asset_ids = {item["asset_id"] for item in source_refs}
    request_plan_asset_ids = {item["asset_id"] for item in request_context["included_assets"]}
    request_plan_candidate_ids = {
        item["source_evidence"]["source_asset_card_candidate_id"] for item in request_context["included_assets"]
    }
    labels_by_type = {(asset["label"], asset["asset_type"]) for asset in storyboard_payload["asset_graph"]["assets"]}
    candidate_labels = {
        item["draft_fields"]["display_name"]
        for item in storyboard_payload["asset_card_candidates"]["candidates"]
    }
    serialized = json.dumps(
        {"generation": payload, "bridge": bridge, "request_plan_context": request_context},
        ensure_ascii=False,
    ).lower()
    low, high = case["expected_shot_range"]

    assert low <= len(storyboard_payload["shots"]) <= high
    assert {("周岚", "character"), ("陈默", "character"), ("餐厅", "scene")} <= labels_by_type
    assert ("信件", "prop") not in labels_by_type
    assert {"周岚", "陈默"} <= candidate_labels
    assert preflight_payload["included_asset_source_evidence_count"] == 2
    assert payload["job"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    assert payload["safe_manifest"]["provider_calls_started"] is False
    assert payload["safe_manifest"]["local_generation_bridge_ready"] is True
    assert payload["safe_manifest"]["context_included_asset_count"] == 2
    assert payload["candidate_previews"] == []
    assert payload["reusable_image_assets"] == []

    assert bridge["summary"]["generation_state"] == "blocked_before_provider"
    assert bridge["context_evidence"]["included_asset_count"] == 2
    assert bridge["context_evidence"]["included_asset_source_evidence_count"] == 2
    assert bridge["context_evidence"]["reference_image_count"] == 1
    assert bridge["context_evidence"]["feedback_context_overlay_ids"] == [overlay["overlay_id"]]
    assert bridge["context_evidence"]["feedback_context_overlay_prompt_policy"]["provider_prompt_includes_context_overlays"] is False
    assert fixed_asset_ids == {zhou["asset_id"], chen["asset_id"]}
    assert source_candidate_ids == {
        "asset_card_candidate:graph_character_周岚",
        "asset_card_candidate:graph_character_陈默",
    }
    assert source_human_gate_ids == {
        "runtime-human-gate:baseline:周岚:accepted",
        "runtime-human-gate:baseline:陈默:accepted",
    }
    assert request_plan_asset_ids == fixed_asset_ids
    assert request_plan_candidate_ids == source_candidate_ids
    assert request_context["feedback_context_overlays"][0]["overlay_id"] == overlay["overlay_id"]
    assert request_context["trace_summary"]["feedback_context_overlay_selected_ids"] == [overlay["overlay_id"]]
    assert all(item["provider_calls_started"] is False for item in source_refs)
    assert all(item["human_creative_acceptance_claimed"] is False for item in source_refs)
    assert bridge["provider_evidence"]["provider_gate"]["status"] == "blocked"
    assert bridge["provider_evidence"]["blocks"][0]["block_id"] == "remote_image_gate_closed"
    assert response_contains_unsafe_marker(bridge) is False
    assert response_contains_unsafe_marker(request_context) is False
    assert '"provider_raw"' not in serialized
    assert '"signed_url"' not in serialized
    assert "data_base64" not in serialized
    assert "d:\\" not in serialized


def _promote_character(client: TestClient, project_id: str, *, label: str, node_id: str) -> dict:
    image_asset_id = upload_image(client, project_id, node_id=node_id, filename=f"{node_id}.png")
    return promote_fixed_asset(
        client,
        project_id,
        image_asset_id,
        label=label,
        signature=f"{label} fixed character identity, restaurant-scene continuity",
        appearance=f"{label} character reference for restaurant note benchmark",
        source_node_id=node_id,
        source_human_gate_id=f"runtime-human-gate:baseline:{label}:accepted",
        source_asset_card_candidate_id=f"asset_card_candidate:graph_character_{label}",
    )


def _keyframe_request(zhou_asset_id: str, chen_asset_id: str, overlay_id: str) -> dict:
    return {
        "node_id": "keyframe_multi_character_bridge_001",
        "prompt_text": "Draw 周岚 pushing the letter toward 陈默 in the restaurant corner.",
        "optimized_prompt": "Cinematic two-character restaurant keyframe: 周岚 pushes the letter toward 陈默.",
        "target_platform": "short_video",
        "style": "cinematic",
        "context_subgraph": {
            "target_node_id": "keyframe_multi_character_bridge_001",
            "runtime_work_mode": "context_generate",
            "nodes": [
                {
                    "id": "keyframe_multi_character_bridge_001",
                    "type": "image",
                    "title": "Two-character handoff keyframe",
                    "prompt": "Draw the restaurant note handoff.",
                    "visual_asset_ids": [],
                    "node_parameters": {
                        "feedback_context_overlay_decisions": [
                            {
                                "overlay_id": overlay_id,
                                "decision": "include_for_next_context",
                                "provider_calls_started": False,
                                "writes_long_term_memory": False,
                                "writes_company_kb": False,
                            }
                        ]
                    },
                },
                {
                    "id": "fixed-asset-zhou-lan",
                    "type": "image",
                    "title": "周岚 fixed asset",
                    "prompt": "",
                    "visual_asset_ids": [zhou_asset_id],
                },
                {
                    "id": "fixed-asset-chen-mo",
                    "type": "image",
                    "title": "陈默 fixed asset",
                    "prompt": "",
                    "visual_asset_ids": [chen_asset_id],
                },
            ],
            "edges": [
                {"id": "edge-zhou-target", "from": "fixed-asset-zhou-lan", "to": "keyframe_multi_character_bridge_001", "relation_type": "reference"},
                {"id": "edge-chen-target", "from": "fixed-asset-chen-mo", "to": "keyframe_multi_character_bridge_001", "relation_type": "reference"},
            ],
        },
        "generated_at": "2026-07-01T00:14:00+08:00",
    }
