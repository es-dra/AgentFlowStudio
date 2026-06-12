from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_memory_assembly import extract_background_context
from apps.api.runtime_service import create_runtime_app


def test_prompt_background_fallback_slots_produce_no_candidates() -> None:
    request = PromptOptimizationRequest(
        node_id="node-empty-slots",
        node_type="image",
        prompt_text="Mood and atmosphere only.",
        generation_target="keyframe",
        target_platform="short_video",
        style="cinematic",
        generated_at="2026-06-12T09:00:00+08:00",
    )

    extracted = extract_background_context(
        "proj_no_placeholder",
        request,
        {"subject": "Primary character", "scene": "Primary scene", "style": "Project style"},
    )

    assert extracted == []


def test_second_node_prompt_optimization_keeps_extracted_context_candidate_only(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_libtv_background_context",
            "project_type": "short_video_campaign",
            "goal": "Optimize repeated node prompts with hidden context.",
        },
    )
    first = client.post(
        "/projects/proj_libtv_background_context/prompt-optimizations",
        json={
            "node_id": "text-node-001",
            "node_type": "text",
            "prompt_text": "A silver-haired detective searches an abandoned observatory at blue hour.",
            "generation_target": "image",
            "target_platform": "short_video",
            "style": "moody cinematic",
            "generated_at": "2026-06-11T10:10:00+08:00",
        },
    ).json()
    second = client.post(
        "/projects/proj_libtv_background_context/prompt-optimizations",
        json={
            "node_id": "image-node-002",
            "node_type": "image",
            "prompt_text": "The recurring detective finds a hidden map under the observatory floor.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "controlled mystery",
            "asset_refs": [first["artifacts"]["creative_brief"]["artifact_id"]],
            "generated_at": "2026-06-11T10:20:00+08:00",
        },
    ).json()

    trace = client.get(f"/artifacts/{second['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
    brief = client.get(f"/artifacts/{second['artifacts']['creative_brief']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"trace": trace, "brief": brief, "response": second}, ensure_ascii=False).lower()
    state_path = tmp_path / "creative_memory" / "proj_libtv_background_context" / "creative_memory_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert trace["background_context_refs"] == []
    assert state["characters"] == []
    assert state["scenes"] == []
    assert state["style_preferences"] == []
    assert state["extracted_context"]
    assert all(item.get("source_node_id") for item in state["extracted_context"])
    assert all(item.get("confidence") is not None for item in state["extracted_context"])
    assert trace["asset_refs"] == [first["artifacts"]["creative_brief"]["artifact_id"]]
    assert "Silver-haired detective" not in brief["optimized_prompt"]
    assert "Abandoned observatory" not in brief["optimized_prompt"]
    assert "candidate_memory" not in serialized
    assert "memory_decision" not in serialized
    assert trace["provider_calls_started"] is False
    assert "not durable memory" in trace["non_claims"]
