from __future__ import annotations

import json

from apps.api.runtime_storyboard_provider_parse import shots_from_provider_text


def test_storyboard_provider_parser_localizes_english_shot_fields() -> None:
    payload = {
        "shots": [
            {
                "shot_id": "shot_01",
                "index": 1,
                "duration": "2.8s",
                "description": "@小红。特写：一只少女左手紧攥试卷右下角，指节发白，纸面剧烈抖动；试卷上‘59分’被褶皱扭曲变形。",
                "shot_size": "extreme_close_up",
                "light_atmosphere": "冷灰高反差，雨滴在画面边缘高速拖影",
                "camera_motion": "static, shallow_depth_of_field_focus_on_fingertips_and_score",
                "dialogue": "班主任（OS）：心比天高，基础不牢……",
                "sound": "暴雨白噪音持续，纸张哗哗震颤声高频叠加",
                "source_span": {"text": "暴雨倾盆的放学路上，高中生小红攥着被风吹得哗哗作响的试卷，低头疾走。"},
                "asset_refs": [
                    {
                        "label": "小红",
                        "asset_type": "character",
                        "status": "mentioned",
                        "source": "explicit",
                    }
                ],
            }
        ]
    }

    shots = shots_from_provider_text(
        json.dumps(payload, ensure_ascii=False),
        source_script_text="暴雨倾盆的放学路上，高中生小红攥着被风吹得哗哗作响的试卷，低头疾走。",
    )

    assert shots[0]["shot_size"] == "极近特写"
    assert shots[0]["camera_motion"] == "固定机位，浅景深，焦点锁定指尖和分数"
    assert shots[0]["dialogue"] == "班主任（画外音）：心比天高，基础不牢……"
    assert "extreme_close_up" not in json.dumps(shots[0], ensure_ascii=False)
    assert "shallow_depth_of_field" not in json.dumps(shots[0], ensure_ascii=False)


def test_storyboard_provider_parser_localizes_lighting_sound_and_compacts_camera_motion() -> None:
    payload = {
        "shots": [
            {
                "shot_id": "shot_01",
                "index": 1,
                "duration": "2.4s",
                "description": "@古战场。暴雨倾盆的古战场俯拍：断戟斜插泥泞，残旗半埋于焦黑土中，妖气如墨色浓雾翻涌蒸腾。",
                "shot_size": "medium_shot",
                "light_atmosphere": (
                    "high-contrast chiaroscuro; cold blue-green key light from storm clouds, "
                    "deep indigo shadows pooling in craters and weapon grooves, mist diffusing highlights"
                ),
                "camera_motion": "tilt_up, tilt",
                "dialogue": "无明确对白",
                "sound": "thunder rumble (low-frequency), torrential rain on metal/earth, distant guttural growls layered beneath",
                "source_span": {"text": "暴雨倾盆的古战场上，断戟斜插泥泞，残旗半埋于焦黑土中。"},
                "asset_refs": [
                    {
                        "label": "古战场",
                        "asset_type": "scene",
                        "status": "mentioned",
                        "source": "explicit",
                    }
                ],
            }
        ]
    }

    shots = shots_from_provider_text(
        json.dumps(payload, ensure_ascii=False),
        source_script_text="暴雨倾盆的古战场上，断戟斜插泥泞，残旗半埋于焦黑土中。",
    )

    shot = shots[0]
    assert shot["shot_size"] == "中景"
    assert shot["camera_motion"] == "向上摇镜"
    assert shot["light_atmosphere"] == "高反差明暗对照，暴风云层投下冷蓝绿色主光，深靛色阴影在弹坑与兵器沟槽中堆积，雾气柔化高光"
    assert shot["sound"] == "低频雷鸣轰隆，暴雨击打金属与泥土，远处喉音低吼在底层铺陈"
    serialized = json.dumps(shot, ensure_ascii=False)
    assert "high-contrast" not in serialized
    assert "thunder rumble" not in serialized
    assert "俯仰摇镜" not in shot["camera_motion"]


def test_storyboard_provider_parser_localizes_mixed_english_chinese_camera_motion() -> None:
    payload = {
        "shots": [
            {
                "shot_id": "shot_03",
                "index": 3,
                "duration": "2.2s",
                "description": "@阿团 @厨房。低角度跟拍：阿团踮脚跃起，后腿绷直，小臂肌肉线条清晰。",
                "shot_size": "medium_shot",
                "light_atmosphere": "暖色主光",
                "camera_motion": "handheld slight rise mimicking阿团's jump",
                "dialogue": "无明确对白",
                "sound": "环境底噪，动作音随画面同步",
                "source_span": {"text": "阿团踮脚跃起，指尖触到橱柜顶层麦片罐底部。"},
                "asset_refs": [
                    {
                        "label": "阿团",
                        "asset_type": "character",
                        "status": "mentioned",
                        "source": "explicit",
                    },
                    {
                        "label": "厨房",
                        "asset_type": "scene",
                        "status": "mentioned",
                        "source": "explicit",
                    },
                ],
            }
        ]
    }

    shots = shots_from_provider_text(
        json.dumps(payload, ensure_ascii=False),
        source_script_text="阿团踮脚跃起，指尖触到橱柜顶层麦片罐底部。",
    )

    assert shots[0]["camera_motion"] == "手持轻晃，轻微上升，模拟阿团跳跃"
    assert "handheld" not in json.dumps(shots[0], ensure_ascii=False)
    assert "mimicking" not in json.dumps(shots[0], ensure_ascii=False)
