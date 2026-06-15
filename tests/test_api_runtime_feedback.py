from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_runtime_feedback_recording_sanitizes_and_whitelists_payload(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "feedback-safety-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback safety demo"}).raise_for_status()

    response = client.post(
        "/feedback",
        json={
            "project_id": project_id,
            "generated_at": "2026-06-15T12:00:00+08:00",
            "feedback": {
                "kind": "studio_quality_feedback",
                "node_id": "video-node-001",
                "node_type": "video",
                "video_job_id": "job-001",
                "artifact_ref": "artifact-001",
                "safe_preview_ref": "http://signed.example.test/video.mp4?token=secret",
                "ratings": {"identity_similarity": 5, "scene_continuity": 4, "extra_metric": 9},
                "target_change_success": 3,
                "drift_notes": r"Bearer abc123 D:\private\shot.png https://signed.example.test/a?sig=secret keep note",
                "provider_raw": {"api_key": "secret"},
                "local_path": r"D:\private\asset.png",
                "preview_url": "https://signed.example.test/preview",
                "prompt_text": "do not persist prompt text",
                "unknown": "drop me",
            },
        },
    )
    response.raise_for_status()
    event = response.json()["feedback_event"]
    feedback = event["feedback"]
    serialized = json.dumps(event, ensure_ascii=False).lower()

    assert feedback == {
        "kind": "studio_quality_feedback",
        "node_id": "video-node-001",
        "node_type": "video",
        "video_job_id": "job-001",
        "video_revision_job_id": "",
        "artifact_ref": "artifact-001",
        "safe_preview_ref": "none",
        "ratings": {"identity_similarity": 5, "scene_continuity": 4},
        "target_change_success": 3,
        "drift_notes": "Bearer <redacted> <local-path-redacted> <url-redacted> keep note",
        "prompt_char_count": 0,
        "result_char_count": 0,
        "raw_evidence_policy": "raw_evidence_not_memory",
        "feedback_is_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "safety_boundary": {
            "no_provider_raw": True,
            "no_signed_url": True,
            "no_local_path": True,
            "no_media_bytes": True,
        },
    }
    for forbidden in ("provider_raw", "local_path", "preview_url", "prompt_text", "unknown"):
        assert forbidden not in feedback
    for forbidden in ("api_key", "signed.example", "secret"):
        assert forbidden not in serialized
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
