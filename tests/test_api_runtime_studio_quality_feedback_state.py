from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_studio_state import sanitize_studio_state


def test_studio_state_persists_quality_feedback_candidate_summary_only(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-quality-feedback-candidates"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio quality feedback candidates"})

    state = _quality_feedback_candidate_state()
    sanitized_state = sanitize_studio_state(state)
    candidates = sanitized_state["nodes"]["image_1"]["params"]["qualityFeedbackCandidates"]
    serialized = str(candidates).lower()
    assert "raw_feedback" not in serialized
    assert "provider_raw" not in serialized
    assert "local_path" not in serialized
    assert "signed_url" not in serialized
    assert "d:\\private" not in serialized

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": sanitized_state})

    assert saved.status_code == 200
    candidates = saved.json()["state"]["nodes"]["image_1"]["params"]["qualityFeedbackCandidates"]
    serialized = str(candidates).lower()
    assert candidates == [
        {
            "feedback_id": "runtime-feedback:project:001",
            "feedback_artifact_id": "artifact_feedback_001",
            "candidate_id": "runtime-feedback-candidate:001",
            "candidate_scope": "quality_feedback_candidate",
            "context_overlay_requested": True,
            "promotion_decision_id": "promotion_decision_001",
            "promotion_artifact_id": "artifact_promotion_001",
            "context_overlay_id": "runtime-feedback-overlay:001",
            "context_overlay_artifact_id": "artifact_overlay_001",
            "status": "context_overlay_recorded",
            "recorded_at": "2026-06-30T21:00:00+08:00",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
    ]
    assert "raw_feedback" not in serialized
    assert "provider_raw" not in serialized
    assert "local_path" not in serialized
    assert "signed_url" not in serialized
    assert "d:\\private" not in serialized


def test_quality_feedback_candidate_state_rejects_provider_raw() -> None:
    with pytest.raises(ValueError, match="provider_raw"):
        sanitize_studio_state(
            {
                "nodes": {
                    "image_1": {
                        "type": "image",
                        "params": {
                            "qualityFeedbackCandidates": [
                                {
                                    "candidate_id": "runtime-feedback-candidate:001",
                                    "provider_raw": {"unsafe": True},
                                }
                            ]
                        },
                    }
                }
            }
        )


def _quality_feedback_candidate_state() -> dict:
    return {
        "nodes": {
            "image_1": {
                "type": "image",
                "params": {
                    "qualityFeedbackCandidates": [
                        {
                            "feedback_id": "runtime-feedback:project:001",
                            "feedback_artifact_id": "artifact_feedback_001",
                            "candidate_id": "runtime-feedback-candidate:001",
                            "candidate_scope": "quality_feedback_candidate",
                            "context_overlay_requested": True,
                            "promotion_decision_id": "promotion_decision_001",
                            "promotion_artifact_id": "artifact_promotion_001",
                            "context_overlay_id": "runtime-feedback-overlay:001",
                            "context_overlay_artifact_id": "artifact_overlay_001",
                            "status": "context_overlay_recorded",
                            "recorded_at": "2026-06-30T21:00:00+08:00",
                            "provider_calls_started": True,
                            "writes_long_term_memory": True,
                            "writes_company_kb": True,
                            "raw_feedback": {"drift_notes": "do not persist raw text"},
                        }
                    ]
                },
            }
        },
        "order": ["image_1"],
    }
