from __future__ import annotations

from apps.api.runtime_director_compiler import compile_director_setup
from apps.api.runtime_models import DirectorSetup2D


def test_director_compiler_blank_stage_does_not_invent_bed_or_poster() -> None:
    result = compile_director_setup(DirectorSetup2D())
    text = "\n".join(section["text"] for section in result["sections"])

    assert result["active_camera_id"] is None
    assert result["active_subject_ids"] == []
    assert "床" not in text
    assert "海报" not in text


def test_director_compiler_outputs_cinematography_language_not_raw_coordinate_readout() -> None:
    result = compile_director_setup(
        DirectorSetup2D.model_validate(
            {
                "subjects": [{"id": "subject_a", "name": "林晚", "x": 52, "y": 55, "angle": 210, "action": "侧身停步"}],
                "cameras": [{"id": "cam_a", "name": "A机位", "x": 22, "y": 78, "angle": -35, "fov": 48, "shot": "中景", "height": "平视"}],
                "lights": [{"id": "key", "kind": "key_light", "name": "主光", "x": 34, "y": 30, "angle": 45, "colorTemp": 4300, "intensity": 70, "softness": 60}],
                "props": [{"id": "window", "kind": "window", "name": "窗", "x": 82, "y": 30, "visible": True, "narrative": "冷色月光"}],
            }
        )
    )
    text = "\n".join(section["text"] for section in result["sections"])

    assert "林晚" in text
    assert "平视" in text
    assert "中景" in text
    assert "侧身" in text or "背面" in text or "正面" in text
    assert "偏暖" in text
    assert "52/55" not in text
    assert "FOV 48" not in text


def test_director_compiler_warns_when_manual_shot_conflicts_with_geometry() -> None:
    result = compile_director_setup(
        DirectorSetup2D.model_validate(
            {
                "subjects": [{"id": "subject_a", "name": "主体A", "x": 90, "y": 90}],
                "cameras": [{"id": "cam_a", "name": "远处机位", "x": 5, "y": 5, "fov": 90, "shot": "特写"}],
            }
        )
    )

    assert any(warning["warning_id"] == "shot_geometry_conflict" for warning in result["warnings"])


def test_director_compiler_uses_active_camera_and_all_active_subjects() -> None:
    result = compile_director_setup(
        DirectorSetup2D.model_validate(
            {
                "activeCameraId": "cam_b",
                "activeSubjectIds": ["sub_a", "sub_b"],
                "subjects": [
                    {"id": "sub_a", "name": "甲", "x": 45, "y": 50},
                    {"id": "sub_b", "name": "乙", "x": 58, "y": 52},
                    {"id": "sub_c", "name": "丙", "x": 70, "y": 50},
                ],
                "cameras": [
                    {"id": "cam_a", "name": "未生效机位", "x": 10, "y": 10, "shot": "全景"},
                    {"id": "cam_b", "name": "生效机位", "x": 20, "y": 75, "shot": "中景"},
                ],
            }
        )
    )
    text = "\n".join(section["text"] for section in result["sections"])

    assert result["active_camera_id"] == "cam_b"
    assert result["active_subject_ids"] == ["sub_a", "sub_b"]
    assert "生效机位" in text
    assert "未生效机位" not in text
    assert "甲" in text and "乙" in text and "丙" not in text
    assert result["trace_summary"]["inactive_camera_ids"] == ["cam_a"]


def test_director_compiler_uses_backend_asset_signature_and_ignores_subject_signature() -> None:
    result = compile_director_setup(
        DirectorSetup2D.model_validate(
            {
                "subjects": [
                    {
                        "id": "sub_a",
                        "name": "主体A",
                        "visual_asset_id": "va_linwan",
                        "signature": "forged frontend signature",
                    }
                ],
                "cameras": [{"id": "cam_a", "name": "机位", "x": 20, "y": 80, "shot": "中景"}],
            }
        ),
        visual_asset_signatures={"va_linwan": "黑短发、红风衣、左眉有疤的年轻女性"},
    )
    text = "\n".join(section["text"] for section in result["sections"])

    assert "黑短发、红风衣、左眉有疤的年轻女性" in text
    assert "forged frontend signature" not in text
    assert result["asset_refs_used"] == ["va_linwan"]
