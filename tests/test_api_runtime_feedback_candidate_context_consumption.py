from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import safe_id


def _record_context_overlay(
    client: TestClient,
    project_id: str,
    *,
    drift_notes: str = "Carry this reviewed note only as safe local context evidence.",
    overlay_intent: str = "Use this reviewed feedback as safe context evidence for the next local pass.",
) -> dict:
    feedback = client.post(
        "/feedback",
        json={
            "project_id": project_id,
            "generated_at": "2026-06-30T19:00:00+08:00",
            "feedback": {
                "kind": "studio_quality_feedback",
                "node_id": "image-node-feedback-context",
                "node_type": "image",
                "artifact_ref": "artifact-keyframe-summary",
                "ratings": {"identity_similarity": 4},
                "drift_notes": drift_notes,
            },
        },
    )
    feedback.raise_for_status()
    feedback_payload = feedback.json()
    candidate = feedback_payload["feedback_event"]["feedback_candidate"]

    promotion = client.post(
        f"/projects/{project_id}/feedback-candidate-promotions",
        json={
            "feedback_artifact_id": feedback_payload["artifact"]["artifact_id"],
            "candidate_id": candidate["candidate_id"],
            "decision": "promote_to_context_overlay",
            "rationale": "Reviewed for the next local context pass.",
            "reviewed_at": "2026-06-30T19:05:00+08:00",
        },
    )
    promotion.raise_for_status()

    overlay = client.post(
        f"/projects/{project_id}/feedback-candidate-context-overlays",
        json={
            "promotion_decision_artifact_id": promotion.json()["artifact"]["artifact_id"],
            "overlay_intent": overlay_intent,
            "generated_at": "2026-06-30T19:10:00+08:00",
        },
    )
    overlay.raise_for_status()
    return overlay.json()["feedback_candidate_context_overlay"]


def _keyframe_request() -> dict:
    return {
        "node_id": "keyframe-feedback-context",
        "prompt_text": "Draw the next keyframe after the reviewed feedback.",
        "optimized_prompt": "Cinematic keyframe after reviewed feedback.",
        "target_platform": "short_video",
        "style": "cinematic",
        "candidate_count": 1,
        "context_subgraph": {
            "target_node_id": "keyframe-feedback-context",
            "runtime_work_mode": "context_generate",
            "nodes": [
                {
                    "id": "keyframe-feedback-context",
                    "type": "image",
                    "title": "Target",
                    "prompt": "Draw the next keyframe.",
                    "visual_asset_ids": [],
                }
            ],
            "edges": [],
        },
        "generated_at": "2026-06-30T19:15:00+08:00",
    }


def _keyframe_request_with_overlay_decisions(decisions: list[dict]) -> dict:
    request = _keyframe_request()
    request["context_subgraph"]["nodes"][0]["node_parameters"] = {
        "feedback_context_overlay_decisions": decisions,
    }
    return request


def test_context_resolver_consumes_promoted_feedback_overlay_without_asset_inclusion(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_feedback_context_consumption"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback context consumption"}).raise_for_status()
    overlay = _record_context_overlay(client, project_id)

    preflight = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=_keyframe_request())
    preflight.raise_for_status()
    preflight_payload = preflight.json()
    bundle = preflight_payload["context_bundle"]
    context_overlays = bundle["feedback_context_overlays"]

    assert preflight_payload["provider_calls_started"] is False
    assert preflight_payload["included_assets"] == []
    assert preflight_payload["reference_image_channel"] == []
    assert preflight_payload["subject_reference_asset_id"] is None
    assert preflight_payload["feedback_context_overlays"] == context_overlays
    assert context_overlays[0]["overlay_id"] == overlay["overlay_id"]
    assert context_overlays[0]["candidate_id"] == overlay["candidate_id"]
    assert context_overlays[0]["feedback_taxonomy"] == overlay["feedback_taxonomy"] == ["character"]
    assert context_overlays[0]["scope_policy"]["global_scope_allowed"] is False
    assert context_overlays[0]["conflict_summary"]["cross_candidate_check_required"] is True
    assert context_overlays[0]["safe_evidence_summary"]["taxonomy_count"] == 1
    assert context_overlays[0]["context_overlay_consumed"] is True
    assert context_overlays[0]["provider_calls_started"] is False
    assert context_overlays[0]["writes_long_term_memory"] is False
    assert context_overlays[0]["writes_company_kb"] is False
    assert bundle["trace_summary"]["feedback_context_overlay_count"] == 1
    assert bundle["trace_summary"]["feedback_context_overlay_ids"] == [overlay["overlay_id"]]

    generation = client.post(f"/projects/{project_id}/keyframe-generations", json=_keyframe_request())
    generation.raise_for_status()
    generation_payload = generation.json()
    bridge = generation_payload["generation_bridge"]
    model_context_artifact_id = generation_payload["artifacts"]["model_call_context"]["artifact_id"]
    model_context = client.get(f"/artifacts/{model_context_artifact_id}").json()["payload"]
    serialized = json.dumps(generation_payload, ensure_ascii=False).lower()

    assert generation_payload["job"]["status"] == "blocked"
    assert generation_payload["provider_calls_started"] is False
    assert generation_payload["safe_manifest"]["provider_calls_started"] is False
    assert generation_payload["safe_manifest"]["context_feedback_overlay_count"] == 1
    assert generation_payload["context_bundle"]["feedback_context_overlays"][0]["overlay_id"] == overlay["overlay_id"]
    assert bridge["context_evidence"]["feedback_context_overlay_count"] == 1
    assert bridge["context_evidence"]["feedback_context_overlay_ids"] == [overlay["overlay_id"]]
    assert model_context["context_sources"]["feedback_context_overlay_count"] == 1
    assert model_context["feedback_context"]["context_overlays"][0]["overlay_id"] == overlay["overlay_id"]
    assert model_context["feedback_context"]["context_overlays"][0]["feedback_taxonomy"] == ["character"]
    assert model_context["feedback_context"]["context_overlays"][0]["scope_policy"]["global_scope_allowed"] is False
    assert model_context["feedback_context"]["context_overlays"][0]["conflict_summary"]["signal_count"] == 0
    assert model_context["feedback_context"]["feedback_is_memory"] is False
    assert model_context["safety_boundary"]["feedback_is_not_memory"] is True
    assert response_contains_unsafe_marker(context_overlays) is False
    assert response_contains_unsafe_marker(model_context["feedback_context"]["context_overlays"]) is False
    assert response_contains_unsafe_marker(bridge["context_evidence"]) is False
    assert "provider_raw" not in serialized
    assert "signed" + "_url" not in serialized
    assert "d:\\" not in serialized


def test_context_resolver_ignores_unreadable_feedback_overlay_refs(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_feedback_context_missing_ref"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback context missing ref"}).raise_for_status()
    manifest_path = tmp_path / "projects" / safe_id(project_id) / "project_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["feedback_refs"].append(
        {
            "artifact_id": "missing-feedback-context-overlay",
            "artifact_type": "agentflow_runtime_feedback_candidate_context_overlay",
            "filename": "missing.json",
            "feedback_id": "runtime-feedback-context-overlay:missing",
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    response = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=_keyframe_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_calls_started"] is False
    assert payload["included_assets"] == []
    assert payload["reference_image_channel"] == []
    assert payload["subject_reference_asset_id"] is None
    assert payload["feedback_context_overlays"] == []
    assert "feedback_context_overlays" not in payload["context_bundle"]


def test_context_resolver_applies_studio_feedback_overlay_selection_decisions(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_feedback_context_selection"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback context selection"}).raise_for_status()
    first = _record_context_overlay(client, project_id)
    second = _record_context_overlay(client, project_id)

    selected = client.post(
        f"/projects/{project_id}/keyframe-generations/preflight",
        json=_keyframe_request_with_overlay_decisions([
            {
                "overlay_id": first["overlay_id"],
                "decision": "include_for_next_context",
                "reviewed_at": "2026-06-30T20:00:00+08:00",
                "provider_calls_started": False,
                "writes_long_term_memory": False,
                "writes_company_kb": False,
            }
        ]),
    )
    selected.raise_for_status()
    selected_payload = selected.json()

    assert [item["overlay_id"] for item in selected_payload["feedback_context_overlays"]] == [first["overlay_id"]]
    assert selected_payload["context_bundle"]["trace_summary"]["feedback_context_overlay_selected_ids"] == [
        first["overlay_id"]
    ]
    assert selected_payload["provider_calls_started"] is False
    assert response_contains_unsafe_marker(selected_payload["feedback_context_overlays"]) is False

    rejected = client.post(
        f"/projects/{project_id}/keyframe-generations/preflight",
        json=_keyframe_request_with_overlay_decisions([
            {
                "overlay_id": first["overlay_id"],
                "decision": "reject_for_next_context",
                "reviewed_at": "2026-06-30T20:01:00+08:00",
                "provider_calls_started": False,
                "writes_long_term_memory": False,
                "writes_company_kb": False,
            }
        ]),
    )
    rejected.raise_for_status()
    rejected_payload = rejected.json()

    assert [item["overlay_id"] for item in rejected_payload["feedback_context_overlays"]] == [second["overlay_id"]]
    assert rejected_payload["context_bundle"]["trace_summary"]["feedback_context_overlay_rejected_ids"] == [
        first["overlay_id"]
    ]
    assert "provider_raw" not in json.dumps(rejected_payload, ensure_ascii=False).lower()


def test_selected_feedback_overlay_stays_out_of_provider_prompt_and_records_policy(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_feedback_context_prompt_policy"
    marker = "PROMPT_POLICY_MARKER_SHOULD_NOT_REACH_PROVIDER_PROMPT"
    client.post("/projects", json={"project_id": project_id, "goal": "Feedback prompt policy"}).raise_for_status()
    overlay = _record_context_overlay(
        client,
        project_id,
        drift_notes=f"Reviewed local note carrying {marker}.",
        overlay_intent=f"Keep {marker} as local context evidence only.",
    )
    request = _keyframe_request_with_overlay_decisions([
        {
            "overlay_id": overlay["overlay_id"],
            "decision": "include_for_next_context",
            "reviewed_at": "2026-06-30T20:05:00+08:00",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
    ])

    generation = client.post(f"/projects/{project_id}/keyframe-generations", json=request)
    generation.raise_for_status()
    payload = generation.json()
    request_plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    model_request_plan = client.get(f"/artifacts/{payload['artifacts']['model_request_plan']['artifact_id']}").json()["payload"]
    model_context = client.get(f"/artifacts/{payload['artifacts']['model_call_context']['artifact_id']}").json()["payload"]

    assert marker in json.dumps(payload["context_bundle"]["feedback_context_overlays"], ensure_ascii=False)
    assert marker not in request_plan["provider_prompt"]
    assert marker not in model_request_plan["provider_request"]["prompt"]
    assert payload["context_bundle"]["feedback_context_overlay_prompt_policy"][
        "provider_prompt_includes_context_overlays"
    ] is False
    assert model_context["feedback_context"]["prompt_policy"]["provider_prompt_includes_context_overlays"] is False
    assert model_context["feedback_context"]["prompt_policy"]["requires_explicit_prompt_policy_gate"] is True
    assert model_context["feedback_context"]["prompt_policy"]["context_overlay_count"] == 1
    assert model_request_plan["trace_summary"]["feedback_context_overlay_prompt_policy"][
        "provider_prompt_includes_context_overlays"
    ] is False
    assert payload["safe_manifest"]["feedback_context_overlay_prompt_policy"][
        "provider_prompt_includes_context_overlays"
    ] is False
    assert payload["generation_bridge"]["context_evidence"]["feedback_context_overlay_prompt_policy"][
        "provider_prompt_includes_context_overlays"
    ] is False
    for policy in (
        payload["context_bundle"]["feedback_context_overlay_prompt_policy"],
        model_context["feedback_context"]["prompt_policy"],
        model_request_plan["trace_summary"]["feedback_context_overlay_prompt_policy"],
        payload["safe_manifest"]["feedback_context_overlay_prompt_policy"],
        payload["generation_bridge"]["context_evidence"]["feedback_context_overlay_prompt_policy"],
    ):
        gate = policy["prompt_provider_gate"]
        assert gate["status"] == "blocked_by_default"
        assert gate["provider_prompt_inclusion_allowed"] is False
        assert gate["requires_human_approval"] is True
        assert gate["requires_provider_gate"] is True
    assert payload["provider_calls_started"] is False
