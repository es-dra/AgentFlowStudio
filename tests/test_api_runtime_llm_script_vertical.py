from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.openapi_export import export_openapi_schema
from apps.api.runtime_service import create_runtime_app


def test_llm_script_plan_is_gate_closed_safe_and_review_reusable(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.setenv("AFS_ENABLE_LEGACY_RUNTIME_V02", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_script_vertical",
            "project_type": "short_video_campaign",
            "goal": "Create a launch video for a local-safe planning tool.",
        },
    )
    review = client.post(
        "/projects/proj_script_vertical/review-decisions",
        json={
            "card_id": "script-card-001",
            "candidate_id": "candidate-script-001",
            "decision": "revise",
            "note": "Make the opening more specific and keep claims evidence-bound.",
            "generated_at": "2026-06-10T20:08:00+08:00",
        },
    ).json()

    result = client.post(
        "/provider/script-draft-plan",
        json={
            "project_id": "proj_script_vertical",
            "goal": "Draft a 45 second script and storyboard for a local-safe planning tool.",
            "target_platform": "douyin",
            "style": "clear_demo",
            "review_feedback_artifact_id": review["artifact"]["artifact_id"],
            "generated_at": "2026-06-10T20:10:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    job = payload["job"]
    safe_manifest_ref = payload["artifacts"]["script_provider_safe_manifest"]
    plan_ref = payload["artifacts"]["llm_script_request_plan"]
    script_ref = payload["artifacts"]["script_storyboard_safe_artifact"]

    assert job["action"] == "llm_script_draft_plan"
    assert job["status"] == "blocked"
    assert job["progress"] == {"stage": "llm_script_draft_plan", "percent": 100, "terminal": True}
    assert payload["provider_gate"] == {
        "capability": "llm",
        "env": "AFS_ALLOW_REMOTE_LLM",
        "status": "blocked",
    }
    assert payload["provider_calls_started"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["writes_company_kb"] is False
    assert "not provider smoke" in payload["non_claims"]

    safe_manifest = client.get(f"/artifacts/{safe_manifest_ref['artifact_id']}").json()["payload"]
    plan = client.get(f"/artifacts/{plan_ref['artifact_id']}").json()["payload"]
    script_artifact = client.get(f"/artifacts/{script_ref['artifact_id']}").json()["payload"]
    serialized = json.dumps(
        {
            "response": payload,
            "safe_manifest": safe_manifest,
            "plan": plan,
            "script_artifact": script_artifact,
        },
        ensure_ascii=False,
    ).lower()

    assert safe_manifest["status"] == "blocked"
    assert safe_manifest["provider_calls_started"] is False
    assert safe_manifest["raw_provider_response_stored"] is False
    assert safe_manifest["generated_media_bytes_stored"] is False
    assert safe_manifest["blocks"][0]["block_id"] == "remote_llm_gate_closed"
    assert plan["feedback_reuse"]["source_artifact_id"] == review["artifact"]["artifact_id"]
    assert plan["feedback_reuse"]["policy"] == "candidate_constraints_only"
    assert script_artifact["provider_output"] is False
    assert script_artifact["local_draft"]["source"] == "local_deterministic_script_draft"
    assert script_artifact["local_draft"]["remote_provider_calls_started"] is False
    assert script_artifact["scripts"][0]["project_id"] == "proj_script_vertical"
    assert "local-safe planning tool" in json.dumps(script_artifact["scripts"][0], ensure_ascii=False).lower()
    assert script_artifact["review_actions"] == ["keep", "revise", "reject"]
    assert "api_key" not in serialized
    assert "bearer " not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert "data/processed/runs" not in serialized


def test_llm_script_plan_reuses_prior_script_feedback_as_candidate_constraints(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.setenv("AFS_ENABLE_LEGACY_RUNTIME_V02", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_script_second_round",
            "project_type": "short_video_campaign",
            "goal": "Create a short video for a quiet AI workbench.",
        },
    )
    first = client.post(
        "/provider/script-draft-plan",
        json={
            "project_id": "proj_script_second_round",
            "goal": "Create a 30 second script for a quiet AI workbench.",
            "target_platform": "douyin",
            "style": "calm_product_demo",
            "generated_at": "2026-06-11T09:00:00+08:00",
        },
    ).json()
    first_script_ref = first["artifacts"]["script_storyboard_safe_artifact"]
    review = client.post(
        "/projects/proj_script_second_round/review-decisions",
        json={
            "card_id": "script-card-001",
            "candidate_id": "candidate-script-001",
            "artifact_id": first_script_ref["artifact_id"],
            "decision": "revise",
            "note": "Keep the tone calm, remove exaggerated claims, and make the evidence gate visible.",
            "generated_at": "2026-06-11T09:05:00+08:00",
        },
    ).json()

    second = client.post(
        "/provider/script-draft-plan",
        json={
            "project_id": "proj_script_second_round",
            "goal": "Revise the 30 second script for a quiet AI workbench.",
            "target_platform": "douyin",
            "style": "calm_product_demo",
            "previous_script_artifact_id": first_script_ref["artifact_id"],
            "review_feedback_artifact_id": review["artifact"]["artifact_id"],
            "generated_at": "2026-06-11T09:10:00+08:00",
        },
    ).json()

    script_ref = second["artifacts"]["script_storyboard_safe_artifact"]
    plan_ref = second["artifacts"]["llm_script_request_plan"]
    script_artifact = client.get(f"/artifacts/{script_ref['artifact_id']}").json()["payload"]
    plan = client.get(f"/artifacts/{plan_ref['artifact_id']}").json()["payload"]

    assert script_artifact["local_draft"]["iteration"] == 2
    assert script_artifact["candidate_constraints"]["previous_script_artifact_id"] == first_script_ref["artifact_id"]
    assert script_artifact["candidate_constraints"]["review_feedback_artifact_id"] == review["artifact"]["artifact_id"]
    assert script_artifact["candidate_constraints"]["review_note"] == (
        "Keep the tone calm, remove exaggerated claims, and make the evidence gate visible."
    )
    assert plan["feedback_reuse"]["constraint_note"] == script_artifact["candidate_constraints"]["review_note"]
    assert script_artifact["remote_provider_calls_started"] is False
    assert script_artifact["writes_long_term_memory"] is False
    assert script_artifact["writes_company_kb"] is False


def test_llm_script_plan_exports_openapi_without_provider_secret_surface(tmp_path) -> None:
    output_path = tmp_path / "frontend" / "afs-runtime-service.openapi.json"
    exported_path = export_openapi_schema(output_path, runtime_root=tmp_path / "openapi_runtime")
    schema = json.loads(exported_path.read_text(encoding="utf-8"))
    serialized = json.dumps(schema, ensure_ascii=False).lower()

    assert "/provider/script-draft-plan" in schema["paths"]
    assert "providerscriptdraftplanrequest" in serialized
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
