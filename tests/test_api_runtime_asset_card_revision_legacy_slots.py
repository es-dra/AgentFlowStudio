from __future__ import annotations

import base64
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


def _with_keyframe_preflight_token(client: TestClient, project_id: str, request: dict) -> dict:
    preflight = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=request)
    assert preflight.status_code == 200
    return {**request, "preflight_token": preflight.json()["preflight_token"]}


def test_asset_card_revision_allows_legacy_zero_reference_slots_for_source_edit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {}

    def fake_dispatch(capability, service_id, request):
        captured["reference_paths"] = list(request.reference_image_paths)
        captured["edit_source_image_path"] = getattr(request, "edit_source_image_path", None)
        captured["edit_reference_image_paths"] = list(getattr(request, "edit_reference_image_paths", ()))
        captured["image_operation"] = getattr(request, "image_operation", "generate")
        image_dir = Path(request.output_dir) / "image_candidates"
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

    monkeypatch.setattr(
        "apps.api.runtime_keyframes.load_provider_registry",
        lambda: _FakeRegistry(fake_dispatch, _FakeDescriptor(reference_image_slots=0)),
    )
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_asset_card_revision_zero_slots"
    ref = _upload_reference(client, project_id)
    request = {
        "node_id": "asset-card-node",
        "prompt_text": "Regenerate the robot asset reference sheet after a card edit.",
        "optimized_prompt": "Regenerate the robot asset reference sheet after a card edit.",
        "target_platform": "short_video",
        "style": "cinematic",
        "aspect_ratio": "16:9",
        "candidate_count": 1,
        "asset_refs": [ref],
        "node_parameters": {
            "node_role": "asset_card_draft",
            "asset_card_revision": {
                "mode": "image_guided_partial_revision",
                "changed_fields": [
                    {"field": "appearance", "label": "外形辨识", "from": "金属机身", "to": "毛绒机身"},
                ],
                "preserve_locks": ["保持体态比例"],
            },
        },
        "generated_at": "2026-06-23T13:40:00+08:00",
    }

    result = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json=_with_keyframe_preflight_token(client, project_id, request),
    )

    assert result.status_code == 200
    payload = result.json()
    artifact_id = payload["artifacts"]["keyframe_request_plan"]["artifact_id"]
    plan = client.get(f"/artifacts/{artifact_id}").json()["payload"]
    assert plan["reference_image_count"] == 1
    assert plan["image_operation"] == "edit"
    assert plan["edit_source_asset_id"] == ref
    assert captured["image_operation"] == "edit"
    assert captured["edit_source_image_path"] == captured["reference_paths"][0]
    assert captured["edit_reference_image_paths"] == captured["reference_paths"]


class _FakeDescriptor:
    required_gate = "AFS_ALLOW_REMOTE_IMAGE"

    def __init__(self, reference_image_slots: int) -> None:
        self.reference_image_slots = reference_image_slots
        self.min_reference_image_edge_px = 0
        self.prompt_char_limit = 1500


class _FakeRegistry:
    def __init__(self, dispatch, descriptor: _FakeDescriptor) -> None:
        self._dispatch = dispatch
        self._descriptor = descriptor

    def descriptor(self, service_id: str) -> _FakeDescriptor:
        return self._descriptor

    def dispatch(self, capability: str, service_id: str, request):
        return self._dispatch(capability, service_id, request)


def _upload_reference(client: TestClient, project_id: str) -> str:
    upload = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "asset-card-node",
            "filename": "old-candidate.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-23T13:39:00+08:00",
        },
    )
    assert upload.status_code == 200
    return upload.json()["asset"]["asset_id"]
