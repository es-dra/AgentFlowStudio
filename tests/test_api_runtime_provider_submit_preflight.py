from __future__ import annotations

import base64
from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api import (
    runtime_generation_comparisons,
    runtime_generation_preflight,
    runtime_keyframe_routes,
    runtime_keyframes,
    runtime_video_routes,
)
from apps.api.runtime_service import create_runtime_app


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_keyframe_submit_gate_open_requires_preflight_before_provider_submit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("missing preflight must block before keyframe submit")

    monkeypatch.setattr(runtime_keyframe_routes, "build_keyframe_generation", fail_submit)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "keyframe-missing-preflight"

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json=_keyframe_request(),
    )

    assert response.status_code == 428
    detail = response.json()["detail"]
    assert detail["error"] == "missing_preflight"
    assert detail["stage"] == "preflight_required"
    assert detail["details"]["provider_calls_started"] is False


def test_keyframe_submit_rejects_gate_closed_token_after_image_gate_opens(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "keyframe-gate-state-stale-preflight"
    request = _keyframe_request()
    preflight = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=request)
    assert preflight.status_code == 200

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("stale preflight must block before keyframe submit")

    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setattr(runtime_keyframe_routes, "build_keyframe_generation", fail_submit)
    stale = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={**request, "preflight_token": preflight.json()["preflight_token"]},
    )

    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["error"] == "stale_preflight"
    assert detail["details"]["provider_calls_started"] is False


def test_keyframe_submit_gate_open_accepts_matching_preflight_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {}

    class FakeImageRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "image_relay"
            return SimpleNamespace(
                required_gate="AFS_ALLOW_REMOTE_IMAGE",
                prompt_char_limit=1500,
                reference_image_slots=0,
                execution_mode="sync",
                min_reference_image_edge_px=0,
            )

        def dispatch(self, capability: str, service_id: str, request):
            captured["capability"] = capability
            captured["service_id"] = service_id
            captured["prompt"] = request.prompt
            return {"outputs": []}

    monkeypatch.setattr(runtime_keyframes, "load_provider_registry", lambda: FakeImageRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "keyframe-valid-preflight"
    request = _keyframe_request()
    preflight = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=request)
    assert preflight.status_code == 200

    submitted = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={**request, "preflight_token": preflight.json()["preflight_token"]},
    )

    assert submitted.status_code == 200
    payload = submitted.json()
    assert payload["job"]["status"] == "succeeded"
    assert payload["provider_calls_started"] is True
    assert captured["capability"] == "image"
    assert captured["service_id"] == "image_relay"


def test_video_submit_gate_open_requires_preflight_before_provider_submit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("missing preflight must block before video submit")

    monkeypatch.setattr(runtime_video_routes, "submit_video_generation", fail_submit)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-missing-preflight"

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json=_video_request(first_frame_image_asset_id="asset_placeholder"),
    )

    assert response.status_code == 428
    detail = response.json()["detail"]
    assert detail["error"] == "missing_preflight"
    assert detail["stage"] == "preflight_required"
    assert detail["details"]["provider_calls_started"] is False


def test_video_submit_rejects_gate_closed_token_after_video_gate_opens(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-gate-state-stale-preflight"
    request = _video_request(first_frame_image_asset_id="asset_placeholder")
    preflight = client.post(f"/projects/{project_id}/video-generations/preflight", json=request)
    assert preflight.status_code == 200

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("stale preflight must block before video submit")

    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setattr(runtime_video_routes, "submit_video_generation", fail_submit)
    stale = client.post(
        f"/projects/{project_id}/video-generations",
        json={**request, "preflight_token": preflight.json()["preflight_token"]},
    )

    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["error"] == "stale_preflight"
    assert detail["details"]["provider_calls_started"] is False


def test_video_submit_gate_open_accepts_matching_preflight_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    captured: dict[str, object] = {}

    class FakeVideoRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "fake_video"
            return SimpleNamespace(
                required_gate="AFS_ALLOW_REMOTE_VIDEO",
                prompt_char_limit=2000,
                min_reference_image_edge_px=0,
                supported_durations_sec=[5],
                supported_resolutions=["720p"],
                supported_aspect_ratios=["9:16"],
                frame_modes=["first_frame"],
            )

        def submit(self, capability: str, service_id: str, request):
            captured["capability"] = capability
            captured["service_id"] = service_id
            captured["duration_sec"] = request.duration_sec
            return {"task": {"status": "submitted", "task_id": "fake-video-task"}}

    monkeypatch.setattr(runtime_video_routes, "load_provider_registry", lambda: FakeVideoRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-valid-preflight"
    client.post("/projects", json={"project_id": project_id, "goal": "Video valid preflight"}).raise_for_status()
    asset_id = _upload_image(client, project_id)
    request = _video_request(first_frame_image_asset_id=asset_id)
    preflight = client.post(f"/projects/{project_id}/video-generations/preflight", json=request)
    assert preflight.status_code == 200

    submitted = client.post(
        f"/projects/{project_id}/video-generations",
        json={**request, "preflight_token": preflight.json()["preflight_token"]},
    )

    assert submitted.status_code == 200
    payload = submitted.json()
    assert payload["job"]["status"] == "submitted"
    assert payload["provider_calls_started"] is True
    assert captured == {"capability": "video", "service_id": "fake_video", "duration_sec": 5}


def test_generation_comparison_gate_open_requires_preflight_before_provider_submit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("missing preflight must block before comparison arm submit")

    monkeypatch.setattr(runtime_generation_comparisons, "build_keyframe_generation", fail_submit)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "comparison-missing-preflight"

    response = client.post(
        f"/projects/{project_id}/generation-comparisons",
        json=_generation_comparison_request(),
    )

    assert response.status_code == 428
    detail = response.json()["detail"]
    assert detail["error"] == "missing_preflight"
    assert detail["stage"] == "preflight_required"
    assert detail["details"]["provider_calls_started"] is False


def test_generation_comparison_rejects_gate_closed_token_after_image_gate_opens(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "comparison-gate-state-stale-preflight"
    request = _generation_comparison_request()
    preflight = client.post(f"/projects/{project_id}/generation-comparisons/preflight", json=request)
    assert preflight.status_code == 200

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("stale preflight must block before comparison arm submit")

    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setattr(runtime_generation_comparisons, "build_keyframe_generation", fail_submit)
    stale = client.post(
        f"/projects/{project_id}/generation-comparisons",
        json={**request, "preflight_token": preflight.json()["preflight_token"]},
    )

    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["error"] == "stale_preflight"
    assert detail["details"]["provider_calls_started"] is False


def test_generation_comparison_gate_open_accepts_matching_preflight_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: list[tuple[str, str]] = []

    class FakeImageRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "image_relay"
            return SimpleNamespace(
                required_gate="AFS_ALLOW_REMOTE_IMAGE",
                prompt_char_limit=1500,
                reference_image_slots=0,
                execution_mode="sync",
                min_reference_image_edge_px=0,
            )

        def dispatch(self, capability: str, service_id: str, request):
            captured.append((capability, service_id))
            return {"outputs": []}

    registry = FakeImageRegistry()
    monkeypatch.setattr(runtime_generation_preflight, "load_provider_registry", lambda: registry)
    monkeypatch.setattr(runtime_keyframes, "load_provider_registry", lambda: registry)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "comparison-valid-preflight"
    request = _generation_comparison_request()
    preflight = client.post(f"/projects/{project_id}/generation-comparisons/preflight", json=request)
    assert preflight.status_code == 200

    submitted = client.post(
        f"/projects/{project_id}/generation-comparisons",
        json={**request, "preflight_token": preflight.json()["preflight_token"]},
    )

    assert submitted.status_code == 200
    payload = submitted.json()
    assert payload["report"]["status"] == "failed"
    assert payload["runtime_recovery"]["status"] == "failed"
    assert payload["runtime_recovery"]["retry"]["default_scope"] == "failed_items_only"
    assert payload["provider_calls_started"] is True
    assert captured == [("image", "image_relay"), ("image", "image_relay"), ("image", "image_relay")]


def _keyframe_request() -> dict[str, object]:
    return {
        "node_id": "keyframe_preflight_guard",
        "prompt_text": "A cinematic keyframe of a pilot looking across a moonlit runway.",
        "optimized_prompt": "Cinematic moonlit runway, pilot portrait, controlled lighting.",
        "provider_service_id": "image_relay",
        "candidate_count": 1,
        "generated_at": "2026-07-02T15:40:00+08:00",
    }


def _generation_comparison_request() -> dict[str, object]:
    return {
        "node_id": "comparison_preflight_guard",
        "prompt_text": "A cinematic keyframe of a pilot looking across a moonlit runway.",
        "optimized_prompt": "Cinematic moonlit runway, pilot portrait, controlled lighting.",
        "provider_service_id": "image_relay",
        "candidate_count": 1,
        "generated_at": "2026-07-02T15:40:00+08:00",
    }


def _video_request(*, first_frame_image_asset_id: str) -> dict[str, object]:
    return {
        "node_id": "video_preflight_guard",
        "prompt_text": "A slow camera push in from the first frame.",
        "provider_service_id": "fake_video",
        "first_frame_image_asset_id": first_frame_image_asset_id,
        "duration_sec": 5,
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generated_at": "2026-07-02T15:40:00+08:00",
    }


def _upload_image(client: TestClient, project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "first_frame_upload",
            "filename": "first-frame.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "first_frame",
            "generated_at": "2026-07-02T15:40:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]["asset_id"]
