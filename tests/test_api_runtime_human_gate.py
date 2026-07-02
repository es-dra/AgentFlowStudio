from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_runtime_human_gate_records_asset_candidate_decision_without_promotion(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "human-gate-asset-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Human gate asset demo"}).raise_for_status()

    response = client.post(
        f"/projects/{project_id}/human-gate-decisions",
        json={
            "target_type": "asset_card_candidate",
            "target_id": "asset_card_candidate:main_character",
            "decision": "accepted_for_next_step",
            "artifact_id": "runs_demo_asset_card_candidates",
            "node_id": "storyboard-node-001",
            "scope": "asset_card_candidate_review",
            "note": "Candidate identity can move to the next local drafting step.",
            "reviewed_at": "2026-06-30T17:30:00+08:00",
        },
    )
    response.raise_for_status()
    payload = response.json()
    event = payload["human_gate_decision"]
    gate = event["decision"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert event["artifact_type"] == "agentflow_runtime_human_gate_decision"
    assert gate["target_type"] == "asset_card_candidate"
    assert gate["decision"] == "accepted_for_next_step"
    assert gate["promotes_fixed_asset"] is False
    assert gate["requires_separate_promotion"] is True
    assert gate["provider_calls_started"] is False
    assert gate["human_acceptance_scope"] == "local_step_gate_only"
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
    assert "not creative quality acceptance" in event["non_claims"]
    assert "not business validation" in event["non_claims"]
    assert payload["artifact"]["role"] == "runtime_human_gate_decision"
    assert payload["job"]["status"] == "succeeded"
    manifest = client.get(f"/projects/{project_id}/manifest").json()["manifest"]
    assert len(manifest["feedback_refs"]) == 1
    assert manifest["feedback_refs"][0]["feedback_id"] == event["human_gate_id"]
    assert "provider_raw" not in serialized
    assert "signed_url" not in serialized
    assert "d:\\private" not in serialized


def test_runtime_human_gate_records_keyframe_bridge_revision_decision(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "human-gate-keyframe-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Human gate keyframe demo"}).raise_for_status()

    response = client.post(
        f"/projects/{project_id}/human-gate-decisions",
        json={
            "target_type": "keyframe_generation_bridge",
            "target_id": "runs_keyframe_bridge_001",
            "decision": "needs_revision",
            "artifact_id": "runs_keyframe_generation_bridge",
            "node_id": "keyframe-node-001",
            "scope": "keyframe_generation_bridge_review",
            "note": "Revise composition before opening any provider gate.",
            "reviewed_at": "2026-06-30T17:45:00+08:00",
        },
    )
    response.raise_for_status()
    gate = response.json()["human_gate_decision"]["decision"]

    assert gate["target_type"] == "keyframe_generation_bridge"
    assert gate["decision"] == "needs_revision"
    assert gate["blocks_provider_step"] is True
    assert gate["provider_calls_started"] is False
    assert gate["human_acceptance_scope"] == "local_step_gate_only"


def test_runtime_human_gate_records_accepted_generation_plan_packet_decision(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "human-gate-plan-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Human gate accepted plan demo"}).raise_for_status()

    response = client.post(
        f"/projects/{project_id}/human-gate-decisions",
        json={
            "target_type": "accepted_generation_plan_packet",
            "target_id": "runs-human-gate-plan-demo-plan-source",
            "decision": "accepted_for_next_step",
            "artifact_id": "runs-human-gate-plan-demo-plan-source",
            "scope": "accepted_generation_plan_packet_review",
            "note": "Local plan packet can move to evaluator review; no creative acceptance claimed.",
            "reviewed_at": "2026-07-02T10:30:00+08:00",
        },
    )
    response.raise_for_status()
    payload = response.json()
    event = payload["human_gate_decision"]
    gate = event["decision"]

    assert gate["target_type"] == "accepted_generation_plan_packet"
    assert gate["decision"] == "accepted_for_next_step"
    assert gate["scope"] == "accepted_generation_plan_packet_review"
    assert gate["provider_calls_started"] is False
    assert gate["human_acceptance_scope"] == "local_step_gate_only"
    assert gate["promotes_fixed_asset"] is False
    assert event["writes_long_term_memory"] is False
    assert "not creative quality acceptance" in event["non_claims"]


def test_runtime_human_gate_rejects_unsafe_note_payload(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "human-gate-safety-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Human gate safety demo"}).raise_for_status()
    unsafe_local_path = f"{chr(68)}:{chr(92)}private{chr(92)}asset.png"

    response = client.post(
        f"/projects/{project_id}/human-gate-decisions",
        json={
            "target_type": "asset_card_candidate",
            "target_id": "asset_card_candidate:unsafe",
            "decision": "accepted_for_next_step",
            "note": f"Provider raw at {unsafe_local_path}",
            "reviewed_at": "2026-06-30T17:50:00+08:00",
        },
    )

    assert response.status_code == 422
