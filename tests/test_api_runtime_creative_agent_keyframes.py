from __future__ import annotations

import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from agentflow_studio.model_gateway.errors import ModelGatewayError
from apps.api.openapi_export import export_openapi_schema
from apps.api.runtime_keyframes import DEFAULT_IMAGE_PROMPT_LIMIT, provider_keyframe_prompt
from apps.api.runtime_service import create_runtime_app

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


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
    assert agent["provider_translation"]["provider"] == "codex_image"
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
            "seed": 120401,
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
    assert plan["seed"] == 120401
    assert plan["claim_boundary"] == "gate_closed_request_plan_only"
    assert "api_key" not in serialized
    assert "bearer " not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert "data/processed/runs" not in serialized


def test_keyframe_generation_strips_user_visible_section_headers_from_provider_prompt(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_plain_prompt/keyframe-generations",
        json={
            "node_id": "image-node-plain-001",
            "prompt_text": "一个人物走在雨夜街头",
            "optimized_prompt": "\n".join(
                [
                    "人物：黑短发女性，穿蓝白校服。",
                    "场景：雨夜街头，路面反光。",
                    "镜头：中景，主体居中。",
                    "灯光：冷色路灯。",
                    "运动：静态关键帧。",
                    "负面约束：不要文字水印。",
                ]
            ),
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-12T12:00:00+08:00",
        },
    )

    assert result.status_code == 200
    plan = client.get(f"/artifacts/{result.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    provider_prompt = plan["provider_prompt"]

    for label in ("人物：", "场景：", "镜头：", "灯光：", "运动：", "负面约束："):
        assert label not in provider_prompt
    assert "黑短发女性" in provider_prompt
    assert "雨夜街头" in provider_prompt


def test_keyframe_generation_returns_safe_image_preview_url(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    def fake_dispatch(capability, service_id, request):
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.png"
        image_path.write_bytes(PNG_BYTES)
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.png",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 1,
                    "height": 1,
                    "aspect_ratio": "1:1",
                    "provider_url_persisted": False,
                }
            ]
        }

    monkeypatch.setattr("apps.api.runtime_keyframes.load_provider_registry", lambda: _FakeRegistry(fake_dispatch))
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_keyframe_preview/keyframe-generations",
        json={
            "node_id": "image-node-preview-001",
            "prompt_text": "A controlled vertical keyframe of a founder in a night studio.",
            "optimized_prompt": "Intent: keyframe.\nCamera/Framing: aspect ratio 9:16.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "seed": 120612,
            "generated_at": "2026-06-12T10:20:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    previews = payload["candidate_previews"]
    reusable_assets = payload["reusable_image_assets"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["job"]["status"] == "succeeded"
    assert previews[0]["candidate_id"] == "candidate_001"
    assert previews[0]["preview_url"].startswith(
        "/projects/proj_keyframe_preview/keyframe-generations/"
    )
    assert previews[0]["preview_url"].endswith("/candidates/candidate_001/preview")
    assert previews[0]["width"] == 1
    assert previews[0]["height"] == 1
    assert previews[0]["aspect_ratio"] == "1:1"
    assert reusable_assets[0]["role"] == "generated_keyframe_reference"
    assert reusable_assets[0]["source_job_id"] == payload["job"]["job_id"]
    assert reusable_assets[0]["source_candidate_id"] == "candidate_001"
    assert reusable_assets[0]["preview_url"].endswith(
        f"/image-assets/{reusable_assets[0]['asset_id']}/preview"
    )
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert "data/processed/runs" not in serialized
    assert "image_candidates/candidate_001.png" not in serialized

    preview = client.get(previews[0]["preview_url"])
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/png")
    assert preview.content == PNG_BYTES

    reusable_preview = client.get(reusable_assets[0]["preview_url"])
    assert reusable_preview.status_code == 200
    assert reusable_preview.headers["content-type"].startswith("image/png")
    assert reusable_preview.content == PNG_BYTES


def test_keyframe_generation_retries_readiness_error_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setattr("apps.api.runtime_provider_dispatch.time.sleep", lambda _seconds: None)
    attempts = {"count": 0}

    def fake_dispatch(capability, service_id, request):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ModelGatewayError("provider temporarily not ready")
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.png"
        image_path.write_bytes(PNG_BYTES)
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.png",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 1,
                    "height": 1,
                    "aspect_ratio": "1:1",
                }
            ]
        }

    monkeypatch.setattr("apps.api.runtime_keyframes.load_provider_registry", lambda: _FakeRegistry(fake_dispatch))
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_keyframe_retry/keyframe-generations",
        json={
            "node_id": "image-node-retry-001",
            "prompt_text": "A controlled vertical keyframe.",
            "optimized_prompt": "A controlled vertical keyframe.",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-12T12:10:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    manifest = client.get(
        f"/artifacts/{payload['artifacts']['keyframe_generation_safe_manifest']['artifact_id']}"
    ).json()["payload"]

    assert attempts["count"] == 2
    assert payload["job"]["status"] == "succeeded"
    assert manifest["retry_count"] == 1


def test_keyframe_prompt_for_minimax_removes_internal_runtime_terms() -> None:
    prompt = provider_keyframe_prompt(
        "\n".join(
            [
                "Intent: a vertical founder keyframe.",
                "Negative Constraints: Provider calls remain off; do not claim provider execution.",
                "Lighting: low-key practical window light.",
                "Agent Rationale: internal scoring should not reach provider prompts.",
                "Continuity: stable wardrobe and room geography.",
            ]
        )
    )

    assert "Provider calls remain off" not in prompt
    assert "Agent Rationale" not in prompt
    assert "Lighting:" not in prompt
    assert "Continuity:" not in prompt
    assert "low-key practical window light." in prompt
    assert "stable wardrobe" in prompt
    assert len(prompt) <= DEFAULT_IMAGE_PROMPT_LIMIT


def test_keyframe_generation_uses_provider_descriptor_prompt_limit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {}

    def fake_dispatch(capability, service_id, request):
        captured["prompt"] = request.prompt
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.png"
        image_path.write_bytes(PNG_BYTES)
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.png",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 1,
                    "height": 1,
                    "aspect_ratio": "1:1",
                }
            ]
        }

    monkeypatch.setattr(
        "apps.api.runtime_keyframes.load_provider_registry",
        lambda: _FakeRegistry(fake_dispatch, prompt_limit=64),
    )
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_descriptor_limit/keyframe-generations",
        json={
            "node_id": "image-node-limit-001",
            "prompt_text": "A long keyframe prompt.",
            "optimized_prompt": "A cinematic rooftop prompt with many details. " * 20,
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-12T10:20:00+08:00",
        },
    )

    assert result.status_code == 200
    assert len(str(captured["prompt"])) <= 64


def test_runtime_keyframes_no_longer_imports_minimax_smoke_directly() -> None:
    source = Path("apps/api/runtime_keyframes.py").read_text(encoding="utf-8")

    assert "run_minimax_image_smoke" not in source


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


class _FakeDescriptor:
    def __init__(self, prompt_limit: int = DEFAULT_IMAGE_PROMPT_LIMIT) -> None:
        self.prompt_char_limit = prompt_limit
        self.reference_image_slots = 1
        self.required_gate = "AFS_ALLOW_REMOTE_IMAGE"


class _FakeRegistry:
    def __init__(self, dispatch, prompt_limit: int = DEFAULT_IMAGE_PROMPT_LIMIT) -> None:
        self._dispatch = dispatch
        self._descriptor = _FakeDescriptor(prompt_limit)

    def descriptor(self, service_id: str) -> _FakeDescriptor:
        return self._descriptor

    def dispatch(self, capability: str, service_id: str, request):
        return self._dispatch(capability, service_id, request)
