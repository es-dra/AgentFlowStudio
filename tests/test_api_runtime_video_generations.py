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
            "node_id": "image_1",
            "filename": "first-frame.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "first_frame",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )
    assert upload.status_code == 200
    return upload.json()["asset"]["asset_id"]


def test_video_generation_requires_explicit_first_frame(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-no-first-frame"
    client.post("/projects", json={"project_id": project_id, "goal": "Video first frame guard"})

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "duration_sec": 5,
            "resolution": "720p",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert response.status_code == 422
    assert "first_frame_image_asset_id" in response.text


def test_video_generation_rejects_candidate_count_not_one(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-count-guard"
    client.post("/projects", json={"project_id": project_id, "goal": "Video count guard"})
    asset_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "candidate_count": 2,
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert response.status_code == 422
    assert "candidate_count" in response.text


def test_video_generation_gate_closed_blocks_before_provider_submit(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-gate-closed"
    client.post("/projects", json={"project_id": project_id, "goal": "Video gate guard"})
    asset_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "blocked"
    assert payload["safe_manifest"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "secret" not in serialized
    assert "fake-video-key" not in serialized


def test_fake_async_video_submit_poll_and_preview(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-fake-async"
    client.post("/projects", json={"project_id": project_id, "goal": "Video async flow"})
    asset_id = _upload_image(client, project_id)

    submitted = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "node_id": "video_1",
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "aspect_ratio": "9:16",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )
    assert submitted.status_code == 200
    job = submitted.json()["job"]
    assert job["status"] == "submitted"

    polled = client.post(f"/projects/{project_id}/video-generations/{job['job_id']}/poll")
    assert polled.status_code == 200
    payload = polled.json()
    assert payload["job"]["status"] == "succeeded"
    assert payload["candidate_previews"][0]["preview_url"].startswith(
        f"/projects/{project_id}/video-generations/{job['job_id']}/candidates/"
    )
    preview = client.get(payload["candidate_previews"][0]["preview_url"])
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("video/")
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "data/processed/runs" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def _fake_video_provider_config(tmp_path) -> str:
    payload = {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "fake_video_account": {
                "auth_type": "none",
                "base_url": "https://video.example.test",
                "default_models": {"video": "fake-video"},
            }
        },
        "account_pools": {
            "video_pool": {
                "accounts": [
                    {
                        "account_id": "fake_video_account",
                        "service_id": "fake_video",
                        "enabled_capabilities": ["video"],
                        "enabled": True,
                        "priority": 10,
                        "weight": 1,
                        "concurrency_limit": 1,
                        "health_state": "healthy",
                    }
                ]
            }
        },
        "services": {
            "fake_video": {
                "provider": "fake",
                "account_ref": "fake_video_account",
                "capability": "video",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.2",
                    "modality": "video",
                    "execution_mode": "async",
                    "capabilities": ["video"],
                    "account_pool_id": "video_pool",
                    "reference_image_slots": 1,
                    "supported_aspect_ratios": ["16:9", "9:16"],
                    "prompt_char_limit": 2000,
                    "seed_supported": False,
                    "cost_hint": "fake-only",
                    "rate_limit_hint": "fake-only",
                    "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                    "frame_slots": {"first_frame": "required"},
                    "frame_modes": ["first_frame"],
                    "supported_durations_sec": [5],
                    "supported_resolutions": ["720p"],
                    "async_poll_interval_sec": 0.1,
                    "async_timeout_sec": 10,
                    "async_max_polls": 1,
                    "prompt_profile": "video_i2v_v1",
                    "cost_estimate": {"unit": "task"},
                },
            }
        },
    }
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)
