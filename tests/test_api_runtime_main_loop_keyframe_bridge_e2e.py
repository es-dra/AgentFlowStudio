from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app
from tests.runtime_main_loop_e2e_support import build_main_loop_e2e_state


def test_real_baseline_context_reaches_blocked_keyframe_generation_bridge(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_main_loop_keyframe_bridge_e2e"
    state = build_main_loop_e2e_state(client, project_id)
    request_payload = {
        **state.keyframe_request,
        "preflight_token": state.preflight_payload["preflight_token"],
        "generated_at": "2026-07-01T00:04:00+08:00",
    }

    response = client.post(f"/projects/{project_id}/keyframe-generations", json=request_payload)

    response.raise_for_status()
    payload = response.json()
    bridge = payload["generation_bridge"]
    safe_manifest = payload["safe_manifest"]
    context_evidence = bridge["context_evidence"]
    source_ref = context_evidence["included_asset_source_evidence_refs"][0]
    prompt_policy = context_evidence["feedback_context_overlay_prompt_policy"]
    artifact_payload = client.get(
        f"/artifacts/{payload['artifacts']['keyframe_generation_bridge']['artifact_id']}"
    ).json()["payload"]
    request_plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()[
        "payload"
    ]
    serialized = json.dumps(
        {
            "response": payload,
            "bridge": bridge,
            "request_plan_context": request_plan.get("context_bundle"),
        },
        ensure_ascii=False,
    ).lower()

    assert payload["job"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    assert payload["candidate_previews"] == []
    assert payload["reusable_image_assets"] == []
    assert safe_manifest["provider_calls_started"] is False
    assert safe_manifest["local_generation_bridge_ready"] is True
    assert safe_manifest["context_included_asset_count"] == 1
    assert safe_manifest["context_feedback_overlay_ids"] == [state.overlay["overlay_id"]]
    assert safe_manifest["feedback_context_overlay_prompt_policy"]["provider_prompt_includes_context_overlays"] is False

    assert bridge == artifact_payload
    assert bridge["summary"]["generation_state"] == "blocked_before_provider"
    assert bridge["summary"]["provider_calls_started"] is False
    assert bridge["summary"]["bridge_media_generated"] is False
    assert bridge["provider_evidence"]["provider_gate"]["status"] == "blocked"
    assert bridge["provider_evidence"]["raw_provider_response_stored"] is False
    assert bridge["provider_evidence"]["generated_media_bytes_stored"] is False
    assert bridge["provider_evidence"]["blocks"][0]["block_id"] == "remote_image_gate_closed"
    assert bridge["planned_outputs"][0]["artifact_state"] == "planned"
    assert bridge["planned_outputs"][0]["media_bytes_available"] is False

    assert context_evidence["context_bundle_present"] is True
    assert context_evidence["included_asset_count"] == 1
    assert context_evidence["included_asset_source_evidence_count"] == 1
    assert source_ref["asset_id"] == state.fixed_asset["asset_id"]
    assert source_ref["asset_type"] == "character"
    assert source_ref["label"] == "林晚"
    assert source_ref["source_human_gate_id"] == "runtime-human-gate:baseline:accepted"
    assert source_ref["source_asset_card_candidate_id"] == "asset_card_candidate:graph_character_林晚"
    assert source_ref["provider_calls_started"] is False
    assert source_ref["generated_media_claimed"] is False
    assert source_ref["human_creative_acceptance_claimed"] is False
    assert context_evidence["feedback_context_overlay_ids"] == [state.overlay["overlay_id"]]
    assert prompt_policy["default_action"] == "context_evidence_only"
    assert prompt_policy["provider_prompt_includes_context_overlays"] is False
    assert prompt_policy["prompt_provider_gate"]["status"] == "blocked_by_default"

    assert request_plan["context_bundle"]["included_assets"][0]["asset_id"] == state.fixed_asset["asset_id"]
    assert request_plan["context_bundle"]["feedback_context_overlays"][0]["overlay_id"] == state.overlay["overlay_id"]
    assert response_contains_unsafe_marker(bridge) is False
    assert response_contains_unsafe_marker(safe_manifest) is False
    assert response_contains_unsafe_marker(request_plan["context_bundle"]) is False
    assert '"provider_raw"' not in serialized
    assert '"signed_url"' not in serialized
    assert "data_base64" not in serialized
    assert "d:\\" not in serialized
