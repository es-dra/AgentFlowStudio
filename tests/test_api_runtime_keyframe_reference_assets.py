from __future__ import annotations

import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


def test_uploaded_image_asset_can_drive_connected_keyframe_reference(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {}

    def fake_dispatch(capability, service_id, request):
        captured["subject_reference_image_path"] = request.subject_reference_image_path
        captured["prompt"] = request.prompt
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.jpg"
        image_path.write_bytes(b"\xff\xd8fake-runtime-jpeg")
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.jpg",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 720,
                    "height": 1280,
                    "aspect_ratio": "720:1280",
                    "provider_url_persisted": False,
                }
            ],
            "input_image": {
                "path_persisted": False,
                "byte_count": len(PNG_BYTES),
                "sha256": "sha256:fake-ref",
                "mime_type": "image/png",
            },
        }

    monkeypatch.setattr("apps.api.runtime_keyframes.load_provider_registry", lambda: _FakeRegistry(fake_dispatch))
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    upload = client.post(
        "/projects/proj_connected_refs/image-assets",
        json={
            "node_id": "view-front-node",
            "filename": "front.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-12T10:25:00+08:00",
        },
    )
    assert upload.status_code == 200
    asset = upload.json()["asset"]
    preview = client.get(asset["preview_url"])
    assert preview.status_code == 200
    assert preview.content == PNG_BYTES

    result = client.post(
        "/projects/proj_connected_refs/keyframe-generations",
        json={
            "node_id": "image-node-with-upstream-ref",
            "prompt_text": "Use the connected three-view reference to create a rain rooftop keyframe.",
            "optimized_prompt": "Use the connected reference image to preserve identity.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "asset_refs": [asset["asset_id"]],
            "seed": 120612,
            "generated_at": "2026-06-12T10:26:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"payload": payload, "plan": plan}, ensure_ascii=False).lower()

    subject_path = Path(str(captured["subject_reference_image_path"]))
    assert subject_path.exists()
    assert subject_path.name == "source.png"
    assert plan["reference_image_count"] == 1
    assert plan["subject_reference_asset_id"] == asset["asset_id"]
    assert plan["reference_images"][0]["asset_id"] == asset["asset_id"]
    assert "Only apply the user-requested edit" in str(captured["prompt"])
    assert "Preserve the reference face, clothing, silhouette" in str(captured["prompt"])
    assert "data_base64" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_generated_keyframe_asset_can_drive_next_connected_reference(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {"subject_paths": []}

    def fake_dispatch(capability, service_id, request):
        captured["subject_paths"].append(request.subject_reference_image_path)
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.png"
        image_path.write_bytes(PNG_BYTES)
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.png",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 1,
                    "height": 1,
                    "aspect_ratio": "1:1",
                    "provider_url_persisted": False,
                }
            ]
        }

    monkeypatch.setattr("apps.api.runtime_keyframes.load_provider_registry", lambda: _FakeRegistry(fake_dispatch))
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    first = client.post(
        "/projects/proj_generated_refs/keyframe-generations",
        json={
            "node_id": "character-reference-node",
            "prompt_text": "Create a reusable character reference keyframe.",
            "optimized_prompt": "A front-facing controlled character reference image.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-12T10:26:00+08:00",
        },
    )
    assert first.status_code == 200
    generated_asset = first.json()["reusable_image_assets"][0]
    assert generated_asset["source_candidate_id"] == "candidate_001"

    second = client.post(
        "/projects/proj_generated_refs/keyframe-generations",
        json={
            "node_id": "downstream-rain-rooftop-node",
            "prompt_text": "Use the connected character reference for a rain rooftop keyframe.",
            "optimized_prompt": "Preserve the connected reference character while changing scene to a rain rooftop.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "asset_refs": [generated_asset["asset_id"]],
            "generated_at": "2026-06-12T10:27:00+08:00",
        },
    )
    assert second.status_code == 200
    payload = second.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"payload": payload, "plan": plan}, ensure_ascii=False).lower()

    assert captured["subject_paths"][0] is None
    subject_path = Path(str(captured["subject_paths"][1]))
    assert subject_path.exists()
    assert subject_path.name == "source.png"
    assert plan["reference_image_count"] == 1
    assert plan["subject_reference_asset_id"] == generated_asset["asset_id"]
    assert plan["reference_images"][0]["asset_id"] == generated_asset["asset_id"]
    assert "image_candidates/candidate_001.png" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


class _FakeDescriptor:
    prompt_char_limit = 1500
    reference_image_slots = 1
    required_gate = "AFS_ALLOW_REMOTE_IMAGE"


class _FakeRegistry:
    def __init__(self, dispatch) -> None:
        self._dispatch = dispatch

    def descriptor(self, service_id: str) -> _FakeDescriptor:
        return _FakeDescriptor()

    def dispatch(self, capability: str, service_id: str, request):
        return self._dispatch(capability, service_id, request)
