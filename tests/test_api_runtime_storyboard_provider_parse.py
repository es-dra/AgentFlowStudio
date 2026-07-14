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
