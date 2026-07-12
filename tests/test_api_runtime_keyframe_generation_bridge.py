from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


def test_generation_bridge_algorithm_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import generation_bridge

    assert "generation_bridge" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert generation_bridge.ALGORITHM_ID == "afs.generation_bridge.v0.1"
    assert generation_bridge.INPUT_CONTRACT
    assert generation_bridge.OUTPUT_CONTRACT
    assert generation_bridge.FAILURE_MODES
    assert generation_bridge.EVIDENCE_BOUNDARY


def test_keyframe_generation_gate_closed_writes_local_bridge_artifact(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_keyframe_generation_bridge"

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "keyframe_bridge_001",
            "prompt_text": "A cinematic keyframe of Lin Wan holding a silver pocket watch at an abandoned station.",
            "optimized_prompt": "Cinematic keyframe, abandoned station, silver pocket watch, red signal light.",
            "target_platform": "short_video",
            "style": "cinematic",
            "candidate_count": 2,
            "seed": 42,
            "generated_at": "2026-06-30T17:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    bridge = payload["generation_bridge"]
    serialized = json.dumps(bridge, ensure_ascii=False).lower()

    assert payload["job"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    assert payload["safe_manifest"]["provider_calls_started"] is False
    assert payload["safe_manifest"]["local_generation_bridge_ready"] is True
    assert "keyframe_generation_bridge" in payload["artifacts"]

    assert bridge["artifact_type"] == "agentflow_generation_bridge"
    assert bridge["bridge_stage"] == "keyframe_local_deterministic_bridge"
    assert bridge["summary"]["project_id"] == project_id
    assert bridge["summary"]["node_id"] == "keyframe_bridge_001"
    assert bridge["summary"]["generation_state"] == "blocked_before_provider"
    assert bridge["summary"]["provider_calls_started"] is False
    assert bridge["summary"]["provider_smoked"] is False
    assert bridge["summary"]["human_accepted"] is False
    assert bridge["summary"]["business_validated"] is False
    assert bridge["summary"]["bridge_media_generated"] is False
    assert bridge["planned_outputs"][0]["candidate_id"] == "planned_candidate_001"
    assert bridge["planned_outputs"][0]["media_bytes_available"] is False
    assert bridge["provider_evidence"]["provider_gate"]["status"] == "blocked"
    assert bridge["provider_evidence"]["raw_provider_response_stored"] is False
    assert bridge["provider_evidence"]["generated_media_bytes_stored"] is False
    assert bridge["writes_long_term_memory"] is False
    assert bridge["writes_company_kb"] is False

    artifact_payload = client.get(f"/artifacts/{payload['artifacts']['keyframe_generation_bridge']['artifact_id']}").json()["payload"]
    assert artifact_payload == bridge
    assert response_contains_unsafe_marker(bridge) is False
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
    assert "data_base64" not in serialized
    assert "d:\\" not in serialized
