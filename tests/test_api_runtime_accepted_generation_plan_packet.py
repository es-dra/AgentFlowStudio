from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


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
    assert payload["job"]["status"] == "succeeded"

    artifact_payload = client.get(f"/artifacts/{payload['artifact']['artifact_id']}").json()["payload"]
    assert artifact_payload["operator_evidence"]["state"]["accepted"] is False
    _assert_no_claim_leaks(payload)
    _assert_no_claim_leaks(artifact_payload)


def test_runtime_generation_plan_preview_requires_explicit_confirmed_fixture_for_acceptance(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "accepted-plan-confirmed"
    client.post("/projects", json={"project_id": project_id, "goal": "Accepted plan preview"}).raise_for_status()

    default_payload = client.post(f"/projects/{project_id}/accepted-generation-plan-packets/preview", json={}).json()
    accepted_payload = client.post(
        f"/projects/{project_id}/accepted-generation-plan-packets/preview",
        json={"fixture_mode": "confirmed_local_fixture"},
    ).json()

    assert default_payload["packet"]["accepted"] is False
    assert accepted_payload["packet"]["packet_state"] == "accepted_local_generation_plan_packet"
    assert accepted_payload["packet"]["accepted"] is True
    assert accepted_payload["operator_evidence"]["provenance"]["fixture_mode"] == "confirmed_local_fixture"
    assert accepted_payload["operator_evidence"]["state"]["request_state"] == "accepted_provider_closed_plan"
    assert accepted_payload["operator_evidence"]["residual_blockers"]["blocked_reasons"] == []
    assert accepted_payload["operator_evidence"]["residual_blockers"]["pending_branch_asset_refs"] == []
    assert accepted_payload["operator_evidence"]["residual_blockers"]["residual_closure_refs"] == [
        "residual_closure:branch-specific-assets-confirmed",
        "residual_closure:pb3-boundary-owner-accepted",
    ]
    assert accepted_payload["operator_evidence"]["non_claim_boundaries"]["provider_calls_started"] is False
    assert accepted_payload["operator_evidence"]["non_claim_boundaries"]["generated_media"] is False
    assert accepted_payload["operator_evidence"]["non_claim_boundaries"]["product_readiness"] is False
    _assert_no_claim_leaks(accepted_payload)


def test_runtime_generation_plan_preview_rejects_unknown_fixture_mode(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "accepted-plan-invalid"
    client.post("/projects", json={"project_id": project_id, "goal": "Accepted plan preview"}).raise_for_status()

    response = client.post(
        f"/projects/{project_id}/accepted-generation-plan-packets/preview",
        json={"fixture_mode": "auto_accept_local_bundle"},
    )

    assert response.status_code == 422


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
