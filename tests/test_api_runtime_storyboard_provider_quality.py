from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_storyboard_breakdown_discards_sparse_provider_storyboard_for_long_script(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")

    class Descriptor:
        modality = "llm"

    class FakeRegistry:
        _descriptors = {"prompt_optimizer": Descriptor()}

        def dispatch(self, capability, service_id, request):
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
                                "description": "@主角 @主要场景。",
                                "shot_size": "中景",
                                "light_atmosphere": "",
                                "camera_motion": "",
                                "dialogue": "",
                                "sound": "",
                                "asset_refs": [],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "provider_calls_started": True,
            }

    monkeypatch.setattr("apps.api.runtime_storyboard_breakdown.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_storyboard_sparse_provider"
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
            "script_text": _long_robot_rooftop_script(),
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {"llm_provider": "prompt_optimizer"},
            "generated_at": "2026-06-22T10:09:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_calls_started"] is True
    assert payload["safe_manifest"]["status"] == "local_fallback"
    assert payload["safe_manifest"]["discard_reason"] == "provider storyboard response too sparse for source script"
    assert len(payload["shots"]) >= 3
    asset_labels = [ref["label"] for shot in payload["shots"] for ref in shot["asset_refs"]]
    assert "夜晚城市屋顶" in asset_labels
    assert "主要场景" not in asset_labels
    assert "信" not in asset_labels
    assert "灯" not in asset_labels


def _long_robot_rooftop_script() -> str:
    return (
        "描绘一个来自未来的机器人在屋顶静静仰望星空的孤独而诗意的科幻瞬间。"
        "一个来自未来的机器人，金属机身带有精密发光纹路，姿态安静专注。"
        "夜晚城市屋顶，远处高楼灯火与天际线微弱闪烁，头顶星空清澈深远。"
        "机器人站在屋顶边缘附近抬头看星星，像是在记录、思考或等待某个遥远信号。"
        "中远景构图，机器人位于画面下方偏侧，广阔星空占据主要空间。"
        "冷蓝月光与星光勾勒机身轮廓，城市霓虹提供低饱和反射。"
        "短暂静止的夜晚片段，微风轻拂屋顶，机器人胸口光源缓慢闪烁。"
    )
