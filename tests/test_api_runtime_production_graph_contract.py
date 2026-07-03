from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


def test_production_graph_algorithm_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import production_graph

    assert "production_graph" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert production_graph.ALGORITHM_ID == "afs.production_graph.v0.1"
    assert production_graph.INPUT_CONTRACT
    assert production_graph.OUTPUT_CONTRACT
    assert production_graph.FAILURE_MODES
    assert production_graph.EVIDENCE_BOUNDARY


def test_storyboard_breakdown_writes_safe_production_graph_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_production_graph_snapshot"
    client.post("/projects", json={"project_id": project_id, "goal": "Production graph contract"})

    response = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_graph_001",
            "script_text": (
                "林晚在办公室收到一张旧地图，地图上用红线标出废弃街道。"
                "林晚从办公室冲出，穿过街道时反复确认地图方向。"
                "雨水打湿地图边缘，她把地图按在墙上，对照远处闪烁的路灯。"
            ),
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-30T12:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    graph = payload["production_graph"]
    node_keys = {(node["node_type"], node["node_id"]) for node in graph["nodes"]}
    relationship_types = {item["relationship_type"] for item in graph["relationships"]}
    serialized = json.dumps(graph, ensure_ascii=False).lower()

    assert graph["artifact_type"] == "agentflow_production_graph_snapshot"
    assert graph["graph_stage"] == "storyboard_candidate_graph"
    assert graph["summary"]["project_id"] == project_id
    assert graph["summary"]["script_node_id"] == "script_graph_001"
    assert graph["summary"]["shot_count"] == len(payload["shots"])
    assert graph["summary"]["asset_count"] == payload["asset_graph"]["asset_count"]
    assert graph["summary"]["human_review_needed"] is True
    assert graph["writes_long_term_memory"] is False
    assert graph["writes_company_kb"] is False

    assert ("script", "script:script_graph_001") in node_keys
    assert any(node_type == "shot" for node_type, _node_id in node_keys)
    assert any(node_type == "asset" for node_type, _node_id in node_keys)
    assert ("quality_report", "quality:script_graph_001") in node_keys
    assert {"script_contains_shot", "shot_contains_asset", "quality_report_evaluates_storyboard"} <= relationship_types

    assert payload["safe_manifest"]["production_graph_node_count"] == len(graph["nodes"])
    assert "production_graph_snapshot" in payload["artifacts"]
    assert response_contains_unsafe_marker(graph) is False
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
    assert "d:\\" not in serialized


def test_storyboard_production_graph_includes_fixed_asset_source_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_production_graph_fixed_asset_source_evidence"
    image_asset_id = _upload_image(client, project_id)
    fixed_asset = _promote_fixed_asset(client, project_id, image_asset_id)

    response = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_graph_fixed_asset_001",
            "script_text": "Lin Wan returns to the old observatory and checks the red map.",
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-30T23:55:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    graph = payload["production_graph"]
    fixed_nodes = [node for node in graph["nodes"] if node.get("node_type") == "fixed_visual_asset"]
    relationships = graph["relationships"]
    serialized = json.dumps(graph, ensure_ascii=False).lower()

    assert graph["summary"]["fixed_visual_asset_count"] == 1
    assert payload["safe_manifest"]["fixed_visual_asset_source_evidence_count"] == 1
    assert fixed_nodes == [
        {
            "node_id": f"fixed_asset:{fixed_asset['asset_id']}",
            "node_type": "fixed_visual_asset",
            "asset_id": fixed_asset["asset_id"],
            "asset_type": "character",
            "label": "Lin Wan",
            "status": "fixed",
            "source_node_id": "node-ref",
            "review_state": "fixed_asset_available_for_reuse",
            "source_evidence": fixed_asset["source_evidence"],
            "writes_long_term_memory": False,
        }
    ]
    assert {
        "relationship_type": "script_can_reuse_fixed_asset",
        "from_node_id": "script:script_graph_fixed_asset_001",
        "to_node_id": f"fixed_asset:{fixed_asset['asset_id']}",
        "source": "runtime_visual_asset_store",
        "evidence_state": "fixed_asset_source_evidence_available",
    } in relationships
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_storyboard_production_graph_auto_binds_reversible_fixed_asset(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_production_graph_auto_binding"
    image_asset_id = _upload_image(client, project_id)
    fixed_asset = _promote_fixed_asset(
        client,
        project_id,
        image_asset_id,
        asset_type="prop",
        label="地图",
        signature="paper map with red route markings",
        feature_card={"appearance": "creased paper map with red route markings"},
        negative_locks=["keep the red route markings"],
        source_asset_card_candidate_id="asset_card_candidate:graph_prop_地图",
    )

    response = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_graph_auto_binding_001",
            "script_text": "林晚在办公室检查地图。她把地图按在墙上，对照远处闪烁的路灯。",
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-07-04T00:20:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    binding_graph = payload["asset_auto_binding_graph"]
    production_graph = payload["production_graph"]
    relationships = production_graph["relationships"]
    ledger_roles = {item["artifact_role"] for item in payload["evidence_ledger"]["evidence_items"]}
    serialized = json.dumps(binding_graph, ensure_ascii=False).lower()

    assert binding_graph == production_graph["asset_auto_binding_graph"]
    assert binding_graph["artifact_type"] == "agentflow_asset_auto_binding_graph"
    assert binding_graph["summary"]["established_binding_count"] == 1
    assert binding_graph["summary"]["suggested_binding_count"] == 1
    assert payload["safe_manifest"]["asset_auto_binding_established_count"] == 1
    assert "asset_auto_binding_graph" in payload["artifacts"]
    assert "asset_auto_binding_graph" in ledger_roles

    suggestion = binding_graph["binding_suggestions"][0]
    assert suggestion["graph_asset_id"] == "graph:prop:地图"
    assert suggestion["fixed_visual_asset_id"] == fixed_asset["asset_id"]
    assert suggestion["reversal_plan"]["action"] == "unbind"
    assert suggestion["lineage_refs"]["source_asset_card_candidate_id"] == "asset_card_candidate:graph_prop_地图"
    assert {
        "relationship_type": "asset_auto_binding_established",
        "from_node_id": "asset:graph:prop:地图",
        "to_node_id": f"fixed_asset:{fixed_asset['asset_id']}",
        "binding_id": suggestion["binding_id"],
        "binding_state": "bound",
        "confidence": 0.82,
        "explainable": True,
        "reversible": True,
        "undo_action": "unbind",
        "source": "afs.asset_auto_binding.v0.1",
    } in relationships
    assert response_contains_unsafe_marker(binding_graph) is False
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized


def _upload_image(client: TestClient, project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "node-ref",
            "filename": "reference.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-30T23:50:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]["asset_id"]


def _promote_fixed_asset(
    client: TestClient,
    project_id: str,
    image_asset_id: str,
    *,
    asset_type: str = "character",
    label: str = "Lin Wan",
    signature: str = "black short hair, red trench coat, scar above left brow",
    feature_card: dict | None = None,
    negative_locks: list[str] | None = None,
    source_asset_card_candidate_id: str = "asset_card_candidate:main_character",
) -> dict:
    response = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_asset_id],
            "asset_type": asset_type,
            "label": label,
            "signature": signature,
            "feature_card": feature_card or {"appearance": "young woman with black short hair"},
            "negative_locks": negative_locks or ["keep black short hair"],
            "source_node_id": "node-ref",
            "source_human_gate_id": "runtime-human-gate:demo:accepted",
            "source_asset_card_candidate_id": source_asset_card_candidate_id,
            "review_decision": "fixed",
            "reviewed_at": "2026-06-30T23:52:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]
