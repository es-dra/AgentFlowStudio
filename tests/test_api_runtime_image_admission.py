from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from agentflow_studio.model_gateway.image_utils import image_dimensions
from apps.api.runtime_image_admission import (
    compile_image_admission_manifest,
    enforce_image_admission_keyframe_request,
    image_admission_capability,
)
from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


PROJECT_ID = "m6-9-image-admission-test"
REQUESTED_AT = "2026-07-24T06:00:00Z"
CURRENT_PROJECT_ID = "studio-1785154250742-86s0uf"
OLD_CURRENT_PROJECT_MANIFEST_HASH = (
    "7089c1827eebf5a993a4f0e95dec6537fb599fb6a7ca5143d69caf5013120cb1"
)


@pytest.mark.parametrize(
    ("configured_model", "configured", "exact_model"),
    [
        ("gpt-image-2", True, True),
        ("image2", False, False),
        ("gpt-image-1", False, False),
    ],
)
def test_image_admission_requires_exact_image2_callable_model(
    monkeypatch,
    configured_model,
    configured,
    exact_model,
) -> None:
    descriptor = SimpleNamespace(
        reference_image_slots=4,
        image_edit_capabilities_present=True,
        image_edit_capabilities=SimpleNamespace(
            supports_image_edit=True,
            max_reference_images=4,
            input_fidelity_modes=[],
        ),
    )
    registry = SimpleNamespace(
        descriptor=lambda service_id: descriptor,
        store=SimpleNamespace(service=lambda service_id: {"model": configured_model}),
    )
    monkeypatch.setattr(
        "apps.api.runtime_image_admission.load_provider_registry",
        lambda: registry,
    )

    capability = image_admission_capability()

    assert capability["configured"] is configured
    assert capability["exact_model"] is exact_model
    assert capability["model"] == "gpt-image-2"
    assert capability["keyframe_continuity_ready"] is configured
    if not configured:
        assert capability["blocker"] == "图片服务没有绑定本次要求的精确模型"


def _asset(
    stable_id: str,
    asset_type: str,
    display_name: str,
    *,
    scene_ids: list[str],
    shot_ids: list[str],
) -> dict:
    return {
        "stable_id": stable_id,
        "asset_type": asset_type,
        "display_name": display_name,
        "aliases": [display_name],
        "review_state": "approved",
        "needs_confirmation": False,
        "negative_locks": ["do not add text/watermark/ui/borders"],
        "visual_identity": f"{display_name} 的已确认轮廓、材质与配色身份",
        "positive_traits": [f"保持 {display_name} 的稳定辨识特征", "材质细节清晰"],
        "continuity_states": [
            {
                "state_id": f"continuity-{stable_id}",
                "label": "当前场次造型与持有物保持一致",
                "status": "confirmed",
                "scene_ids": scene_ids,
                "shot_ids": shot_ids,
            }
        ],
        "pending_fields": [],
        "source_evidence": [
            {
                "source_type": "occurrence_ledger",
                "source_id": stable_id,
                "scene_ids": scene_ids,
                "shot_ids": shot_ids,
                "excerpt": "已应用分镜中的资产出现范围",
            }
        ],
        "occurrences": {"scene_ids": scene_ids, "shot_ids": shot_ids},
    }


def source_contract(*, graph_version: int = 0, graph_digest: str = "") -> dict:
    scenes = [
        {"scene_id": f"scene-{index}", "name": f"场景 {index}", "number": index}
        for index in range(1, 4)
    ]
    shots = [
        {
            "shot_id": f"scene-{1 + (index > 6) + (index > 12)}-shot-{index}",
            "scene_id": f"scene-{1 + (index > 6) + (index > 12)}",
            "title": f"镜头 {index:02d}",
            "number": index,
            "purpose": f"推进第 {index} 个叙事节拍",
            "shot_size": "中景",
            "composition": "主体位于画面三分线，保留动作空间",
            "camera_angle": "平视",
            "movement": "稳定跟随",
            "action": f"角色完成镜头 {index} 的明确动作",
            "dialogue": "" if index % 2 else f"第 {index} 镜对白",
            "emotion": "克制而专注",
            "continuity_cues": ["服装与关键道具位置延续上一镜"],
        }
        for index in range(1, 18)
    ]
    assets = [
        _asset("asset-character-a", "character", "角色甲", scene_ids=["scene-1"], shot_ids=["scene-1-shot-1"]),
        _asset("asset-character-b", "character", "角色乙", scene_ids=["scene-1"], shot_ids=["scene-1-shot-2"]),
        _asset("asset-character-c", "character", "角色丙", scene_ids=["scene-3"], shot_ids=["scene-3-shot-17"]),
        _asset(
            "asset-scene-a",
            "scene",
            "主场景",
            scene_ids=["scene-1"],
            shot_ids=[f"scene-1-shot-{index}" for index in range(1, 7)],
        ),
        _asset(
            "asset-scene-b",
            "scene",
            "次场景",
            scene_ids=["scene-2"],
            shot_ids=[f"scene-2-shot-{index}" for index in range(7, 13)],
        ),
        _asset(
            "asset-scene-c",
            "scene",
            "终场景",
            scene_ids=["scene-3"],
            shot_ids=[f"scene-3-shot-{index}" for index in range(13, 18)],
        ),
        _asset(
            "asset-prop-a",
            "prop",
            "核心道具甲",
            scene_ids=["scene-1", "scene-2"],
            shot_ids=[f"scene-1-shot-{index}" for index in range(1, 7)] + ["scene-2-shot-7"],
        ),
        _asset(
            "asset-prop-b",
            "prop",
            "核心道具乙",
            scene_ids=["scene-1"],
            shot_ids=["scene-1-shot-2", "scene-1-shot-3", "scene-1-shot-4", "scene-1-shot-5"],
        ),
        _asset(
            "asset-prop-c",
            "prop",
            "辅助道具",
            scene_ids=["scene-3"],
            shot_ids=["scene-3-shot-16", "scene-3-shot-17"],
        ),
    ]
    bible = {
        "schema_version": "afs.asset_bible.v0.1",
        "version": 7,
        "status": "locked",
        "current_revision_id": "asset-bible-r7-current",
        "locked_revision_id": "asset-bible-r7-current",
        "candidate_set": {
            "candidate_set_id": "asset-candidates-current",
            "script_revision_id": "script-revision-current",
            "shot_candidate_id": "shot-candidate-current",
            "scene_index": scenes,
            "shot_index": shots,
            "scene_count": 3,
            "shot_count": 17,
        },
        "assets": assets,
        "art_direction": {
            "visual_style": "写实古装动作片",
            "medium": "电影摄影，真实皮肤、织物与金属质感",
            "palette": "低饱和青绿与暖金点缀",
            "lighting": "黄昏侧逆光，人物面部清晰可辨",
            "status": "confirmed",
            "source": "human_review",
            "confirmed_at": REQUESTED_AT,
        },
        "coverage": {
            "coverage_pass": True,
            "quality_pass": True,
            "scene_total": 3,
            "scene_covered": 3,
            "shot_total": 17,
            "shot_covered": 17,
            "asset_shot_covered": 17,
            "missing_source_evidence_shot_count": 0,
            "required_occurrence_total": 35,
            "resolved_required": 35,
            "unresolved_required": 0,
        },
        "recognition_quality": {
            "status": "pass",
            "issues": [],
            "missing_anchor_count": 0,
            "orphan_scene_coverage_count": 0,
            "alias_collision_count": 0,
            "recognition_ambiguity_count": 0,
        },
    }
    return {
        "authority_mode": "canonical_production_graph" if graph_version else "legacy_studio_adapter",
        "production_graph_version": graph_version,
        "production_graph_digest": graph_digest,
        "studio_state_version": "studio-state-current",
        "art_direction": bible["art_direction"],
        "shot_grounding": {
            "scenes": scenes,
            "shots": shots,
        },
        "asset_bible": bible,
    }


def compact_source_contract(*, shot_count: int = 3) -> dict:
    source = source_contract()
    shot_ids = [f"scene-1-shot-{index}" for index in range(1, shot_count + 1)]
    shots = [
        item
        for item in source["shot_grounding"]["shots"]
        if item["shot_id"] in shot_ids
    ]
    scenes = [source["shot_grounding"]["scenes"][0]]
    assets = [
        item
        for item in source["asset_bible"]["assets"]
        if item["stable_id"] in {"asset-character-a", "asset-scene-a", "asset-prop-a"}
    ]
    renamed = {
        "asset-character-a": "巡夜人·甲",
        "asset-scene-a": "北侧检修站",
        "asset-prop-a": "六角校准器",
    }
    for asset in assets:
        asset["display_name"] = renamed[asset["stable_id"]]
        asset["aliases"] = [asset["display_name"]]
        asset["occurrences"] = {"scene_ids": ["scene-1"], "shot_ids": shot_ids}
        asset["source_evidence"] = [
            {
                "source_type": "occurrence_ledger",
                "source_id": asset["stable_id"],
                "scene_ids": ["scene-1"],
                "shot_ids": shot_ids,
                "excerpt": "已应用分镜中的资产出现范围",
            }
        ]
        asset["continuity_states"][0]["scene_ids"] = ["scene-1"]
        asset["continuity_states"][0]["shot_ids"] = shot_ids
    bible = source["asset_bible"]
    bible["assets"] = assets
    bible["candidate_set"]["scene_index"] = scenes
    bible["candidate_set"]["shot_index"] = shots
    bible["candidate_set"]["scene_count"] = 1
    bible["candidate_set"]["shot_count"] = shot_count
    bible["coverage"].update(
        {
            "scene_total": 1,
            "scene_covered": 1,
            "shot_total": shot_count,
            "shot_covered": shot_count,
            "asset_shot_covered": shot_count,
            "required_occurrence_total": len(assets) * shot_count,
            "resolved_required": len(assets) * shot_count,
        }
    )
    source["shot_grounding"] = {"scenes": scenes, "shots": shots}
    return source


def current_project_locked_source_contract() -> dict:
    scene_specs = [
        ("01", "重生甜虐短剧切片", 12),
        ("02", "重生甜虐后台追逃", 7),
        ("03", "古言棋局推广", 12),
        ("04", "古言图形落版", 4),
    ]
    scenes: list[dict] = []
    shots: list[dict] = []
    shot_lookup: dict[int, tuple[str, str]] = {}
    ordinal = 1
    for scene_order, (scene_suffix, scene_name, shot_total) in enumerate(scene_specs, start=1):
        scene_id = f"scene-embedded-f0879c54f044ebb3-{scene_suffix}"
        scenes.append(
            {
                "scene_id": scene_id,
                "name": scene_name,
                "number": scene_order,
                "description": f"{scene_name} 的已应用分镜场景。",
            }
        )
        for shot_order in range(1, shot_total + 1):
            shot_id = f"shot-embedded-f0879c54f044ebb3-{scene_suffix}-{shot_order:02d}"
            shot_lookup[ordinal] = (shot_id, scene_id)
            shots.append(
                {
                    "shot_id": shot_id,
                    "scene_id": scene_id,
                    "title": "深海坠落" if ordinal == 1 else f"镜头 {ordinal:02d}",
                    "number": ordinal,
                    "purpose": "保持当前真实项目镜头结构的准入回归。",
                    "shot_size": "中景",
                    "composition": "主体清楚，保留动作与环境关系。",
                    "camera_angle": "平视或轻微运动机位",
                    "movement": "按镜头节奏推进",
                    "action": "按已应用分镜完成叙事动作。",
                    "dialogue": "",
                    "emotion": "清楚可读",
                    "continuity_cues": ["延续已确认角色、场景、道具和风格资产。"],
                }
            )
            ordinal += 1
    asset_defs = {
        "M-CHAR-01": (
            "character",
            "叶安安",
            "清秀倔强、杏眼、黑色长发、纤细；同脸连续表现恐惧/警觉/奶凶/决绝。",
            ["泳池湿身（非情色）", "白浴巾伪装", "灰黑防水脏污妆+粗框眼镜+乱发+低饱和碎花裙"],
            ["禁止族裔模仿式黑脸"],
        ),
        "M-CHAR-02": ("character", "傅凉川", "高挑、短黑发、锐利眉眼、克制冷感。", ["深炭黑修身西装"], []),
        "M-CHAR-03": ("character", "孟欣", "温暖明快、棕黑中长卷发。", ["香槟/珊瑚派对裙"], []),
        "M-CHAR-04": ("character", "主持人", "成熟专业，不抢主角视觉。", ["黑色正式礼服或西装"], []),
        "M-ENV-01": ("scene", "象征性深海", "深蓝黑水体、上方弱冷白光、气泡颗粒。", ["非血腥写实"], []),
        "M-ENV-02": ("scene", "前世创伤空间", "冷暗宅邸走廊/封闭房间/离开车辆。", ["灰蓝压迫光"], []),
        "M-ENV-03": ("scene", "豪宅泳池派对", "夜间泳池、暖金庭院灯、蓝绿水面。", ["克制宾客背景"], []),
        "M-ENV-04": ("scene", "后台化妆区", "镜前灯、衣架、化妆台。", ["支持扮丑蒙太奇"], []),
        "M-ENV-05": ("scene", "华丽演播厅", "黑金舞台、观众暗区。", ["主持/嘉宾区关系明确"], []),
        "M-ENV-06": ("scene", "演播厅后台走廊", "冷白顶灯、黑幕、设备箱与转角。", ["支持追逃拦截"], []),
        "M-PROP-01": ("prop", "白色浴巾", "厚棉质无品牌，湿度/折叠连续。", ["非情色伪装用途"], []),
        "M-PROP-02": ("prop", "厚四眼眼镜", "黑色粗框、尺寸固定。", ["不做真正畸变"], []),
        "M-PROP-03": ("prop", "主持手麦", "哑光黑无品牌。", ["舞台主持用途"], []),
        "A-CHAR-01": ("character", "容华", "修长清贵、深眉眼、黑发高束。", ["墨黑暗金棋纹锦袍/黑玉冠"], []),
        "A-CHAR-02": ("character", "白筱", "明净不柔弱、黑长发半挽。", ["月白浅青叠穿/细金发簪"], []),
        "A-CHAR-03": ("character", "古越", "忠犬将军，玄铁轻甲、深蓝披风。", ["沉稳克制"], []),
        "A-CHAR-04": ("character", "风荻", "俊美锋锐，朱红锦袍、黑银束发。", ["少量银饰，动作开放"], []),
        "A-ENV-01": ("scene", "棋剑虚空", "墨黑空间、微尘、局部暗金光。", ["服务抽象意象"], []),
        "A-ENV-02": ("scene", "黑檀棋室", "黑檀棋盘、深木格栅。", ["暖烛冷月并置"], []),
        "A-ENV-03": ("scene", "灯火长街", "石板街、木构店面、暖灯笼、夜雾。", ["无现代招牌/乱码"], []),
        "A-ENV-04": ("scene", "风雪祭天坛", "高台石阶、青铜礼器、强风雪旗幡。", ["人物清楚"], []),
        "A-PROP-01": ("prop", "金色棋子", "温润旧金、扁圆、细棋纹。", ["尺寸统一"], []),
        "A-PROP-02": ("prop", "古剑", "冷锻钢直刃、黑革柄、暗金护手。", ["不发光"], []),
        "A-PROP-03": ("prop", "黑檀棋盘", "深色木纹、浅金格线。", ["比例固定"], []),
        "A-PROP-04": ("prop", "相思锁", "旧铜鎏金、双鱼/缠枝暗纹。", ["无模型乱码"], []),
        "A-PROP-05": ("prop", "龙纹密旨", "暗黄丝帛、朱红封印、压纹龙纹。", ["正文后期"], []),
        "GFX-01": ("prop", "《请夫入瓮》无字封面母版", "容华、白筱、棋子、古剑，不含模型字。", ["无字母版"], []),
        "GFX-02": ("prop", "读者好评卡模板", "统一边框/头像占位/星级/短评区。", ["文字后期"], []),
        "GFX-03": ("prop", "书名作者落版", "准确书名作者由后期图形完成。", ["视频模型不得仿制文字"], []),
        "GFX-04": ("prop", "起点阅读引导", "经核准准确LOGO/阅读原文CTA后期完成。", ["视频模型不得仿制"], []),
    }
    shot_refs = {
        1: ["M-CHAR-01", "M-ENV-01", "M-STY-01"],
        2: ["M-CHAR-01", "M-CHAR-02", "M-ENV-02", "M-STY-01"],
        3: ["M-CHAR-01", "M-CHAR-02", "M-ENV-02", "M-STY-01"],
        4: ["M-CHAR-01", "M-CHAR-03", "M-ENV-03", "M-STY-01"],
        5: ["M-CHAR-01", "M-CHAR-02", "M-ENV-03", "M-STY-01"],
        6: ["M-CHAR-01", "M-CHAR-02", "M-ENV-03", "M-STY-01"],
        7: ["M-CHAR-01", "M-PROP-01", "M-ENV-03", "M-STY-01"],
        8: ["M-CHAR-01", "M-CHAR-02", "M-ENV-03", "M-STY-01"],
        9: ["M-CHAR-01", "M-PROP-02", "M-ENV-04", "M-STY-01"],
        10: ["M-CHAR-02", "M-CHAR-04", "M-PROP-03", "M-ENV-05"],
        11: ["M-CHAR-02", "M-CHAR-04", "M-PROP-03", "M-ENV-05"],
        12: ["M-CHAR-01", "M-PROP-02", "M-ENV-06", "M-STY-01"],
        13: ["M-CHAR-01", "M-CHAR-02", "M-ENV-06", "M-STY-01"],
        14: ["M-CHAR-01", "M-CHAR-02", "M-ENV-06", "M-STY-01"],
        15: ["M-CHAR-01", "M-CHAR-02", "M-ENV-06", "M-STY-01"],
        16: ["M-CHAR-01", "M-PROP-02", "M-ENV-06", "M-STY-01"],
        17: ["M-CHAR-01", "M-CHAR-02", "M-ENV-06", "M-STY-01"],
        18: ["M-CHAR-01", "M-CHAR-02", "M-ENV-06", "M-STY-01"],
        19: ["M-CHAR-01", "M-CHAR-02", "M-ENV-06", "M-STY-01"],
        20: ["A-PROP-01", "A-PROP-02", "A-ENV-01", "A-STY-01"],
        21: ["A-CHAR-01", "A-CHAR-02", "A-PROP-01", "A-PROP-02"],
        22: ["A-CHAR-01", "A-PROP-01", "A-PROP-03", "A-ENV-02"],
        23: ["A-CHAR-02", "A-PROP-01", "A-ENV-03", "A-STY-01"],
        24: ["A-CHAR-03", "A-CHAR-04", "A-CHAR-02", "A-ENV-03"],
        25: ["A-CHAR-01", "A-CHAR-02", "A-PROP-03", "A-ENV-02"],
        26: ["A-CHAR-03", "A-CHAR-02", "A-ENV-03", "A-STY-01"],
        27: ["A-CHAR-02", "A-CHAR-01", "A-PROP-04", "A-ENV-02"],
        28: ["A-PROP-04", "A-PROP-05", "A-PROP-02", "A-ENV-04"],
        29: ["A-CHAR-02", "A-CHAR-01", "A-ENV-02", "A-STY-01"],
        30: ["A-CHAR-01", "A-CHAR-02", "A-PROP-02", "A-ENV-04"],
        31: ["GFX-01", "GFX-02", "A-PROP-01", "A-STY-01"],
        32: ["A-CHAR-01", "A-CHAR-02", "A-PROP-03", "A-ENV-02"],
        33: ["GFX-01", "GFX-03", "A-STY-01"],
        34: ["GFX-03", "GFX-04", "GFX-01", "A-STY-01"],
        35: ["A-PROP-01", "A-PROP-02", "A-ENV-01", "A-STY-01"],
    }
    occurrences = {asset_id: {"scene_ids": set(), "shot_ids": set()} for asset_id in asset_defs}
    for ordinal, refs in shot_refs.items():
        shot_id, scene_id = shot_lookup[ordinal]
        for ref_id in refs:
            if ref_id in occurrences:
                occurrences[ref_id]["shot_ids"].add(shot_id)
                occurrences[ref_id]["scene_ids"].add(scene_id)
    assets = []
    for stable_id, (asset_type, display_name, visual_identity, traits, negative_locks) in sorted(asset_defs.items()):
        scene_ids = sorted(occurrences[stable_id]["scene_ids"])
        shot_ids = sorted(occurrences[stable_id]["shot_ids"])
        assets.append(
            {
                "stable_id": stable_id,
                "asset_type": asset_type,
                "asset_subtype": "graphic" if stable_id.startswith("GFX-") else "",
                "display_name": display_name,
                "aliases": [display_name],
                "review_state": "approved",
                "needs_confirmation": False,
                "owner_supplied": True,
                "owner_draft_id": "owner-asset-bible-20260728-v1",
                "style_domain_id": "M-STY-01" if stable_id.startswith("M-") else "A-STY-01",
                "visual_identity": visual_identity,
                "positive_traits": traits,
                "negative_locks": negative_locks,
                "pending_fields": [],
                "occurrences": {"scene_ids": scene_ids, "shot_ids": shot_ids},
                "continuity_states": [
                    {
                        "state_id": f"continuity-{stable_id}",
                        "label": f"{display_name} 由 Owner 底稿确认，跨引用镜头保持同一视觉身份。",
                        "status": "confirmed",
                        "scene_ids": scene_ids,
                        "shot_ids": shot_ids,
                    }
                ],
                "source_evidence": [
                    {
                        "source_type": "shot_reference_map",
                        "source_id": stable_id,
                        "excerpt": "Owner 确认的镜头引用范围。",
                        "scene_ids": scene_ids,
                        "shot_ids": shot_ids,
                    }
                ],
            }
        )
    bible = {
        "schema_version": "afs.asset_bible.v0.1",
        "version": 5,
        "status": "locked",
        "current_revision_id": "asset-bible-r2-4c9bb9b5cf",
        "locked_revision_id": "asset-bible-r2-4c9bb9b5cf",
        "candidate_set": {
            "candidate_set_id": "asset-candidates-owner-20260728-v1",
            "script_revision_id": "script-revision-current-project",
            "shot_candidate_id": "shot-candidate-current-project",
            "scene_index": scenes,
            "shot_index": shots,
            "scene_count": 4,
            "shot_count": 35,
            "style_domains": [
                {
                    "domain_id": "M-STY-01",
                    "art_direction_id": "M-STY-01",
                    "label": "现代重生甜虐",
                    "visual_style": "商业级都市重生甜虐短剧；写实、表演清楚；前世冷青黑低饱和，泳池香槟金/暖白/蓝绿水光，演播厅黑金冷白。",
                    "medium": "写实短剧摄影，真实人物表演，皮肤、织物、水面和舞台材质清楚。",
                    "palette": "前世冷青黑低饱和；泳池香槟金/暖白/蓝绿水光；演播厅黑金冷白。",
                    "lighting": "恐惧贴近移动浅景深、喜剧干净中近景、暧昧慢推距离压缩。",
                    "negative_locks": ["禁止廉价网大滤镜"],
                    "status": "approved",
                    "owner_supplied": True,
                },
                {
                    "domain_id": "A-STY-01",
                    "art_direction_id": "A-STY-01",
                    "label": "古言棋局",
                    "visual_style": "高概念甜虐古言/爱情棋局/权谋寓言，架空东方。",
                    "medium": "丝绸暗纹锦缎、旧铜、玉石、黑檀、冷锻钢。",
                    "palette": "墨黑、暗金、朱红、月白。",
                    "lighting": "构图强调对峙、遮挡、棋盘线条和距离。",
                    "negative_locks": ["拒绝仙侠光污染", "拒绝廉价金粉", "拒绝无意义慢动作"],
                    "status": "approved",
                    "owner_supplied": True,
                },
            ],
        },
        "assets": assets,
        "art_direction": {
            "visual_style": "双域商业短剧资产参考；现代都市甜虐与古言棋局分别保持命名空间。",
            "medium": "电影摄影级写实资产设定，清楚表演与可复用材质。",
            "palette": "现代冷青黑/香槟金/泳池蓝绿；古言墨黑暗金朱红月白。",
            "lighting": "人物脸部与资产轮廓清楚，避免廉价滤镜和文字生成。",
            "status": "confirmed",
            "source": "human_review",
            "confirmed_at": REQUESTED_AT,
        },
        "coverage": {
            "coverage_pass": True,
            "quality_pass": True,
            "scene_total": 4,
            "scene_covered": 4,
            "shot_total": 35,
            "shot_covered": 35,
            "asset_shot_covered": 35,
            "missing_source_evidence_shot_count": 0,
            "required_occurrence_total": sum(len(row) for row in shot_refs.values()),
            "resolved_required": sum(len(row) for row in shot_refs.values()),
            "unresolved_required": 0,
        },
        "recognition_quality": {
            "status": "pass",
            "issues": [],
            "missing_anchor_count": 0,
            "orphan_scene_coverage_count": 0,
            "alias_collision_count": 0,
            "recognition_ambiguity_count": 0,
        },
    }
    return {
        "authority_mode": "canonical_production_graph",
        "production_graph_version": 5,
        "production_graph_digest": "28885fbc833635c9edac94e0a0f5412eb29bce2a169b884ee56cceb6d145f34b",
        "studio_state_version": "studio-state-current",
        "art_direction": bible["art_direction"],
        "shot_grounding": {"scenes": scenes, "shots": shots},
        "asset_bible": bible,
    }


def _command(client: TestClient, command: dict, source: dict, *, confirm: bool = True) -> dict:
    body = {"command": command, "source": source, "requested_at": REQUESTED_AT}
    preview = client.post(f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview", json=body)
    assert preview.status_code == 200, preview.text
    if not confirm:
        return preview.json()
    body["preview_digest"] = preview.json()["preview_digest"]
    response = client.post(f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _compiled_locked_client(tmp_path, monkeypatch) -> tuple[TestClient, dict]:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "false")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    source = source_contract()
    _command(client, {"type": "compile"}, source)
    _command(client, {"type": "lock"}, source)
    return client, source


def test_public_image_admission_history_summary_reports_latest_target_lifecycle(tmp_path) -> None:
    runtime_root = tmp_path / "runtime"
    store = RuntimeStore(runtime_root)
    store.ensure_project_manifest(PROJECT_ID)
    root = runtime_root / "projects" / PROJECT_ID / "image_admission"
    history = root / "history"
    history.mkdir(parents=True)

    def manifest(manifest_id: str, updated_at: str, items: list[dict]) -> dict:
        return {
            "schema_version": "afs.image_admission_manifest.v0.1",
            "project_id": PROJECT_ID,
            "manifest_id": manifest_id,
            "manifest_hash": "a" * 64,
            "status": "locked",
            "updated_at": updated_at,
            "items": items,
        }

    (history / "image-admission-old-failed.json").write_text(
        json.dumps(
            manifest(
                "image-admission-old-failed",
                "2026-07-24T00:00:00Z",
                [
                    {"item_id": "admit-character-a", "target_asset_ids": ["asset-character-a"], "state": "failed"},
                    {"item_id": "admit-scene-a", "target_asset_ids": ["asset-scene-a"], "state": "failed"},
                ],
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (history / "image-admission-recovered.json").write_text(
        json.dumps(
            manifest(
                "image-admission-recovered",
                "2026-07-24T01:00:00Z",
                [{"item_id": "admit-character-a", "target_asset_ids": ["asset-character-a"], "state": "approved"}],
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "manifest.json").write_text(
        json.dumps(
            manifest(
                "image-admission-current",
                "2026-07-24T02:00:00Z",
                [{"item_id": "admit-scene-b", "target_asset_ids": ["asset-scene-b"], "state": "candidate"}],
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    response = client.get(f"/projects/{PROJECT_ID}/m6/image-admission")

    assert response.status_code == 200, response.text
    assert response.json()["history_summary"] == {
        "target_item_count": 3,
        "approved_item_count": 1,
        "candidate_item_count": 1,
        "pending_item_count": 1,
        "planned_item_count": 0,
        "deferred_item_count": 1,
        "rejected_item_count": 0,
        "cancelled_item_count": 0,
    }


def test_fixed_manifest_approval_preview_tolerates_stale_browser_source_without_relaxing_continuation(
    tmp_path,
    monkeypatch,
) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    monkeypatch.setenv("AFS_ALLOW_DETERMINISTIC_MEDIA_FIXTURES", "true")
    current = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    item = next(item for item in current["items"] if item["item_type"] == "character_design")
    _command(
        client,
        {
            "type": "record_candidate",
            "item_id": item["item_id"],
            "fixture": True,
        },
        source,
    )
    stale_source = deepcopy(source)
    stale_source["asset_bible"]["assets"][0]["visual_identity"] = "stale browser-only source"

    approve = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "approve",
                "item_id": item["item_id"],
                "idempotency_key": "stale-browser-source-approve-preview",
            },
            "source": stale_source,
            "requested_at": REQUESTED_AT,
        },
    )

    assert approve.status_code == 200, approve.text
    assert approve.json()["command"]["type"] == "approve"
    assert approve.json()["provider_dispatch_count"] == 0
    preview_item = next(
        entry
        for entry in approve.json()["result"]["manifest"]["items"]
        if entry["item_id"] == item["item_id"]
    )
    assert preview_item["state"] == "approved"

    continuation = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "inspect_next_batch",
                "idempotency_key": "stale-browser-source-continuation-preview",
            },
            "source": stale_source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert continuation.status_code == 422
    assert "image admission manifest source is stale" in continuation.json()["detail"]["details"]["raw_detail"]


def test_manifest_compiler_produces_dynamic_unique_lineage_items_without_name_rules() -> None:
    manifest = compile_image_admission_manifest(PROJECT_ID, source_contract(), created_at=REQUESTED_AT)

    assert manifest["status"] == "draft"
    assert len(manifest["items"]) == len({item["item_id"] for item in manifest["items"]}) == 12
    assert [item["item_type"] for item in manifest["items"]].count("character_design") == 3
    assert [item["item_type"] for item in manifest["items"]].count("scene_plate") == 3
    assert [item["item_type"] for item in manifest["items"]].count("prop_design") == 3
    assert [item["item_type"] for item in manifest["items"]].count("shot_keyframe") == 3
    assert all(item["candidate_count"] == 1 for item in manifest["items"])
    assert all(item["source_fingerprint"] == manifest["source_fingerprint"] for item in manifest["items"])
    assert manifest["budget_contract"]["unit_estimate_usd"] == "0.0377"
    assert manifest["budget_contract"]["max_estimated_usd"] == "0.0377"
    assert manifest["budget_contract"]["max_dispatches"] == 1
    assert manifest["budget_contract"]["program_max_usd"] == "50.0000"
    assert manifest["art_direction"]["visual_style"] == "写实古装动作片"
    assert manifest["creative_grounding"]["status"] == "ready"
    assert manifest["creative_grounding"]["source_evidence_summary"]["status"] == "complete"
    assert manifest["creative_grounding"]["source_evidence_summary"]["traceable_shot_count"] == 17
    character = next(item for item in manifest["items"] if item["item_type"] == "character_design")
    assert character["asset_grounding"]["visual_identity"]
    assert character["asset_grounding"]["positive_traits"]
    assert character["asset_grounding"]["continuity_states"][0]["status"] == "confirmed"
    assert character["prompt_contract"]["provider_prompt_digest"] == canonical_digest(
        character["prompt_contract"]["provider_prompt"]
    )
    assert "【资产身份】" in character["prompt_contract"]["provider_prompt"]
    assert "角色设定" in character["prompt_contract"]["provider_prompt"]
    assert "禁止添加文字、水印、界面元素或边框" in character["prompt_contract"]["provider_prompt"]
    assert "character_design" not in character["prompt_contract"]["provider_prompt"]
    assert "do not add text" not in character["prompt_contract"]["provider_prompt"]
    keyframe = next(item for item in manifest["items"] if item["item_type"] == "shot_keyframe")
    assert keyframe["shot_grounding"]["purpose"]
    assert keyframe["reference_asset_grounding"]
    assert "【镜头依据】" in keyframe["prompt_contract"]["provider_prompt"]
    assert "【引用资产】" in keyframe["prompt_contract"]["provider_prompt"]


def test_character_design_prompt_is_identity_first_and_preserves_owner_metadata() -> None:
    source = source_contract()
    character = source["asset_bible"]["assets"][0]
    character["demographics"] = "modern East Asian young woman"
    character["visual_identity"] = "modern East Asian young woman, clear oval face, compact athletic build"
    character["positive_traits"] = [
        "clean canonical costume silhouette for base identity",
        "wet pool plot-state variant must stay nonsexual",
        "theatrical messy waterproof disguise variant, never ethnic blackface",
    ]
    character["negative_locks"] = ["never ethnic blackface"]

    manifest = compile_image_admission_manifest(PROJECT_ID, source, created_at=REQUESTED_AT)
    item = next(entry for entry in manifest["items"] if entry["target_asset_ids"] == ["asset-character-a"])
    prompt = item["prompt_contract"]["provider_prompt"]

    assert "【基准身份参考】" in prompt
    assert "制作命名空间：asset-character-a" in prompt
    assert "人口与身份锚点：modern East Asian young woman" in prompt
    assert "production reference sheet framing" in prompt
    assert "全身或四分之三" in prompt
    assert "中性站姿、无遮挡" in prompt
    assert "稳定同一张脸、同一身份、同一体型" in prompt
    assert "【变体连续性】" in prompt
    assert "基准 canonical identity 优先" in prompt
    assert "保留同一张脸和同一身体身份" in prompt
    assert "wet pool plot-state variant must stay nonsexual" in prompt
    assert "剧情驱动、非情色化" in prompt
    assert "不得呈现为族裔模仿式黑脸" in prompt
    assert "禁止添加任何文字、字幕、标题、Logo、水印、界面、联系表标签、误生成文字或边框" in prompt
    assert "叶安安" not in prompt
    assert "M-CHAR-01" not in prompt


def test_character_design_prompt_does_not_invent_demographics_or_inflate_other_assets() -> None:
    manifest = compile_image_admission_manifest(PROJECT_ID, source_contract(), created_at=REQUESTED_AT)
    character = next(entry for entry in manifest["items"] if entry["target_asset_ids"] == ["asset-character-a"])
    scene = next(entry for entry in manifest["items"] if entry["item_type"] == "scene_plate")
    prop = next(entry for entry in manifest["items"] if entry["item_type"] == "prop_design")

    character_prompt = character["prompt_contract"]["provider_prompt"]
    scene_prompt = scene["prompt_contract"]["provider_prompt"]
    prop_prompt = prop["prompt_contract"]["provider_prompt"]

    assert "人口与身份锚点" not in character_prompt
    assert "East Asian" not in character_prompt
    assert "【基准身份参考】" in character_prompt
    assert "production reference sheet framing" in character_prompt
    assert "【基准身份参考】" not in scene_prompt
    assert "production reference sheet framing" not in scene_prompt
    assert "production environment reference / scene plate" in scene_prompt
    assert "【变体连续性】" not in prop_prompt
    assert "同一张脸" not in prop_prompt


def test_scene_plate_prompt_is_production_environment_reference_with_shot_continuity() -> None:
    source = source_contract()
    scene_asset = next(
        asset for asset in source["asset_bible"]["assets"] if asset["stable_id"] == "asset-scene-a"
    )
    scene_asset["style_domain_id"] = "domain-modern-test"
    scene_asset["visual_identity"] = "北侧检修站，玻璃顶棚、湿地面、金属门廊，入口朝东"
    scene_asset["positive_traits"] = ["可见入口/出口", "湿地面反射连续", "保留巡夜路线"]
    source["asset_bible"]["candidate_set"]["style_domains"] = [
        {
            "domain_id": "domain-modern-test",
            "art_direction_id": "domain-modern-test",
            "visual_style": "现代工业悬疑写实",
            "medium": "电影摄影，金属、玻璃和潮湿混凝土材质清楚",
            "palette": "冷绿灰与钠灯暖色对比",
            "lighting": "入口顶灯和室内安全灯形成可复现 practical lighting",
        },
        {
            "domain_id": "domain-unused-ancient",
            "art_direction_id": "domain-unused-ancient",
            "visual_style": "古代宫廷棋局",
            "medium": "丝绸黑檀玉石",
            "palette": "墨黑暗金",
            "lighting": "烛火冷月",
        },
    ]

    manifest = compile_image_admission_manifest(PROJECT_ID, source, created_at=REQUESTED_AT)
    item = next(entry for entry in manifest["items"] if entry["target_asset_ids"] == ["asset-scene-a"])
    prompt = item["prompt_contract"]["provider_prompt"]

    assert item["item_type"] == "scene_plate"
    assert item["aspect_ratio"] == "16:9"
    assert item["size"] == "1280x720"
    assert "制作命名空间：asset-scene-a" in prompt
    assert "风格域：domain-modern-test" in prompt
    assert "现代工业悬疑写实" in prompt
    assert "古代宫廷棋局" not in prompt
    assert "16:9 production environment reference / scene plate" in prompt
    assert "不是装饰性概念背景" in prompt
    assert "匿名背景剪影或虚化宾客" in prompt
    assert "前景/中景/背景 depth 分层" in prompt
    assert "入口、出口或 circulation path" in prompt
    assert "key landmark positions" in prompt
    assert "至少两个 camera-accessible actor blocking/action zones" in prompt
    assert "sightlines" in prompt
    assert "practical lighting" in prompt
    assert "反射与明暗关系必须连续" in prompt
    assert "引用镜头" in prompt
    assert "scene-1-shot-1" in prompt
    assert "scene-1-shot-6" in prompt
    assert "根据引用镜头的 title/id/purpose/action 摘要" in prompt
    assert "禁止添加任何文字、字幕、标题、Logo、水印、界面、地图标签、导视牌文字、误生成文字或边框" in prompt
    assert "featured character" in prompt
    assert "【基准身份参考】" not in prompt
    assert "同一张脸" not in prompt
    assert item["prompt_contract"]["provider_prompt_digest"] == canonical_digest(prompt)


def test_current_project_mchar01_prompt_regression_changes_manifest_hash_deterministically() -> None:
    source = current_project_locked_source_contract()
    first = compile_image_admission_manifest(CURRENT_PROJECT_ID, source, created_at=REQUESTED_AT)
    second = compile_image_admission_manifest(CURRENT_PROJECT_ID, source, created_at=REQUESTED_AT)

    assert first["manifest_id"] == second["manifest_id"]
    assert first["manifest_hash"] == second["manifest_hash"]
    assert first["manifest_id"] == "image-admission-e2a1d2c8370d9915"
    assert first["manifest_hash"] == "e2a1d2c8370d9915d3eb883bf0a2597d6db4463a6b83b683c2a72b0c02e27325"
    assert first["manifest_hash"] != OLD_CURRENT_PROJECT_MANIFEST_HASH
    assert len(first["items"]) == 33
    assert first["selection_summary"] == {
        "canonical_character_count": 8,
        "canonical_scene_count": 10,
        "canonical_prop_count": 12,
        "applied_shot_count": 35,
        "representative_shot_count": 3,
        "item_count": 33,
    }
    item = next(entry for entry in first["items"] if entry["target_asset_ids"] == ["M-CHAR-01"])
    prompt = item["prompt_contract"]["provider_prompt"]

    assert item["item_id"] == "admit-character_design-a14c33cdb7"
    assert item["item_type"] == "character_design"
    assert item["aspect_ratio"] == "3:4"
    assert "叶安安" in prompt
    assert "制作命名空间：M-CHAR-01" in prompt
    assert "production reference sheet framing" in prompt
    assert "全身或四分之三" in prompt
    assert "单一角色、中性站姿、无遮挡" in prompt
    assert "基准 canonical identity 优先" in prompt
    assert "泳池湿身（非情色）" in prompt
    assert "白浴巾伪装" in prompt
    assert "灰黑防水脏污妆+粗框眼镜+乱发+低饱和碎花裙" in prompt
    assert "同一张脸和同一身体身份" in prompt
    assert "剧情驱动、非情色化" in prompt
    assert "不得呈现为族裔模仿式黑脸" in prompt
    assert "禁止添加任何文字、字幕、标题、Logo、水印、界面、联系表标签、误生成文字或边框" in prompt
    assert "人口与身份锚点" not in prompt
    assert "East Asian" not in prompt
    assert item["prompt_contract"]["provider_prompt_digest"] == canonical_digest(prompt)

    scene_item = next(entry for entry in first["items"] if entry["target_asset_ids"] == ["M-ENV-03"])
    scene_prompt = scene_item["prompt_contract"]["provider_prompt"]
    scene_refs = [
        reference["shot_id"]
        for reference in scene_item.get("shot_reference_grounding", [])
    ]

    assert scene_item["item_id"] == "admit-scene_plate-d682ac4be7"
    assert scene_item["item_type"] == "scene_plate"
    assert scene_item["aspect_ratio"] == "16:9"
    assert scene_item["size"] == "1280x720"
    assert scene_item["prompt_contract"]["provider_prompt_digest"] == (
        "964db078b781fef2a00645920c8dcd13896fde67339920e9294b60b95cef558e"
    )
    assert scene_item["prompt_contract"]["provider_prompt_digest"] == canonical_digest(scene_prompt)
    assert scene_refs == [
        "shot-embedded-f0879c54f044ebb3-01-04",
        "shot-embedded-f0879c54f044ebb3-01-05",
        "shot-embedded-f0879c54f044ebb3-01-06",
        "shot-embedded-f0879c54f044ebb3-01-07",
        "shot-embedded-f0879c54f044ebb3-01-08",
    ]
    assert "豪宅泳池派对" in scene_prompt
    assert "制作命名空间：M-ENV-03" in scene_prompt
    assert "风格域：M-STY-01" in scene_prompt
    assert "商业级都市重生甜虐短剧" in scene_prompt
    assert "夜间泳池、暖金庭院灯、蓝绿水面" in scene_prompt
    assert "克制宾客背景" in scene_prompt
    assert "16:9 production environment reference / scene plate" in scene_prompt
    assert "不是装饰性概念背景" in scene_prompt
    assert "匿名背景剪影或虚化宾客" in scene_prompt
    assert "前景/中景/背景 depth 分层" in scene_prompt
    assert "入口、出口或 circulation path" in scene_prompt
    assert "至少两个 camera-accessible actor blocking/action zones" in scene_prompt
    assert "sightlines" in scene_prompt
    assert "practical lighting" in scene_prompt
    assert "反射与明暗关系必须连续" in scene_prompt
    assert "shot-embedded-f0879c54f044ebb3-01-04" in scene_prompt
    assert "shot-embedded-f0879c54f044ebb3-01-08" in scene_prompt
    assert "根据引用镜头的 title/id/purpose/action 摘要" in scene_prompt
    assert "禁止添加任何文字、字幕、标题、Logo、水印、界面、地图标签、导视牌文字、误生成文字或边框" in scene_prompt
    for ancient_term in ("古言", "棋局", "黑檀", "古剑", "棋子", "祭天"):
        assert ancient_term not in scene_prompt


def test_manifest_compile_fails_closed_for_visual_pending_or_missing_art_direction() -> None:
    source = source_contract()
    source["asset_bible"]["assets"][0]["pending_fields"] = ["visual_identity"]
    with pytest.raises(ValueError, match="图片准入创意依据不完整"):
        compile_image_admission_manifest(PROJECT_ID, source)


def test_manifest_compile_fails_closed_for_missing_traceable_source_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "false")
    source = source_contract()
    for asset in source["asset_bible"]["assets"]:
        asset["source_evidence"] = []
    with pytest.raises(ValueError, match="0/17 traceable"):
        compile_image_admission_manifest(PROJECT_ID, source)
    forged = source_contract()
    for asset in forged["asset_bible"]["assets"]:
        asset["occurrences"]["shot_ids"] = []
    with pytest.raises(ValueError, match="0/17 traceable"):
        compile_image_admission_manifest(PROJECT_ID, forged)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    response = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {"type": "compile", "idempotency_key": "missing-evidence"},
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 422
    readback = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()
    assert readback["status"] == "empty"
    assert readback["provider_dispatch_count"] == 0
    assert readback["external_cost_usd"] == "0.0000"

    source = source_contract()
    source["art_direction"] = {}
    source["asset_bible"]["art_direction"] = {}
    with pytest.raises(ValueError, match="统一美术方向"):
        compile_image_admission_manifest(PROJECT_ID, source)


@pytest.mark.parametrize(
    ("source_type", "source_id"),
    [
        ("", "source-id"),
        ("script_revision", ""),
        ("custom_source", "source-id"),
        ("script_revision", "../unsafe-source"),
        ("script_revision", "script-revision-current"),
        ("occurrence_ledger", "asset-other"),
        ("applied_shot_plan", "shot-outside-occurrence"),
    ],
)
def test_manifest_compile_recomputes_authoritative_evidence_semantics(
    source_type: str,
    source_id: str,
) -> None:
    source = source_contract()
    for asset in source["asset_bible"]["assets"]:
        asset["source_evidence"] = [
            {
                "source_type": source_type,
                "source_id": source_id,
                "scene_ids": asset["occurrences"]["scene_ids"],
                "shot_ids": asset["occurrences"]["shot_ids"],
                "excerpt": "伪造的镜头覆盖记录",
            }
        ]
    with pytest.raises(ValueError, match="0/17 traceable"):
        compile_image_admission_manifest(PROJECT_ID, source)


def test_prompt_and_source_fingerprint_change_with_reviewed_creative_facts() -> None:
    original = compile_image_admission_manifest(PROJECT_ID, source_contract(), created_at=REQUESTED_AT)
    revised_source = source_contract()
    revised_source["asset_bible"]["assets"][0]["visual_identity"] += "，额外确认面部纹理"
    revised = compile_image_admission_manifest(PROJECT_ID, revised_source, created_at=REQUESTED_AT)

    assert revised["source_fingerprint"] != original["source_fingerprint"]
    assert revised["manifest_hash"] != original["manifest_hash"]
    original_item = next(item for item in original["items"] if item["target_asset_ids"] == ["asset-character-a"])
    revised_item = next(item for item in revised["items"] if item["target_asset_ids"] == ["asset-character-a"])
    assert revised_item["prompt_contract"]["provider_prompt_digest"] != original_item["prompt_contract"]["provider_prompt_digest"]


@pytest.mark.parametrize("shot_count", [1, 2, 3])
def test_manifest_compiler_accepts_general_canonical_asset_and_shot_counts(shot_count: int) -> None:
    manifest = compile_image_admission_manifest(
        PROJECT_ID,
        compact_source_contract(shot_count=shot_count),
    )

    assert manifest["selection_summary"] == {
        "canonical_character_count": 1,
        "canonical_scene_count": 1,
        "canonical_prop_count": 1,
        "applied_shot_count": shot_count,
        "representative_shot_count": shot_count,
        "item_count": 3 + shot_count,
    }
    assert {item["label"] for item in manifest["items"] if item["target_asset_ids"]} == {
        "巡夜人·甲",
        "北侧检修站",
        "六角校准器",
    }


def test_preview_cancel_is_non_mutating_and_confirm_reload_is_stable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "false")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    source = source_contract()

    preview = _command(client, {"type": "compile"}, source, confirm=False)
    assert preview["result"]["graph_mutation"] == 0
    assert preview["provider_dispatch_count"] == 0
    assert client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["status"] == "empty"

    _command(client, {"type": "compile"}, source)
    _command(client, {"type": "lock"}, source)
    first = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    second = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    assert first == second
    assert first["status"] == "locked"
    assert first["provider_dispatch_count"] == 0


def test_source_revision_drift_invalidates_commands(tmp_path, monkeypatch) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    stale = deepcopy(source)
    stale["asset_bible"]["locked_revision_id"] = "asset-bible-r8-new"
    response = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={"command": {"type": "cancel_batch"}, "source": stale, "requested_at": REQUESTED_AT},
    )
    assert response.status_code == 422
    assert "source is stale" in response.json()["detail"]["details"]["raw_detail"]


def test_gate_closed_and_reference_contract_block_before_budget_reservation(tmp_path, monkeypatch) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    manifest = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    asset_item = next(item for item in manifest["items"] if item["item_type"] == "character_design")
    response = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {"type": "reserve_dispatch", "item_id": asset_item["item_id"], "idempotency_key": "reserve-1"},
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 422
    assert "未发送任何外部请求" in response.json()["detail"]["details"]["raw_detail"]
    persisted = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    assert persisted["budget"]["dispatches_reserved"] == 0


def test_legacy_multi_dispatch_budget_contract_fails_closed_before_reservation(
    tmp_path,
    monkeypatch,
) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    path = (
        tmp_path
        / "runtime"
        / "projects"
        / PROJECT_ID
        / "image_admission"
        / "manifest.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["budget_contract"]["max_dispatches"] = 9
    manifest["budget_contract"]["max_estimated_usd"] = "0.3500"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    item_id = next(
        item["item_id"]
        for item in manifest["items"]
        if item["item_type"] == "character_design"
    )

    blocked = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "reserve_dispatch",
                "item_id": item_id,
                "idempotency_key": "legacy-budget-reserve",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )

    assert blocked.status_code == 422
    assert "费用合同已更新" in blocked.json()["detail"]["details"]["raw_detail"]
    persisted = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()[
        "manifest"
    ]
    assert persisted["budget"]["dispatches_reserved"] == 0


def test_failed_single_smoke_creates_one_new_manifest_without_reusing_old_ledger(
    tmp_path,
    monkeypatch,
) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    manifest = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    item_id = next(item["item_id"] for item in manifest["items"] if item["item_type"] == "character_design")

    reserve = {
        "type": "reserve_dispatch",
        "item_id": item_id,
        "idempotency_key": "reserve-1",
    }
    request = {"command": reserve, "source": source, "requested_at": REQUESTED_AT}
    preview = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json=request,
    ).json()
    request["preview_digest"] = preview["preview_digest"]
    confirmed = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        json=request,
    )
    assert confirmed.status_code == 200
    replay = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        json=request,
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    failed = _command(
        client,
        {
            "type": "record_failure",
            "item_id": item_id,
            "idempotency_key": "failure-1",
            "error_category": "controlled_test_failure",
        },
        source,
    )["result"]["manifest"]
    old_manifest = deepcopy(failed)
    old_other_items = [
        entry["item_id"] for entry in old_manifest["items"] if entry["item_id"] != item_id
    ]

    replace_blocked = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "replace",
                "item_id": item_id,
                "idempotency_key": "replace-exhausted",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert replace_blocked.status_code == 422
    assert "create a new recovery manifest" in replace_blocked.json()["detail"]["details"]["raw_detail"]

    recovery_command = {
        "type": "create_recovery_manifest",
        "item_id": item_id,
        "source_manifest_id": old_manifest["manifest_id"],
        "idempotency_key": "recovery-manifest-1",
    }
    request = {
        "command": recovery_command,
        "source": source,
        "requested_at": REQUESTED_AT,
    }
    preview_response = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json=request,
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    preview_manifest = preview["result"]["manifest"]
    assert preview["provider_dispatch_count"] == 0
    assert preview["external_cost_usd"] == "0.0000"
    assert preview["impact"]["recovery_manifest"] == {
        "creates_new_manifest": True,
        "previous_manifest_preserved_on_confirm": True,
        "selected_item_count": 1,
        "previous_dispatches_preserved": 1,
        "previous_estimated_reserved_usd": "0.0377",
        "new_max_dispatches": 1,
        "new_max_estimated_usd": "0.0377",
        "auto_retry": 0,
        "provider_calls_before_confirm": 0,
        "requires_separate_generation_confirmation": True,
    }
    assert len(preview_manifest["items"]) == 1
    assert preview_manifest["items"][0]["item_id"] == item_id
    assert preview_manifest["items"][0]["state"] == "planned"
    assert preview_manifest["status"] == "locked"
    assert preview_manifest["budget"]["dispatches_reserved"] == 0
    assert preview_manifest["budget"]["remaining_dispatches"] == 1
    assert preview_manifest["provider_dispatch_count"] == 0
    assert preview_manifest["recovery_contract"]["auto_retry"] == 0
    assert preview_manifest["recovery_contract"]["requires_separate_generation_confirmation"] is True
    assert client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"] == old_manifest

    concurrent_request = {
        "command": {
            **recovery_command,
            "idempotency_key": "recovery-manifest-concurrent",
        },
        "source": source,
        "requested_at": REQUESTED_AT,
    }
    concurrent_preview = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json=concurrent_request,
    )
    assert concurrent_preview.status_code == 200
    concurrent_request["preview_digest"] = concurrent_preview.json()["preview_digest"]

    request["preview_digest"] = preview["preview_digest"]
    confirmed_response = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        json=request,
    )
    assert confirmed_response.status_code == 200, confirmed_response.text
    confirmed = confirmed_response.json()["result"]["manifest"]
    assert confirmed == client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    assert confirmed["manifest_id"] != old_manifest["manifest_id"]
    assert confirmed["project_id"] == old_manifest["project_id"]
    assert confirmed["source_fingerprint"] == old_manifest["source_fingerprint"]
    assert confirmed["accepted_graph_snapshots"] == old_manifest["accepted_graph_snapshots"]
    assert confirmed["source"]["asset_bible_revision_id"] == old_manifest["source"]["asset_bible_revision_id"]
    assert confirmed["recovery_contract"]["source_manifest_id"] == old_manifest["manifest_id"]
    assert confirmed["receipts"][-1]["state"] == "recovery_manifest_created"
    assert confirmed_response.json()["result"]["graph_mutation"] == 0

    archive_path = (
        tmp_path
        / "runtime"
        / "projects"
        / PROJECT_ID
        / "image_admission"
        / "history"
        / f"{old_manifest['manifest_id']}.json"
    )
    assert json.loads(archive_path.read_text(encoding="utf-8")) == old_manifest
    assert all(
        entry["state"] == "planned"
        for entry in old_manifest["items"]
        if entry["item_id"] in old_other_items
    )

    replay = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        json=request,
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert json.loads(archive_path.read_text(encoding="utf-8")) == old_manifest

    concurrent_confirm = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        json=concurrent_request,
    )
    assert concurrent_confirm.status_code == 422
    assert json.loads(archive_path.read_text(encoding="utf-8")) == old_manifest

    duplicate = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                **recovery_command,
                "idempotency_key": "recovery-manifest-2",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert duplicate.status_code == 422
    assert "already a single-item recovery manifest" in duplicate.json()["detail"]["details"]["raw_detail"]

    reserve_preview = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "reserve_dispatch",
                "item_id": item_id,
                "idempotency_key": "recovery-reserve-preview",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert reserve_preview.status_code == 200, reserve_preview.text
    persisted = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    assert persisted["budget"]["dispatches_reserved"] == 0
    assert persisted["provider_dispatch_count"] == 0
    assert len(persisted["items"]) == 1


def test_legacy_failed_manifest_recovers_against_current_server_graph_without_relaxing_other_commands(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    runtime_root = tmp_path / "runtime"
    store = RuntimeStore(runtime_root)
    store.ensure_project_manifest(PROJECT_ID)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.ensure(PROJECT_ID)
    graph = graph_store.append(
        PROJECT_ID,
        expected_version=graph["version"],
        idempotency_key="seed-recovery-lineage",
        semantic_digest=canonical_digest({"node_id": "recovery-lineage-root"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "recovery-lineage-root",
                    "category": "revision",
                    "state": "active",
                },
            }
        ],
    )
    old_source = source_contract(
        graph_version=graph["version"],
        graph_digest=graph["graph_digest"],
    )
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    _command(client, {"type": "compile"}, old_source)
    _command(client, {"type": "lock"}, old_source)
    manifest = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    item_id = next(
        item["item_id"]
        for item in manifest["items"]
        if item["item_type"] == "character_design"
    )
    _command(
        client,
        {
            "type": "reserve_dispatch",
            "item_id": item_id,
            "idempotency_key": "legacy-lineage-reserve",
        },
        old_source,
    )
    old_manifest = _command(
        client,
        {
            "type": "record_failure",
            "item_id": item_id,
            "idempotency_key": "legacy-lineage-failure",
            "error_category": "blocked",
        },
        old_source,
    )["result"]["manifest"]

    advanced = graph_store.append(
        PROJECT_ID,
        expected_version=graph["version"],
        idempotency_key="advance-after-legacy-manifest",
        semantic_digest=canonical_digest({"state": "post-admission-projection"}),
        events=[
            {
                "type": "node_metadata_updated",
                "node_id": "recovery-lineage-root",
                "patch": {"projection_state": "post-admission"},
            }
        ],
    )
    current_source = source_contract(
        graph_version=advanced["version"],
        graph_digest=advanced["graph_digest"],
    )
    recovery_command = {
        "type": "create_recovery_manifest",
        "item_id": item_id,
        "source_manifest_id": old_manifest["manifest_id"],
        "idempotency_key": "legacy-lineage-recovery",
    }

    ordinary_command = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "cancel_batch",
                "idempotency_key": "ordinary-command-stays-stale",
            },
            "source": current_source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert ordinary_command.status_code == 422
    assert "ProductionGraph source is stale" in ordinary_command.json()["detail"]["details"]["raw_detail"]

    stale_accepted = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                **recovery_command,
                "idempotency_key": "stale-accepted-recovery",
            },
            "source": old_source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert stale_accepted.status_code == 422
    assert "not the current project graph" in stale_accepted.json()["detail"]["details"]["raw_detail"]

    forged_graph = deepcopy(current_source)
    forged_graph["production_graph_digest"] = "f" * 64
    forged = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": recovery_command,
            "source": forged_graph,
            "requested_at": REQUESTED_AT,
        },
    )
    assert forged.status_code == 422
    assert "not the current project graph" in forged.json()["detail"]["details"]["raw_detail"]

    changed_bible = deepcopy(current_source)
    changed_bible["asset_bible"]["assets"][0]["visual_identity"] = "changed identity"
    semantic_drift = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": recovery_command,
            "source": changed_bible,
            "requested_at": REQUESTED_AT,
        },
    )
    assert semantic_drift.status_code == 422
    assert "manifest source is stale" in semantic_drift.json()["detail"]["details"]["raw_detail"]

    request = {
        "command": recovery_command,
        "source": current_source,
        "requested_at": REQUESTED_AT,
    }
    preview = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json=request,
    )
    assert preview.status_code == 200, preview.text
    assert client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"] == old_manifest
    request["preview_digest"] = preview.json()["preview_digest"]
    confirmed = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        json=request,
    )
    assert confirmed.status_code == 200, confirmed.text
    recovery = confirmed.json()["result"]["manifest"]
    assert recovery["accepted_graph_snapshots"] == [
        {
            "version": advanced["version"],
            "graph_digest": advanced["graph_digest"],
            "reason": "manifest_source",
        }
    ]
    assert len(recovery["items"]) == 1
    assert recovery["items"][0]["item_id"] == item_id
    assert recovery["provider_dispatch_count"] == 0
    assert recovery["budget"]["dispatches_reserved"] == 0
    assert recovery["budget"]["remaining_dispatches"] == 1
    assert recovery["budget_contract"]["auto_retry"] == 0
    assert graph_store.load(PROJECT_ID)["graph_digest"] == advanced["graph_digest"]
    archive = (
        runtime_root
        / "projects"
        / PROJECT_ID
        / "image_admission"
        / "history"
        / f"{old_manifest['manifest_id']}.json"
    )
    assert json.loads(archive.read_text(encoding="utf-8")) == old_manifest


def test_recovery_manifest_fails_closed_on_stale_source_or_nonfailed_selection(
    tmp_path,
    monkeypatch,
) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    path = (
        tmp_path
        / "runtime"
        / "projects"
        / PROJECT_ID
        / "image_admission"
        / "manifest.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    failed_item = next(item for item in manifest["items"] if item["item_type"] == "character_design")
    planned_item = next(item for item in manifest["items"] if item["item_id"] != failed_item["item_id"])
    manifest["budget"].update(
        {
            "dispatches_reserved": 1,
            "estimated_reserved_usd": "0.0377",
            "remaining_dispatches": 0,
            "remaining_estimated_usd": "0.0000",
        }
    )
    manifest["provider_dispatch_count"] = 1
    failed_item["state"] = "failed"
    failed_item["dispatch_ordinal"] = 1
    failed_item["error_category"] = "blocked"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    base_command = {
        "type": "create_recovery_manifest",
        "source_manifest_id": manifest["manifest_id"],
    }
    wrong_item = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                **base_command,
                "item_id": planned_item["item_id"],
                "idempotency_key": "wrong-item",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert wrong_item.status_code == 422
    stale_source = deepcopy(source)
    stale_source["asset_bible"]["locked_revision_id"] = "asset-bible-r9-stale"
    stale = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                **base_command,
                "item_id": failed_item["item_id"],
                "idempotency_key": "stale-source",
            },
            "source": stale_source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert stale.status_code == 422
    assert json.loads(path.read_text(encoding="utf-8")) == manifest

    monkeypatch.setenv("AFS_IMAGE_ADMISSION_UNIT_ESTIMATE_USD", "0.0500")
    monkeypatch.setenv("AFS_IMAGE_ADMISSION_MAX_ESTIMATED_USD", "0.0500")
    price_drift = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                **base_command,
                "item_id": failed_item["item_id"],
                "idempotency_key": "price-drift",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert price_drift.status_code == 422
    assert "pricing changed" in price_drift.json()["detail"]["details"]["raw_detail"]
    assert json.loads(path.read_text(encoding="utf-8")) == manifest

    monkeypatch.setenv("AFS_IMAGE_ADMISSION_UNIT_ESTIMATE_USD", "0.0377")
    monkeypatch.setenv("AFS_IMAGE_ADMISSION_MAX_ESTIMATED_USD", "0.0377")
    incompatible_legacy = deepcopy(manifest)
    incompatible_item = next(
        item
        for item in incompatible_legacy["items"]
        if item["item_id"] == failed_item["item_id"]
    )
    incompatible_item["prompt_contract"]["provider_prompt"] = "incompatible legacy prompt"
    path.write_text(json.dumps(incompatible_legacy, ensure_ascii=False), encoding="utf-8")
    incompatible = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                **base_command,
                "item_id": failed_item["item_id"],
                "idempotency_key": "incompatible-legacy-item",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert incompatible.status_code == 422
    assert "no longer matches" in incompatible.json()["detail"]["details"]["raw_detail"]
    assert json.loads(path.read_text(encoding="utf-8")) == incompatible_legacy


def test_generation_job_binding_survives_reload_without_another_reservation(tmp_path, monkeypatch) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    manifest = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    item = next(entry for entry in manifest["items"] if entry["item_type"] == "character_design")

    reserved = _command(
        client,
        {"type": "reserve_dispatch", "item_id": item["item_id"], "idempotency_key": "reserve-job-a"},
        source,
    )["result"]["manifest"]
    processing = _command(
        client,
        {
            "type": "record_job",
            "item_id": item["item_id"],
            "provider_job_id": "keyframe-generation-job-a",
            "idempotency_key": "record-job-a",
        },
        source,
    )["result"]["manifest"]
    reloaded = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]

    assert reserved["budget"]["dispatches_reserved"] == 1
    assert processing["budget"]["dispatches_reserved"] == 1
    assert reloaded["budget"]["dispatches_reserved"] == 1
    reloaded_item = next(entry for entry in reloaded["items"] if entry["item_id"] == item["item_id"])
    assert reloaded_item["state"] == "processing"
    assert reloaded_item["provider_job_id"] == "keyframe-generation-job-a"
    assert next(
        receipt for receipt in reloaded["receipts"] if receipt["state"] == "job_recorded"
    )["provider_job_id"] == "keyframe-generation-job-a"


def test_locked_prompt_contract_is_the_only_dispatch_prompt(tmp_path, monkeypatch) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setattr(
        "apps.api.runtime_image_admission.image_admission_capability",
        lambda: {
            "configured": True,
            "exact_model": True,
            "keyframe_continuity_ready": True,
            "blocker": "",
        },
    )
    manifest = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    item = next(entry for entry in manifest["items"] if entry["item_type"] == "character_design")
    reserved = _command(
        client,
        {"type": "reserve_dispatch", "item_id": item["item_id"], "idempotency_key": "reserve-prompt-a"},
        source,
    )["result"]["manifest"]
    item = next(entry for entry in reserved["items"] if entry["item_id"] == item["item_id"])
    request = SimpleNamespace(
        node_parameters={
            "image_admission": {
                "manifest_id": reserved["manifest_id"],
                "item_id": item["item_id"],
                "reservation_token": item["reservation_token"],
            },
            "disable_provider_retry": True,
        },
        candidate_count=1,
        provider_service_id="image_relay",
        aspect_ratio=item["aspect_ratio"],
        asset_refs=[],
        node_id=item["target_asset_ids"][0],
        prompt_text=item["prompt_contract"]["provider_prompt"],
        style=reserved["art_direction"]["visual_style"],
    )
    store = RuntimeStore(tmp_path / "runtime")
    assert enforce_image_admission_keyframe_request(store, PROJECT_ID, request)["item"]["item_id"] == item["item_id"]
    request.prompt_text += "\n未审核附加内容"
    with pytest.raises(ValueError, match="prompt differs"):
        enforce_image_admission_keyframe_request(store, PROJECT_ID, request)


def test_existing_keyframe_route_cannot_bypass_locked_admission_manifest(tmp_path, monkeypatch) -> None:
    runtime_root = tmp_path / "runtime"
    client, _source = _compiled_locked_client(tmp_path, monkeypatch)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    request = {
        "node_id": "image-node-a",
        "prompt_text": "A deterministic admission guard test.",
        "target_platform": "short_video",
        "style": "cinematic",
        "aspect_ratio": "3:4",
        "candidate_count": 1,
        "provider_service_id": "image_relay",
        "asset_refs": [],
        "node_parameters": {},
        "generated_at": REQUESTED_AT,
    }
    preflight = client.post(
        f"/projects/{PROJECT_ID}/keyframe-generations/preflight",
        json=request,
    )
    assert preflight.status_code == 200
    request["preflight_token"] = preflight.json()["preflight_token"]
    response = client.post(
        f"/projects/{PROJECT_ID}/keyframe-generations",
        json=request,
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["stage"] == "image_admission"
    assert detail["details"]["reason"] == "image admission manifest id mismatch"
    assert detail["details"]["provider_calls_started"] is False
    assert not list((runtime_root / "runs").glob("**/image_candidates/*"))


def test_deterministic_fixture_candidate_review_history_and_cancel_semantics(tmp_path, monkeypatch) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    monkeypatch.setenv("AFS_ALLOW_DETERMINISTIC_MEDIA_FIXTURES", "true")
    manifest = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    item = next(item for item in manifest["items"] if item["item_type"] == "character_design")
    failure_item = next(
        entry
        for entry in manifest["items"]
        if entry["item_type"] == "character_design" and entry["item_id"] != item["item_id"]
    )
    fixture_failure = _command(
        client,
        {
            "type": "record_failure",
            "item_id": failure_item["item_id"],
            "fixture": True,
            "error_category": "deterministic_fixture_failure",
        },
        source,
    )["result"]["manifest"]
    failed = next(entry for entry in fixture_failure["items"] if entry["item_id"] == failure_item["item_id"])
    assert failed["state"] == "failed"
    assert fixture_failure["provider_dispatch_count"] == 0
    assert fixture_failure["budget"]["dispatches_reserved"] == 0
    preview = _command(
        client,
        {"type": "record_candidate", "item_id": item["item_id"], "fixture": True},
        source,
        confirm=False,
    )
    preview_item = next(entry for entry in preview["result"]["manifest"]["items"] if entry["item_id"] == item["item_id"])
    preview_candidate = preview_item["candidate"]
    fixture_dir = (
        tmp_path
        / "runtime"
        / "projects"
        / PROJECT_ID
        / "image_assets"
        / preview_candidate["image_asset_id"]
    )
    assert not fixture_dir.exists()

    confirmed = _command(
        client,
        {"type": "record_candidate", "item_id": item["item_id"], "fixture": True},
        source,
    )["result"]["manifest"]
    confirmed_item = next(entry for entry in confirmed["items"] if entry["item_id"] == item["item_id"])
    confirmed_candidate = confirmed_item["candidate"]
    assert confirmed_candidate == preview_candidate
    assert fixture_dir.joinpath("source.png").is_file()
    preview_response = client.get(confirmed_candidate["preview_url"])
    assert preview_response.status_code == 200
    assert preview_response.headers["content-type"].startswith("image/png")
    assert image_dimensions(preview_response.content) == {
        "width": 960,
        "height": 1280,
        "aspect_ratio": "960:1280",
    }
    _command(client, {"type": "reject", "item_id": item["item_id"], "reason": "identity mismatch"}, source)
    _command(client, {"type": "replace", "item_id": item["item_id"], "reason": "review replacement"}, source)
    cancelled = _command(client, {"type": "cancel_batch"}, source)["result"]["manifest"]
    assert cancelled["history"][0]["candidate"]["sha256"] == confirmed_candidate["sha256"]
    assert cancelled["cancel_semantics"]["in_flight_cancelled"] == 0
    assert cancelled["provider_dispatch_count"] == 0
    assert cancelled["actual_usd"] is None


def test_candidate_media_missing_blocks_server_side_approval(tmp_path, monkeypatch) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    monkeypatch.setenv("AFS_ALLOW_DETERMINISTIC_MEDIA_FIXTURES", "true")
    manifest = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    item = next(entry for entry in manifest["items"] if entry["item_type"] == "character_design")
    candidate_manifest = _command(
        client,
        {"type": "record_candidate", "item_id": item["item_id"], "fixture": True},
        source,
    )["result"]["manifest"]
    candidate_item = next(entry for entry in candidate_manifest["items"] if entry["item_id"] == item["item_id"])
    candidate = candidate_item["candidate"]
    source_path = (
        tmp_path
        / "runtime"
        / "projects"
        / PROJECT_ID
        / "image_assets"
        / candidate["image_asset_id"]
        / "source.png"
    )
    source_path.unlink()

    response = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "approve",
                "item_id": item["item_id"],
                "idempotency_key": "approve-missing-media",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 422
    assert "candidate media is missing" in response.json()["detail"]["details"]["raw_detail"]
    restored = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    assert next(entry for entry in restored["items"] if entry["item_id"] == item["item_id"])["state"] == "candidate"


def test_approve_writes_exactly_once_to_existing_production_graph(tmp_path, monkeypatch) -> None:
    runtime_root = tmp_path / "runtime"
    store = RuntimeStore(runtime_root)
    store.ensure_project_manifest(PROJECT_ID)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.ensure(PROJECT_ID)
    source = source_contract(graph_version=graph["version"], graph_digest=graph["graph_digest"])
    manifest = compile_image_admission_manifest(PROJECT_ID, source, created_at=REQUESTED_AT)
    target_ids = sorted({target for item in manifest["items"] for target in item["target_asset_ids"]})
    graph = graph_store.append(
        PROJECT_ID,
        expected_version=graph["version"],
        idempotency_key="seed-authority",
        semantic_digest=canonical_digest(target_ids),
        events=[
            {"type": "node_upserted", "node": {"node_id": target_id, "category": "entity", "state": "active"}}
            for target_id in target_ids
        ],
    )
    source = source_contract(graph_version=graph["version"], graph_digest=graph["graph_digest"])
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    _command(client, {"type": "compile"}, source)
    _command(client, {"type": "lock"}, source)
    monkeypatch.setenv("AFS_ALLOW_DETERMINISTIC_MEDIA_FIXTURES", "true")
    current = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    item = next(item for item in current["items"] if item["item_type"] == "character_design")
    _command(
        client,
        {
            "type": "record_candidate",
            "item_id": item["item_id"],
            "fixture": True,
            "candidate": {
                "image_asset_id": "fixture-approved-a",
                "sha256": "b" * 64,
                "format": "png",
                "width": 960,
                "height": 1280,
            },
        },
        source,
    )
    result = _command(
        client,
        {"type": "approve", "item_id": item["item_id"], "idempotency_key": "approve-item-a"},
        source,
    )["result"]["manifest"]
    promoted = next(entry for entry in result["items"] if entry["item_id"] == item["item_id"])
    loaded_graph = graph_store.load(PROJECT_ID)
    assert promoted["promotion"]["production_graph_node_id"] in loaded_graph["nodes"]
    assert len(
        [
            node
            for node in loaded_graph["nodes"].values()
            if node.get("metadata", {}).get("item_id") == item["item_id"]
        ]
    ) == 1
    workspace = client.get(f"/projects/{PROJECT_ID}/m5/sequence-workspace").json()
    approved_media = workspace["sequence"]["approved_media"]
    approved_candidate = promoted["candidate"]
    assert approved_media == [
        {
            "media_node_id": promoted["promotion"]["production_graph_node_id"],
            "media_kind": "image",
            "preview_url": (
                f"/projects/{PROJECT_ID}/image-assets/"
                f"{approved_candidate['image_asset_id']}/preview"
            ),
            "width": 960,
            "height": 1280,
            "approval_graph_version": loaded_graph["version"],
            "target_node_ids": item["target_asset_ids"],
        }
    ]
    assert workspace["project_id"] == PROJECT_ID
    assert workspace["provider_dispatch_count"] == 0
    assert workspace["cost_usd"] == 0
    reloaded_source = source_contract(
        graph_version=loaded_graph["version"],
        graph_digest=loaded_graph["graph_digest"],
    )
    next_item = next(
        entry
        for entry in result["items"]
        if entry["item_type"] == "character_design" and entry["item_id"] != item["item_id"]
    )
    reloaded = _command(
        client,
        {
            "type": "record_candidate",
            "item_id": next_item["item_id"],
            "fixture": True,
            "candidate": {
                "image_asset_id": "fixture-approved-b",
                "sha256": "c" * 64,
                "format": "png",
                "width": 960,
                "height": 1280,
            },
        },
        reloaded_source,
    )
    assert reloaded["result"]["manifest"]["status"] == "locked"

    unrelated = graph_store.append(
        PROJECT_ID,
        expected_version=loaded_graph["version"],
        idempotency_key="unrelated-graph-change",
        semantic_digest=canonical_digest({"node_id": "unrelated-node"}),
        events=[
            {
                "type": "node_upserted",
                "node": {"node_id": "unrelated-node", "category": "artifact", "state": "active"},
            }
        ],
    )
    stale_response = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {"type": "cancel_batch"},
            "source": source_contract(
                graph_version=unrelated["version"],
                graph_digest=unrelated["graph_digest"],
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert stale_response.status_code == 422
    assert "ProductionGraph source is stale" in stale_response.json()["detail"]["details"]["raw_detail"]


def test_next_batches_preserve_history_scale_budget_and_bind_approved_references(
    tmp_path,
    monkeypatch,
) -> None:
    runtime_root = tmp_path / "runtime"
    store = RuntimeStore(runtime_root)
    store.ensure_project_manifest(PROJECT_ID)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.ensure(PROJECT_ID)
    initial = compile_image_admission_manifest(PROJECT_ID, compact_source_contract(shot_count=3))
    target_ids = sorted(
        {
            target
            for item in initial["items"]
            for target in [*item["target_asset_ids"], item.get("target_shot_id")]
            if target
        }
    )
    graph_store.append(
        PROJECT_ID,
        expected_version=graph["version"],
        idempotency_key="seed-next-batch-authority",
        semantic_digest=canonical_digest(target_ids),
        events=[
            {"type": "node_upserted", "node": {"node_id": target_id, "category": "entity", "state": "active"}}
            for target_id in target_ids
        ],
    )

    def current_source() -> dict:
        value = compact_source_contract(shot_count=3)
        current = graph_store.load(PROJECT_ID)
        value["production_graph_version"] = current["version"]
        value["production_graph_digest"] = current["graph_digest"]
        return value

    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    source = current_source()
    _command(client, {"type": "compile"}, source)
    _command(client, {"type": "lock"}, source)
    monkeypatch.setenv("AFS_ALLOW_DETERMINISTIC_MEDIA_FIXTURES", "true")
    manifest = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    character = next(item for item in manifest["items"] if item["item_type"] == "character_design")
    _command(client, {"type": "record_candidate", "item_id": character["item_id"], "fixture": True}, source)
    _command(
        client,
        {"type": "approve", "item_id": character["item_id"], "idempotency_key": "approve-next-character"},
        source,
    )
    source = current_source()
    _command(client, {"type": "cancel_batch"}, source)

    option_preview = _command(client, {"type": "inspect_next_batch"}, source, confirm=False)
    selectable = option_preview["result"]["manifest"]["next_batch_options"]
    assert character["item_id"] not in {item["item_id"] for item in selectable}
    assert {item["item_type"] for item in selectable} == {"scene_plate", "prop_design"}
    premature_keyframe = next(
        item
        for item in compile_image_admission_manifest(PROJECT_ID, source)["items"]
        if item["item_type"] == "shot_keyframe"
    )
    blocked_keyframe = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "create_next_batch_manifest",
                "source_manifest_id": client.get(
                    f"/projects/{PROJECT_ID}/m6/image-admission"
                ).json()["manifest"]["manifest_id"],
                "item_ids": [premature_keyframe["item_id"]],
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert blocked_keyframe.status_code == 422
    assert "every canonical asset" in blocked_keyframe.json()["detail"]["details"]["raw_detail"]
    selected = [
        item for item in selectable if item["item_type"] in {"scene_plate", "prop_design"}
    ]
    assert len(selected) == 2
    before = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    command = {
        "type": "create_next_batch_manifest",
        "source_manifest_id": before["manifest_id"],
        "item_ids": [item["item_id"] for item in selected],
        "idempotency_key": "next-scene-prop-batch",
    }
    preview = _command(client, command, source, confirm=False)
    assert preview["provider_dispatch_count"] == 0
    assert preview["impact"]["next_batch_manifest"]["new_max_dispatches"] == 2
    assert preview["impact"]["next_batch_manifest"]["new_max_estimated_usd"] == "0.0754"
    batch = _command(client, command, source)["result"]["manifest"]
    assert batch["budget_contract"]["max_dispatches"] == 2
    assert batch["budget_contract"]["auto_retry"] == 0
    assert batch["provider_dispatch_count"] == 0
    replay = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        json={
            "command": command,
            "source": source,
            "requested_at": REQUESTED_AT,
            "preview_digest": preview["preview_digest"],
        },
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["result"]["manifest"] == batch
    semantic_conflict = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        json={
            "command": {
                **command,
                "item_ids": command["item_ids"][:1],
            },
            "source": source,
            "requested_at": REQUESTED_AT,
            "preview_digest": preview["preview_digest"],
        },
    )
    assert semantic_conflict.status_code == 422
    assert "idempotency key conflicts" in semantic_conflict.json()["detail"]["details"]["raw_detail"]
    assert client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"] == batch
    concurrent = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                **command,
                "idempotency_key": "competing-next-scene-prop-batch",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert concurrent.status_code == 422
    assert "source manifest is stale" in concurrent.json()["detail"]["details"]["raw_detail"]
    archived = (
        runtime_root
        / "projects"
        / PROJECT_ID
        / "image_admission"
        / "history"
        / f"{before['manifest_id']}.json"
    )
    assert json.loads(archived.read_text(encoding="utf-8")) == before

    for item in batch["items"]:
        source = current_source()
        _command(client, {"type": "record_candidate", "item_id": item["item_id"], "fixture": True}, source)
        _command(
            client,
            {
                "type": "approve",
                "item_id": item["item_id"],
                "idempotency_key": f"approve-next-{item['item_id']}",
            },
            source,
        )
    source = current_source()
    keyframe_preview = _command(client, {"type": "inspect_next_batch"}, source, confirm=False)
    keyframes = [
        item
        for item in keyframe_preview["result"]["manifest"]["next_batch_options"]
        if item["item_type"] == "shot_keyframe"
    ]
    assert len(keyframes) == 3
    current = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    keyframe_batch = _command(
        client,
        {
            "type": "create_next_batch_manifest",
            "source_manifest_id": current["manifest_id"],
            "item_ids": [keyframes[0]["item_id"]],
            "idempotency_key": "next-keyframe-batch",
        },
        source,
    )["result"]["manifest"]
    assert keyframe_batch["budget_contract"]["max_dispatches"] == 1
    assert 1 <= len(keyframe_batch["items"][0]["reference_media_ids"]) <= 4
    assert keyframe_batch["provider_dispatch_count"] == 0


def test_next_batch_price_drift_fails_before_options_or_manifest_creation(
    tmp_path,
    monkeypatch,
) -> None:
    client, source = _compiled_locked_client(tmp_path, monkeypatch)
    _command(client, {"type": "cancel_batch"}, source)
    monkeypatch.setenv("AFS_IMAGE_ADMISSION_UNIT_ESTIMATE_USD", "0.0400")

    response = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {"type": "inspect_next_batch"},
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )

    assert response.status_code == 422
    assert "pricing changed" in response.json()["detail"]["details"]["raw_detail"]
    persisted = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    assert persisted["status"] == "cancelled"
    assert persisted["provider_dispatch_count"] == 0
