from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_prompt_optimization_user_prompt_consumes_director_setup_2d(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_director_setup_prompt",
            "project_type": "short_video_campaign",
            "goal": "Use a 2D director setup as invisible prompt context.",
        },
    )

    result = client.post(
        "/projects/proj_director_setup_prompt/prompt-optimizations",
        json={
            "node_id": "image-node-directed-001",
            "node_type": "image",
            "prompt_text": "一个男孩坐在昏暗房间里，墙上有海报，情绪低落。",
            "generation_target": "image",
            "target_platform": "short_video",
            "style": "克制、真实、低照度室内电影感",
            "director_setup": {
                "view": "top_down_2d",
                "subjects": [
                    {
                        "id": "subject_a",
                        "name": "男孩",
                        "x": 52,
                        "y": 58,
                        "angle": 210,
                        "action": "坐姿抱膝",
                        "emotion": "低落",
                    }
                ],
                "cameras": [
                    {
                        "id": "camera_main",
                        "name": "机位1",
                        "x": 22,
                        "y": 76,
                        "angle": -35,
                        "fov": 48,
                        "focalLength": 35,
                        "height": "平视",
                        "shot": "中近景",
                        "composition": "三分构图",
                        "lookAt": "男孩",
                    }
                ],
                "lights": [
                    {
                        "id": "key_light",
                        "kind": "key_light",
                        "name": "Key Light",
                        "x": 36,
                        "y": 28,
                        "angle": 45,
                        "intensity": 72,
                        "colorTemp": 4300,
                        "softness": 65,
                        "distance": 3.0,
                        "motivated": True,
                    },
                    {
                        "id": "back_light",
                        "kind": "back_light",
                        "name": "Back Light",
                        "x": 58,
                        "y": 22,
                        "angle": 125,
                        "intensity": 40,
                        "colorTemp": 5200,
                        "softness": 35,
                        "distance": 3.5,
                        "motivated": False,
                    },
                ],
                "modifiers": [
                    {"id": "flag", "kind": "flag", "name": "遮光旗", "x": 26, "y": 50, "angle": 90, "influence": "压暗背景墙"}
                ],
                "props": [
                    {"id": "bed", "kind": "bed", "name": "床", "x": 58, "y": 68, "width": 28, "height": 14, "visible": True, "narrative": "主体坐位"},
                    {"id": "poster", "kind": "poster", "name": "海报", "x": 76, "y": 46, "width": 12, "height": 8, "visible": True, "narrative": "角色身份线索"},
                ],
                "composition": "主体偏左，海报在右侧提供叙事信息",
                "notes": "暗调房间，主光来自床侧，墙上海报作为情绪线索。",
            },
            "node_parameters": {
                "model": "local-preview",
                "director_summary": "机位1 / Key Light / 海报",
            },
            "generated_at": "2026-06-11T12:00:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    user_prompt = payload["user_prompt"]
    user_sections = {section["title"]: section["text"] for section in payload["user_prompt_sections"]}

    assert list(user_sections) == ["人物", "场景", "镜头", "灯光", "运动", "负面约束"]
    assert "男孩" in user_sections["人物"]
    assert "坐姿抱膝" in user_sections["人物"]
    assert "海报" in user_sections["场景"]
    assert "机位1" in user_sections["镜头"]
    assert "FOV 48" not in user_sections["镜头"]
    assert "机械读数" in user_sections["镜头"]
    assert "Key Light" in user_sections["灯光"]
    assert "Back Light" in user_sections["灯光"]
    assert "避免光源冲突" in user_sections["负面约束"]
    assert "provider" not in user_prompt.lower()
    assert payload["provider_calls_started"] is False
