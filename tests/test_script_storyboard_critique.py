from __future__ import annotations

import json
from pathlib import Path


FORBIDDEN_FIELDS = {
    "raw_provider_response",
    "provider_raw_payload",
    "signed_url",
    "image_path",
    "output_path",
    "request_path",
    "local_path",
    "media_bytes",
    "data_base64",
    "api_key",
    "token",
    "cookie",
    "authorization",
    "provider_key",
}


def test_primary_story_assets_are_not_overridden_by_secondary_asset_graph() -> None:
    from agentflow import algorithms
    from agentflow.algorithms.script_storyboard_critique import build_script_storyboard_critique

    critique = build_script_storyboard_critique(
        project_id="proj_story_critique",
        node_id="script_tang_seng_baigujing",
        user_request="把唐僧娶了白骨精改成短剧分镜，重点是婚礼冲突和身份反转。",
        script_text=(
            "唐僧决定迎娶白骨精，寺院众人震动。\n"
            "孙悟空和猪八戒在山门外争论是否阻止婚礼。\n"
            "白骨精掀开红盖头，唐僧第一次意识到这场婚礼背后另有目的。"
        ),
        shots=[
            {
                "shot_id": "shot_01",
                "source_span": {"text": "孙悟空和猪八戒在山门外争论是否阻止婚礼。"},
                "asset_refs": [
                    {"label": "孙悟空", "asset_type": "character"},
                    {"label": "猪八戒", "asset_type": "character"},
                ],
            }
        ],
        asset_graph={
            "assets": [
                {"label": "孙悟空", "asset_type": "character"},
                {"label": "猪八戒", "asset_type": "character"},
            ]
        },
    )

    missing_labels = {item["label"] for item in critique["missing_primary_assets"]}
    salience = {item["label"]: item for item in critique["asset_salience"]}
    issue_ids = {issue["id"] for issue in critique["issues"]}

    assert "script_storyboard_critique" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert critique["artifact_type"] == "agentflow_script_storyboard_critique"
    assert critique["packet_state"] == "needs_repair"
    assert {"唐僧", "白骨精"} <= missing_labels
    assert "孙悟空" not in missing_labels
    assert "猪八戒" not in missing_labels
    assert salience["唐僧"]["score"] > salience["孙悟空"]["score"]
    assert salience["白骨精"]["score"] > salience["猪八戒"]["score"]
    assert "primary_assets_missing_from_storyboard" in issue_ids
    assert "secondary_assets_over_selected" in issue_ids
    _assert_boundary(critique)


def test_prompt_like_source_is_flagged_but_dialogue_script_is_not() -> None:
    from agentflow.algorithms.script_storyboard_critique import build_script_storyboard_critique

    prompt_like = build_script_storyboard_critique(
        project_id="proj_story_critique",
        script_text="请生成一个电影感分镜提示词，画面要求玄幻婚礼，风格高对比，镜头描述要有冲突。",
        shots=[],
        asset_graph={"assets": []},
    )
    dialogue_script = build_script_storyboard_critique(
        project_id="proj_story_critique",
        script_text=(
            "唐僧：我若退后，便再也看不清她的真心。\n"
            "白骨精：你看见的是妖，还是一个想活下去的人？"
        ),
        shots=[
            {
                "shot_id": "shot_01",
                "source_span": {"text": "唐僧：我若退后，便再也看不清她的真心。"},
                "asset_refs": [{"label": "唐僧", "asset_type": "character"}],
            },
            {
                "shot_id": "shot_02",
                "source_span": {"text": "白骨精：你看见的是妖，还是一个想活下去的人？"},
                "asset_refs": [{"label": "白骨精", "asset_type": "character"}],
            },
        ],
        asset_graph={
            "assets": [
                {"label": "唐僧", "asset_type": "character"},
                {"label": "白骨精", "asset_type": "character"},
            ]
        },
    )

    assert "script_prompt_like_not_script" in {issue["id"] for issue in prompt_like["issues"]}
    assert prompt_like["script_form"]["prompt_like_not_script"] is True
    assert "script_prompt_like_not_script" not in {issue["id"] for issue in dialogue_script["issues"]}
    assert dialogue_script["script_form"]["prompt_like_not_script"] is False
    _assert_boundary(prompt_like)
    _assert_boundary(dialogue_script)


def test_storyboard_shots_need_source_grounding_and_primary_asset_refs() -> None:
    from agentflow.algorithms.script_storyboard_critique import build_script_storyboard_critique

    critique = build_script_storyboard_critique(
        project_id="proj_story_critique",
        user_request="唐僧娶了白骨精",
        script_text="唐僧站在山门前，白骨精穿着嫁衣走近。",
        shots=[
            {"shot_id": "shot_missing_source", "description": "唐僧站在山门前。", "asset_refs": []},
            {"shot_id": "shot_missing_refs", "source_text": "唐僧站在山门前，白骨精穿着嫁衣走近。", "asset_refs": []},
        ],
        asset_graph={"assets": []},
    )
    issues = {issue["id"]: issue for issue in critique["issues"]}

    assert issues["shot_missing_source_grounding"]["evidence"]["shot_ids"] == ["shot_missing_source"]
    assert issues["shot_missing_primary_asset_refs"]["evidence"]["shot_ids"] == ["shot_missing_refs"]
    assert set(issues["shot_missing_primary_asset_refs"]["evidence"]["primary_labels"]) >= {"唐僧", "白骨精"}
    assert {item["action"] for item in critique["repair_suggestions"]} >= {
        "add_candidate_asset_ref",
        "restore_source_span_text",
        "link_primary_assets_to_mentioning_shots",
    }
    _assert_boundary(critique)


def test_critique_has_no_provider_media_runtime_or_memory_dependency() -> None:
    from agentflow.algorithms.script_storyboard_critique import build_script_storyboard_critique

    source = Path("agentflow/algorithms/script_storyboard_critique/__init__.py").read_text(encoding="utf-8")
    banned_import_markers = (
        "import httpx",
        "import requests",
        "import openai",
        "apps.api",
        "provider_adapter",
        "import subprocess",
        "import PIL",
        "import cv2",
    )
    unsafe = build_script_storyboard_critique(
        project_id="proj_story_critique",
        shots=[
            {
                "shot_id": "unsafe",
                "raw_provider_response": {"signed_url": "https://private.example.test/out.png?token=secret-token-value"},
            }
        ],
        asset_graph={},
    )

    assert all(marker not in source for marker in banned_import_markers)
    assert unsafe["packet_state"] == "blocked_unsafe"
    serialized = json.dumps(unsafe, ensure_ascii=False).lower()
    assert "private.example" not in serialized
    assert "secret-token-value" not in serialized
    _assert_boundary(unsafe)


def _assert_boundary(packet: dict) -> None:
    serialized = json.dumps(packet, ensure_ascii=False).lower()
    assert packet["provider_calls_started"] is False
    assert packet["generated_media_claimed"] is False
    assert packet["writes_long_term_memory"] is False
    assert packet["writes_company_kb"] is False
    assert packet["safety_boundary"]["provider_calls_started"] is False
    assert packet["safety_boundary"]["generated_media_claimed"] is False
    assert packet["safety_boundary"]["writes_long_term_memory"] is False
    assert packet["safety_boundary"]["writes_company_kb"] is False
    for field in FORBIDDEN_FIELDS:
        assert field not in serialized
