from __future__ import annotations

import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


BENCHMARK_PATH = Path("examples/agentflow/content_quality_benchmark_scripts.example.json")
PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


def test_real_baseline_script_runs_provider_closed_main_loop_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_main_loop_e2e_baseline"
    client.post("/projects", json={"project_id": project_id, "goal": "Main loop E2E baseline"}).raise_for_status()
    case = _benchmark_case("multi_scene_map_chase")
    image_asset_id = _upload_image(client, project_id)
    fixed_asset = _promote_fixed_asset(client, project_id, image_asset_id)

    storyboard = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_main_loop_e2e_001",
            "script_text": case["script_text"],
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-30T23:58:00+08:00",
        },
    )
    storyboard.raise_for_status()
    payload = storyboard.json()
    labels_by_type = {(asset["label"], asset["asset_type"]) for asset in payload["asset_graph"]["assets"]}
    checks = {item["id"]: item for item in payload["content_quality_report"]["checks"]}
    graph_relationships = {item["relationship_type"] for item in payload["production_graph"]["relationships"]}
    ledger_roles = {item["artifact_role"] for item in payload["evidence_ledger"]["evidence_items"]}
    candidate = _candidate_for_label(payload, "林晚")
    low, high = case["expected_shot_range"]

    assert low <= len(payload["shots"]) <= high
    assert payload["provider_calls_started"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["writes_company_kb"] is False
    assert payload["content_quality_report"]["summary"]["human_review_needed"] is True
    assert checks["script_source_grounding"]["status"] == "passed"
    assert checks["dynamic_shot_count"]["status"] == "passed"
    assert checks["asset_evidence"]["status"] == "passed"
    assert {("林晚", "character"), ("办公室", "scene"), ("地图", "prop")} <= labels_by_type
    assert payload["production_graph"]["summary"]["fixed_visual_asset_count"] == 1
    assert payload["safe_manifest"]["fixed_visual_asset_source_evidence_count"] == 1
    assert "script_can_reuse_fixed_asset" in graph_relationships
    assert {
        "storyboard_breakdown_safe_manifest",
        "asset_graph",
        "content_quality_report",
        "production_graph_snapshot",
        "asset_card_candidates",
    } <= ledger_roles
    assert payload["evidence_ledger"]["provider_evidence"]["provider_gate"]["status"] in {"blocked", "ready_not_run"}
    assert candidate["reuse_policy"]["suggested_reuse_scope"] == "project_reuse_candidate"
    assert candidate["asset_memory_policy"]["writes_fixed_asset"] is False

    gate = client.post(
        f"/projects/{project_id}/human-gate-decisions",
        json={
            "target_type": "asset_card_candidate",
            "target_id": candidate["candidate_id"],
            "decision": "accepted_for_next_step",
            "artifact_id": payload["artifacts"]["asset_card_candidates"]["artifact_id"],
            "node_id": "script_main_loop_e2e_001",
            "scope": "asset_card_candidate_review",
            "note": "Baseline character candidate can feed the next local context pass.",
            "reviewed_at": "2026-06-30T23:59:00+08:00",
        },
    )
    gate.raise_for_status()
    gate_decision = gate.json()["human_gate_decision"]["decision"]

    assert gate_decision["target_id"] == candidate["candidate_id"]
    assert gate_decision["promotes_fixed_asset"] is False
    assert gate_decision["provider_calls_started"] is False

    feedback = client.post(
        "/feedback",
        json={
            "project_id": project_id,
            "generated_at": "2026-07-01T00:00:00+08:00",
            "feedback": {
                "kind": "studio_asset_graph_feedback",
                "node_id": "script_main_loop_e2e_001",
                "node_type": "script",
                "asset_graph_ref": payload["artifacts"]["asset_graph"]["artifact_id"],
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
    feedback.raise_for_status()
    feedback_payload = feedback.json()
    feedback_event = feedback_payload["feedback_event"]
    feedback_candidate = feedback_event["feedback_candidate"]

    assert feedback_candidate["candidate_scope"] == "asset_graph_feedback_candidate"
    assert feedback_candidate["scope_policy"]["global_scope_allowed"] is False
    assert feedback_candidate["conflict_summary"]["status"] == "conflict_signal_present"
    assert feedback_candidate["provider_calls_started"] is False

    promotion = client.post(
        f"/projects/{project_id}/feedback-candidate-promotions",
        json={
            "feedback_artifact_id": feedback_payload["artifact"]["artifact_id"],
            "candidate_id": feedback_candidate["candidate_id"],
            "decision": "promote_to_context_overlay",
            "rationale": "Promote only as project-local context evidence for the next deterministic pass.",
            "reviewed_at": "2026-07-01T00:01:00+08:00",
        },
    )
    promotion.raise_for_status()
    overlay_response = client.post(
        f"/projects/{project_id}/feedback-candidate-context-overlays",
        json={
            "promotion_decision_artifact_id": promotion.json()["artifact"]["artifact_id"],
            "overlay_intent": "Use asset graph feedback as bounded local context evidence only.",
            "generated_at": "2026-07-01T00:02:00+08:00",
        },
    )
    overlay_response.raise_for_status()
    overlay = overlay_response.json()["feedback_candidate_context_overlay"]

    preflight = client.post(
        f"/projects/{project_id}/keyframe-generations/preflight",
        json={
            "node_id": "keyframe_main_loop_e2e_001",
            "prompt_text": "Draw 林晚 checking the red map on the rainy street.",
            "optimized_prompt": "Cinematic keyframe of 林晚 checking the red map on the rainy street.",
            "target_platform": "short_video",
            "style": "cinematic",
            "context_subgraph": _context_subgraph(fixed_asset["asset_id"], overlay["overlay_id"]),
            "generated_at": "2026-07-01T00:03:00+08:00",
        },
    )
    preflight.raise_for_status()
    preflight_payload = preflight.json()
    serialized = json.dumps(
        {
            "storyboard": payload,
            "gate": gate.json(),
            "feedback": feedback_payload,
            "promotion": promotion.json(),
            "overlay": overlay_response.json(),
            "preflight": preflight_payload,
        },
        ensure_ascii=False,
    ).lower()

    assert preflight_payload["provider_calls_started"] is False
    assert preflight_payload["included_asset_source_evidence_count"] == 1
    assert preflight_payload["included_asset_source_evidence_refs"][0]["source_asset_card_candidate_id"] == (
        "asset_card_candidate:graph_character_林晚"
    )
    assert preflight_payload["feedback_context_overlays"][0]["overlay_id"] == overlay["overlay_id"]
    assert preflight_payload["feedback_context_overlays"][0]["context_overlay_consumed"] is True
    assert preflight_payload["context_bundle"]["trace_summary"]["feedback_context_overlay_selected_ids"] == [
        overlay["overlay_id"]
    ]
    for safe_projection in (
        payload["production_graph"],
        payload["evidence_ledger"],
        gate.json()["human_gate_decision"],
        feedback_candidate,
        overlay,
        preflight_payload["included_asset_source_evidence_refs"],
        preflight_payload["feedback_context_overlays"],
    ):
        assert response_contains_unsafe_marker(safe_projection) is False
    assert '"provider_raw"' not in serialized
    assert '"signed_url"' not in serialized
    assert "data_base64" not in serialized
    assert "d:\\" not in serialized


def _benchmark_case(case_id: str) -> dict:
    payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    return next(case for case in payload["cases"] if case["id"] == case_id)


def _candidate_for_label(payload: dict, label: str) -> dict:
    return next(
        item
        for item in payload["asset_card_candidates"]["candidates"]
        if item["draft_fields"]["display_name"] == label
    )


def _upload_image(client: TestClient, project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "node-ref-lin-wan",
            "filename": "lin-wan-reference.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-30T23:54:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]["asset_id"]


def _promote_fixed_asset(client: TestClient, project_id: str, image_asset_id: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_asset_id],
            "asset_type": "character",
            "label": "林晚",
            "signature": "short black hair, red trench coat, alert investigator posture",
            "feature_card": {"appearance": "young investigator with short black hair and red trench coat"},
            "negative_locks": ["do not change face identity", "keep red trench coat"],
            "source_node_id": "node-ref-lin-wan",
            "source_human_gate_id": "runtime-human-gate:baseline:accepted",
            "source_asset_card_candidate_id": "asset_card_candidate:graph_character_林晚",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-30T23:55:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]


def _context_subgraph(asset_id: str, overlay_id: str) -> dict:
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
