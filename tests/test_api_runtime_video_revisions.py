from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _upload_image(client: TestClient, project_id: str) -> str:
    upload = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "video_revision_frame",
            "filename": "revision-first-frame.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "first_frame",
            "generated_at": "2026-06-15T10:00:00+08:00",
        },
    )
    assert upload.status_code == 200
    return upload.json()["asset"]["asset_id"]


def _revision_request(asset_id: str) -> dict:
    return {
        "node_id": "video_1",
        "base_video_job_id": "video_generation_base_001",
        "revision_intent": "Adjust the light on frame 34 to be softer while keeping the character, camera, duration, and scene stable.",
        "editable_targets": ["lighting"],
        "locked_aspects": ["character_identity", "camera_path", "duration", "scene_layout"],
        "temporal_scope": {"kind": "frame_range", "start_frame": 34, "end_frame": 34},
        "provider_service_id": "fake_video",
        "first_frame_image_asset_id": asset_id,
        "duration_sec": 5,
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "candidate_count": 1,
        "generated_at": "2026-06-15T10:01:00+08:00",
    }


def test_video_revision_preflight_is_experimental_best_effort_and_provider_safe(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-revision-preflight"
    client.post("/projects", json={"project_id": project_id, "goal": "Video revision preflight"})
    asset_id = _upload_image(client, project_id)
    request = _revision_request(asset_id)

    first = client.post(f"/projects/{project_id}/video-revisions/preflight", json=request)
    second = client.post(f"/projects/{project_id}/video-revisions/preflight", json=request)
    changed = client.post(
        f"/projects/{project_id}/video-revisions/preflight",
        json={**request, "revision_intent": "Change the entrance path but preserve the accepted base identity."},
    )

    assert first.status_code == 200
    payload = first.json()
    assert payload["schema_version"] == "afs_video_revision_preflight.v0.1"
    assert payload["experimental"] is True
    assert payload["provider_calls_started"] is False
    assert payload["feature_flag"]["env"] == "AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION"
    assert payload["feature_flag"]["status"] == "blocked"
    assert payload["provider_capability_mode"] == "i2v_revision_attempt"
    assert payload["preserve_policy"] == "best_effort"
    assert payload["base_lineage_root_job_id"] == request["base_video_job_id"]
    assert payload["preserve_change_taxonomy"]["editable_targets"] == ["lighting"]
    assert "not_pixel_identical_guarantee" in payload["non_claims"]
    assert payload["preflight_token"] == second.json()["preflight_token"]
    assert payload["preflight_token"] != changed.json()["preflight_token"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "secret" not in serialized
    assert "token" not in serialized.replace("preflight_token", "")
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_video_revision_submit_is_flagged_and_rejects_stale_preflight(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-revision-submit"
    client.post("/projects", json={"project_id": project_id, "goal": "Video revision submit"})
    asset_id = _upload_image(client, project_id)
    request = _revision_request(asset_id)

    preflight = client.post(f"/projects/{project_id}/video-revisions/preflight", json=request)
    assert preflight.status_code == 200
    stale = client.post(
        f"/projects/{project_id}/video-revisions",
        json={**request, "revision_intent": "Change a different thing.", "preflight_token": preflight.json()["preflight_token"]},
    )
    blocked = client.post(
        f"/projects/{project_id}/video-revisions",
        json={**request, "preflight_token": preflight.json()["preflight_token"]},
    )

    assert stale.status_code == 409
    assert "stale_preflight" in stale.text
    assert blocked.status_code == 200
    payload = blocked.json()
    assert payload["job"]["action"] == "video_revision"
    assert payload["job"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    manifest = payload["safe_manifest"]
    assert manifest["schema_version"] == "afs_video_revision_safe_manifest.v0.1"
    assert manifest["experimental"] is True
    assert manifest["status"] == "blocked"
    assert manifest["provider_calls_started"] is False
    assert manifest["feature_flag"]["status"] == "blocked"
    assert manifest["base_video_job_id"] == request["base_video_job_id"]
    assert manifest["base_lineage_root_job_id"] == request["base_video_job_id"]
    assert manifest["editable_targets"] == ["lighting"]
    assert manifest["locked_aspect_count"] == 4
    assert "not_pixel_identical_guarantee" in payload["non_claims"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "secret" not in serialized
    assert "fake-video-key" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_video_revision_rejects_unsafe_base_id_without_leaking_detail(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-revision-unsafe-base"
    client.post("/projects", json={"project_id": project_id, "goal": "Video revision unsafe base"})
    asset_id = _upload_image(client, project_id)
    request = {
        **_revision_request(asset_id),
        "base_video_job_id": r"D:\private\providers.local.json api_key token signed_url",
    }

    response = client.post(f"/projects/{project_id}/video-revisions", json=request)

    assert response.status_code == 422
    serialized = json.dumps(response.json(), ensure_ascii=False).lower()
    assert "invalid_video_revision" in serialized
    assert "providers.local.json" not in serialized
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "signed_url" not in serialized
    assert "d:\\" not in serialized
