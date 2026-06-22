from __future__ import annotations

from apps.api.runtime_director_compiler_v2 import DirectorSceneBlockingV1, compile_director_scene_blocking
from apps.api.runtime_models import DirectorSetup2D


def _compiled_text(result: dict[str, object]) -> str:
    sections = result["sections"]
    assert isinstance(sections, list)
    return "\n".join(str(section["text"]) for section in sections)


def test_director_scene_blocking_blank_stage_does_not_invent_props() -> None:
    result = compile_director_scene_blocking(DirectorSceneBlockingV1())
    text = _compiled_text(result)

    assert result["active_camera_id"] is None
    assert result["active_subject_ids"] == []
    assert result["prop_ids"] == []
    assert "床" not in text
    assert "海报" not in text


def test_director_scene_blocking_outputs_camera_subject_and_prop_language() -> None:
    result = compile_director_scene_blocking(
        {
            "camera": {
                "id": "cam_main",
                "position": {"x": 0.2, "y": 0.68, "z": 0.18},
                "target": {"x": 0.55, "y": 0.4, "z": 0.5},
                "shot_size": "中景",
                "angle": "低机位仰拍",
                "movement": "缓慢推轨",
            },
            "subjects": [
                {
                    "id": "sub_a",
                    "label": "林晚",
                    "visual_asset_id": "va_linwan",
                    "position": {"x": 0.48, "y": 0.0, "z": 0.45},
                    "rotation": {"y": 25},
                    "pose": "侧身停步",
                    "action": "回头看向入口",
                },
                {
                    "id": "sub_b",
                    "label": "守卫",
                    "position": {"x": 0.72, "y": 0.0, "z": 0.58},
                    "pose": "站立警戒",
                    "action": "挡在门边",
                },
            ],
            "props": [
                {
                    "id": "door",
                    "label": "金属门",
                    "position": {"x": 0.82, "y": 0.0, "z": 0.62},
                    "scale": {"x": 1.0, "y": 2.2, "z": 0.1},
                }
            ],
            "lights": [
                {
                    "id": "rim",
                    "type": "rim",
                    "position": {"x": 0.2, "y": 0.8, "z": 0.8},
                    "intensity": 0.82,
                    "color": "cold blue",
                    "direction": {"x": 0.4, "y": -0.4, "z": -0.2},
                }
            ],
        },
        visual_asset_signatures={"va_linwan": "黑短发、红风衣、左眉有疤的年轻女性"},
    )
    text = _compiled_text(result)

    assert result["active_camera_id"] == "cam_main"
    assert result["active_subject_ids"] == ["sub_a", "sub_b"]
    assert result["prop_ids"] == ["door"]
    assert result["asset_refs_used"] == ["va_linwan"]
    assert "黑短发、红风衣、左眉有疤的年轻女性" in text
    assert "守卫" in text
    assert "金属门" in text
    assert "中景" in text
    assert "低机位仰拍" in text
    assert "缓慢推轨" in text
    assert "冷蓝" in text
    assert "床" not in text
    assert "海报" not in text
    assert "0.48" not in text


def test_director_scene_blocking_ignores_frontend_forged_signature() -> None:
    result = compile_director_scene_blocking(
        {
            "subjects": [
                {
                    "id": "sub_a",
                    "label": "主体A",
                    "visual_asset_id": "va_real",
                    "signature": "forged frontend signature",
                }
            ]
        },
        visual_asset_signatures={"va_real": "后端固定资产签名"},
    )
    text = _compiled_text(result)

    assert "后端固定资产签名" in text
    assert "forged frontend signature" not in text
    assert result["asset_refs_used"] == ["va_real"]


def test_director_scene_blocking_exports_safe_artifact_metadata_only() -> None:
    result = compile_director_scene_blocking(
        {
            "exports": {
                "screenshot_artifact_id": "artifact_director_screen_1",
                "thumbnail_artifact_id": "artifact_director_thumb_1",
                "local_path": "D:/private/raw.png",
                "signed_url": "https://signed.example.invalid/raw.png",
            }
        }
    )
    text = _compiled_text(result)

    assert result["safe_exports"] == {
        "screenshot_artifact_id": "artifact_director_screen_1",
        "thumbnail_artifact_id": "artifact_director_thumb_1",
    }
    assert "D:/private" not in text
    assert "signed.example" not in text


def test_director_scene_blocking_falls_back_to_2d_setup_when_v2_missing() -> None:
    result = compile_director_scene_blocking(
        None,
        fallback_setup=DirectorSetup2D.model_validate(
            {
                "subjects": [{"id": "sub_a", "name": "林晚", "x": 52, "y": 55}],
                "cameras": [{"id": "cam_a", "name": "A机位", "x": 22, "y": 78, "shot": "中景"}],
            }
        ),
    )
    text = _compiled_text(result)

    assert result["schema_version"] == "director_compile_result.v1"
    assert result["active_camera_id"] == "cam_a"
    assert result["active_subject_ids"] == ["sub_a"]
    assert result["trace_summary"]["fallback_source"] == "director_setup_2d"
    assert "林晚" in text
    assert "中景" in text
