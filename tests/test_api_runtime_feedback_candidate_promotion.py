from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _record_feedback(client: TestClient, project_id: str) -> dict:
    response = client.post(
        "/feedback",
        json={
            "project_id": project_id,
            "generated_at": "2026-06-30T11:00:00+08:00",
            "feedback": {
                "kind": "studio_quality_feedback",
                "node_id": "image-node-001",
                "node_type": "image",
                "artifact_ref": "artifact-keyframe-summary",
                "ratings": {"identity_similarity": 4, "scene_continuity": 3},
                "drift_notes": "Use this as candidate evidence for the next local context pass.",
            },
        },
    )
    response.raise_for_status()
    return response.json()


def test_runtime_feedback_candidate_promotion_records_context_overlay_decision(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "feedback-candidate-promotion-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback candidate promotion demo"}).raise_for_status()
    feedback_payload = _record_feedback(client, project_id)
    feedback_event = feedback_payload["feedback_event"]
    candidate = feedback_event["feedback_candidate"]

    response = client.post(
        f"/projects/{project_id}/feedback-candidate-promotions",
        json={
            "feedback_artifact_id": feedback_payload["artifact"]["artifact_id"],
            "candidate_id": candidate["candidate_id"],
            "decision": "promote_to_context_overlay",
            "rationale": "Candidate is safe and relevant for the next local context overlay.",
            "reviewed_at": "2026-06-30T11:10:00+08:00",
        },
    )
    response.raise_for_status()
    payload = response.json()
    decision = payload["feedback_candidate_promotion_decision"]
    effect = decision["decision"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert decision["artifact_type"] == "agentflow_runtime_feedback_candidate_promotion_decision"
    assert decision["source_feedback_id"] == feedback_event["feedback_id"]
    assert decision["source_feedback_artifact_id"] == feedback_payload["artifact"]["artifact_id"]
    assert decision["candidate_id"] == candidate["candidate_id"]
    assert decision["candidate_scope"] == "quality_feedback_candidate"
    assert decision["safe_target"] == candidate["safe_target"]
    assert decision["safe_evidence_summary"] == candidate["safe_evidence_summary"]
    assert effect["decision"] == "promote_to_context_overlay"
    assert effect["decision_effect"] == "eligible_for_next_context_overlay"
    assert effect["context_overlay_allowed"] is True
    assert effect["context_overlay_written"] is False
    assert effect["durable_memory_allowed"] is False
    assert effect["provider_calls_started"] is False
    assert decision["writes_long_term_memory"] is False
    assert decision["writes_company_kb"] is False
    assert payload["artifact"]["role"] == "runtime_feedback_candidate_promotion_decision"
    assert payload["job"]["status"] == "succeeded"
    manifest = client.get(f"/projects/{project_id}/manifest").json()["manifest"]
    assert len(manifest["feedback_refs"]) == 2
    assert manifest["feedback_refs"][1]["feedback_id"] == decision["decision_id"]
    assert "provider_raw" not in serialized
    assert "signed_url" not in serialized
    assert "d:\\private" not in serialized


def test_runtime_feedback_candidate_promotion_rejects_candidate_mismatch(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "feedback-candidate-mismatch-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback candidate mismatch demo"}).raise_for_status()
    feedback_payload = _record_feedback(client, project_id)

    response = client.post(
        f"/projects/{project_id}/feedback-candidate-promotions",
        json={
            "feedback_artifact_id": feedback_payload["artifact"]["artifact_id"],
            "candidate_id": "runtime-feedback-candidate:wrong",
            "decision": "promote_to_context_overlay",
            "rationale": "This should not match the stored candidate.",
            "reviewed_at": "2026-06-30T11:15:00+08:00",
        },
    )

    assert response.status_code == 422


def test_runtime_feedback_candidate_promotion_rejects_unsafe_rationale(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "feedback-candidate-unsafe-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback candidate unsafe demo"}).raise_for_status()
    feedback_payload = _record_feedback(client, project_id)
    candidate = feedback_payload["feedback_event"]["feedback_candidate"]
    unsafe_local_path = f"{chr(68)}:{chr(92)}private{chr(92)}asset.png"

    response = client.post(
        f"/projects/{project_id}/feedback-candidate-promotions",
        json={
            "feedback_artifact_id": feedback_payload["artifact"]["artifact_id"],
            "candidate_id": candidate["candidate_id"],
            "decision": "promote_to_context_overlay",
            "rationale": f"Review evidence from {unsafe_local_path}",
            "reviewed_at": "2026-06-30T11:20:00+08:00",
        },
    )

    assert response.status_code == 422
