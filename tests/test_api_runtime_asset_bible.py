from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_asset_bible import (
    build_asset_candidate_set,
    confirm_asset_bible_command_result,
    preview_asset_bible_command_result,
)
from apps.api.runtime_studio_state_sanitizer import sanitize_studio_state
from apps.api.runtime_service import create_runtime_app


PROJECT_ID = "codex-clawed-fighter-smoke-20260624-h"
SOURCE_TEXT = """
场景一：雨夜天台。林晚握着红绳，和机器人阿虎机器人对峙。
场景二：楼梯间。林晚把红绳系在栏杆上，阿虎机器人守住出口。
场景三：清晨街道。林晚收起红绳，阿虎机器人跟在她身后。
""".strip()


def shot_plan() -> dict:
    scenes = []
    for scene_index, scene_name in enumerate(("雨夜天台", "楼梯间", "清晨街道"), start=1):
        shots = []
        count = 6 if scene_index < 3 else 5
        for shot_index in range(1, count + 1):
            shots.append(
                {
                    "shot_id": f"shot-{scene_index}-{shot_index}",
                    "title": f"镜头 {scene_index}-{shot_index}",
                    "description": f"{scene_name}，林晚握着红绳，阿虎机器人观察她。",
                    "duration_sec": 8 + shot_index % 3,
                }
            )
        scenes.append(
            {
                "scene_id": f"scene-{scene_index}",
                "name": scene_name,
                "shots": shots,
            }
        )
    return {
        "candidate_id": "shot-candidate-current",
        "scenes": scenes,
        "total_shots": 17,
    }


def generation_body() -> dict:
    return {
        "source_node_id": "story-source",
        "script_revision_id": "revision-current",
        "source_text": SOURCE_TEXT,
        "shot_plan": shot_plan(),
        "command": {"type": "generate_candidates"},
    }


def generated_bible() -> dict:
    return preview_asset_bible_command_result(PROJECT_ID, generation_body())["result"]["asset_bible"]


def command_preview(bible: dict, command: dict) -> dict:
    return preview_asset_bible_command_result(
        PROJECT_ID,
        {
            "asset_bible": bible,
            "command": command,
        },
    )


def complete_visual_review(bible: dict) -> dict:
    for asset in list(bible["assets"]):
        bible = command_preview(
            bible,
            {
                "type": "edit",
                "target_id": asset["stable_id"],
                "patch": {
                    "visual_identity": f"{asset['display_name']} 的轮廓、材质与主色已由人工确认",
                    "positive_traits": [f"保持 {asset['display_name']} 的稳定辨识特征"],
                    "continuity_states": ["当前场次造型与持有物保持一致"],
                },
            },
        )["result"]["asset_bible"]
    return command_preview(
        bible,
        {
            "type": "set_art_direction",
            "art_direction": {
                "visual_style": "写实动作片",
                "medium": "电影摄影，真实材质",
                "palette": "低饱和冷色与暖光点缀",
                "lighting": "主体面部清晰的侧逆光",
            },
        },
    )["result"]["asset_bible"]


def test_candidate_generation_is_zero_provider_preview_with_stable_occurrence_lineage() -> None:
    first = build_asset_candidate_set(PROJECT_ID, generation_body())
    second = build_asset_candidate_set(PROJECT_ID, generation_body())

    assert first["candidate_set_id"] == second["candidate_set_id"]
    assert [item["stable_id"] for item in first["assets"]] == [item["stable_id"] for item in second["assets"]]
    assert first["scene_count"] == 3
    assert first["shot_count"] == 17
    assert {"character", "scene", "prop"} <= {item["asset_type"] for item in first["assets"]}
    assert all(item["review_state"] == "candidate" for item in first["assets"])
    assert all(item["needs_confirmation"] is True for item in first["assets"])
    assert all(item["pending_fields"] for item in first["assets"])
    assert any(item["occurrences"]["shot_ids"] for item in first["assets"] if item["asset_type"] != "scene")
    traceable_shots = {
        shot_id
        for asset in first["assets"]
        for evidence in asset["source_evidence"]
        for shot_id in evidence.get("shot_ids", [])
    }
    assert len(traceable_shots) == 17

    preview = preview_asset_bible_command_result(PROJECT_ID, generation_body())
    assert preview["status"] == "preview"
    assert preview["requires_confirmation"] is True
    assert preview["provider_dispatch_count"] == 0
    assert preview["external_cost_usd"] == 0
    assert preview["result"]["graph_mutation"] == 0
    assert preview["impact"]["preserved_on_cancel"] is True


def test_visual_identity_and_art_direction_fail_closed_before_approval_and_lock() -> None:
    bible = generated_bible()
    target = bible["assets"][0]
    with pytest.raises(ValueError, match="仍缺少视觉身份、正向视觉特征、连续性状态"):
        command_preview(bible, {"type": "approve", "target_id": target["stable_id"]})

    bible = complete_visual_review(bible)
    for asset in list(bible["assets"]):
        bible = command_preview(
            bible,
            {"type": "approve", "target_id": asset["stable_id"]},
        )["result"]["asset_bible"]
    assert bible["art_direction"]["status"] == "confirmed"
    assert bible["art_direction"]["source"] == "human_review"
    missing_evidence = deepcopy(bible)
    for asset in missing_evidence["assets"]:
        asset["source_evidence"] = []
    with pytest.raises(ValueError, match="17 个镜头缺少来源证据"):
        command_preview(missing_evidence, {"type": "lock"})
    locked = command_preview(bible, {"type": "lock"})["result"]["asset_bible"]
    assert locked["status"] == "locked"
    assert locked["art_direction"]["visual_style"] == "写实动作片"
    assert locked["coverage"]["asset_shot_covered"] == 17
    assert locked["coverage"]["missing_source_evidence_shot_count"] == 0


def test_approve_reject_edit_and_lock_create_versioned_revisions() -> None:
    bible = complete_visual_review(generated_bible())
    original_ids = [item["stable_id"] for item in bible["assets"]]
    original_version = bible["version"]

    for index, stable_id in enumerate(original_ids):
        action = "reject" if index == len(original_ids) - 1 else "approve"
        bible = command_preview(bible, {"type": action, "target_id": stable_id})["result"]["asset_bible"]

    approved = next(item for item in bible["assets"] if item["review_state"] == "approved")
    edited = command_preview(
        bible,
        {
            "type": "edit",
            "target_id": approved["stable_id"],
            "patch": {
                "display_name": f"{approved['display_name']}（确认版）",
                "visual_identity": approved["visual_identity"],
                "positive_traits": ["银灰色表面", "轮廓稳定"],
                "continuity_states": ["当前场次造型与持有物保持一致"],
                "negative_locks": ["不得改变身份", "不得添加文字"],
            },
        },
    )["result"]["asset_bible"]
    edited_asset = next(item for item in edited["assets"] if item["stable_id"] == approved["stable_id"])
    assert edited_asset["review_state"] == "candidate"
    assert approved["display_name"] in edited_asset["aliases"]
    assert edited_asset["positive_traits"] == ["银灰色表面", "轮廓稳定"]

    with pytest.raises(ValueError, match="approve or reject"):
        command_preview(edited, {"type": "lock"})

    edited = command_preview(edited, {"type": "approve", "target_id": approved["stable_id"]})["result"]["asset_bible"]
    with pytest.raises(ValueError, match="required occurrences unresolved"):
        command_preview(edited, {"type": "lock"})
    rejected = next(item for item in edited["assets"] if item["review_state"] == "rejected")
    unresolved = [
        item["requirement_id"]
        for item in edited["resolution_ledger"]
        if item["assigned_asset_id"] == rejected["stable_id"] and not item["resolved"]
    ]
    edited = command_preview(
        edited,
        {
            "type": "mark_not_needed",
            "requirement_ids": unresolved,
            "reason": "人工确认该资产在这些镜头中不构成连续性需求",
        },
    )["result"]["asset_bible"]
    locked = command_preview(edited, {"type": "lock"})["result"]["asset_bible"]
    assert locked["status"] == "locked"
    assert locked["locked_revision_id"] == locked["current_revision_id"]
    assert locked["version"] > original_version
    assert len(locked["revisions"]) == locked["version"]
    assert locked["coverage"]["coverage_pass"] is True
    assert locked["coverage"]["shot_covered"] == locked["coverage"]["shot_total"] == 17


def test_merge_and_split_preserve_lineage_and_require_exact_occurrence_assignment() -> None:
    bible = generated_bible()
    scene_assets = [item for item in bible["assets"] if item["asset_type"] == "scene"]
    merged = command_preview(
        bible,
        {
            "type": "merge",
            "target_ids": [scene_assets[0]["stable_id"], scene_assets[1]["stable_id"]],
            "display_name": "天台与楼梯过渡空间",
        },
    )
    merged_state = merged["result"]["asset_bible"]
    merged_asset = next(item for item in merged_state["assets"] if item["display_name"] == "天台与楼梯过渡空间")
    assert set(merged_asset["lineage"]["merged_from_ids"]) == {
        scene_assets[0]["stable_id"],
        scene_assets[1]["stable_id"],
    }
    assert merged["impact"]["scene_count"] == 2

    source_refs = merged_asset["occurrences"]["scene_ids"]
    source_shots = merged_asset["occurrences"]["shot_ids"]
    split = command_preview(
        merged_state,
        {
            "type": "split",
            "target_id": merged_asset["stable_id"],
            "names": ["天台区域", "楼梯区域"],
                "occurrence_assignments": {
                    "0": {"scene_ids": source_refs[:1], "shot_ids": source_shots[: len(source_shots) // 2]},
                    "1": {"scene_ids": source_refs[1:], "shot_ids": source_shots[len(source_shots) // 2 :]},
            },
        },
    )["result"]["asset_bible"]
    children = [item for item in split["assets"] if merged_asset["stable_id"] in item["lineage"]["parent_ids"]]
    history = [item for item in split["assets"] if item["review_state"] == "superseded"]
    assert {item["display_name"] for item in children} == {"天台区域", "楼梯区域"}
    assert set().union(*(set(item["occurrences"]["scene_ids"]) for item in children)) == set(source_refs)
    assert {item["stable_id"] for item in history} >= {
        scene_assets[0]["stable_id"],
        scene_assets[1]["stable_id"],
        merged_asset["stable_id"],
    }
    child_ids = {item["stable_id"] for item in children}
    assert all(
        item["assigned_asset_id"] in child_ids
        for item in split["resolution_ledger"]
        if item["source_asset_id"] in {scene_assets[0]["stable_id"], scene_assets[1]["stable_id"]}
    )

    with pytest.raises(ValueError, match="cover every source occurrence"):
        command_preview(
            merged_state,
            {
                "type": "split",
                "target_id": merged_asset["stable_id"],
                "names": ["天台区域", "楼梯区域"],
                "occurrence_assignments": {
                    "0": {"scene_ids": source_refs[:1], "shot_ids": []},
                    "1": {"scene_ids": [], "shot_ids": []},
                },
            },
        )


def test_studio_state_roundtrip_preserves_asset_bible_without_accepting_provider_fields() -> None:
    bible = complete_visual_review(generated_bible())
    state = sanitize_studio_state(
        {
            "meta": {"projectName": "Clawed Fighter", "canvasName": "主画布"},
            "nodes": {},
            "edges": {},
            "order": [],
            "assetBible": bible,
        },
        project_id=PROJECT_ID,
    )
    assert state["assetBible"]["candidate_set"]["shot_count"] == 17
    assert state["assetBible"]["current_revision_id"] == bible["current_revision_id"]
    assert state["assetBible"]["assets"][0]["stable_id"] == bible["assets"][0]["stable_id"]
    assert state["assetBible"]["assets"][0]["visual_identity"] == bible["assets"][0]["visual_identity"]
    assert state["assetBible"]["assets"][0]["continuity_states"][0]["status"] == "confirmed"
    assert state["assetBible"]["assets"][0]["source_evidence"][0]["shot_ids"]
    assert state["assetBible"]["art_direction"]["status"] == "confirmed"
    assert state["assetBible"]["art_direction"]["visual_style"] == "写实动作片"
    assert state["assetBible"]["provider_dispatch_count"] == 0

    unsafe = deepcopy(bible)
    unsafe["provider_raw"] = {"output": "forbidden"}
    with pytest.raises(ValueError, match="forbidden"):
        sanitize_studio_state(
            {
                "meta": {},
                "nodes": {},
                "edges": {},
                "order": [],
                "assetBible": unsafe,
            },
            project_id=PROJECT_ID,
        )


def test_api_preview_confirm_retry_and_studio_reload_are_zero_provider_and_idempotent(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    request = {
        **generation_body(),
        "requested_at": "2026-07-24T00:00:00Z",
    }
    preview = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/preview",
        json=request,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["result"]["graph_mutation"] == 0
    assert not (tmp_path / "runtime" / "projects" / PROJECT_ID / "production_graph.json").exists()
    assert not (tmp_path / "runtime" / "projects" / PROJECT_ID / "studio_state.json").exists()

    confirm_body = {
        **request,
        "preview_digest": preview.json()["preview_digest"],
        "command_id": preview.json()["command_id"],
        "expected_graph_version": 0,
    }
    first = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        json=confirm_body,
    )
    retry = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        json=confirm_body,
    )
    assert first.status_code == retry.status_code == 200
    assert first.json()["asset_bible"]["current_revision_id"] == retry.json()["asset_bible"]["current_revision_id"]
    assert first.json()["asset_bible"]["version"] == retry.json()["asset_bible"]["version"] == 1
    assert first.json()["provider_dispatch_count"] == retry.json()["provider_dispatch_count"] == 0
    assert first.json()["external_cost_usd"] == retry.json()["external_cost_usd"] == 0
    mismatched = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        json={**confirm_body, "command_id": "asset-command-" + "f" * 32},
    )
    assert mismatched.status_code == 422
    assert "identity does not match" in mismatched.text

    saved = client.put(
        f"/projects/{PROJECT_ID}/studio-state",
        json={
            "expected_version": "",
            "state": {
                "meta": {"projectName": "Clawed Fighter", "canvasName": "主画布"},
                "nodes": {},
                "edges": {},
                "order": [],
                "assetBible": first.json()["asset_bible"],
            },
        },
    )
    assert saved.status_code == 200, saved.text
    reloaded = client.get(f"/projects/{PROJECT_ID}/studio-state")
    assert reloaded.status_code == 200
    restored = reloaded.json()["state"]["assetBible"]
    assert restored["current_revision_id"] == first.json()["asset_bible"]["current_revision_id"]
    assert restored["candidate_set"]["shot_count"] == 17
    assert restored["idempotency_keys"] == [preview.json()["command_id"]]


def test_canonical_graph_owns_asset_bible_without_copying_or_invalidating_source_assets(tmp_path) -> None:
    from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
    from apps.api.runtime_store import RuntimeStore

    runtime_root = tmp_path / "runtime"
    store = RuntimeStore(runtime_root)
    graph_store = ProductionGraphStore(store)
    graph_store.append(
        PROJECT_ID,
        expected_version=0,
        idempotency_key="seed-story-truth",
        semantic_digest=canonical_digest({"seed": "story"}),
        events=[
            {"type": "node_upserted", "node": {"node_id": "revision-current", "category": "revision", "metadata": {"source_digest": "a" * 64}}},
            {"type": "node_upserted", "node": {"node_id": "character-orchid", "category": "entity", "metadata": {"display_name": "Orchid Vale", "appearance": "silver braid"}}},
            {"type": "node_upserted", "node": {"node_id": "scene-observatory", "category": "location", "metadata": {"name": "Glass Observatory", "space": "high glass dome"}}},
            {"type": "node_upserted", "node": {"node_id": "scene-archive", "category": "location", "metadata": {"name": "Tidal Archive", "space": "submerged shelves"}}},
            {"type": "node_upserted", "node": {"node_id": "prop-astrolabe", "category": "resource", "metadata": {"name": "Ivory Astrolabe", "kind": "prop", "classification": "canonical_prop", "style": "engraved ivory"}}},
            {"type": "node_upserted", "node": {"node_id": "aid-moonlight", "category": "resource", "metadata": {"name": "Moonlight Reference", "kind": "reference_set", "classification": "production_aid"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-observatory", "category": "unit", "metadata": {"intent": "align the astrolabe", "duration_seconds": 4, "blocking": "Orchid aligns the instrument"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-archive", "category": "unit", "metadata": {"intent": "trace the tide chart", "duration_seconds": 5, "blocking": "Orchid enters the archive"}}},
            *[
                {"type": "relation_upserted", "from_id": "revision-current", "to_id": node_id, "relation_type": "derived_from"}
                for node_id in ("character-orchid", "scene-observatory", "scene-archive", "prop-astrolabe", "aid-moonlight")
            ],
            {"type": "relation_upserted", "from_id": "scene-observatory", "to_id": "shot-observatory", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-archive", "to_id": "shot-archive", "relation_type": "contains"},
            *[
                {"type": "relation_upserted", "from_id": asset_id, "to_id": shot_id, "relation_type": "required_by"}
                for asset_id in ("character-orchid", "prop-astrolabe")
                for shot_id in ("shot-observatory", "shot-archive")
            ],
        ],
    )
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    generate_request = {
        "command": {"type": "generate_candidates"},
        "requested_at": "2026-07-24T00:00:00Z",
    }
    generated_preview = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/preview",
        json=generate_request,
    ).json()
    assert generated_preview["expected_graph_version"] == 1
    generated = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        json={
            **generate_request,
            "preview_digest": generated_preview["preview_digest"],
            "command_id": generated_preview["command_id"],
            "expected_graph_version": 1,
        },
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["authority_mode"] == "canonical_production_graph"
    generated_ids = {
        item["stable_id"] for item in generated.json()["asset_bible"]["assets"]
    }
    assert generated_ids == {
        "character-orchid",
        "scene-observatory",
        "scene-archive",
        "prop-astrolabe",
    }
    assert generated.json()["asset_bible"]["candidate_set"]["source_graph_asset_ids"] == sorted(generated_ids)
    assert generated.json()["provider_dispatch_count"] == 0
    assert generated.json()["external_cost_usd"] == 0
    graph_version = generated.json()["graph_version"]
    regenerated_preview = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/preview",
        json={
            "asset_bible": generated.json()["asset_bible"],
            "command": {"type": "regenerate_candidates"},
            "requested_at": "2026-07-24T00:00:30Z",
        },
    )
    assert regenerated_preview.status_code == 200, regenerated_preview.text
    assert regenerated_preview.json()["expected_graph_version"] == graph_version
    assert {
        item["stable_id"]
        for item in regenerated_preview.json()["result"]["asset_bible"]["assets"]
        if item["review_state"] not in {"rejected", "superseded"}
    } == generated_ids
    assert regenerated_preview.json()["provider_dispatch_count"] == 0
    replayed = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        json={
            **generate_request,
            "preview_digest": generated_preview["preview_digest"],
            "command_id": generated_preview["command_id"],
            "expected_graph_version": 1,
        },
    )
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["idempotent_replay"] is True
    assert replayed.json()["graph_version"] == graph_version
    bible = generated.json()["asset_bible"]
    scene_assets = [item for item in bible["assets"] if item["asset_type"] == "scene"][:2]

    merge_request = {
        "asset_bible": bible,
        "requested_at": "2026-07-24T00:01:00Z",
        "command": {
            "type": "merge",
            "target_ids": [item["stable_id"] for item in scene_assets],
            "display_name": "合并场景",
        },
    }
    merge_preview = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/preview",
        json=merge_request,
    ).json()
    merged = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        json={
            **merge_request,
            "preview_digest": merge_preview["preview_digest"],
            "idempotency_key": "canonical-assets-merge",
            "expected_graph_version": graph_version,
        },
    )
    assert merged.status_code == 200, merged.text
    graph = graph_store.load(PROJECT_ID)
    for source in scene_assets:
        assert graph["nodes"][source["stable_id"]]["state"] == "active"
        assert graph["nodes"][source["stable_id"]]["metadata"]["space"] in {
            "high glass dome",
            "submerged shelves",
        }
        assert any(
            relation["from_id"] == source["stable_id"]
            and relation["relation_type"] == "contains"
            for relation in graph["relations"]
        )
    restored = client.get(f"/projects/{PROJECT_ID}/m6/asset-bible").json()
    assert restored["authority_mode"] == "canonical_production_graph"
    assert restored["asset_bible"]["current_revision_id"] == merged.json()["asset_bible"]["current_revision_id"]

    graph_store.append(
        PROJECT_ID,
        expected_version=merged.json()["graph_version"],
        idempotency_key="seed-ambiguous-active-revision",
        semantic_digest=canonical_digest({"seed": "ambiguous-revision"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "revision-history-still-active",
                    "category": "revision",
                    "metadata": {"source_digest": "b" * 64},
                },
            },
        ],
    )
    ambiguous = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/preview",
        json={
            "asset_bible": merged.json()["asset_bible"],
            "command": {"type": "regenerate_candidates"},
            "requested_at": "2026-07-24T00:02:00Z",
        },
    )
    assert ambiguous.status_code == 422
    assert "exactly one active canonical script revision" in ambiguous.text


def test_nested_sequence_graph_generates_zero_provider_two_domain_candidates(tmp_path) -> None:
    from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
    from apps.api.runtime_store import RuntimeStore

    runtime_root = tmp_path / "runtime"
    store = RuntimeStore(runtime_root)
    graph_store = ProductionGraphStore(store)
    graph_store.append(
        PROJECT_ID,
        expected_version=0,
        idempotency_key="seed-nested-sequence-story",
        semantic_digest=canonical_digest({"seed": "nested-sequence"}),
        events=[
            {"type": "node_upserted", "node": {"node_id": "revision-v3", "category": "revision", "metadata": {"source_digest": "c" * 64}}},
            {"type": "node_upserted", "node": {"node_id": "sequence-v3", "category": "collection", "metadata": {"kind": "story_sequence"}}},
            {"type": "node_upserted", "node": {"node_id": "scene-modern", "category": "location", "metadata": {"name": "现代重生域 医院走廊", "style_domain": "M-modern-rebirth", "space": "冷白医院走廊"}}},
            {"type": "node_upserted", "node": {"node_id": "scene-ancient", "category": "location", "metadata": {"name": "古言棋局域 王府密室", "style_domain": "A-ancient-chess", "space": "烛火王府密室"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-modern-a", "category": "unit", "metadata": {"title": "重逢对峙", "duration_seconds": 8, "blocking": "林晚面对傅行舟，手握红绳，压住重生后的情绪。", "intent": "建立现代重生甜虐身份冲突"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-modern-b", "category": "unit", "metadata": {"title": "证据浮现", "duration_seconds": 7, "blocking": "傅行舟拿起手机，林晚抢回照片。", "intent": "推进现代证据线"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-ancient-a", "category": "unit", "metadata": {"title": "棋局开场", "duration_seconds": 6, "blocking": "容华面对白筱，握紧竹简，盯住棋盘。", "intent": "建立古言棋局推广设定"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-ancient-b", "category": "unit", "metadata": {"title": "密令反转", "duration_seconds": 6, "blocking": "白筱拔出长剑，容华展开旧军籍册。", "intent": "推进古言密令反转"}}},
            {"type": "relation_upserted", "from_id": "revision-v3", "to_id": "sequence-v3", "relation_type": "derived_from"},
            {"type": "relation_upserted", "from_id": "sequence-v3", "to_id": "scene-modern", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "sequence-v3", "to_id": "scene-ancient", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-modern", "to_id": "shot-modern-a", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-modern", "to_id": "shot-modern-b", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-ancient", "to_id": "shot-ancient-a", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-ancient", "to_id": "shot-ancient-b", "relation_type": "contains"},
        ],
    )
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    preview = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/preview",
        json={
            "command": {"type": "generate_candidates"},
            "requested_at": "2026-07-24T00:00:00Z",
        },
    )

    assert preview.status_code == 200, preview.text
    result = preview.json()
    assert result["provider_dispatch_count"] == 0
    assert result["result"]["graph_mutation"] == 0
    assert graph_store.load(PROJECT_ID)["version"] == 1
    candidate_set = result["result"]["asset_bible"]["candidate_set"]
    assert candidate_set["source_graph_version"] == 1
    assert candidate_set["scene_count"] == 2
    assert candidate_set["shot_count"] == 4
    assert {
        item["label"]
        for item in candidate_set["style_domains"]
    } == {"M-modern-rebirth", "A-ancient-chess"}
    assert len(candidate_set["reference_candidates"]) == 2
    assets = result["result"]["asset_bible"]["assets"]
    by_type = {
        asset_type: {item["display_name"] for item in assets if item["asset_type"] == asset_type}
        for asset_type in ("character", "scene", "prop")
    }
    assert {"林晚", "傅行舟", "容华", "白筱"} <= by_type["character"]
    assert "现代重生域 医院走廊" in by_type["scene"]
    assert "古言棋局域 王府密室" in by_type["scene"]
    assert {"红绳", "手机", "照片", "竹简", "长剑", "旧军籍册"} & by_type["prop"]
    assert not any("林晚" in name and "容华" in name for name in by_type["character"])


def _seed_owner_import_graph(graph_store, project_id: str = PROJECT_ID) -> dict:
    from apps.api.runtime_production_graph import canonical_digest

    graph_store.append(
        project_id,
        expected_version=0,
        idempotency_key="seed-owner-import-story",
        semantic_digest=canonical_digest({"seed": "owner-import-story"}),
        events=[
            {"type": "node_upserted", "node": {"node_id": "revision-owner", "category": "revision", "metadata": {"source_digest": "d" * 64}}},
            {"type": "node_upserted", "node": {"node_id": "sequence-owner", "category": "collection", "metadata": {"kind": "story_sequence"}}},
            {"type": "node_upserted", "node": {"node_id": "scene-modern-owner", "category": "location", "metadata": {"name": "现代重生甜虐 泳池夜", "space": "夜间泳池暖金灯与蓝绿水面"}}},
            {"type": "node_upserted", "node": {"node_id": "scene-ancient-owner", "category": "location", "metadata": {"name": "古言棋局 王府密室", "space": "黑檀棋盘与冷月烛火"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-modern-owner-1", "category": "unit", "metadata": {"title": "深海坠落", "duration_seconds": 6, "blocking": "叶安安在象征性深海中下沉。"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-modern-owner-2", "category": "unit", "metadata": {"title": "泳池对峙", "duration_seconds": 6, "blocking": "叶安安警觉看向泳池边的傅凉川。"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-ancient-owner-1", "category": "unit", "metadata": {"title": "棋局开场", "duration_seconds": 6, "blocking": "容华在黑檀棋盘前落下金色棋子。"}}},
            {"type": "node_upserted", "node": {"node_id": "shot-ancient-owner-2", "category": "unit", "metadata": {"title": "封面落版", "duration_seconds": 6, "blocking": "无字封面母版进入后期图形段落。"}}},
            {"type": "relation_upserted", "from_id": "revision-owner", "to_id": "sequence-owner", "relation_type": "derived_from"},
            {"type": "relation_upserted", "from_id": "sequence-owner", "to_id": "scene-modern-owner", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "sequence-owner", "to_id": "scene-ancient-owner", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-modern-owner", "to_id": "shot-modern-owner-1", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-modern-owner", "to_id": "shot-modern-owner-2", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-ancient-owner", "to_id": "shot-ancient-owner-1", "relation_type": "contains"},
            {"type": "relation_upserted", "from_id": "scene-ancient-owner", "to_id": "shot-ancient-owner-2", "relation_type": "contains"},
        ],
    )
    return graph_store.load(project_id)


def _owner_import_body(graph: dict) -> dict:
    return {
        "requested_at": "2026-07-28T00:00:00Z",
        "idempotency_key": "owner-asset-bible-20260728-v1-import",
        "command": {
            "type": "import_asset_draft",
            "draft_id": "owner-asset-bible-20260728-v1",
            "idempotency_key": "owner-asset-bible-20260728-v1-import",
            "graph_version": graph["version"],
            "graph_digest": graph["graph_digest"],
            "art_directions": [
                {
                    "stable_id": "M-STY-01",
                    "label": "现代重生甜虐",
                    "visual_style": "商业级都市重生甜虐短剧；写实、表演清楚",
                    "medium": "电影摄影，真实皮肤与织物",
                    "palette": "冷青黑、香槟金、暖白、蓝绿水光",
                    "lighting": "恐惧贴近移动浅景深，喜剧干净中近景",
                    "negative_locks": ["禁止廉价网大滤镜"],
                },
                {
                    "stable_id": "A-STY-01",
                    "label": "古言作品推广",
                    "visual_style": "高概念甜虐古言/爱情棋局/权谋寓言",
                    "medium": "丝绸暗纹锦缎、旧铜玉石、黑檀冷锻钢",
                    "palette": "墨黑、暗金、朱红、月白",
                    "lighting": "对峙、遮挡、棋盘线条和距离",
                    "negative_locks": ["拒绝仙侠光污染"],
                },
            ],
            "assets": [
                {
                    "stable_id": "M-CHAR-01",
                    "asset_type": "character",
                    "display_name": "叶安安",
                    "demographics": "modern East Asian young woman",
                    "visual_identity": "清秀倔强，杏眼，黑色长发，纤细，同脸连续",
                    "variants": ["泳池湿身", "白浴巾伪装"],
                    "negative_locks": ["禁止族裔模仿式黑脸"],
                },
                {
                    "stable_id": "M-ENV-01",
                    "asset_type": "scene",
                    "display_name": "象征性深海",
                    "visual_identity": "深蓝黑水体，上方弱冷白光，气泡颗粒",
                },
                {
                    "stable_id": "A-CHAR-01",
                    "asset_type": "character",
                    "display_name": "容华",
                    "visual_identity": "修长清贵，深眉眼，黑发高束，墨黑暗金棋纹锦袍",
                },
                {
                    "stable_id": "A-PROP-01",
                    "asset_type": "prop",
                    "display_name": "金色棋子",
                    "visual_identity": "温润旧金，扁圆，细棋纹，尺寸统一",
                },
                {
                    "stable_id": "GFX-01",
                    "asset_type": "graphic",
                    "display_name": "《请夫入瓮》无字封面母版",
                    "visual_identity": "容华、白筱、棋子、古剑，不含模型字",
                },
            ],
            "shot_reference_map": {
                "1": ["M-CHAR-01", "M-ENV-01", "M-STY-01"],
                "2": ["M-CHAR-01", "M-STY-01"],
                "3": ["A-CHAR-01", "A-PROP-01", "A-STY-01"],
                "4": ["GFX-01", "A-PROP-01", "A-STY-01"],
            },
        },
    }


def test_owner_asset_draft_import_previews_and_confirms_into_canonical_graph(tmp_path) -> None:
    from apps.api.runtime_production_graph import ProductionGraphStore
    from apps.api.runtime_store import RuntimeStore

    runtime_root = tmp_path / "runtime"
    store = RuntimeStore(runtime_root)
    graph_store = ProductionGraphStore(store)
    graph = _seed_owner_import_graph(graph_store)
    body = _owner_import_body(graph)

    preview = preview_asset_bible_command_result(PROJECT_ID, body, graph=graph)
    assert preview["provider_dispatch_count"] == 0
    assert preview["result"]["graph_mutation"] == 0
    assert graph_store.load(PROJECT_ID)["version"] == graph["version"]
    bible = preview["result"]["asset_bible"]
    assert bible["status"] == "candidate_review"
    assert bible["locked_revision_id"] == ""
    assert {item["stable_id"] for item in bible["assets"]} == {
        "M-CHAR-01",
        "M-ENV-01",
        "A-CHAR-01",
        "A-PROP-01",
        "GFX-01",
    }
    assert all(item["review_state"] == "approved" and item["owner_supplied"] for item in bible["assets"])
    assert bible["coverage"]["unresolved_required"] == 0
    assert bible["coverage"]["coverage_pass"] is True
    assert bible["candidate_set"]["import"]["draft_id"] == "owner-asset-bible-20260728-v1"
    assert len(bible["candidate_set"]["style_domains"]) == 2
    assert len(bible["candidate_set"]["shot_reference_map"]) == 4
    imported_character = next(item for item in bible["assets"] if item["stable_id"] == "M-CHAR-01")
    assert imported_character["demographics"] == "modern East Asian young woman"

    confirmed = confirm_asset_bible_command_result(
        PROJECT_ID,
        {
            **body,
            "preview_digest": preview["preview_digest"],
            "command_id": preview["command_id"],
            "expected_graph_version": graph["version"],
        },
        graph_store=graph_store,
    )
    assert confirmed["status"] == "confirmed"
    assert confirmed["graph_version"] == graph["version"] + 1
    assert confirmed["asset_bible"]["status"] == "candidate_review"
    updated = graph_store.load(PROJECT_ID)
    assert updated["nodes"]["asset-bible-codex-clawed-fighter-smoke-20260624-h"]["metadata"]["kind"] == "asset_bible"
    assert updated["nodes"]["M-CHAR-01"]["metadata"]["owner_supplied"] is True
    assert updated["nodes"]["M-CHAR-01"]["metadata"]["demographics"] == "modern East Asian young woman"
    assert updated["nodes"]["GFX-01"]["metadata"]["asset_subtype"] == "graphic"
    assert any(
        relation == {
            "from_id": "M-CHAR-01",
            "to_id": "shot-modern-owner-1",
            "relation_type": "required_by",
        }
        for relation in updated["relations"]
    )

    replayed = confirm_asset_bible_command_result(
        PROJECT_ID,
        {
            **body,
            "preview_digest": preview["preview_digest"],
            "command_id": preview["command_id"],
            "expected_graph_version": graph["version"],
        },
        graph_store=graph_store,
    )
    assert replayed["idempotent_replay"] is True
    assert replayed["graph_version"] == confirmed["graph_version"]

    restored = TestClient(create_runtime_app(runtime_root=runtime_root)).get(
        f"/projects/{PROJECT_ID}/m6/asset-bible"
    )
    assert restored.status_code == 200
    restored_bible = restored.json()["asset_bible"]
    assert restored_bible["candidate_set"]["style_domains"][0]["owner_supplied"] is True
    assert restored_bible["candidate_set"]["shot_reference_map"][0]["reference_ids"] == [
        "M-CHAR-01",
        "M-ENV-01",
        "M-STY-01",
    ]
    restored_character = next(item for item in restored_bible["assets"] if item["stable_id"] == "M-CHAR-01")
    assert restored_character["demographics"] == "modern East Asian young woman"


def test_owner_asset_draft_import_rejects_bad_id_collision_and_cross_domain(tmp_path) -> None:
    from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
    from apps.api.runtime_store import RuntimeStore

    runtime_root = tmp_path / "runtime"
    store = RuntimeStore(runtime_root)
    graph_store = ProductionGraphStore(store)
    graph = _seed_owner_import_graph(graph_store)
    body = _owner_import_body(graph)

    bad_id = deepcopy(body)
    bad_id["command"]["assets"][0]["stable_id"] = "B-CHAR-01"
    with pytest.raises(ValueError, match="owner namespace"):
        preview_asset_bible_command_result(PROJECT_ID, bad_id, graph=graph)

    collision_graph = graph_store.append(
        PROJECT_ID,
        expected_version=graph["version"],
        idempotency_key="seed-owner-id-collision",
        semantic_digest=canonical_digest({"collision": "M-CHAR-01"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "M-CHAR-01",
                    "category": "resource",
                    "metadata": {"kind": "reserved"},
                },
            }
        ],
    )
    collision_body = _owner_import_body(collision_graph)
    with pytest.raises(ValueError, match="collides with existing graph node"):
        preview_asset_bible_command_result(PROJECT_ID, collision_body, graph=collision_graph)

    fresh_root = tmp_path / "runtime-cross"
    fresh_store = RuntimeStore(fresh_root)
    fresh_graph_store = ProductionGraphStore(fresh_store)
    fresh_graph = _seed_owner_import_graph(fresh_graph_store)
    cross_domain = _owner_import_body(fresh_graph)
    cross_domain["command"]["shot_reference_map"]["3"] = ["M-CHAR-01", "A-CHAR-01", "A-PROP-01", "A-STY-01"]
    with pytest.raises(ValueError, match="crosses style domains"):
        preview_asset_bible_command_result(PROJECT_ID, cross_domain, graph=fresh_graph)


def test_split_rejects_duplicate_occurrence_assignment() -> None:
    candidate = build_asset_candidate_set(PROJECT_ID, generation_body())
    state = preview_asset_bible_command_result(
        PROJECT_ID,
        {
            **generation_body(),
            "command": {"type": "generate_candidates"},
            "requested_at": "2026-07-24T00:00:00Z",
        },
    )["result"]["asset_bible"]
    source = next(item for item in candidate["assets"] if item["occurrences"]["shot_ids"])
    ref = source["occurrences"]["shot_ids"][0]
    with pytest.raises(ValueError, match="exactly once"):
        preview_asset_bible_command_result(
            PROJECT_ID,
            {
                "asset_bible": state,
                "expected_asset_bible_revision_id": state["current_revision_id"],
                "command": {
                    "type": "split",
                    "target_id": source["stable_id"],
                    "names": ["资产 A", "资产 B"],
                    "occurrence_assignments": {
                        "0": {"scene_ids": source["occurrences"]["scene_ids"], "shot_ids": source["occurrences"]["shot_ids"]},
                        "1": {"scene_ids": [], "shot_ids": [ref]},
                    },
                },
            },
        )


def test_referenced_reject_blocks_lock_until_same_type_reassignment() -> None:
    bible = complete_visual_review(generated_bible())
    characters = [
        item
        for item in bible["assets"]
        if item["asset_type"] == "character" and item["occurrences"]["shot_ids"]
    ]
    assert len(characters) >= 2
    rejected, destination = characters[:2]
    for asset in list(bible["assets"]):
        bible = command_preview(
            bible,
            {
                "type": "reject" if asset["stable_id"] == rejected["stable_id"] else "approve",
                "target_id": asset["stable_id"],
            },
        )["result"]["asset_bible"]

    assert rejected["stable_id"] in bible["coverage"]["unresolved_asset_ids"]
    assert bible["coverage"]["unresolved_required"] > 0
    assert any(
        item["status"] == "rejected" and item["assigned_asset_id"] == rejected["stable_id"]
        for item in bible["resolution_ledger"]
    )
    with pytest.raises(ValueError, match="required occurrences unresolved"):
        command_preview(bible, {"type": "lock"})

    requirement_ids = [
        item["requirement_id"]
        for item in bible["resolution_ledger"]
        if item["assigned_asset_id"] == rejected["stable_id"] and not item["resolved"]
    ]
    preview = command_preview(
        bible,
        {
            "type": "reassign_occurrences",
            "target_id": destination["stable_id"],
            "requirement_ids": requirement_ids,
            "reason": "人工确认这些镜头引用同一角色资产",
        },
    )
    assert preview["impact"]["unresolved_required_before"] == len(requirement_ids)
    assert preview["impact"]["unresolved_required_after"] == 0
    assert {
        item["requirement_id"] for item in preview["impact"]["occurrence_resolution_changes"]
    } == set(requirement_ids)
    expected_scene_ids = {
        item["occurrence_id"]
        for item in bible["resolution_ledger"]
        if item["requirement_id"] in requirement_ids and item["occurrence_kind"] == "scene"
    }
    expected_shot_ids = {
        item["occurrence_id"]
        for item in bible["resolution_ledger"]
        if item["requirement_id"] in requirement_ids and item["occurrence_kind"] == "shot"
    }
    assert preview["impact"]["scene_count"] == len(expected_scene_ids)
    assert preview["impact"]["shot_count"] == len(expected_shot_ids)
    reassigned = preview["result"]["asset_bible"]
    assert reassigned["coverage"]["coverage_pass"] is True
    assert command_preview(reassigned, {"type": "lock"})["result"]["asset_bible"]["status"] == "locked"


def test_explicit_not_needed_requires_reason_and_preview_preserves_state() -> None:
    bible = generated_bible()
    target = next(item for item in bible["assets"] if item["occurrences"]["shot_ids"])
    bible = command_preview(bible, {"type": "reject", "target_id": target["stable_id"]})["result"]["asset_bible"]
    requirement_ids = [
        item["requirement_id"]
        for item in bible["resolution_ledger"]
        if item["assigned_asset_id"] == target["stable_id"] and item["occurrence_kind"] == "shot"
    ]
    with pytest.raises(ValueError, match="reviewable reason"):
        command_preview(
            bible,
            {"type": "mark_not_needed", "requirement_ids": requirement_ids, "reason": ""},
        )
    preview = command_preview(
        bible,
        {
            "type": "mark_not_needed",
            "requirement_ids": requirement_ids,
            "reason": "人工确认这些镜头仅提及背景，不要求资产连续性",
        },
    )
    assert preview["result"]["graph_mutation"] == 0
    assert preview["impact"]["preserved_on_cancel"] is True
    assert all(item["reason"] for item in preview["impact"]["occurrence_resolution_changes"])


def test_human_review_can_add_missing_asset_with_traced_occurrences() -> None:
    bible = generated_bible()
    created = command_preview(
        bible,
        {
            "type": "create_asset",
            "asset_type": "prop",
            "display_name": "折叠伞",
            "aliases": ["雨伞"],
            "scene_ids": ["scene-1"],
            "shot_ids": ["shot-1-1", "shot-1-2"],
            "evidence": "人工审核确认前两个镜头持续使用同一道具",
        },
    )
    state = created["result"]["asset_bible"]
    asset = next(item for item in state["assets"] if item["display_name"] == "折叠伞")
    assert asset["aliases"] == ["折叠伞", "雨伞"]
    assert asset["occurrences"]["shot_ids"] == ["shot-1-1", "shot-1-2"]
    requirements = [
        item for item in state["resolution_ledger"] if item["source_asset_id"] == asset["stable_id"]
    ]
    assert len(requirements) == 3
    assert all(item["status"] == "pending" and not item["resolved"] for item in requirements)
    assert created["impact"]["graph_mutation_before_confirm"] == 0


def test_alias_collision_blocks_coverage_and_lock() -> None:
    bible = complete_visual_review(generated_bible())
    characters = [item for item in bible["assets"] if item["asset_type"] == "character"][:2]
    shared_alias = "同一别名"
    for character in characters:
        bible = command_preview(
            bible,
            {
                "type": "edit",
                "target_id": character["stable_id"],
                "patch": {"aliases": [*character["aliases"], shared_alias]},
            },
        )["result"]["asset_bible"]
    for asset in list(bible["assets"]):
        bible = command_preview(
            bible,
            {"type": "approve", "target_id": asset["stable_id"]},
        )["result"]["asset_bible"]
    assert bible["coverage"]["alias_collision_count"] == 1
    assert bible["coverage"]["coverage_pass"] is False
    with pytest.raises(ValueError, match="lock blocked"):
        command_preview(bible, {"type": "lock"})
