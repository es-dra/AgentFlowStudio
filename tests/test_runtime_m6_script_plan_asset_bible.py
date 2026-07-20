from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

from apps.api.runtime_m6_script_plan_asset_bible import (
    REVIEW_ROLES,
    build_m6_script_plan_asset_bible,
    validate_m6_candidate,
)
from apps.api.runtime_service import create_runtime_app


IDEA_TEXT = """
角色：林澈、唐予。场景：夜晚旧剪辑室、清晨屋顶。道具：场记板、旧镜头。特写：林澈手背的伤痕、时间线上的红色标记。
风格：克制写实冷暖对照。时间：夜晚到清晨。光线：剪辑室屏幕冷光与屋顶晨光。季节：初秋。连续性：旧镜头始终在唐予手边。
目标：林澈想证明被删掉的素材能救回影片。冲突：唐予担心返工会拖垮拍摄预算。关系：两人从互相指责转为共同承担。变化：林澈从逃避失误转为主动承认。
林澈盯着屏幕里的断帧，低声说“如果这一秒还在，结尾就不是谎言”。
唐予把场记板放到桌边，要求他在十分钟内给出能拍的重做方案。
两人带着旧镜头上到屋顶，晨光压住城市噪声，林澈终于说出自己删错素材的真相。
唐予没有责备，只把红色标记改成新的拍摄任务，让林澈先拍自己的手和那支旧镜头。
"""

SCRIPT_TEXT = """
角色：米拉、陶、阿衡。场景：傍晚观测台、雨后的信号室、地下水泵间。道具：铜色罗盘、裂开的玻璃杯、备用电池。
外观：米拉短发银灰外套；陶黑色雨衣；阿衡戴旧耳机。服装：三人保持同一夜晚的湿冷质感。年龄：二十七到三十五岁。比例：真人写实。
空间：观测台有环形轨道，信号室狭窄，水泵间低顶。光线：傍晚橙光、绿色设备灯、手电硬光。季节：雨季。连续性：铜色罗盘每场都必须在画面内有明确位置。
米拉校准镜头时，远处信号突然偏移，她要求陶记录频率。
陶在信号室打开备用电池，却发现玻璃杯裂纹与信号波形完全一致。
阿衡听见水泵间的旧广播，意识到偏移不是天气，而是有人在地下重放十年前的呼救。
三人沿着水声进入地下，罗盘开始倒转，米拉用镜头对准墙面反光。
陶读出最后一段呼救，阿衡摘下耳机，承认当年自己听过同样的声音却没有上报。
米拉决定不再追逐信号源，而是把镜头留在三人的沉默上，让真相成为下一场戏的压力。
"""


def test_m6_preview_builds_varied_professional_candidates_without_fixed_profiles() -> None:
    idea = build_m6_script_plan_asset_bible("m6-idea", {"source_kind": "idea", "source_text": IDEA_TEXT})
    script = build_m6_script_plan_asset_bible("m6-script", {"source_kind": "script", "source_text": SCRIPT_TEXT})

    idea_candidate = idea["candidate"]
    script_candidate = script["candidate"]
    assert idea["validation"]["verdict"] == "PASS"
    assert script["validation"]["verdict"] == "PASS"
    assert len(idea_candidate["shots"]) != len(script_candidate["shots"])
    for candidate in (idea_candidate, script_candidate):
        durations = [shot["duration_seconds"] for shot in candidate["shots"]]
        assert len(set(durations)) > 1
        assert not (len(durations) == 4 and set(durations) == {15.0})
        assert not (len(durations) == 10 and set(durations) == {6.0})
        assert candidate["asset_bible"]["status"] == "pending_confirmation"
        assert {"4x15", "10x6"} <= set(candidate["sequence"]["dynamic_policy"]["fixed_profile_forbidden"])
        assert {row["role"] for row in candidate["review_requirements"]} == set(REVIEW_ROLES)
        assert candidate["provider_dispatch_count"] == 0
        assert candidate["cost_usd"] == 0
        assert all(item["promotion_state"] != "promoted" for item in candidate["knowledge_context"]["items"])
        assert all(shot["shot_size"] and shot["camera_movement"] and shot["narrative_purpose"] for shot in candidate["shots"])


def test_m6_confirm_writes_the_same_production_graph_consumed_by_m5_workspace(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    preview = client.post("/projects/m6-graph/m6/script-plan-asset-bible/preview", json={
        "source_kind": "idea",
        "source_text": IDEA_TEXT,
    })
    assert preview.status_code == 200, preview.text
    candidate = preview.json()["candidate"]

    confirmed = client.post("/projects/m6-graph/m6/script-plan-asset-bible/confirm", json={
        "expected_graph_version": 0,
        "idempotency_key": "confirm-m6",
        "candidate": candidate,
    })
    assert confirmed.status_code == 200, confirmed.text
    graph = confirmed.json()["graph"]
    assert graph["version"] == 1
    assert graph["provider_gates"] == {key: False for key in graph["provider_gates"]}
    assert any(node["category"] == "entity" and node["metadata"].get("goal") for node in graph["nodes"].values())
    assert any(node["category"] == "location" and node["metadata"].get("lighting") for node in graph["nodes"].values())
    assert any(node["category"] == "unit" and node["metadata"].get("shot_size") for node in graph["nodes"].values())

    workspace = client.get("/projects/m6-graph/m5/sequence-workspace").json()
    assert workspace["status"] == "ready"
    assert workspace["graph_digest"] == graph["graph_digest"] == workspace["storyboard"]["graph_digest"]
    assert workspace["sequence"]["characters"]
    assert workspace["sequence"]["reference_sets"]
    assert workspace["provider_dispatch_count"] == 0
    assert workspace["cost_usd"] == 0
    assert not (tmp_path / "runtime" / "projects" / "m6-graph" / "studio_state.json").exists()


def test_m6_confirm_rejects_template_gaming_and_unresolved_lineage(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    candidate = build_m6_script_plan_asset_bible("m6-bad", {"source_kind": "script", "source_text": SCRIPT_TEXT})["candidate"]

    fixed_duration = deepcopy(candidate)
    for shot in fixed_duration["shots"]:
        shot["duration_seconds"] = 6.0
    fixed_duration["sequence"]["target_duration_seconds"] = 6.0 * len(fixed_duration["shots"])
    response = client.post("/projects/m6-bad/m6/script-plan-asset-bible/confirm", json={
        "expected_graph_version": 0,
        "idempotency_key": "bad-fixed",
        "candidate": fixed_duration,
    })
    assert response.status_code == 409
    assert "fixed equal durations" in response.text

    unresolved = deepcopy(candidate)
    unresolved["shots"][0]["asset_refs"] = ["missing-asset"]
    response = client.post("/projects/m6-bad/m6/script-plan-asset-bible/confirm", json={
        "expected_graph_version": 0,
        "idempotency_key": "bad-ref",
        "candidate": unresolved,
    })
    assert response.status_code == 409
    assert "unresolved asset" in response.text

    promoted = deepcopy(candidate)
    promoted["knowledge_context"]["items"][0]["promotion_state"] = "promoted"
    response = client.post("/projects/m6-bad/m6/script-plan-asset-bible/confirm", json={
        "expected_graph_version": 0,
        "idempotency_key": "bad-knowledge",
        "candidate": promoted,
    })
    assert response.status_code == 409
    assert "cannot be promoted" in response.text


def test_m6_preview_requires_named_entities_and_story_beats() -> None:
    try:
        build_m6_script_plan_asset_bible("m6-empty", {"source_kind": "idea", "source_text": "一个人想拍一部片子，但是没有名字，也没有场景。"})
    except ValueError as exc:
        assert "named character" in str(exc)
    else:
        raise AssertionError("unnamed idea should require planning")

    valid = build_m6_script_plan_asset_bible("m6-direct", {"source_kind": "idea", "source_text": IDEA_TEXT})["candidate"]
    assert validate_m6_candidate(valid)["P0"] == 0
