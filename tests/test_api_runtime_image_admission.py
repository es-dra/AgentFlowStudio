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


def test_single_smoke_cap_failed_dispatch_consumption_and_confirm_replay(tmp_path, monkeypatch) -> None:
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
    _command(
        client,
        {
            "type": "record_failure",
            "item_id": item_id,
            "idempotency_key": "failure-1",
            "error_category": "controlled_test_failure",
        },
        source,
    )
    _command(
        client,
        {
            "type": "replace",
            "item_id": item_id,
            "idempotency_key": "replace-1",
            "reason": "bounded retry preview",
        },
        source,
    )
    blocked = client.post(
        f"/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        json={
            "command": {
                "type": "reserve_dispatch",
                "item_id": item_id,
                "idempotency_key": "reserve-2",
            },
            "source": source,
            "requested_at": REQUESTED_AT,
        },
    )
    assert blocked.status_code == 422
    assert "仅允许发送一次" in blocked.json()["detail"]["details"]["raw_detail"]

    persisted = client.get(f"/projects/{PROJECT_ID}/m6/image-admission").json()["manifest"]
    assert persisted["budget"]["dispatches_reserved"] == 1
    assert persisted["budget"]["estimated_reserved_usd"] == "0.0377"
    assert persisted["budget"]["remaining_dispatches"] == 0
    assert persisted["actual_usd"] is None
    assert len([receipt for receipt in persisted["receipts"] if receipt["state"] == "failed"]) == 1


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
