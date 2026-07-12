from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _optimize(tmp_path, payload: dict) -> tuple[dict, dict]:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post("/projects", json={"project_id": "proj_professional_prompt", "goal": "Professional prompt optimization"})
    response = client.post("/projects/proj_professional_prompt/prompt-optimizations", json=payload)
    assert response.status_code == 200
    result = response.json()
    trace = client.get(f"/artifacts/{result['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
    return result, trace


def test_character_emotion_image_prompt_gets_professional_visual_contract(tmp_path) -> None:
    payload, trace = _optimize(
        tmp_path,
        {
            "node_id": "image-emotion-girl",
            "node_type": "image",
            "prompt_text": "女生在笑",
            "generation_target": "image",
            "target_platform": "short_video",
            "style": "写实、克制、电影感",
            "generated_at": "2026-07-02T10:00:00+08:00",
        },
    )

    text = payload["optimized_prompt"]
    assert payload["provider_calls_started"] is False
    assert trace["selected_slots"]["language"] == "zh"
    assert trace["selected_slots"]["subject"] == "女生"
    assert "女生" in text
    assert "restrained realistic expression" in text
    assert "soft smile" in text
    assert "shoulders" in text and "breathing" in text
    assert "grounded scene" in text
    assert "motivated light" in text
    assert "watermark" in text and "exaggerated grin" in text


def test_character_emotion_video_prompt_gets_temporalized_contract(tmp_path) -> None:
    payload, trace = _optimize(
        tmp_path,
        {
            "node_id": "video-emotion-smile",
            "node_type": "video",
            "prompt_text": "女生微笑",
            "generation_target": "video",
            "target_platform": "short_video",
            "style": "自然写实",
            "node_parameters": {"duration": "5s"},
            "generated_at": "2026-07-02T10:05:00+08:00",
        },
    )

    text = payload["optimized_prompt"]
    assert trace["selected_slots"]["subject"] == "女生"
    assert trace["selected_slots"]["emotion"] == "微笑"
    assert "Start state:" in text
    assert "Transition:" in text
    assert "End state:" in text
    assert "5s" in text
    assert "body carrier" in text
    assert "camera/environment motion" in text
    assert "not a static image-edit prompt" in text


def test_scene_atmosphere_prompt_preserves_scene_grounding(tmp_path) -> None:
    payload, trace = _optimize(
        tmp_path,
        {
            "node_id": "image-scene-atmosphere",
            "node_type": "image",
            "prompt_text": "雨夜街道，紧张",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "克制现实主义",
            "generated_at": "2026-07-02T10:10:00+08:00",
        },
    )

    text = payload["optimized_prompt"]
    assert trace["selected_slots"]["scene"] == "雨夜街道"
    assert trace["selected_slots"]["emotion"] == "紧张"
    assert "rainy night street" in text
    assert "tension" in text
    assert "foreground, midground, and background" in text
    assert "source, direction, contrast" in text


def test_upstream_image_to_video_prompt_focuses_on_motion_and_source_continuity(tmp_path) -> None:
    payload, trace = _optimize(
        tmp_path,
        {
            "node_id": "video-upstream-i2v",
            "node_type": "video",
            "prompt_text": "让她慢慢回头微笑",
            "generation_target": "video",
            "target_platform": "short_video",
            "style": "克制真实",
            "asset_refs": ["img_first_frame_001"],
            "node_parameters": {
                "duration": "6s",
                "motion": "从首帧站立状态开始，慢慢回头，最后轻微微笑",
                "first_frame_image_asset_id": "img_first_frame_001",
                "input_source": {
                    "source_mode": "upstream_generated_image",
                    "source_asset_id": "img_first_frame_001",
                    "source_node_id": "keyframe_001",
                    "source_job_id": "job_keyframe_001",
                    "role": "first_frame",
                },
            },
            "generated_at": "2026-07-02T10:15:00+08:00",
        },
    )

    text = payload["optimized_prompt"]
    serialized_trace = json.dumps(trace, ensure_ascii=False)
    assert payload["provider_calls_started"] is False
    assert "first-frame source" in text
    assert "upstream_generated_image" in text
    assert "keyframe_001" in text
    assert "motion-first continuation" in text
    assert "avoid restating the whole image" in text
    assert "Start state:" in text and "End state:" in text
    assert "img_first_frame_001" in serialized_trace


def test_restraint_anti_exaggeration_case_suppresses_style_overreach(tmp_path) -> None:
    payload, trace = _optimize(
        tmp_path,
        {
            "node_id": "image-restraint",
            "node_type": "image",
            "prompt_text": "开心",
            "generation_target": "image",
            "target_platform": "short_video",
            "style": "用户偏好：夸张大笑、强烈炫光、高饱和；项目风格：克制、真实",
            "generated_at": "2026-07-02T10:20:00+08:00",
        },
    )

    text = payload["optimized_prompt"]
    assert trace["selected_slots"]["emotion"] == "开心"
    assert trace["suppressed_context"]
    assert "restrained realistic expression" in text
    assert "avoid exaggerated grin" in text
    assert "avoid oversaturation" in text
    assert "strong flares" in text
    assert "provider calls remain off" in text.lower()
