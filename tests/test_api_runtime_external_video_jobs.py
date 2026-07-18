from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_external_video_replay_job_creates_safe_preview_and_download(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    monkeypatch.delenv("AFS_ALLOW_EXTERNAL_DOWNLOAD", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "external-video-replay"
    client.post("/projects", json={"project_id": project_id, "goal": "AI comic roadshow demo"})

    response = client.post(
        f"/projects/{project_id}/external-video-jobs",
        json={
            "node_id": "roadshow_demo_1",
            "engine": "replay",
            "title": "AI 漫剧路演演示",
            "prompt_text": "三幕式 AI 漫剧：主角进入未来内容工厂，生成分镜，完成成片下载。",
            "style": "animated_comic",
            "aspect_ratio": "9:16",
            "duration_sec": 2,
            "scene_count": 3,
            "generated_at": "2026-07-17T20:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["action"] == "external_video_generation"
    assert payload["job"]["status"] == "succeeded"
    assert payload["engine"] == "replay"
    assert payload["provider_calls_started"] is False
    assert payload["external_download_started"] is False
    assert payload["safe_manifest"]["preview_available"] is True
    assert payload["safe_manifest"]["download_available"] is True
    assert payload["safe_manifest"]["provider_urls_persisted"] is False
    assert payload["preview"]["preview_url"].endswith("/preview")
    assert payload["preview"]["download_url"].endswith("/download")

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert ".mp4" not in serialized
    assert "data/processed/runs" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert "secret" not in serialized
    assert "access_token" not in serialized

    preview = client.get(payload["preview"]["preview_url"])
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("video/")
    assert len(preview.content) > 0

    download = client.get(payload["preview"]["download_url"])
    assert download.status_code == 200
    assert download.headers["content-disposition"].startswith("attachment")
    assert len(download.content) == len(preview.content)

    artifact = client.get(f"/artifacts/{payload['artifacts']['external_video_safe_manifest']['artifact_id']}")
    assert artifact.status_code == 200
    assert artifact.json()["payload"]["artifact_type"] == "afs_external_video_safe_manifest"


def test_external_video_libtv_gate_closed_blocks_before_provider_call(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    monkeypatch.setenv("LIBTV_ACCESS_KEY", "should-not-be-used")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "external-video-libtv-blocked"
    client.post("/projects", json={"project_id": project_id, "goal": "LibTV gate guard"})

    response = client.post(
        f"/projects/{project_id}/external-video-jobs",
        json={
            "engine": "libtv",
            "title": "LibTV live demo",
            "prompt_text": "生成一段 AI 漫剧。",
            "duration_sec": 6,
            "generated_at": "2026-07-17T20:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    assert payload["safe_manifest"]["engine"] == "libtv"
    assert payload["safe_manifest"]["blocks"][0]["block_id"] == "remote_video_gate_closed"
    assert payload["preview"] is None

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "should-not-be-used" not in serialized
    assert "authorization" not in serialized
    assert "bearer" not in serialized


def test_external_video_libtv_uses_official_session_envelope_without_downloading(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.delenv("AFS_ALLOW_EXTERNAL_DOWNLOAD", raising=False)
    monkeypatch.setenv("LIBTV_ACCESS_KEY", "test-access-key")
    monkeypatch.setenv("OPENAPI_IM_BASE", "https://im.example.test")
    monkeypatch.delenv("LIBTV_OPENAPI_BASE_URL", raising=False)
    monkeypatch.delenv("IM_BASE_URL", raising=False)
    calls: list[tuple[str, str, dict[str, str], dict | None]] = []

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    def fake_post(url: str, *, headers: dict[str, str], json: dict, timeout: float) -> FakeResponse:
        calls.append(("POST", url, headers, json))
        assert timeout == 30.0
        return FakeResponse({"data": {"projectUuid": "provider-project-1", "sessionId": "session-abc"}})

    def fake_get(url: str, *, headers: dict[str, str], timeout: float) -> FakeResponse:
        calls.append(("GET", url, headers, None))
        assert timeout == 30.0
        return FakeResponse({"data": {"status": "completed", "messages": [{"content": "result https://cdn.example.test/final.mp4"}]}})

    monkeypatch.setattr("apps.api.runtime_external_video_libtv.httpx.post", fake_post)
    monkeypatch.setattr("apps.api.runtime_external_video_libtv.httpx.get", fake_get)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "external-video-libtv-envelope"
    client.post("/projects", json={"project_id": project_id, "goal": "LibTV official envelope"})

    created = client.post(
        f"/projects/{project_id}/external-video-jobs",
        json={
            "engine": "libtv",
            "title": "LibTV live demo",
            "prompt_text": "生成一段 AI 漫剧。",
            "duration_sec": 6,
            "generated_at": "2026-07-17T20:00:00+00:00",
        },
    )

    assert created.status_code == 200
    job_id = created.json()["job"]["job_id"]
    assert created.json()["job"]["status"] == "submitted"
    polled = client.post(f"/projects/{project_id}/external-video-jobs/{job_id}/poll")

    assert polled.status_code == 200
    payload = polled.json()
    assert payload["job"]["status"] == "needs_attention"
    assert payload["provider_calls_started"] is True
    assert payload["external_download_started"] is False
    assert payload["safe_manifest"]["blocks"][0]["block_id"] == "external_video_download_gate_closed"
    assert payload["preview"] is None
    assert calls[0][0:2] == ("POST", "https://im.example.test/openapi/session")
    assert calls[1][0:2] == ("GET", "https://im.example.test/openapi/session/session-abc")
    assert calls[0][2]["Authorization"] == "Bearer test-access-key"
    assert "生成一段 AI 漫剧。" in (calls[0][3] or {})["message"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "test-access-key" not in serialized
    assert "https://cdn.example.test" not in serialized
    assert ".mp4" not in serialized


def test_external_video_poll_replays_terminal_state(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "external-video-poll"
    client.post("/projects", json={"project_id": project_id, "goal": "Poll replay"})

    created = client.post(
        f"/projects/{project_id}/external-video-jobs",
        json={
            "engine": "replay",
            "prompt_text": "AI 漫剧 replay poll。",
            "duration_sec": 1,
            "generated_at": "2026-07-17T20:00:00+00:00",
        },
    )
    assert created.status_code == 200
    job_id = created.json()["job"]["job_id"]

    polled = client.post(f"/projects/{project_id}/external-video-jobs/{job_id}/poll")

    assert polled.status_code == 200
    assert polled.json()["job"]["status"] == "succeeded"
    assert polled.json()["preview"]["preview_url"] == created.json()["preview"]["preview_url"]
