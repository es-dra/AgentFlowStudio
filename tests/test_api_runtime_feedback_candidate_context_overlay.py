from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _record_feedback(client: TestClient, project_id: str) -> dict:
    response = client.post(
        "/feedback",
        json={
            "project_id": project_id,
            "generated_at": "2026-06-30T12:00:00+08:00",
            "feedback": {
                "kind": "studio_quality_feedback",
                "node_id": "image-node-ctx-001",
                "node_type": "image",
                "artifact_ref": "artifact-keyframe-summary",
                "ratings": {"identity_similarity": 4, "scene_continuity": 3},
                "drift_notes": "Use as safe evidence for the next local context overlay.",
            },
        },
    )
    response.raise_for_status()
    return response.json()


def _promote_candidate(client: TestClient, project_id: str, *, decision: str = "promote_to_context_overlay") -> dict:
    feedback_payload = _record_feedback(client, project_id)
    candidate = feedback_payload["feedback_event"]["feedback_candidate"]
    response = client.post(
        f"/projects/{project_id}/feedback-candidate-promotions",
        json={
            "feedback_artifact_id": feedback_payload["artifact"]["artifact_id"],
            "candidate_id": candidate["candidate_id"],
            "decision": decision,
            "rationale": "Reviewed as safe local feedback evidence.",
            "reviewed_at": "2026-06-30T12:10:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()


def test_runtime_feedback_candidate_context_overlay_records_safe_overlay(tmp_path) -> None:
    from agentflow import algorithms

    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "feedback-candidate-context-overlay-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback candidate overlay demo"}).raise_for_status()
    promotion_payload = _promote_candidate(client, project_id)
    promotion = promotion_payload["feedback_candidate_promotion_decision"]

    response = client.post(
        f"/projects/{project_id}/feedback-candidate-context-overlays",
        json={
            "promotion_decision_artifact_id": promotion_payload["artifact"]["artifact_id"],
            "overlay_intent": "Carry this reviewed feedback into the next local context pass.",
            "generated_at": "2026-06-30T12:20:00+08:00",
        },
    )
    response.raise_for_status()
    payload = response.json()
    overlay = payload["feedback_candidate_context_overlay"]
    overlay_effect = overlay["overlay"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert overlay["artifact_type"] == "agentflow_runtime_feedback_candidate_context_overlay"
    assert overlay["source_promotion_decision_id"] == promotion["decision_id"]
    assert overlay["source_promotion_decision_artifact_id"] == promotion_payload["artifact"]["artifact_id"]
    assert overlay["source_feedback_id"] == promotion["source_feedback_id"]
    assert overlay["source_feedback_artifact_id"] == promotion["source_feedback_artifact_id"]
    assert overlay["candidate_id"] == promotion["candidate_id"]
    assert overlay["candidate_scope"] == "quality_feedback_candidate"
    assert overlay["safe_target"] == promotion["safe_target"]
    assert overlay["target_binding"] == promotion["target_binding"]
    assert overlay["scope_policy"] == promotion["scope_policy"]
    assert overlay["conflict_summary"] == promotion["conflict_summary"]
    assert overlay["scope_policy"]["cross_project_reuse_allowed"] is False
    assert overlay["conflict_summary"]["global_rule_promotion_allowed"] is False
    assert overlay["safe_evidence_summary"] == promotion["safe_evidence_summary"]
    assert overlay["feedback_taxonomy"] == promotion["feedback_taxonomy"] == ["character", "scene"]
    assert overlay["safe_evidence_summary"]["taxonomy_count"] == 2
    assert overlay_effect["overlay_scope"] == "next_local_context_pass"
    assert overlay_effect["candidate_included_in_context"] is True
    assert overlay_effect["context_overlay_written"] is True
    assert overlay_effect["context_bundle_written"] is False
    assert overlay_effect["durable_memory_written"] is False
    assert overlay_effect["provider_calls_started"] is False
    assert overlay["writes_long_term_memory"] is False
    assert overlay["writes_company_kb"] is False
    assert payload["artifact"]["role"] == "runtime_feedback_candidate_context_overlay"
    assert payload["job"]["status"] == "succeeded"
    manifest = client.get(f"/projects/{project_id}/manifest").json()["manifest"]
    assert len(manifest["feedback_refs"]) == 3
    assert manifest["feedback_refs"][2]["feedback_id"] == overlay["overlay_id"]
    assert "provider_raw" not in serialized
    assert "signed" + "_url" not in serialized
    assert "d:\\private" not in serialized
    assert "feedback_candidate_context_overlay" in algorithms.CORE_AGENT_ALGORITHM_MODULES


def test_runtime_feedback_candidate_context_overlay_rejects_non_promoted_decision(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "feedback-candidate-overlay-rejected-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Rejected overlay demo"}).raise_for_status()
    promotion_payload = _promote_candidate(client, project_id, decision="reject")

    response = client.post(
        f"/projects/{project_id}/feedback-candidate-context-overlays",
        json={
            "promotion_decision_artifact_id": promotion_payload["artifact"]["artifact_id"],
            "overlay_intent": "This rejected candidate must not enter the local context pass.",
            "generated_at": "2026-06-30T12:25:00+08:00",
        },
    )

    assert response.status_code == 422


def test_runtime_feedback_candidate_context_overlay_rejects_unsafe_intent(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "feedback-candidate-overlay-unsafe-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Unsafe overlay demo"}).raise_for_status()
    promotion_payload = _promote_candidate(client, project_id)
    unsafe_local_path = f"{chr(68)}:{chr(92)}private{chr(92)}context.png"

    response = client.post(
        f"/projects/{project_id}/feedback-candidate-context-overlays",
        json={
            "promotion_decision_artifact_id": promotion_payload["artifact"]["artifact_id"],
            "overlay_intent": f"Use evidence from {unsafe_local_path}",
            "generated_at": "2026-06-30T12:30:00+08:00",
        },
    )

    assert response.status_code == 422
