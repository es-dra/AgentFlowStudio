from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_studio_state import sanitize_studio_state


def test_studio_state_preserves_safe_feedback_context_overlay_summary() -> None:
    sanitized = sanitize_studio_state({"nodes": {"image_1": _overlay_node()}})

    overlays = sanitized["nodes"]["image_1"]["params"]["lastContextBundle"]["feedback_context_overlays"]
    policy = sanitized["nodes"]["image_1"]["params"]["lastContextBundle"]["feedback_context_overlay_prompt_policy"]
    overlay = overlays[0]
    serialized = str(sanitized).lower()
    assert overlay["overlay_id"] == "runtime-feedback-overlay:abc123"
    assert overlay["candidate_id"] == "runtime-feedback-candidate:feedback001"
    assert overlay["safe_target"]["node_id"] == "image_1"
    assert overlay["safe_evidence_summary"]["raw_evidence_policy"] == "raw_evidence_not_memory"
    assert overlay["safe_evidence_summary"]["taxonomy_count"] == 2
    assert overlay["feedback_taxonomy"] == ["character", "scene"]
    assert overlay["context_overlay_consumed"] is True
    assert overlay["provider_calls_started"] is False
    assert overlay["writes_long_term_memory"] is False
    assert overlay["writes_company_kb"] is False
    assert overlay["artifact_ref"]["artifact_id"] == "artifact_feedback_overlay_001"
    assert policy["policy_id"] == "feedback_overlay_context_evidence_only_v0"
    assert policy["provider_prompt_includes_context_overlays"] is False
    assert policy["requires_explicit_prompt_policy_gate"] is True
    assert policy["context_overlay_count"] == 1
    assert policy["selected_overlay_ids"] == ["runtime-feedback-overlay:abc123"]
    assert policy["prompt_provider_gate"]["status"] == "blocked_by_default"
    assert policy["prompt_provider_gate"]["provider_prompt_inclusion_allowed"] is False
    assert policy["prompt_provider_gate"]["requires_human_approval"] is True
    assert "safety_boundary" not in overlay
    assert "trace_summary" not in overlay
    assert "provider_raw" not in overlay
    assert "local_path" not in overlay
    assert "signed_url" not in overlay
    assert "provider_raw" not in policy["prompt_provider_gate"]
    assert "signed_url" not in policy["prompt_provider_gate"]
    assert "media_bytes" not in serialized
    assert "d:\\private" not in serialized
    assert "unsafe-signed-reference-redacted" not in serialized


def test_studio_state_persists_feedback_context_overlay_summary_only(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-feedback-overlay"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio feedback overlay persistence"})

    saved = client.put(
        f"/projects/{project_id}/studio-state",
        json={"state": {"nodes": {"image_1": _overlay_node()}, "order": ["image_1"]}},
    )

    assert saved.status_code == 200
    restored = client.get(f"/projects/{project_id}/studio-state").json()["state"]
    overlays = restored["nodes"]["image_1"]["params"]["lastContextBundle"]["feedback_context_overlays"]
    policy = restored["nodes"]["image_1"]["params"]["lastContextBundle"]["feedback_context_overlay_prompt_policy"]
    serialized = str(restored).lower()
    assert overlays[0]["overlay_id"] == "runtime-feedback-overlay:abc123"
    assert overlays[0]["candidate_id"] == "runtime-feedback-candidate:feedback001"
    assert overlays[0]["safe_target"]["node_id"] == "image_1"
    assert overlays[0]["feedback_taxonomy"] == ["character", "scene"]
    assert overlays[0]["context_overlay_consumed"] is True
    assert overlays[0]["provider_calls_started"] is False
    assert overlays[0]["writes_long_term_memory"] is False
    assert overlays[0]["writes_company_kb"] is False
    assert policy["provider_prompt_includes_context_overlays"] is False
    assert policy["overlay_text_channel"] == "disabled_by_default"
    assert policy["prompt_provider_gate"]["provider_prompt_inclusion_allowed"] is False
    assert policy["prompt_provider_gate"]["requires_provider_gate"] is True
    assert "safety_boundary" not in overlays[0]
    assert "provider_raw" not in overlays[0]
    assert "trace_summary" not in overlays[0]
    assert "local_path" not in overlays[0]
    assert "media_bytes" not in serialized
    assert "d:\\private" not in serialized


def test_studio_state_persists_feedback_overlay_decisions_as_safe_node_params(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-feedback-overlay-decisions"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio feedback overlay decisions"})

    state = {
        "nodes": {
            "image_1": {
                "type": "image",
                "params": {
                    "feedbackOverlayDecisions": [
                        {
                            "overlay_id": "runtime-feedback-overlay:abc123",
                            "candidate_id": "runtime-feedback-candidate:feedback001",
                            "decision": "reject_for_next_context",
                            "reviewed_at": "2026-06-30T20:01:00+08:00",
                            "provider_calls_started": True,
                            "writes_long_term_memory": True,
                            "writes_company_kb": True,
                            "provider_raw": {"unsafe": True},
                            "local_path": "D:\\private\\feedback.png",
                        }
                    ]
                },
            }
        },
        "order": ["image_1"],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})

    assert saved.status_code == 200
    decisions = saved.json()["state"]["nodes"]["image_1"]["params"]["feedbackOverlayDecisions"]
    serialized = str(decisions).lower()
    assert decisions == [
        {
            "overlay_id": "runtime-feedback-overlay:abc123",
            "candidate_id": "runtime-feedback-candidate:feedback001",
            "decision": "reject_for_next_context",
            "reviewed_at": "2026-06-30T20:01:00+08:00",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
    ]
    assert "provider_raw" not in serialized
    assert "local_path" not in serialized
    assert "d:\\private" not in serialized


def _overlay_node() -> dict:
    return {
        "type": "image",
        "title": "feedback context target",
        "params": {
            "lastContextBundle": {
                "feedback_context_overlays": [
                    {
                        "overlay_id": "runtime-feedback-overlay:abc123",
                        "source_feedback_id": "runtime-feedback:project:feedback001",
                        "source_promotion_decision_id": "runtime-feedback-promotion:decision001",
                        "candidate_id": "runtime-feedback-candidate:feedback001",
                        "candidate_scope": "quality_feedback_candidate",
                        "safe_target": {"kind": "studio_quality_feedback", "node_id": "image_1"},
                        "safe_evidence_summary": {
                            "rating_count": 1,
                            "decision_count": 2,
                            "has_note": True,
                            "taxonomy_count": 2,
                            "raw_evidence_policy": "raw_evidence_not_memory",
                        },
                        "feedback_taxonomy": ["character", "scene"],
                        "overlay_scope": "next_local_context_pass",
                        "overlay_intent": "Use reviewed feedback only as safe local context.",
                        "decision_effect": "included_in_context",
                        "context_overlay_consumed": True,
                        "candidate_feedback_included_in_context": True,
                        "provider_calls_started": False,
                        "writes_long_term_memory": False,
                        "writes_company_kb": False,
                        "safety_boundary": {
                            "raw_provider_response_stored": False,
                            "external_private_link_stored": False,
                            "absolute_path_stored": False,
                            "media_bytes_stored": False,
                        },
                        "artifact_ref": {
                            "artifact_id": "artifact_feedback_overlay_001",
                            "artifact_type": "agentflow_runtime_feedback_candidate_context_overlay",
                            "role": "runtime_feedback_candidate_context_overlay",
                            "filename": "runtime_feedback_candidate_context_overlay.json",
                        },
                        "trace_summary": {"unsafe": "not persisted"},
                        "provider_raw": {"unsafe": True},
                        "local_path": "D:\\private\\feedback.png",
                        "signed_url": "unsafe-signed-reference-redacted",
                    }
                ],
                "feedback_context_overlay_prompt_policy": {
                    "schema_version": "afs_feedback_overlay_prompt_policy.v0.1",
                    "policy_id": "feedback_overlay_context_evidence_only_v0",
                    "default_action": "context_evidence_only",
                    "provider_prompt_includes_context_overlays": False,
                    "overlay_text_channel": "disabled_by_default",
                    "requires_explicit_prompt_policy_gate": True,
                    "prompt_provider_gate": {
                        "gate_id": "feedback_overlay_provider_prompt_gate_v0",
                        "status": "blocked_by_default",
                        "provider_prompt_inclusion_allowed": False,
                        "requires_human_approval": True,
                        "requires_provider_gate": True,
                        "requires_prompt_budget_review": True,
                        "requires_safety_filter": True,
                        "gate_record_ref": "not_approved",
                        "provider_raw": {"unsafe": True},
                        "signed_url": "unsafe-signed-reference-redacted",
                    },
                    "context_overlay_count": 1,
                    "selected_overlay_ids": ["runtime-feedback-overlay:abc123"],
                    "rejected_overlay_ids": [],
                    "provider_raw": {"unsafe": True},
                    "signed_url": "unsafe-signed-reference-redacted",
                },
                "trace_summary": {
                    "feedback_context_overlay_prompt_policy": {
                        "policy_id": "unsafe-trace-policy",
                        "provider_prompt_includes_context_overlays": True,
                    }
                },
            }
        },
    }
