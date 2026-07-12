from __future__ import annotations

import json

from fastapi.testclient import TestClient

from agentflow.harness.json_io import write_json
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


def test_runtime_generation_plan_preview_is_blocked_by_default(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "accepted-plan-default"
    client.post("/projects", json={"project_id": project_id, "goal": "Accepted plan preview"}).raise_for_status()

    response = client.post(f"/projects/{project_id}/accepted-generation-plan-packets/preview", json={})

    response.raise_for_status()
    payload = response.json()
    packet = payload["packet"]
    evidence = payload["operator_evidence"]

    assert packet["packet_state"] == "blocked_pending_generation_plan_prerequisites"
    assert packet["accepted"] is False
    assert evidence["state"]["packet_state"] == "blocked_pending_generation_plan_prerequisites"
    assert evidence["state"]["accepted"] is False
    assert evidence["provenance"]["fixture_mode"] == "default_unconfirmed"
    assert evidence["provenance"]["evidence_origin"] == "repo_local_fixture"
    assert evidence["residual_blockers"]["blocked_reasons"]
    assert evidence["residual_blockers"]["pending_branch_asset_refs"] == [
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]
    assert "not_provider_smoke" in evidence["non_claim_boundaries"]["explicit_non_claims"]
    assert evidence["non_claim_boundaries"]["provider_calls_started"] is False
    assert evidence["non_claim_boundaries"]["generated_media"] is False
    assert evidence["non_claim_boundaries"]["product_readiness"] is False
    assert payload["job"]["action"] == "accepted_generation_plan_packet_preview"
    assert payload["job"]["status"] == "blocked"
    assert payload["preview_status"] == "blocked"

    artifact_payload = client.get(f"/artifacts/{payload['artifact']['artifact_id']}").json()["payload"]
    assert artifact_payload["operator_evidence"]["state"]["accepted"] is False
    manifest = client.get(f"/projects/{project_id}/manifest").json()["manifest"]
    assert manifest["status"] == "blocked"
    assert manifest["accepted_generation_plan_refs"][0]["workflow_status"] == "blocked"
    assert manifest["accepted_generation_plan_refs"][0]["accepted"] is False
    assert manifest["accepted_generation_plan_refs"][0]["human_creative_acceptance_claimed"] is False
    _assert_no_claim_leaks(payload)
    _assert_no_claim_leaks(artifact_payload)


def test_runtime_generation_plan_confirmed_fixture_remains_non_acceptance_demo(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "accepted-plan-confirmed"
    client.post("/projects", json={"project_id": project_id, "goal": "Accepted plan preview"}).raise_for_status()

    default_payload = client.post(f"/projects/{project_id}/accepted-generation-plan-packets/preview", json={}).json()
    fixture_payload = client.post(
        f"/projects/{project_id}/accepted-generation-plan-packets/preview",
        json={"fixture_mode": "confirmed_local_fixture"},
    ).json()

    assert default_payload["packet"]["accepted"] is False
    assert fixture_payload["packet"]["packet_state"] == "fixture_demo_non_acceptance"
    assert fixture_payload["packet"]["accepted"] is False
    assert fixture_payload["job"]["status"] == "blocked"
    assert fixture_payload["preview_status"] == "blocked"
    assert fixture_payload["operator_evidence"]["provenance"]["fixture_mode"] == "confirmed_local_fixture"
    assert fixture_payload["operator_evidence"]["provenance"]["fixture_demo_non_acceptance"] is True
    assert fixture_payload["operator_evidence"]["residual_blockers"]["blocked_reasons"] == [
        "fixture_demo_requires_project_human_gate_decision",
    ]
    assert "fixture_demo_not_acceptance" in fixture_payload["operator_evidence"]["non_claim_boundaries"]["explicit_non_claims"]
    _assert_no_claim_leaks(fixture_payload)


def test_runtime_generation_plan_project_source_requires_local_human_gate_for_acceptance(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "accepted-plan-project-source"
    client.post("/projects", json={"project_id": project_id, "goal": "Accepted plan preview"}).raise_for_status()
    source_artifact = _register_project_plan_source(tmp_path, project_id, accepted=True)

    missing_gate = client.post(
        f"/projects/{project_id}/accepted-generation-plan-packets/preview",
        json={"source_artifact_id": source_artifact["artifact_id"]},
    )
    assert missing_gate.status_code == 422

    gate_response = client.post(
        f"/projects/{project_id}/human-gate-decisions",
        json={
            "target_type": "accepted_generation_plan_packet",
            "target_id": source_artifact["artifact_id"],
            "decision": "accepted_for_next_step",
            "artifact_id": source_artifact["artifact_id"],
            "scope": "accepted_generation_plan_packet_review",
            "note": "Local plan packet can move to evaluator review; no creative acceptance claimed.",
            "reviewed_at": "2026-07-02T10:30:00+08:00",
        },
    )
    gate_response.raise_for_status()
    human_gate_id = gate_response.json()["human_gate_decision"]["human_gate_id"]

    accepted = client.post(
        f"/projects/{project_id}/accepted-generation-plan-packets/preview",
        json={"source_artifact_id": source_artifact["artifact_id"], "source_human_gate_id": human_gate_id},
    )
    accepted.raise_for_status()
    payload = accepted.json()

    assert payload["packet"]["accepted"] is True
    assert payload["job"]["status"] == "succeeded"
    assert payload["preview_status"] == "succeeded"
    assert payload["operator_evidence"]["provenance"]["source_mode"] == "project_artifact"
    assert payload["operator_evidence"]["provenance"]["source_artifact_id"] == source_artifact["artifact_id"]
    assert payload["operator_evidence"]["provenance"]["source_human_gate_id"] == human_gate_id
    assert payload["operator_evidence"]["state"]["workflow_status"] == "accepted"
    assert "project_step_gate_not_creative_acceptance" in payload["operator_evidence"]["non_claim_boundaries"]["explicit_non_claims"]
    manifest = client.get(f"/projects/{project_id}/manifest").json()["manifest"]
    ref = manifest["accepted_generation_plan_refs"][-1]
    assert ref["workflow_status"] == "accepted"
    assert ref["source_artifact_id"] == source_artifact["artifact_id"]
    assert ref["source_human_gate_id"] == human_gate_id
    assert ref["human_creative_acceptance_claimed"] is False
    _assert_no_claim_leaks(payload)


def test_runtime_generation_plan_project_source_rejects_accepted_repo_fixture_artifact(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "accepted-plan-unsafe-source"
    client.post("/projects", json={"project_id": project_id, "goal": "Accepted plan preview"}).raise_for_status()
    source_artifact = _register_project_plan_source(tmp_path, project_id, accepted=True, evidence_origin="repo_local_fixture")

    response = client.post(
        f"/projects/{project_id}/accepted-generation-plan-packets/preview",
        json={"source_artifact_id": source_artifact["artifact_id"], "source_human_gate_id": "runtime-human-gate:fake"},
    )

    assert response.status_code == 422


def test_runtime_generation_plan_project_source_rejects_missing_artifact(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "accepted-plan-missing-source"
    client.post("/projects", json={"project_id": project_id, "goal": "Accepted plan preview"}).raise_for_status()

    response = client.post(
        f"/projects/{project_id}/accepted-generation-plan-packets/preview",
        json={"source_artifact_id": "runs-accepted-plan-missing-source-does-not-exist"},
    )

    assert response.status_code == 422


def test_runtime_generation_plan_preview_rejects_unknown_fixture_mode(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "accepted-plan-invalid"
    client.post("/projects", json={"project_id": project_id, "goal": "Accepted plan preview"}).raise_for_status()

    response = client.post(
        f"/projects/{project_id}/accepted-generation-plan-packets/preview",
        json={"fixture_mode": "auto_accept_local_bundle"},
    )

    assert response.status_code == 422


def _register_project_plan_source(
    runtime_root,
    project_id: str,
    *,
    accepted: bool,
    evidence_origin: str = "project_local_step_gate",
) -> dict[str, str]:
    store = RuntimeStore(runtime_root)
    output_dir = store.run_dir(project_id, "accepted-plan-source")
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "agentflow_project_accepted_generation_plan_source",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "accepted_generation_plan_packet": {
            "packet_state": "accepted_project_generation_plan_packet" if accepted else "blocked_project_generation_plan_packet",
            "accepted": accepted,
            "generation_request_plan": {
                "request_state": "accepted_provider_closed_plan" if accepted else "blocked_provider_closed_plan",
                "provider_gate": "closed",
            },
            "evidence_origin": evidence_origin,
            "claim_level": "local_step_gate_evidence_only",
            "generation_planning_candidate_ref": "generation_plan:project-local",
            "fixed_asset_confirmation_evidence_ref": "evidence:project-fixed-assets",
            "blocked_reasons": [] if accepted else ["project_plan_prerequisites_missing"],
            "residual_closure_refs": ["residual_closure:project-plan-local-step-gate"] if accepted else [],
            "close_condition_refs": ["close_condition:project-plan-local-step-gate"],
            "non_claim_boundary": {
                "provider_smoke": False,
                "generated_media_quality": False,
                "human_creative_acceptance": False,
                "business_validation": False,
                "product_readiness": False,
            },
        },
    }
    path = write_json(output_dir / "accepted_generation_plan_source.json", payload)
    return store.register_artifact(path, role="accepted_generation_plan_packet_source")


def _assert_no_claim_leaks(payload: object) -> None:
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    forbidden_true_claims = (
        '"provider_calls_started": true',
        '"generated_media": true',
        '"product_readiness": true',
        '"provider_smoke_claimed": true',
        '"generated_media_quality_claimed": true',
        '"human_creative_acceptance": true',
        '"business_validation": true',
    )
    for fragment in forbidden_true_claims:
        assert fragment not in serialized
    assert "signed_url" not in serialized
    assert "provider_raw" not in serialized
    assert "data_base64" not in serialized
