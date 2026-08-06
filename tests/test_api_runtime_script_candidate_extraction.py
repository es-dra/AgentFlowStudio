from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_script_core_truth import ANALYSIS_CANDIDATE_SCHEMA_VERSION
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


def test_direct_alias_link_proposals_cannot_bypass_default_off_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ENABLE_ALIAS_LINK_PROPOSALS", raising=False)
    project_id = "alias-proposals-direct-flag-off"
    source_text = "人物：陈默\n陈师傅把零件放在修理铺。"
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)
    character_start = source_text.index("陈默")
    alias_start = source_text.index("陈师傅")
    scene_start = source_text.index("修理铺")

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
            "named_characters": [
                {
                    "display_name": "陈默",
                    "aliases": [],
                    "pronoun_links": [],
                    "evidence_spans": [
                        {"start": character_start, "end": character_start + 2, "quote": "陈默"}
                    ],
                    "confidence": 0.98,
                }
            ],
            "main_scenes": [
                {
                    "name": "修理铺",
                    "evidence_spans": [
                        {"start": scene_start, "end": scene_start + 3, "quote": "修理铺"}
                    ],
                    "confidence": 0.98,
                }
            ],
            "alias_link_proposals": [
                {
                    "proposal_id": "aliasprop_direct_flag_bypass",
                    "schema_version": "afs.alias_link_proposal.v0.1",
                    "relation_type": "alias_identity_link",
                    "status": "candidate",
                    "authority": "non_authoritative_proposal",
                    "target_display_name": "陈默",
                    "alias": "陈师傅",
                    "confidence": 0.9,
                    "evidence_spans": [
                        {"start": alias_start, "end": alias_start + 3, "quote": "陈师傅"}
                    ],
                    "extraction_method": "surname_title_same_scene",
                    "review_action": "use_core_asset_command_merge_alias",
                    "provider_dispatch_count": 0,
                    "remote_dispatch_count": 0,
                }
            ],
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["error"] == "alias_link_proposals_disabled"
    projection = client.get(f"/projects/{project_id}/script-truth").json()["projection"]
    assert projection["assets"] == []
    assert projection["current_revision"]["analysis_state"] == "analysis_required"


def test_direct_alias_link_proposals_require_valid_distinct_candidate_target(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ENABLE_ALIAS_LINK_PROPOSALS", "true")
    source_text = "人物：陈默\n陈师傅把零件放在修理铺。"

    for suffix, target_name, alias, expected_error in (
        ("orphan", "不存在", "陈师傅", "alias_link_proposal_target_not_found"),
        ("self", "陈默", "陈默", "alias_link_proposal_self_reference"),
    ):
        project_id = f"alias-proposals-invalid-{suffix}"
        client = _client(tmp_path / suffix)
        revision = _create_revision(client, project_id, source_text)
        character_start = source_text.index("陈默")
        alias_start = source_text.index(alias)
        scene_start = source_text.index("修理铺")
        response = client.post(
            f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
            json={
                "project_id": project_id,
                "revision_id": revision["revision_id"],
                "source_digest": revision["source_digest"],
                "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
                "named_characters": [
                    {
                        "display_name": "陈默",
                        "aliases": [],
                        "pronoun_links": [],
                        "evidence_spans": [
                            {"start": character_start, "end": character_start + 2, "quote": "陈默"}
                        ],
                        "confidence": 0.98,
                    }
                ],
                "main_scenes": [
                    {
                        "name": "修理铺",
                        "evidence_spans": [
                            {"start": scene_start, "end": scene_start + 3, "quote": "修理铺"}
                        ],
                        "confidence": 0.98,
                    }
                ],
                "alias_link_proposals": [
                    {
                        "proposal_id": f"aliasprop_invalid_{suffix}",
                        "schema_version": "afs.alias_link_proposal.v0.1",
                        "relation_type": "alias_identity_link",
                        "status": "candidate",
                        "authority": "non_authoritative_proposal",
                        "target_display_name": target_name,
                        "alias": alias,
                        "confidence": 0.9,
                        "evidence_spans": [
                            {"start": alias_start, "end": alias_start + len(alias), "quote": alias}
                        ],
                        "extraction_method": "test_direct_submission",
                        "review_action": "use_core_asset_command_merge_alias",
                        "provider_dispatch_count": 0,
                        "remote_dispatch_count": 0,
                    }
                ],
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            },
        )

        assert response.status_code == 409, response.text
        assert response.json()["detail"]["error"] == expected_error
        projection = client.get(f"/projects/{project_id}/script-truth").json()["projection"]
        assert projection["assets"] == []


def test_alias_proposal_methods_stay_source_backed_and_suppress_unsafe_titles(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ENABLE_ALIAS_LINK_PROPOSALS", "true")
    project_id = "alias-proposals-method-coverage"
    source_text = """人物：王岚、赵平、陈默、陈明

第一场 - 内景 - 教室 - 夜

王岚（外号「阿岚」）打开讲义。
大家叫他：老赵。
远处有人喊：王老师
陈默和陈明坐在第一排。
陈老师走到门口。
"""
    client = _client(tmp_path)
    revision = _create_revision(client, project_id, source_text)

    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    proposals = response.json()["candidate"]["alias_link_proposals"]
    identities = {
        (item["target_display_name"], item["alias"], item["extraction_method"])
        for item in proposals
    }

    assert ("王岚", "阿岚", "explicit_aka_label") in identities
    assert ("赵平", "老赵", "lao_x_unique_anchor") in identities
    assert not any(item["alias"] in {"王老师", "陈老师"} for item in proposals)
    for proposal in proposals:
        for span in proposal["evidence_spans"]:
            assert source_text[span["start"] : span["end"]] == span["quote"]


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
    graph_before_merge = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert graph_before_merge["nodes"][character_assets["陈默"]["asset_id"]]["metadata"]["aliases"] == []

    bypass = client.post(
        f"/projects/{project_id}/core-assets/commands/confirm",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
            "command_type": "edit_asset",
            "target_asset_id": character_assets["陈默"]["asset_id"],
            "patch": {"aliases": ["陈师傅"]},
            "expected_asset_version": reviewed.json()["asset"]["version"],
            "idempotency_key": "edit-alias-bypass-must-fail",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert bypass.status_code == 409, bypass.text
    assert bypass.json()["detail"]["error"] == "edit_asset_aliases_require_merge_alias"
    after_bypass = client.get(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates"
    ).json()
    unchanged_character = next(
        item
        for item in after_bypass["assets"]
        if item["asset_id"] == character_assets["陈默"]["asset_id"]
    )
    assert unchanged_character["aliases"] == []
    assert unchanged_character["version"] == reviewed.json()["asset"]["version"]

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
    graph_after_merge = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    graph_character = graph_after_merge["nodes"][character_assets["陈默"]["asset_id"]]
    assert graph_after_merge["version"] == graph_before_merge["version"] + 1
    assert graph_character["metadata"]["asset_version_id"] == merged_character["version_id"]
    assert graph_character["metadata"]["aliases"] == ["陈师傅"]
    assert merged.json()["receipt"]["production_graph_version"] == graph_after_merge["version"]

    undone = client.post(
        f"/projects/{project_id}/core-assets/commands/undo",
        json={
            "project_id": project_id,
            "receipt_id": merged.json()["receipt"]["receipt_id"],
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        },
    )
    assert undone.status_code == 200, undone.text
    undone_character = next(
        item for item in undone.json()["projection"]["assets"] if item["asset_id"] == character_assets["陈默"]["asset_id"]
    )
    graph_after_undo = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    graph_character_after_undo = graph_after_undo["nodes"][character_assets["陈默"]["asset_id"]]
    assert graph_after_undo["version"] == graph_after_merge["version"] + 1
    assert graph_character_after_undo["metadata"]["asset_version_id"] == undone_character["version_id"]
    assert graph_character_after_undo["metadata"]["aliases"] == []


def test_studio_runtime_client_exposes_the_same_extraction_route() -> None:
    runtime_client = (
        Path(__file__).resolve().parents[1] / "apps" / "studio" / "src" / "runtime-client.js"
    ).read_text(encoding="utf-8")

    assert "extractStructuredAnalysisCandidate(revisionId)" in runtime_client
    assert "/analysis-candidates/extract" in runtime_client
    assert 'return "extract_structured_analysis_candidate"' in runtime_client
