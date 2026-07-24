from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_asset_bible import (
    build_asset_candidate_set,
    preview_asset_bible_command_result,
)
from apps.api.runtime_asset_recognition import recognize_asset_occurrences
from apps.api.runtime_image_admission import compile_image_admission_manifest
from apps.api.runtime_service import create_runtime_app


PROJECT_ID = "asset-recognition-quality-test"
SCRIPT = """
黄昏，高老庄外芦苇田。取经行囊放在青石旁，孙悟空握住金箍棒。
猪八戒扛着九齿钉耙走来。猪八戒 猴子，这包袱是俺老猪看守的。
孙悟空 呆子，放下钉耙。猪八戒 猴哥，你先别喊我呆子。
唐僧 师徒同行要彼此信任。孙悟空 师父，我会护住行囊。
""".strip()


def _shot_plan() -> dict:
    scene_specs = (
        (
            "scene-field",
            "外景 - 高老庄外芦苇田 - 黄昏",
            4,
            "孙悟空在青石旁查看取经行囊，手持金箍棒；猪八戒扛九齿钉耙靠近。",
        ),
        (
            "scene-ridge",
            "外景 - 高老庄外田埂 - 黄昏",
            6,
            "悟空与八戒交手，棍和钉耙相击，两人仍护住行囊。",
        ),
        (
            "scene-temple",
            "内景 - 破庙 - 夜",
            7,
            "唐僧劝悟空、八戒停手；猴哥收棍，呆子放下耙子，师父拾起包袱。",
        ),
    )
    scenes = []
    ordinal = 0
    for scene_id, name, count, context in scene_specs:
        shots = []
        for index in range(1, count + 1):
            ordinal += 1
            shots.append(
                {
                    "shot_id": f"{scene_id}-shot-{index}",
                    "title": f"镜头 {ordinal:02d}",
                    "description": context,
                    "purpose": "保持人物、武器、行囊与场景连续性。",
                }
            )
        scenes.append({"scene_id": scene_id, "name": name, "shots": shots})
    return {"candidate_id": "shot-plan-quality-v1", "scenes": scenes, "total_shots": 17}


def _body(*, command_type: str = "generate_candidates") -> dict:
    return {
        "source_node_id": "story-source",
        "script_revision_id": "script-revision-v1",
        "source_text": SCRIPT,
        "source_context_texts": [SCRIPT],
        "shot_plan": _shot_plan(),
        "command": {"type": command_type},
        "requested_at": "2026-07-24T00:00:00Z",
    }


def _generated_bible() -> dict:
    return preview_asset_bible_command_result(PROJECT_ID, _body())["result"]["asset_bible"]


def _command(bible: dict, command: dict) -> dict:
    return preview_asset_bible_command_result(
        PROJECT_ID,
        {"asset_bible": bible, "command": command, "requested_at": "2026-07-24T00:01:00Z"},
    )


def _complete_visual(asset: dict) -> None:
    asset["visual_identity"] = f"{asset['display_name']} 的轮廓、材质与主色已确认"
    asset["positive_traits"] = [f"保持 {asset['display_name']} 的稳定辨识特征"]
    asset["continuity_states"] = [
        {
            "state_id": f"continuity-{asset['stable_id']}",
            "label": "当前场次造型与持有物保持一致",
            "status": "confirmed",
            "scene_ids": asset["occurrences"]["scene_ids"],
            "shot_ids": asset["occurrences"]["shot_ids"],
        }
    ]
    asset["pending_fields"] = []


def test_recognition_clusters_aliases_and_propagates_scene_descendants_stably() -> None:
    first = recognize_asset_occurrences(SCRIPT, [SCRIPT], _shot_plan()["scenes"])
    second = recognize_asset_occurrences(SCRIPT, [SCRIPT], _shot_plan()["scenes"])
    assert [
        (item["asset_type"], item["display_name"]) for item in first["assets"]
    ] == [
        (item["asset_type"], item["display_name"]) for item in second["assets"]
    ]

    by_type = {
        asset_type: [item for item in first["assets"] if item["asset_type"] == asset_type]
        for asset_type in ("character", "scene", "prop")
    }
    assert [item["display_name"] for item in by_type["character"]] == ["孙悟空", "猪八戒", "唐僧"]
    assert {item["display_name"] for item in by_type["prop"]} == {"取经行囊", "金箍棒", "九齿钉耙"}
    aliases = {item["display_name"]: item["aliases"] for item in first["assets"]}
    assert {"悟空", "猴子", "猴哥"} <= aliases["孙悟空"]
    assert {"八戒", "老猪", "呆子"} <= aliases["猪八戒"]
    assert {"师父"} <= aliases["唐僧"]
    assert {"棍"} <= aliases["金箍棒"]
    assert {"钉耙", "耙子"} <= aliases["九齿钉耙"]
    assert {"行囊", "包袱"} <= aliases["取经行囊"]
    assert [len(item["shot_ids"]) for item in by_type["scene"]] == [4, 6, 7]
    assert not first["recognition_ambiguities"]


def test_distinct_same_family_props_emit_ambiguity_instead_of_silent_merge() -> None:
    source = "旅行行囊和医疗行囊分别属于两支队伍。"
    scenes = [
        {
            "scene_id": "scene-1",
            "name": "营地",
            "shots": [
                {
                    "shot_id": "shot-1",
                    "title": "清点",
                    "description": "旅行行囊和医疗行囊并排放置。",
                }
            ],
        }
    ]
    result = recognize_asset_occurrences(source, [source], scenes)
    assert any(
        item["code"] == "ambiguous_prop_instances"
        and {"旅行行囊", "医疗行囊"} <= set(item["labels"])
        for item in result["recognition_ambiguities"]
    )


def test_quality_gate_blocks_missing_anchor_and_image_manifest() -> None:
    bible = _generated_bible()
    removed = next(item for item in bible["assets"] if item["display_name"] == "九齿钉耙")
    bible["assets"] = [item for item in bible["assets"] if item["stable_id"] != removed["stable_id"]]
    for asset in bible["assets"]:
        _complete_visual(asset)
        asset["review_state"] = "approved"
        asset["needs_confirmation"] = False
    preview = _command(bible, {"type": "approve", "target_id": bible["assets"][0]["stable_id"]})
    blocked = preview["result"]["asset_bible"]
    assert blocked["recognition_quality"]["status"] == "blocked"
    assert blocked["coverage"]["missing_anchor_count"] == 1
    with pytest.raises(ValueError, match="lock blocked"):
        _command(blocked, {"type": "lock"})

    blocked["status"] = "locked"
    blocked["locked_revision_id"] = blocked["current_revision_id"]
    blocked["coverage"]["coverage_pass"] = True
    blocked["coverage"]["unresolved_required"] = 0
    source = {
        "asset_bible": blocked,
        "studio_state_version": "studio-v1",
        "production_graph_version": 0,
        "production_graph_digest": "",
    }
    with pytest.raises(ValueError, match="recognition quality gate"):
        compile_image_admission_manifest(PROJECT_ID, source)


def test_rerecognition_preview_preserves_approved_assets_and_creates_history() -> None:
    bible = _generated_bible()
    approved = next(item for item in bible["assets"] if item["display_name"] == "孙悟空")
    _complete_visual(approved)
    bible = _command(
        bible,
        {"type": "approve", "target_id": approved["stable_id"]},
    )["result"]["asset_bible"]
    duplicate = deepcopy(next(item for item in bible["assets"] if item["display_name"] == "金箍棒"))
    duplicate["stable_id"] = "asset-prop-generic-stick-old"
    duplicate["display_name"] = "棍"
    duplicate["aliases"] = ["棍"]
    duplicate["review_state"] = "candidate"
    bible["assets"].append(duplicate)
    before = deepcopy(bible)

    preview = preview_asset_bible_command_result(
        PROJECT_ID,
        {**_body(command_type="regenerate_candidates"), "asset_bible": bible},
    )
    assert bible == before
    refreshed = preview["result"]["asset_bible"]
    active = [
        item
        for item in refreshed["assets"]
        if item["review_state"] not in {"rejected", "superseded"}
    ]
    assert len(active) == 9
    retained = next(item for item in active if item["stable_id"] == approved["stable_id"])
    assert retained["review_state"] == "approved"
    assert duplicate["stable_id"] in refreshed["recognition_delta"]["history_asset_ids"]
    assert any(
        item["stable_id"] == duplicate["stable_id"] and item["review_state"] == "superseded"
        for item in refreshed["assets"]
    )
    assert refreshed["recognition_quality"]["status"] == "pass"
    assert preview["impact"]["preserved_on_cancel"] is True
    assert preview["result"]["provider_dispatch_count"] == 0
    assert preview["result"]["external_cost_usd"] == 0


def test_rerecognition_confirm_is_idempotent_and_reload_preserves_quality(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    bible = _generated_bible()
    duplicate = deepcopy(next(item for item in bible["assets"] if item["display_name"] == "金箍棒"))
    duplicate["stable_id"] = "asset-prop-generic-stick-reload"
    duplicate["display_name"] = "棍"
    duplicate["aliases"] = ["棍"]
    bible["assets"].append(duplicate)
    request = {**_body(command_type="regenerate_candidates"), "asset_bible": bible}
    preview = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/preview",
        json=request,
    )
    assert preview.status_code == 200, preview.text
    confirm = {
        **request,
        "preview_digest": preview.json()["preview_digest"],
        "idempotency_key": "recognition-quality-refresh-v2",
    }
    first = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        json=confirm,
    )
    replay_request = {
        **confirm,
        "asset_bible": first.json()["asset_bible"],
    }
    replay = client.post(
        f"/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        json=replay_request,
    )
    assert first.status_code == replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert (
        first.json()["asset_bible"]["current_revision_id"]
        == replay.json()["asset_bible"]["current_revision_id"]
    )
    refreshed = first.json()["asset_bible"]
    assert refreshed["recognition_quality"]["status"] == "pass"
    assert sum(
        item["review_state"] not in {"rejected", "superseded"}
        for item in refreshed["assets"]
    ) == 9
    assert any(
        item["stable_id"] == duplicate["stable_id"] and item["review_state"] == "superseded"
        for item in refreshed["assets"]
    )

    saved = client.put(
        f"/projects/{PROJECT_ID}/studio-state",
        json={
            "expected_version": "",
            "state": {
                "meta": {"projectName": "资产识别质量测试", "canvasName": "主画布"},
                "nodes": {},
                "edges": {},
                "order": [],
                "assetBible": refreshed,
            },
        },
    )
    assert saved.status_code == 200, saved.text
    restored = client.get(f"/projects/{PROJECT_ID}/studio-state").json()["state"]["assetBible"]
    assert restored["current_revision_id"] == refreshed["current_revision_id"]
    assert restored["recognition_quality"]["status"] == "pass"
    assert restored["coverage"]["quality_pass"] is True
    assert restored["provider_dispatch_count"] == 0
    assert restored["external_cost_usd"] == 0
