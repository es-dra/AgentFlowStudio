from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


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
