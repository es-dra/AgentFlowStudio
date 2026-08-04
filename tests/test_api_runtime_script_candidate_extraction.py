from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_script_core_truth import ANALYSIS_REVIEW_SCHEMA_VERSION
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


def test_studio_runtime_client_exposes_the_same_extraction_route() -> None:
    runtime_client = (
        Path(__file__).resolve().parents[1] / "apps" / "studio" / "src" / "runtime-client.js"
    ).read_text(encoding="utf-8")

    assert "extractStructuredAnalysisCandidate(revisionId)" in runtime_client
    assert "/analysis-candidates/extract" in runtime_client
    assert 'return "extract_structured_analysis_candidate"' in runtime_client
