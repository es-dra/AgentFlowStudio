from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.openapi_export import export_openapi_schema
from apps.api.runtime_service import create_runtime_app


def test_prompt_optimizer_records_creative_agent_candidates_and_node_constraints(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_creative_agent_trace",
            "project_type": "short_video_campaign",
            "goal": "Generate controllable keyframes for a short film.",
        },
    )

    result = client.post(
        "/projects/proj_creative_agent_trace/prompt-optimizations",
        json={
            "node_id": "image-node-agent-001",
            "node_type": "image",
            "prompt_text": "A quiet founder stands in a glass studio at night, reflecting on a failed launch.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic, user preference: square crop, saturated flashy lighting",
            "node_parameters": {
                "aspect_ratio": "9:16",
                "shot_scale": "wide shot",
                "camera": "locked camera with slight push-in",
                "lighting": "low-key practical window light",
            },
            "generated_at": "2026-06-12T10:00:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    trace = client.get(
        f"/artifacts/{payload['artifacts']['prompt_assembly_trace']['artifact_id']}"
    ).json()["payload"]
    brief = client.get(f"/artifacts/{payload['artifacts']['creative_brief']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"payload": payload, "trace": trace, "brief": brief}, ensure_ascii=False).lower()

    agent = trace["creative_agent"]
    selected = agent["selected_candidate"]

    assert agent["agent_name"] == "creative_intent_control_agent_v1"
    assert agent["candidate_count"] == 3
    assert {candidate["candidate_id"] for candidate in agent["candidates"]} >= {
        "continuity_safe",
        "expressive_cinematic",
        "provider_safe_keyframe",
    }
    assert selected["candidate_id"] in {candidate["candidate_id"] for candidate in agent["candidates"]}
    assert selected["score"]["visual_controllability"] >= selected["score"]["preference_fit"]
    assert agent["provider_translation"]["capability"] == "image_keyframe"
    assert agent["provider_translation"]["provider"] == "minimax_image"
    assert agent["constraint_layers"]["hard_constraints"]
    assert any(item["key"] == "aspect_ratio" and item["value"] == "9:16" for item in agent["constraint_layers"]["hard_constraints"])
    assert trace["conflict_resolution"]["suppressed_count"] >= 1
    assert "aspect ratio 9:16" in brief["optimized_prompt"].lower()
    assert payload["provider_calls_started"] is False
    assert "api_key" not in serialized
    assert "bearer " not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_keyframe_generation_gate_closed_blocks_before_network(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_keyframe_gate/keyframe-generations",
        json={
            "node_id": "image-node-001",
            "prompt_text": "A controlled vertical keyframe of a founder in a night studio.",
            "optimized_prompt": "Intent: keyframe.\nCamera/Framing: aspect ratio 9:16.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-12T10:20:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    manifest = client.get(
        f"/artifacts/{payload['artifacts']['keyframe_generation_safe_manifest']['artifact_id']}"
    ).json()["payload"]
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"payload": payload, "manifest": manifest, "plan": plan}, ensure_ascii=False).lower()

    assert payload["job"]["action"] == "keyframe_generation"
    assert payload["job"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    assert payload["provider_gate"] == {
        "capability": "image",
        "env": "AFS_ALLOW_REMOTE_IMAGE",
        "status": "blocked",
    }
    assert manifest["status"] == "blocked"
    assert manifest["provider_calls_started"] is False
    assert manifest["raw_provider_response_stored"] is False
    assert manifest["generated_media_bytes_stored"] is False
    assert plan["live_call_authorized"] is False
    assert plan["claim_boundary"] == "gate_closed_request_plan_only"
    assert "api_key" not in serialized
    assert "bearer " not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert "data/processed/runs" not in serialized


def test_keyframe_generation_openapi_has_no_provider_secret_surface(tmp_path) -> None:
    output_path = tmp_path / "frontend" / "afs-runtime-service.openapi.json"
    exported_path = export_openapi_schema(output_path, runtime_root=tmp_path / "openapi_runtime")
    schema = json.loads(exported_path.read_text(encoding="utf-8"))
    keyframe_schema = schema["components"]["schemas"]["KeyframeGenerationRequest"]
    serialized = json.dumps(keyframe_schema, ensure_ascii=False).lower()

    assert "/projects/{project_id}/keyframe-generations" in schema["paths"]
    assert "keyframegenerationrequest" in serialized
    assert "provider_config" not in serialized
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
