from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.openapi_export import export_openapi_schema
from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


def test_storyboard_breakdown_gate_closed_uses_safe_local_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_storyboard_gate_closed",
            "project_type": "short_video_campaign",
            "goal": "Create a visual story from a complete script.",
        },
    )

    response = client.post(
        "/projects/proj_storyboard_gate_closed/storyboard-breakdowns",
        json={
            "node_id": "text_001",
            "script_text": "机器人站在城市屋顶看星星。它低头检查手里的发光地图。远处霓虹灯亮起。",
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-22T10:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["job"]["action"] == "storyboard_breakdown"
    assert payload["provider_calls_started"] is False
    assert payload["safe_manifest"]["status"] == "local_fallback"
    assert payload["safe_manifest"]["raw_provider_response_stored"] is False
    assert payload["safe_manifest"]["asset_nodes_created"] is False
    assert len(payload["shots"]) >= 1
    first = payload["shots"][0]
    for field in ("shot_id", "index", "duration", "description", "shot_size", "light_atmosphere", "camera_motion", "asset_refs"):
        assert field in first
    assert any(asset["label"] for asset in first["asset_refs"])
    assert "api_key" not in serialized
    assert "bearer " not in serialized
    assert "d:\\" not in serialized
    assert response_contains_unsafe_marker(payload) is False


def test_storyboard_local_fallback_does_not_turn_signal_or_city_lights_into_props(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_storyboard_local_asset_boundaries"
    client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "short_video_campaign",
            "goal": "Create a visual story from a complete script.",
        },
    )

    response = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "text_001",
            "script_text": "未来机器人站在城市屋顶仰望星空，远处高楼灯火闪烁，像是在等待遥远信号。",
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-22T10:03:00+08:00",
        },
    )

    assert response.status_code == 200
    refs = response.json()["shots"][0]["asset_refs"]
    assert [item["asset_type"] for item in refs] == ["character", "scene"]
    assert [item["label"] for item in refs] == ["主角", "主要场景"]


def test_storyboard_breakdown_uses_llm_structured_json_when_gate_open(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    calls: list[object] = []

    class Descriptor:
        modality = "llm"

    class FakeRegistry:
        _descriptors = {"prompt_optimizer": Descriptor()}

        def dispatch(self, capability, service_id, request):
            calls.append(request)
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            return {
                "text": json.dumps(
                    {
                        "shots": [
                            {
                                "shot_id": "shot_01",
                                "index": 1,
                                "duration": "5s",
                                "description": "@主角 站在屋顶边缘，城市霓虹在身后打开。",
                                "shot_size": "远景",
                                "light_atmosphere": "蓝紫色霓虹与冷月光交错",
                                "camera_motion": "缓慢推近",
                                "dialogue": "无明确对白",
                                "sound": "城市低频环境音",
                                "asset_refs": [
                                    {"label": "主角", "asset_type": "character", "status": "mentioned", "source": "explicit"},
                                    {"label": "屋顶夜景", "asset_type": "scene", "status": "mentioned", "source": "explicit"},
                                ],
                            },
                            {
                                "shot_id": "shot_02",
                                "index": 2,
                                "duration": "6s",
                                "description": "@主角 展开发光地图，地图光照亮手部机械结构。",
                                "shot_size": "特写",
                                "light_atmosphere": "地图冷光作为主光，背景压暗",
                                "camera_motion": "固定机位，轻微呼吸感",
                                "dialogue": "无明确对白",
                                "sound": "电子脉冲声",
                                "asset_refs": [
                                    {"label": "主角", "asset_type": "character", "status": "mentioned", "source": "explicit"},
                                    {"label": "发光地图", "asset_type": "prop", "status": "mentioned", "source": "explicit"},
                                ],
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                "provider_calls_started": True,
            }

    monkeypatch.setattr("apps.api.runtime_storyboard_breakdown.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_storyboard_llm",
            "project_type": "short_video_campaign",
            "goal": "Create a visual story from a complete script.",
        },
    )

    response = client.post(
        "/projects/proj_storyboard_llm/storyboard-breakdowns",
        json={
            "node_id": "text_001",
            "script_text": "机器人站在城市屋顶看星星。它低头检查手里的发光地图。",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {"llm_provider": "prompt_optimizer"},
            "generated_at": "2026-06-22T10:05:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(calls) == 1
    assert payload["provider_calls_started"] is True
    assert payload["safe_manifest"]["status"] == "provider_structured"
    assert payload["safe_manifest"]["raw_provider_response_stored"] is False
    assert payload["shots"][0]["description"].startswith("@主角")
    assert payload["shots"][1]["asset_refs"][1]["asset_type"] == "prop"


def test_storyboard_breakdown_accepts_llm_json_with_markdown_and_trailing_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")

    class Descriptor:
        modality = "llm"

    class FakeRegistry:
        _descriptors = {"prompt_optimizer": Descriptor()}

        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            return {
                "text": (
                    "```json\n"
                    "{\"shots\":[{\"shot_id\":\"shot_01\",\"index\":1,\"duration\":\"6s\","
                    "\"description\":\"@主角 在 @主要场景 静静仰望星空。\","
                    "\"shot_size\":\"远景\",\"light_atmosphere\":\"冷蓝月光\","
                    "\"camera_motion\":\"固定机位\",\"dialogue\":\"无明确对白\","
                    "\"sound\":\"城市环境底噪\","
                    "\"asset_refs\":["
                    "{\"label\":\"主角\",\"asset_type\":\"character\",\"status\":\"mentioned\",\"source\":\"explicit\"},"
                    "{\"label\":\"主要场景\",\"asset_type\":\"scene\",\"status\":\"mentioned\",\"source\":\"explicit\"}"
                    "]}]}\n"
                    "```\n"
                    "以上是可审查分镜。"
                ),
                "provider_calls_started": True,
            }

    monkeypatch.setattr("apps.api.runtime_storyboard_breakdown.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_storyboard_llm_fenced",
            "project_type": "short_video_campaign",
            "goal": "Create a visual story from a complete script.",
        },
    )

    response = client.post(
        "/projects/proj_storyboard_llm_fenced/storyboard-breakdowns",
        json={
            "node_id": "text_001",
            "script_text": "未来机器人站在城市屋顶仰望星空。",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {"llm_provider": "prompt_optimizer"},
            "generated_at": "2026-06-22T10:06:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_calls_started"] is True
    assert payload["safe_manifest"]["status"] == "provider_structured"
    assert payload["safe_manifest"]["discard_reason"] is None
    assert payload["shots"][0]["asset_refs"][1]["asset_type"] == "scene"


def test_storyboard_breakdown_keeps_provider_started_when_llm_json_is_discarded(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")

    class Descriptor:
        modality = "llm"

    class FakeRegistry:
        _descriptors = {"prompt_optimizer": Descriptor()}

        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            return {"text": "not json", "provider_calls_started": True}

    monkeypatch.setattr("apps.api.runtime_storyboard_breakdown.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_storyboard_llm_discard",
            "project_type": "short_video_campaign",
            "goal": "Create a visual story from a complete script.",
        },
    )

    response = client.post(
        "/projects/proj_storyboard_llm_discard/storyboard-breakdowns",
        json={
            "node_id": "text_001",
            "script_text": "机器人站在城市屋顶看星星。它低头检查手里的发光地图。",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {"llm_provider": "prompt_optimizer"},
            "generated_at": "2026-06-22T10:08:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_calls_started"] is True
    assert payload["safe_manifest"]["status"] == "local_fallback"
    assert payload["safe_manifest"]["raw_provider_response_stored"] is False
    assert payload["safe_manifest"]["discard_reason"]
    assert payload["shots"]


def test_storyboard_breakdown_is_exported_without_secret_surface(tmp_path) -> None:
    output_path = tmp_path / "frontend" / "afs-runtime-service.openapi.json"
    exported_path = export_openapi_schema(output_path, runtime_root=tmp_path / "openapi_runtime")
    schema = json.loads(exported_path.read_text(encoding="utf-8"))
    serialized = json.dumps(schema, ensure_ascii=False).lower()

    assert "/projects/{project_id}/storyboard-breakdowns" in schema["paths"]
    assert "storyboardbreakdownrequest" in serialized
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
