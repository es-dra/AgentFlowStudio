from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "afs_keyframe_local_edit_request.v0.1",
        "request_id": "kle_test_001",
        "target_node_id": "keyframe_001",
        "parent_lineage": {
            "immutable_parent": True,
            "parent_node_id": "keyframe_001",
            "parent_keyframe_job_id": "kg_job_001",
            "parent_image_asset_id": "img_asset_001",
            "parent_candidate_id": "candidate_001",
            "parent_preview_url_present": True,
        },
        "edit_intent": "Only cool the window light while preserving the character and composition.",
        "edit_scope": {"kind": "semantic_region", "target_description": "left window light area"},
        "preserve_locks": ["character_identity", "scene_layout", "camera_angle"],
        "negative_locks": ["do not redraw the full frame"],
        "fallback_policy": {
            "allow_full_frame_fallback": False,
            "fallback_truth_label": "not_allowed_in_first_slice",
            "user_confirmation_required": True,
        },
        "provider_capability_mode": "no_provider_execution",
        "created_at": "2026-07-06T00:00:00.000Z",
        "updated_at": "2026-07-06T00:00:00.000Z",
    }
    payload.update(overrides)
    return payload


def test_keyframe_local_edit_preflight_validates_existing_draft_without_execution(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "local-edit-preflight"
    request = _request()

    first = client.post(f"/projects/{project_id}/keyframe-local-edits/preflight", json=request)
    second = client.post(f"/projects/{project_id}/keyframe-local-edits/preflight", json=request)
    changed = client.post(
        f"/projects/{project_id}/keyframe-local-edits/preflight",
        json={**request, "edit_intent": "Only warm the sign reflection while preserving character identity."},
    )

    assert first.status_code == 200
    payload = first.json()
    assert payload["schema_version"] == "afs_keyframe_local_edit_preflight.v0.1"
    assert payload["project_id"] == project_id
    assert payload["request_id"] == request["request_id"]
    assert payload["contract_status"] == "ready_no_provider_execution"
    assert payload["execution_status"] == "blocked_no_local_transform"
    assert payload["provider_calls_started"] is False
    assert payload["local_transformation_started"] is False
    assert payload["generated_media_created"] is False
    assert payload["fallback_full_frame_edit"] is False
    assert payload["local_edit_truth_label"] == "request_contract_only"
    assert payload["parent_lineage"]["immutable_parent"] is True
    assert payload["parent_lineage"]["parent_keyframe_job_id"] == "kg_job_001"
    assert payload["parent_lineage"]["parent_image_asset_id"] == "img_asset_001"
    assert payload["blockers"][0]["code"] == "execution_not_implemented"
    assert "no_pixel_transformation" in payload["non_claims"]
    assert payload["preflight_token"] == second.json()["preflight_token"]
    assert payload["preflight_token"] != changed.json()["preflight_token"]

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "secret" not in serialized
    assert "access_token" not in serialized
    assert "signed_url" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert list((tmp_path / "runtime" / "jobs").glob("*.json")) == []
    assert not (tmp_path / "runtime" / "runs" / project_id).exists()


def test_keyframe_local_edit_draft_persists_through_studio_state_without_token(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "local-edit-state"
    request = _request()
    preflight = client.post(f"/projects/{project_id}/keyframe-local-edits/preflight", json=request).json()
    availability = {
        "status": "contract_ready_execution_blocked",
        "required_capability": "image_edit_or_masked_local_transform",
        "reason": "execution_not_implemented",
        "user_message": "Local edit request recorded; no provider or pixel transform has run.",
    }
    state = {
        "nodes": {
            "keyframe_001": {
                "type": "image",
                "title": "Keyframe 001",
                "params": {
                    "nodeRole": "keyframe_generation",
                    "lastKeyframeCompletedJobId": "kg_job_001",
                    "keyframeLocalEditDraft": {
                        "schema_version": "afs_keyframe_local_edit_draft.v0.1",
                        "request": request,
                        "preflight": preflight,
                        "availability": availability,
                    },
                    "local_edit_availability": availability,
                },
            }
        },
        "order": ["keyframe_001"],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    loaded = client.get(f"/projects/{project_id}/studio-state")

    assert saved.status_code == 200
    assert loaded.status_code == 200
    params = loaded.json()["state"]["nodes"]["keyframe_001"]["params"]
    draft = params["keyframeLocalEditDraft"]
    assert draft["request"]["schema_version"] == "afs_keyframe_local_edit_request.v0.1"
    assert draft["request"]["parent_lineage"]["parent_keyframe_job_id"] == "kg_job_001"
    assert draft["request"]["parent_lineage"]["parent_image_asset_id"] == "img_asset_001"
    assert draft["preflight"]["schema_version"] == "afs_keyframe_local_edit_preflight.v0.1"
    assert draft["preflight"]["contract_status"] == "ready_no_provider_execution"
    assert draft["preflight"]["execution_status"] == "blocked_no_local_transform"
    assert draft["preflight"]["provider_calls_started"] is False
    assert draft["preflight"]["local_transformation_started"] is False
    assert draft["preflight"]["generated_media_created"] is False
    assert draft["preflight"]["blockers"][0]["code"] == "execution_not_implemented"
    assert params["local_edit_availability"]["status"] == "contract_ready_execution_blocked"
    serialized = json.dumps(params, ensure_ascii=False).lower()
    assert "preflight_token" not in serialized
    assert preflight["preflight_token"] not in serialized
    assert "access_token" not in serialized
    assert "signed_url" not in serialized


def test_keyframe_local_edit_preflight_blocks_incomplete_studio_draft_without_422(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    request = _request(
        target_node_id="",
        parent_lineage={
            "immutable_parent": True,
            "parent_node_id": "keyframe_missing",
            "parent_keyframe_job_id": "",
            "parent_image_asset_id": "",
            "parent_candidate_id": "",
            "parent_preview_url_present": False,
        },
        edit_intent="",
        edit_scope={"kind": "semantic_region", "target_description": ""},
    )

    response = client.post("/projects/local-edit-incomplete/keyframe-local-edits/preflight", json=request)

    assert response.status_code == 200
    payload = response.json()
    blocker_codes = {blocker["code"] for blocker in payload["blockers"]}
    assert payload["contract_status"] == "draft_needs_input"
    assert payload["execution_status"] == "blocked_missing_required_input"
    assert "missing_target_node_id" in blocker_codes
    assert "missing_parent_keyframe_job" in blocker_codes
    assert "missing_parent_image_asset" in blocker_codes
    assert "missing_edit_intent" in blocker_codes
    assert "missing_edit_scope" in blocker_codes
    assert payload["provider_calls_started"] is False
    assert payload["generated_media_created"] is False


def test_keyframe_local_edit_preflight_rejects_forbidden_fallback_and_unsafe_text(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "local-edit-unsafe"
    fallback = client.post(
        f"/projects/{project_id}/keyframe-local-edits/preflight",
        json=_request(
            fallback_policy={
                "allow_full_frame_fallback": True,
                "fallback_truth_label": "full_frame_fallback",
                "user_confirmation_required": True,
            }
        ),
    )
    unsafe = client.post(
        f"/projects/{project_id}/keyframe-local-edits/preflight",
        json=_request(edit_intent=r"Use D:\private\providers.local.json access_token signed_url Bearer abc"),
    )

    assert fallback.status_code == 422
    assert unsafe.status_code == 422
    for response in (fallback, unsafe):
        payload = response.json()
        serialized = json.dumps(payload, ensure_ascii=False).lower()
        assert "invalid_keyframe_local_edit" in serialized
        assert "provider_calls_started" in serialized
        assert "providers.local.json" not in serialized
        assert "access_token" not in serialized
        assert "signed_url" not in serialized
        assert "bearer" not in serialized
        assert "d:\\" not in serialized


@pytest.mark.parametrize(
    "unsafe_marker",
    [
        "data:image/png;base64",
        "base64",
        "data_base64",
        "raw_provider_response",
        "provider_response",
        "provider_raw",
    ],
)
def test_keyframe_local_edit_preflight_rejects_unsafe_media_and_provider_markers(
    tmp_path,
    monkeypatch,
    unsafe_marker: str,
) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))

    response = client.post(
        "/projects/local-edit-unsafe-markers/keyframe-local-edits/preflight",
        json=_request(edit_intent=f"Apply local edit using {unsafe_marker} evidence."),
    )

    assert response.status_code == 422
    serialized = json.dumps(response.json(), ensure_ascii=False).lower()
    assert "invalid_keyframe_local_edit" in serialized
    assert "unsafe_local_edit_request" in serialized
    assert unsafe_marker not in serialized
    assert "provider_calls_started" in serialized
    assert "local_transformation_started" in serialized
    assert "generated_media_created" in serialized


def test_keyframe_local_edit_preflight_openapi_contract_is_public(tmp_path) -> None:
    schema = create_runtime_app(runtime_root=tmp_path / "runtime").openapi()
    route = schema["paths"]["/projects/{project_id}/keyframe-local-edits/preflight"]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]

    assert request_ref.endswith("/KeyframeLocalEditRequest")
    assert "KeyframeLocalEditRequest" in schema["components"]["schemas"]
    assert "KeyframeLocalEditFallbackPolicy" in schema["components"]["schemas"]
