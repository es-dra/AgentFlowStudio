from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient


BENCHMARK_PATH = Path("examples/agentflow/content_quality_benchmark_scripts.example.json")
PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


@dataclass(frozen=True)
class MainLoopE2EState:
    case: dict
    image_asset_id: str
    fixed_asset: dict
    storyboard_payload: dict
    candidate: dict
    gate_payload: dict
    feedback_payload: dict
    feedback_candidate: dict
    promotion_payload: dict
    overlay_response_payload: dict
    overlay: dict
    keyframe_request: dict
    preflight_payload: dict


def build_main_loop_e2e_state(client: TestClient, project_id: str) -> MainLoopE2EState:
    client.post("/projects", json={"project_id": project_id, "goal": "Main loop E2E baseline"}).raise_for_status()
    case = benchmark_case("multi_scene_map_chase")
    image_asset_id = upload_image(client, project_id)
    fixed_asset = promote_fixed_asset(client, project_id, image_asset_id)
    storyboard_payload = _storyboard_breakdown(client, project_id, case)
    candidate = candidate_for_label(storyboard_payload, "林晚")
    gate_payload = _accept_candidate(client, project_id, storyboard_payload, candidate)
    feedback_payload = _record_asset_graph_feedback(client, project_id, storyboard_payload)
    feedback_candidate = feedback_payload["feedback_event"]["feedback_candidate"]
    promotion_payload = _promote_feedback_candidate(client, project_id, feedback_payload, feedback_candidate)
    overlay_response_payload = _create_feedback_overlay(client, project_id, promotion_payload)
    overlay = overlay_response_payload["feedback_candidate_context_overlay"]
    keyframe_request = keyframe_request_payload(fixed_asset["asset_id"], overlay["overlay_id"])
    preflight_payload = _keyframe_preflight(client, project_id, keyframe_request)
    return MainLoopE2EState(
        case=case,
        image_asset_id=image_asset_id,
        fixed_asset=fixed_asset,
        storyboard_payload=storyboard_payload,
        candidate=candidate,
        gate_payload=gate_payload,
        feedback_payload=feedback_payload,
        feedback_candidate=feedback_candidate,
        promotion_payload=promotion_payload,
        overlay_response_payload=overlay_response_payload,
        overlay=overlay,
        keyframe_request=keyframe_request,
        preflight_payload=preflight_payload,
    )


def benchmark_case(case_id: str) -> dict:
    payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    return next(case for case in payload["cases"] if case["id"] == case_id)


def candidate_for_label(payload: dict, label: str) -> dict:
    return next(
        item
        for item in payload["asset_card_candidates"]["candidates"]
        if item["draft_fields"]["display_name"] == label
    )


def upload_image(
    client: TestClient,
    project_id: str,
    *,
    node_id: str = "node-ref-lin-wan",
    filename: str = "lin-wan-reference.png",
) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": node_id,
            "filename": filename,
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-30T23:54:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]["asset_id"]


def promote_fixed_asset(
    client: TestClient,
    project_id: str,
    image_asset_id: str,
    *,
    label: str = "林晚",
    signature: str = "short black hair, red trench coat, alert investigator posture",
    appearance: str = "young investigator with short black hair and red trench coat",
    source_node_id: str = "node-ref-lin-wan",
    source_human_gate_id: str = "runtime-human-gate:baseline:accepted",
    source_asset_card_candidate_id: str = "asset_card_candidate:graph_character_林晚",
) -> dict:
    response = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_asset_id],
            "asset_type": "character",
            "label": label,
            "signature": signature,
            "feature_card": {"appearance": appearance},
            "negative_locks": ["do not change face identity", "keep red trench coat"],
            "source_node_id": source_node_id,
            "source_human_gate_id": source_human_gate_id,
            "source_asset_card_candidate_id": source_asset_card_candidate_id,
            "review_decision": "fixed",
            "reviewed_at": "2026-06-30T23:55:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]


def keyframe_request_payload(asset_id: str, overlay_id: str) -> dict:
    return {
        "node_id": "keyframe_main_loop_e2e_001",
        "prompt_text": "Draw 林晚 checking the red map on the rainy street.",
        "optimized_prompt": "Cinematic keyframe of 林晚 checking the red map on the rainy street.",
        "target_platform": "short_video",
        "style": "cinematic",
        "context_subgraph": context_subgraph(asset_id, overlay_id),
        "generated_at": "2026-07-01T00:03:00+08:00",
    }


def context_subgraph(asset_id: str, overlay_id: str) -> dict:
    return {
        "target_node_id": "keyframe_main_loop_e2e_001",
        "runtime_work_mode": "context_generate",
        "nodes": [
            {
                "id": "keyframe_main_loop_e2e_001",
                "type": "image",
                "title": "Target keyframe",
                "prompt": "Draw the next baseline keyframe.",
                "visual_asset_ids": [],
                "node_parameters": {
                    "feedback_context_overlay_decisions": [
                        {
                            "overlay_id": overlay_id,
                            "decision": "include_for_next_context",
                            "reviewed_at": "2026-07-01T00:03:00+08:00",
                            "provider_calls_started": False,
                            "writes_long_term_memory": False,
                            "writes_company_kb": False,
                        }
                    ]
                },
            },
            {
                "id": "fixed-asset-lin-wan",
                "type": "image",
                "title": "林晚 fixed asset",
                "prompt": "",
                "visual_asset_ids": [asset_id],
            },
        ],
        "edges": [
            {
                "id": "edge-fixed-asset-target",
                "from": "fixed-asset-lin-wan",
                "to": "keyframe_main_loop_e2e_001",
                "relation_type": "reference",
            }
        ],
    }


def _storyboard_breakdown(client: TestClient, project_id: str, case: dict) -> dict:
    response = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_main_loop_e2e_001",
            "script_text": case["script_text"],
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-30T23:58:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()


def _accept_candidate(client: TestClient, project_id: str, storyboard_payload: dict, candidate: dict) -> dict:
    response = client.post(
        f"/projects/{project_id}/human-gate-decisions",
        json={
            "target_type": "asset_card_candidate",
            "target_id": candidate["candidate_id"],
            "decision": "accepted_for_next_step",
            "artifact_id": storyboard_payload["artifacts"]["asset_card_candidates"]["artifact_id"],
            "node_id": "script_main_loop_e2e_001",
            "scope": "asset_card_candidate_review",
            "note": "Baseline character candidate can feed the next local context pass.",
            "reviewed_at": "2026-06-30T23:59:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()


def _record_asset_graph_feedback(client: TestClient, project_id: str, storyboard_payload: dict) -> dict:
    response = client.post(
        "/feedback",
        json={
            "project_id": project_id,
            "generated_at": "2026-07-01T00:00:00+08:00",
            "feedback": {
                "kind": "studio_asset_graph_feedback",
                "node_id": "script_main_loop_e2e_001",
                "node_type": "script",
                "asset_graph_ref": storyboard_payload["artifacts"]["asset_graph"]["artifact_id"],
                "decisions": [
                    {
                        "graph_asset_id": "graph:character:林晚",
                        "decision": "confirm",
                        "label": "林晚",
                        "note": "Keep the character identity across the next keyframe pass.",
                    },
                    {
                        "graph_asset_id": "graph:prop:地图",
                        "decision": "revise",
                        "label": "地图",
                        "note": "Map markings need clearer red-line continuity.",
                    },
                ],
            },
        },
    )
    response.raise_for_status()
    return response.json()


def _promote_feedback_candidate(client: TestClient, project_id: str, feedback_payload: dict, feedback_candidate: dict) -> dict:
    response = client.post(
        f"/projects/{project_id}/feedback-candidate-promotions",
        json={
            "feedback_artifact_id": feedback_payload["artifact"]["artifact_id"],
            "candidate_id": feedback_candidate["candidate_id"],
            "decision": "promote_to_context_overlay",
            "rationale": "Promote only as project-local context evidence for the next deterministic pass.",
            "reviewed_at": "2026-07-01T00:01:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()


def _create_feedback_overlay(client: TestClient, project_id: str, promotion_payload: dict) -> dict:
    response = client.post(
        f"/projects/{project_id}/feedback-candidate-context-overlays",
        json={
            "promotion_decision_artifact_id": promotion_payload["artifact"]["artifact_id"],
            "overlay_intent": "Use asset graph feedback as bounded local context evidence only.",
            "generated_at": "2026-07-01T00:02:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()


def _keyframe_preflight(client: TestClient, project_id: str, request_payload: dict) -> dict:
    response = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=request_payload)
    response.raise_for_status()
    return response.json()
