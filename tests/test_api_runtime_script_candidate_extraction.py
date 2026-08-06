from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_script_core_truth import ANALYSIS_REVIEW_SCHEMA_VERSION
from apps.api.runtime_script_core_truth import CORE_ASSET_COMMAND_SCHEMA_VERSION
from apps.api.runtime_service import create_runtime_app


def _client(tmp_path) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=tmp_path))


def _create_revision(client: TestClient, project_id: str, source_text: str) -> dict:
    created = client.post("/projects", json={"project_id": project_id, "goal": "Extract script facts"})
    assert created.status_code == 200, created.text
    response = client.post(
        f"/projects/{project_id}/script-revisions",
        json={
            "source_kind": "script",
            "source_text": source_text,
            "provenance": {"fixture": "deterministic_candidate_extraction"},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["revision"]


def _merge_alias_command(project_id: str, revision: dict, target_asset_id: str, alias: str) -> dict:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        "command_type": "merge_alias",
        "target_asset_id": target_asset_id,
        "patch": {"alias": alias},
        "idempotency_key": f"merge-{target_asset_id}-{alias}",
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _merge_scene_name_command(
    project_id: str,
    revision: dict,
    canonical_asset_id: str,
    variant_asset_id: str,
    key: str = "merge-scene-name",
) -> dict:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        "command_type": "merge_scene_name",
        "target_asset_id": canonical_asset_id,
        "patch": {"variant_asset_id": variant_asset_id},
        "idempotency_key": key,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def test_deterministic_extraction_enters_the_existing_review_loop(tmp_path) -> None:
    project_id = "candidate-extraction-letter"
    source_text = """标题：海边的信

第一场 - 内景 - 老式邮局 - 清晨

苏晴（20多岁，安静）站在柜台前。邮局职员老王（50多岁）抬起头。

老王
又来寄信啊？

苏晴
第十七封了。

第二场 - 外景 - 海边礁石 - 黄昏

她的朋友林悦（20多岁，直率）从远处走来。

林悦
你还在等他回信？

苏晴没说话，只是望着远处。灯上落了一层灰。

第三场 - 内景 - 苏晴的房间 - 深夜

苏晴
爸，今天我又去了海边礁石那里……
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["provider_dispatch_count"] == 0
    assert payload["remote_dispatch_count"] == 0
    assert payload["candidate"]["missing_slots"] == []
    assets = payload["projection"]["assets"]
    assert {item["display_name"] for item in assets if item["asset_type"] == "character"} == {
        "苏晴",
        "老王",
        "林悦",
    }
    assert {item["name"] for item in assets if item["asset_type"] == "main_scene"} == {
        "老式邮局",
        "海边礁石",
        "苏晴的房间",
    }
    assert "苏晴没" not in {item["display_name"] for item in assets if item["asset_type"] == "character"}
    assert "灯上" not in {item["name"] for item in assets if item["asset_type"] == "main_scene"}

    assert {item["evidence_status"] for item in assets} == {"extracted_from_text"}
    assert all(item["extraction_method"] for item in assets)
    for asset in assets:
        for span in asset["evidence_spans"]:
            assert source_text[span["start"] : span["end"]] == span["quote"]

    replay = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["candidate"]["candidate_id"] == payload["candidate"]["candidate_id"]
    assert replay.json()["preserved_asset_ids"]


def test_reextraction_preserves_final_human_decisions_and_graph_authority(tmp_path) -> None:
    project_id = "candidate-reextraction-authority"
    source_text = "Characters: Mira\nScenes: Archive Hall"
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    extracted = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert extracted.status_code == 200, extracted.text
    initial = extracted.json()
    character = next(item for item in initial["projection"]["assets"] if item["asset_type"] == "character")
    scene = next(item for item in initial["projection"]["assets"] if item["asset_type"] == "main_scene")

    confirmed = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character['asset_id']}/review",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "candidate_id": initial["candidate"]["candidate_id"],
            "asset_version_id": character["version_id"],
            "expected_asset_version": character["version"],
            "expected_graph_version": 0,
            "idempotency_key": "confirm-mira-before-reextract",
            "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
            "decision": "confirm",
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    rejected = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{scene['asset_id']}/review",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "candidate_id": initial["candidate"]["candidate_id"],
            "asset_version_id": scene["version_id"],
            "expected_asset_version": scene["version"],
            "expected_graph_version": 1,
            "idempotency_key": "reject-scene-before-reextract",
            "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
            "decision": "reject",
        },
    )
    assert rejected.status_code == 200, rejected.text
    final_versions = {
        character["asset_id"]: confirmed.json()["asset"]["version_id"],
        scene["asset_id"]: rejected.json()["asset"]["version_id"],
    }

    replay = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert replay.status_code == 200, replay.text
    replay_assets = {item["asset_id"]: item for item in replay.json()["projection"]["assets"]}
    assert replay_assets[character["asset_id"]]["status"] == "confirmed"
    assert replay_assets[scene["asset_id"]]["status"] == "rejected"
    assert {
        asset_id: item["version_id"] for asset_id, item in replay_assets.items()
    } == final_versions
    assert set(replay.json()["preserved_asset_ids"]) == {character["asset_id"], scene["asset_id"]}
    graph = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert character["asset_id"] in graph["nodes"]
    assert scene["asset_id"] not in graph["nodes"]


def test_deterministic_extraction_records_missing_without_inventing_facts(tmp_path) -> None:
    project_id = "candidate-extraction-missing"
    source_text = """第一场 - 内景 - 一个房间 - 夜

女人坐在桌边。苏晴没说话，从远处传来铃声。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    candidate = response.json()["candidate"]

    assert candidate["named_character_count"] == 0
    assert candidate["main_scene_count"] == 0
    assert candidate["missing_slots"] == ["named_characters", "main_scenes"]
    assert candidate["extraction_notes"] == [
        "named characters missing: no source-backed proper name found",
        "main scenes missing: no specific labeled location or industry heading found",
    ]
    assert response.json()["projection"]["assets"] == []
    assert response.json()["analysis_state"] == "low_confidence_pending"


def test_deterministic_extraction_rejects_standalone_action_fragments(tmp_path) -> None:
    project_id = "candidate-extraction-adversarial"
    source_text = """第一场 - 内景 - 废弃灯塔 - 夜

颤抖
灯上落了一层灰。

苏晴
我们该走了。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    assets = response.json()["projection"]["assets"]

    assert {item["display_name"] for item in assets if item["asset_type"] == "character"} == {"苏晴"}
    assert {item["name"] for item in assets if item["asset_type"] == "main_scene"} == {"废弃灯塔"}


def test_alias_link_proposals_are_feature_flagged_off_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ENABLE_ALIAS_LINK_PROPOSALS", raising=False)
    project_id = "alias-proposals-flag-off"
    source_text = """标题：夜校的灯

第一场 - 内景 - 修理铺后院 - 夜

人物：陈默、李薇

李薇
陈师傅，零件送来了。

陈默
放门口就行。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert "alias_link_proposal_count" not in payload["candidate"]
    assert "alias_link_proposals" not in payload["candidate"]
    assert all(item["aliases"] == [] for item in payload["projection"]["assets"] if item["asset_type"] == "character")


def test_alias_link_proposals_are_candidates_until_merge_alias_confirms_them(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ENABLE_ALIAS_LINK_PROPOSALS", "true")
    project_id = "alias-proposals-enabled"
    source_text = """标题：夜校的灯

第一场 - 内景 - 修理铺后院 - 夜

人物：陈默、李薇、林悦安

李薇
陈师傅，零件送来了。

林悦安
今天从第二段开始。

导演
悦安，眼神再收一点。

陈默
放门口就行。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    proposals = payload["candidate"]["alias_link_proposals"]

    assert {
        (item["target_display_name"], item["alias"], item["extraction_method"])
        for item in proposals
    } >= {
        ("陈默", "陈师傅", "surname_title_same_scene"),
        ("林悦安", "悦安", "given_name_suffix_same_scene_unique_anchor"),
    }
    assert {item["status"] for item in proposals} == {"candidate"}
    assert {item["authority"] for item in proposals} == {"non_authoritative_proposal"}
    assert {item["review_action"] for item in proposals} == {"use_core_asset_command_merge_alias"}
    for proposal in proposals:
        for span in proposal["evidence_spans"]:
            assert source_text[span["start"] : span["end"]] == span["quote"]

    character_assets = {
        item["display_name"]: item for item in payload["projection"]["assets"] if item["asset_type"] == "character"
    }
    assert character_assets["陈默"]["aliases"] == []
    assert character_assets["林悦安"]["aliases"] == []

    reviewed = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{character_assets['陈默']['asset_id']}/review",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "candidate_id": payload["candidate"]["candidate_id"],
            "asset_version_id": character_assets["陈默"]["version_id"],
            "expected_asset_version": character_assets["陈默"]["version"],
            "expected_graph_version": 0,
            "idempotency_key": "confirm-chenmo-without-alias-authority",
            "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
            "decision": "confirm",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["asset"]["status"] == "confirmed"
    assert reviewed.json()["asset"]["aliases"] == []

    merged = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_merge_alias_command(project_id, revision, character_assets["陈默"]["asset_id"], "陈师傅"),
            "expected_asset_version": reviewed.json()["asset"]["version"],
        },
    )
    assert merged.status_code == 200, merged.text
    merged_character = next(
        item for item in merged.json()["projection"]["assets"] if item["asset_id"] == character_assets["陈默"]["asset_id"]
    )
    assert "陈师傅" in merged_character["aliases"]


def test_scene_name_normalization_proposals_are_feature_flagged_off_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ENABLE_SCENE_NAME_NORMALIZATION_PROPOSALS", raising=False)
    project_id = "scene-norm-flag-off"
    source_text = """标题：邮局

第一场

地点：老城区二十四小时邮局大厅

顾晚
上班。

第二场 - 内景 - 邮局大厅 - 夜

顾晚
加班。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert "scene_name_normalization_proposals" not in payload["candidate"]
    assert "scene_name_normalization_proposal_count" not in payload["candidate"]
    scenes = {item["name"] for item in payload["projection"]["assets"] if item["asset_type"] == "main_scene"}
    assert "老城区二十四小时邮局大厅" in scenes
    assert "邮局大厅" in scenes


def test_scene_name_normalization_proposals_are_non_authoritative(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ENABLE_SCENE_NAME_NORMALIZATION_PROPOSALS", "true")
    project_id = "scene-norm-enabled"
    source_text = """标题：邮局

第一场

地点：老城区二十四小时邮局大厅

顾晚
上班。

第二场 - 内景 - 邮局大厅 - 夜

顾晚
加班。

第三场 - 内景 - 顾晚合租屋的客厅 - 夜

顾晚坐着。

第四场 - 内景 - 合租屋客厅 - 日

顾晚站着。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    proposals = payload["candidate"]["scene_name_normalization_proposals"]

    assert {
        (item["canonical_scene_name"], item["variant_scene_name"], item["extraction_method"])
        for item in proposals
    } == {("老城区二十四小时邮局大厅", "邮局大厅", "scene_name_prefix_or_suffix_unique")}
    # Mid-substring with intervening 的 is intentionally not proposed.
    assert all(item["variant_scene_name"] != "合租屋客厅" for item in proposals)
    assert {item["status"] for item in proposals} == {"candidate"}
    assert {item["authority"] for item in proposals} == {"non_authoritative_proposal"}
    assert {item["review_action"] for item in proposals} == {"use_core_asset_command_merge_scene_name"}
    for proposal in proposals:
        for span in proposal["evidence_spans"]:
            assert source_text[span["start"] : span["end"]] == span["quote"]

    scene_assets = [item for item in payload["projection"]["assets"] if item["asset_type"] == "main_scene"]
    assert {item["name"] for item in scene_assets} >= {
        "老城区二十四小时邮局大厅",
        "邮局大厅",
        "顾晚合租屋的客厅",
        "合租屋客厅",
    }
    # Proposals never collapse scene assets.
    assert len({item["asset_id"] for item in scene_assets if item["name"] in {"老城区二十四小时邮局大厅", "邮局大厅"}}) == 2
    assert all(item["aliases"] == [] for item in scene_assets)


def test_scene_name_normalization_proposal_requires_explicit_merge_scene_name_confirm(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ENABLE_SCENE_NAME_NORMALIZATION_PROPOSALS", "true")
    project_id = "scene-norm-confirm"
    source_text = """标题：邮局

第一场

地点：老城区二十四小时邮局大厅

顾晚
上班。

第二场 - 内景 - 邮局大厅 - 夜

顾晚
加班。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    proposal = payload["candidate"]["scene_name_normalization_proposals"][0]
    assert proposal["canonical_scene_name"] == "老城区二十四小时邮局大厅"
    assert proposal["variant_scene_name"] == "邮局大厅"

    scene_assets = {item["name"]: item for item in payload["projection"]["assets"] if item["asset_type"] == "main_scene"}
    canonical = scene_assets["老城区二十四小时邮局大厅"]
    variant = scene_assets["邮局大厅"]
    assert canonical["aliases"] == []
    assert variant["aliases"] == []

    preview = client.post(
        f"/projects/{project_id}/core-assets/commands/preview",
        json={
            **_merge_scene_name_command(
                project_id,
                revision,
                canonical["asset_id"],
                variant["asset_id"],
                key="preview-scene-name",
            ),
            "expected_asset_version": canonical["version"],
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["command"]["requires_confirmation"] is True
    assert preview.json()["command"]["after"]["aliases"] == ["邮局大厅"]

    truth_before_confirm = client.get(f"/projects/{project_id}/script-truth")
    assert truth_before_confirm.status_code == 200, truth_before_confirm.text
    canonical_before = next(
        item
        for item in truth_before_confirm.json()["projection"]["assets"]
        if item["asset_id"] == canonical["asset_id"]
    )
    assert canonical_before["aliases"] == []

    confirmed = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_merge_scene_name_command(
                project_id,
                revision,
                canonical["asset_id"],
                variant["asset_id"],
                key="confirm-scene-name",
            ),
            "expected_asset_version": canonical["version"],
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_payload = confirmed.json()
    assert confirmed_payload["receipt"]["command_type"] == "merge_scene_name"
    scenes_after = {
        item["asset_id"]: item
        for item in confirmed_payload["projection"]["assets"]
        if item["asset_type"] == "main_scene"
    }
    assert scenes_after[canonical["asset_id"]]["name"] == "老城区二十四小时邮局大厅"
    assert scenes_after[canonical["asset_id"]]["aliases"] == ["邮局大厅"]
    assert scenes_after[variant["asset_id"]]["name"] == "邮局大厅"
    assert scenes_after[variant["asset_id"]]["aliases"] == []

    replay = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_merge_scene_name_command(
                project_id,
                revision,
                canonical["asset_id"],
                variant["asset_id"],
                key="confirm-scene-name",
            ),
            "expected_asset_version": canonical["version"],
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["receipt"]["receipt_id"] == confirmed_payload["receipt"]["receipt_id"]

    stale = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_merge_scene_name_command(
                project_id,
                revision,
                canonical["asset_id"],
                variant["asset_id"],
                key="stale-scene-name",
            ),
            "expected_asset_version": canonical["version"],
        },
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["detail"]["error"] == "core_asset_version_conflict"


def test_merge_scene_name_rejects_invalid_scene_targets(tmp_path) -> None:
    project_id = "scene-norm-invalid-targets"
    source_text = """Characters: Mira
Scenes: Archive Hall

Mira
Ready.
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    assets = response.json()["projection"]["assets"]
    character = next(item for item in assets if item["asset_type"] == "character")
    scene = next(item for item in assets if item["asset_type"] == "main_scene")

    wrong_target = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_merge_scene_name_command(
                project_id,
                revision,
                character["asset_id"],
                scene["asset_id"],
                key="wrong-canonical-type",
            ),
            "expected_asset_version": character["version"],
        },
    )
    assert wrong_target.status_code == 409, wrong_target.text
    assert wrong_target.json()["detail"]["error"] == "merge_scene_name_requires_main_scene"

    missing_variant = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_merge_scene_name_command(
                project_id,
                revision,
                scene["asset_id"],
                "scene_missing",
                key="missing-variant-id",
            ),
            "expected_asset_version": scene["version"],
        },
    )
    assert missing_variant.status_code == 404, missing_variant.text
    assert missing_variant.json()["detail"]["error"] == "core_asset_target_not_found"

    same_scene = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_merge_scene_name_command(
                project_id,
                revision,
                scene["asset_id"],
                scene["asset_id"],
                key="same-scene-id",
            ),
            "expected_asset_version": scene["version"],
        },
    )
    assert same_scene.status_code == 409, same_scene.text
    assert same_scene.json()["detail"]["error"] == "scene_name_variant_matches_canonical"


def test_studio_runtime_client_exposes_the_same_extraction_route() -> None:
    runtime_client = (
        Path(__file__).resolve().parents[1] / "apps" / "studio" / "src" / "runtime-client.js"
    ).read_text(encoding="utf-8")

    assert "extractStructuredAnalysisCandidate(revisionId)" in runtime_client
    assert "/analysis-candidates/extract" in runtime_client
    assert 'return "extract_structured_analysis_candidate"' in runtime_client


def _fake_indirect_judge(_text: str, mention: str, _output_dir) -> dict:
    """Mock paid LLM judge — never hits a remote provider in unit/API tests."""
    if mention in {"顾衡", "沈岚", "江澄", "柯衡"}:
        return {
            "refers_to_real_character": True,
            "refers_to_real_character_confidence": 0.95,
            "refers_to_real_character_reason": f"{mention} 是真实人物",
            "is_present_in_scene": False,
            "is_present_in_scene_confidence": 0.9,
            "is_present_in_scene_reason": "仅被提及",
            "is_indirect_mention": True,
        }
    return {
        "refers_to_real_character": False,
        "refers_to_real_character_confidence": 0.95,
        "refers_to_real_character_reason": "噪声",
        "is_present_in_scene": False,
        "is_present_in_scene_confidence": 0.95,
        "is_present_in_scene_reason": "非人物",
        "is_indirect_mention": False,
    }


def test_indirect_mention_llm_proposals_are_feature_flagged_off_by_default(tmp_path, monkeypatch) -> None:
    # Paid path must stay off by default so extract remains free/zero-dispatch.
    monkeypatch.delenv("AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS", raising=False)
    project_id = "indirect-mention-flag-off"
    source_text = """标题：夜班

第一场 - 内景 - 邮局大厅 - 夜

人物：顾晚

顾晚拆开汇款单：收款人是「顾衡」。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider_dispatch_count"] == 0
    assert payload["remote_dispatch_count"] == 0
    assert "indirect_mention_proposals" not in payload["candidate"]
    assert "indirect_mention_proposal_count" not in payload["candidate"]
    assert "indirect_mention_budget_skipped" not in payload["candidate"]
    assert all(
        item["display_name"] != "顾衡"
        for item in payload["projection"]["assets"]
        if item["asset_type"] == "character"
    )


def test_indirect_mention_llm_proposals_are_non_authoritative_until_manual_create(
    tmp_path, monkeypatch
) -> None:
    # COST: flag enables paid remote LLM. This test mocks the judge — no real calls.
    monkeypatch.setenv("AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS", "true")
    monkeypatch.setenv("AFS_INDIRECT_MENTION_LLM_MAX_CALLS", "12")
    monkeypatch.setattr(
        "apps.api.runtime_script_indirect_mention_proposals._default_remote_judge",
        _fake_indirect_judge,
    )
    project_id = "indirect-mention-enabled"
    source_text = """标题：夜班

第一场 - 内景 - 邮局大厅 - 夜

人物：顾晚

顾晚拆开：收款人是「顾衡」。

方糖
顾衡是谁？

顾晚
照片背面写着「沈岚」。电话那头喊「江澄」。
巷口喷着「默记修缮」。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider_dispatch_count"] > 0
    assert payload["remote_dispatch_count"] == payload["provider_dispatch_count"]
    assert any("PAID remote LLM" in note for note in payload["extraction"]["notes"])

    proposals = payload["candidate"]["indirect_mention_proposals"]
    mentions = {item["mention"] for item in proposals}
    assert {"顾衡", "沈岚", "江澄"} <= mentions
    assert "默记修缮" not in mentions
    assert {item["status"] for item in proposals} == {"candidate"}
    assert {item["authority"] for item in proposals} == {"non_authoritative_proposal"}
    assert {item["cost_class"] for item in proposals} == {"paid_remote_llm"}
    assert {item["review_action"] for item in proposals} == {
        "use_core_asset_command_create_manual_character"
    }
    character_names = {
        item["display_name"] for item in payload["projection"]["assets"] if item["asset_type"] == "character"
    }
    assert "顾衡" not in character_names
    assert "沈岚" not in character_names
    assert "江澄" not in character_names

    guwan = next(item for item in payload["projection"]["assets"] if item["display_name"] == "顾晚")
    reviewed = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-assets/{guwan['asset_id']}/review",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "candidate_id": payload["candidate"]["candidate_id"],
            "asset_version_id": guwan["version_id"],
            "expected_asset_version": guwan["version"],
            "expected_graph_version": 0,
            "idempotency_key": "confirm-guwan-no-indirect-authority",
            "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
            "decision": "confirm",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["asset"]["status"] == "confirmed"
    truth_after_review = client.get(f"/projects/{project_id}/script-truth")
    assert truth_after_review.status_code == 200, truth_after_review.text
    after_review_names = {
        item["display_name"]
        for item in truth_after_review.json()["projection"]["assets"]
        if item["asset_type"] == "character"
    }
    assert "顾衡" not in after_review_names
    assert "沈岚" not in after_review_names
    assert "江澄" not in after_review_names

    proposal = next(item for item in proposals if item["mention"] == "顾衡")
    preview = client.post(
        f"/projects/{project_id}/core-assets/commands/preview",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "create_manual_character",
            "patch": {
                "display_name": proposal["mention"],
                "evidence_spans": proposal["evidence_spans"],
                "proposal_id": proposal["proposal_id"],
            },
            "idempotency_key": "preview-manual-guheng",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["command"]["requires_confirmation"] is True
    assert preview.json()["command"]["after"]["status"] == "confirmed"
    assert preview.json()["command"]["after"]["asset_type"] == "character"

    truth_before_confirm = client.get(f"/projects/{project_id}/script-truth")
    assert truth_before_confirm.status_code == 200, truth_before_confirm.text
    assert "顾衡" not in {
        item["display_name"]
        for item in truth_before_confirm.json()["projection"]["assets"]
        if item["asset_type"] == "character"
    }

    confirmed = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "create_manual_character",
            "patch": {
                "display_name": proposal["mention"],
                "evidence_spans": proposal["evidence_spans"],
                "proposal_id": proposal["proposal_id"],
            },
            "idempotency_key": "confirm-manual-guheng",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["receipt"]["command_type"] == "create_manual_character"
    confirmed_names = {
        item["display_name"]
        for item in confirmed.json()["projection"]["assets"]
        if item["asset_type"] == "character"
    }
    assert "顾衡" in confirmed_names
    guheng = next(
        item
        for item in confirmed.json()["projection"]["assets"]
        if item["display_name"] == "顾衡"
    )
    assert guheng["status"] == "confirmed"
    assert guheng["source_mode"] == "manual"


def test_indirect_mention_budget_skip_is_explicit(tmp_path, monkeypatch) -> None:
    # COST: paid path with tiny budget — over-budget discoveries must be explicit.
    monkeypatch.setenv("AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS", "true")
    monkeypatch.setenv("AFS_INDIRECT_MENTION_LLM_MAX_CALLS", "1")
    monkeypatch.setattr(
        "apps.api.runtime_script_indirect_mention_proposals._default_remote_judge",
        _fake_indirect_judge,
    )
    project_id = "indirect-mention-budget"
    source_text = """标题：预算探针

第一场 - 内景 - 实验室 - 夜

人物：顾晚

收款人是「顾衡」。
照片背面写着「沈岚」。
电话里说「江澄」。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)
    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider_dispatch_count"] == 1
    skipped = payload["candidate"]["indirect_mention_budget_skipped"]
    assert skipped
    assert all(item["status"] == "budget_skipped_unjudged" for item in skipped)
    assert all(item["cost_class"] == "paid_remote_llm" for item in skipped)
    assert all("Exceeded" in item["reason"] for item in skipped)


def test_studio_agent_chat_exposes_manual_character_entry() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "apps" / "studio" / "src" / "agent-chat-lifecycle.js"
    ).read_text(encoding="utf-8")
    assert "/manual-character" in source
    assert 'commandType: "create_manual_character"' in source
    assert "create_manual_character: \"手动角色创建\"" in source


def test_indirect_mention_suppresses_already_extracted_suheng_and_chenmo(tmp_path, monkeypatch) -> None:
    # Real cases from live e2e: 苏衡 / 陈默 were extracted AND wrongly proposed.
    # Force the LLM judge to say "indirect" so suppression (not judgment) is what blocks them.
    def force_indirect_judge(_text: str, mention: str, _output_dir) -> dict:
        return {
            "refers_to_real_character": True,
            "refers_to_real_character_confidence": 0.95,
            "refers_to_real_character_reason": f"{mention} forced",
            "is_present_in_scene": False,
            "is_present_in_scene_confidence": 0.9,
            "is_present_in_scene_reason": "forced absent",
            "is_indirect_mention": True,
        }

    monkeypatch.setenv("AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS", "true")
    monkeypatch.setenv("AFS_INDIRECT_MENTION_LLM_MAX_CALLS", "20")
    monkeypatch.setattr(
        "apps.api.runtime_script_indirect_mention_proposals._default_remote_judge",
        force_indirect_judge,
    )
    project_id = "indirect-suppress-known"
    source_text = """标题：回声与夜班

第一场 - 内景 - 旅馆走廊 - 夜

人物：苏衡、陈默、顾晚

苏衡
别回头。

陈默
我只修水管。

杂音里仿佛有人喊了一声「苏衡」，随后恢复死寂。
草稿上又把「陈默」三个字划掉。
顾晚拆开汇款单：收款人是「顾衡」。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)
    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    proposals = payload["candidate"].get("indirect_mention_proposals") or []
    suppressed = payload["candidate"].get("indirect_mention_suppressed_known_identity") or []
    proposal_names = {item["mention"] for item in proposals}
    suppressed_names = {item["mention"] for item in suppressed}
    assert "苏衡" in suppressed_names
    assert "陈默" in suppressed_names
    assert "苏衡" not in proposal_names
    assert "陈默" not in proposal_names
    assert "顾衡" in proposal_names
    assert all(item["status"] == "suppressed_known_identity" for item in suppressed)
    assert all(item["already_extracted_as_character"] is True for item in suppressed)
    # Suppressed known identities must not consume paid dispatches.
    assert "suppressed_known_identity=" in " ".join(payload["extraction"]["notes"])


def test_create_manual_character_rejects_exact_identity_duplicates(tmp_path) -> None:
    project_id = "manual-char-dedupe"
    source_text = """标题：夜班

第一场 - 内景 - 邮局 - 夜

人物：顾晚、陈默

顾晚
上班。

陈默
到了。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)
    extracted = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert extracted.status_code == 200, extracted.text

    # Duplicate exact canonical name must be rejected (no silent second identity).
    dup = client.post(
        f"/projects/{project_id}/core-assets/commands/preview",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "create_manual_character",
            "patch": {"display_name": "顾晚"},
            "idempotency_key": "dup-guwan",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert dup.status_code == 409, dup.text
    detail = dup.json()["detail"]
    assert detail["error"] == "manual_character_identity_exists"
    assert detail["details"]["suggested_command"] == "merge_alias"

    # A5-style distinct people sharing only a surname must not be blocked.
    chenming = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "create_manual_character",
            "patch": {"display_name": "陈明"},
            "idempotency_key": "create-chenming",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert chenming.status_code == 200, chenming.text
    names = {
        item["display_name"]
        for item in chenming.json()["projection"]["assets"]
        if item["asset_type"] == "character"
    }
    assert "陈默" in names
    assert "陈明" in names

    # True homonym bypass: allow_duplicate_display_name=true.
    twin = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "create_manual_character",
            "patch": {"display_name": "陈默", "allow_duplicate_display_name": True},
            "idempotency_key": "create-chenmo-homonym",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert twin.status_code == 200, twin.text
    chenmo_assets = [
        item
        for item in twin.json()["projection"]["assets"]
        if item["asset_type"] == "character" and item["display_name"] == "陈默"
    ]
    assert len(chenmo_assets) >= 2
    assert any(
        (item.get("lineage") or {}).get("allow_duplicate_display_name") is True for item in chenmo_assets
    )


def test_create_manual_character_rejects_alias_surface_duplicates(tmp_path) -> None:
    project_id = "manual-char-alias-dedupe"
    source_text = """标题：排练

第一场

人物：林悦安

林悦安
今天从第二段开始。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)
    extracted = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert extracted.status_code == 200, extracted.text
    character = next(
        item
        for item in extracted.json()["projection"]["assets"]
        if item["asset_type"] == "character" and item["display_name"] == "林悦安"
    )
    merged = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            **_merge_alias_command(project_id, revision, character["asset_id"], "悦安"),
            "expected_asset_version": character["version"],
        },
    )
    assert merged.status_code == 200, merged.text

    blocked = client.post(
        f"/projects/{project_id}/core-assets/commands/preview",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "create_manual_character",
            "patch": {"display_name": "悦安"},
            "idempotency_key": "dup-yuean-alias",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["error"] == "manual_character_identity_exists"
    assert blocked.json()["detail"]["details"]["matched_as"] == "alias"
