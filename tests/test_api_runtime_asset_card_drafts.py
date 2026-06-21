from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


def _upload_image(client: TestClient, project_id: str, node_id: str = "node-ref") -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": node_id,
            "filename": "reference.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "reference_image",
            "generated_at": "2026-06-17T09:00:00+08:00",
        },
    )
    assert response.status_code == 200
    return response.json()["asset"]["asset_id"]


def _draft_payload(asset_type: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "asset_type": asset_type,
        "source_image_asset_refs": [],
        "source_video_artifact_id": None,
        "sampled_image_asset_refs": [],
        "node_id": "node-draft",
        "prompt_text": "Lin Wan in a rainy rooftop scene.",
        "provider_service_id": "vision_image",
        "generated_at": "2026-06-17T09:05:00+08:00",
    }
    payload.update(overrides)
    return payload


def _configure_fake_vision_provider(tmp_path, monkeypatch) -> None:
    path = tmp_path / "providers.local.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "company_provider_secrets.local.v2",
                "accounts": {
                    "vision_worker": {
                        "auth_type": "none",
                        "base_url": "https://vision.example.invalid",
                        "default_models": {"vision": "fake-vision"},
                    }
                },
                "account_pools": {
                    "vision_pool": {
                        "accounts": [
                            {
                                "account_id": "vision_worker",
                                "service_id": "vision_image",
                                "enabled_capabilities": ["vision"],
                                "enabled": True,
                                "priority": 10,
                                "weight": 1,
                                "concurrency_limit": 1,
                                "health_state": "healthy",
                            },
                            {
                                "account_id": "vision_worker",
                                "service_id": "vision_video",
                                "enabled_capabilities": ["vision"],
                                "enabled": True,
                                "priority": 20,
                                "weight": 1,
                                "concurrency_limit": 1,
                                "health_state": "healthy",
                            },
                        ]
                    }
                },
                "services": {
                    "vision_image": _vision_service("vision_image", ["1:1"]),
                    "vision_video": _vision_service("vision_video", ["16:9", "9:16", "1:1"]),
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(path))


def _vision_service(service_id: str, ratios: list[str]) -> dict[str, object]:
    return {
        "provider": "fake",
        "account_ref": "vision_worker",
        "capability": "vision",
        "required_gate": "AFS_ALLOW_REMOTE_VISION",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "vision",
            "execution_mode": "sync",
            "capabilities": ["vision"],
            "account_pool_id": "vision_pool",
            "reference_image_slots": 8,
            "supported_aspect_ratios": ratios,
            "prompt_char_limit": 5000,
            "seed_supported": False,
            "cost_hint": "fake-only",
            "rate_limit_hint": "fake-only",
            "required_gate": "AFS_ALLOW_REMOTE_VISION",
        },
    }


def test_asset_card_draft_gate_closed_blocks_before_provider_and_stays_safe(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VISION", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_asset_card_gate"
    image_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/asset-card-drafts",
        json=_draft_payload("character", source_image_asset_refs=[image_id]),
    )

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["job"]["action"] == "asset_card_draft"
    assert payload["job"]["status"] == "blocked"
    assert payload["draft"] is None
    assert payload["provider_calls_started"] is False
    assert payload["provider_gate"] == {
        "capability": "vision",
        "required_gate": "AFS_ALLOW_REMOTE_VISION",
        "status": "blocked",
    }
    assert payload["safe_manifest"]["failure_class"] == "remote_vision_gate_closed"
    assert response_contains_unsafe_marker(payload) is False
    assert "provider raw" not in serialized
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_vision_image_drafts_character_and_scene_cards_without_fixed_asset_pollution(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    _configure_fake_vision_provider(tmp_path, monkeypatch)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_asset_card_fake"
    character_image = _upload_image(client, project_id, "char-node")
    scene_image = _upload_image(client, project_id, "scene-node")

    character = client.post(
        f"/projects/{project_id}/asset-card-drafts",
        json=_draft_payload("character", source_image_asset_refs=[character_image], node_id="char-node"),
    )
    scene = client.post(
        f"/projects/{project_id}/asset-card-drafts",
        json=_draft_payload(
            "scene",
            source_image_asset_refs=[scene_image],
            node_id="scene-node",
            prompt_text="A rain-soaked observatory interior with blue moonlight.",
        ),
    )

    assert character.status_code == 200
    assert scene.status_code == 200
    char_payload = character.json()
    scene_payload = scene.json()

    assert char_payload["job"]["status"] == "succeeded"
    assert char_payload["provider_calls_started"] is True
    assert char_payload["draft"]["status"] == "draft"
    assert char_payload["draft"]["asset_type"] == "character"
    assert char_payload["draft"]["feature_card"]["identity"]
    assert char_payload["draft"]["candidate_locks"]
    assert char_payload["draft"]["safe_evidence"]["source_image_asset_count"] == 1
    assert scene_payload["draft"]["asset_type"] == "scene"
    assert scene_payload["draft"]["feature_card"]["location"]
    assert scene_payload["draft"]["safe_manifest"]["provider_raw_response_stored"] is False

    fixed_assets = client.get(f"/projects/{project_id}/visual-assets").json()["assets"]
    assert fixed_assets == []

    keyframe = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "Draw the drafted character.",
            "optimized_prompt": "Draw the drafted character.",
            "context_subgraph": {
                "target_node_id": "target-node",
                "runtime_work_mode": "context_generate",
                "nodes": [
                    {"id": "target-node", "type": "image", "title": "Target", "prompt": "Draw"},
                    {
                        "id": "char-node",
                        "type": "image",
                        "title": "Draft only",
                        "prompt": "Draft only",
                        "visual_asset_ids": [char_payload["draft"]["draft_id"]],
                    },
                ],
                "edges": [{"id": "edge-1", "from": "char-node", "to": "target-node", "relation_type": "reference"}],
            },
            "generated_at": "2026-06-17T09:10:00+08:00",
        },
    )
    assert keyframe.status_code == 200
    plan = client.get(f"/artifacts/{keyframe.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    assert plan["context_bundle"]["included_assets"] == []
    assert char_payload["draft"]["draft_id"] not in plan["provider_prompt"]


def test_vision_image_drafts_prop_card_without_fixed_asset_pollution(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    _configure_fake_vision_provider(tmp_path, monkeypatch)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_prop_asset_card_fake"
    prop_image = _upload_image(client, project_id, "prop-node")

    response = client.post(
        f"/projects/{project_id}/asset-card-drafts",
        json=_draft_payload(
            "prop",
            source_image_asset_refs=[prop_image],
            node_id="prop-node",
            prompt_text="A brass compass prop with scratches, used by Lin Wan in the observatory.",
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["job"]["status"] == "succeeded"
    assert payload["provider_calls_started"] is True
    assert payload["draft"]["status"] == "draft"
    assert payload["draft"]["asset_type"] == "prop"
    assert payload["draft"]["feature_card"]["category"]
    assert payload["draft"]["feature_card"]["appearance"]
    assert payload["draft"]["asset_memory_policy"]["writes_fixed_asset"] is False
    assert client.get(f"/projects/{project_id}/visual-assets").json()["assets"] == []
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized


def test_vision_video_draft_and_video_asset_promote_use_segment_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    _configure_fake_vision_provider(tmp_path, monkeypatch)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_video_asset_card"
    sampled_frame = _upload_image(client, project_id, "video-frame")

    draft_response = client.post(
        f"/projects/{project_id}/asset-card-drafts",
        json=_draft_payload(
            "video",
            source_video_artifact_id="art_video_123",
            sampled_image_asset_refs=[sampled_frame],
            prompt_text="A five second shot: camera pushes in as Lin Wan opens the rooftop door.",
            provider_service_id="vision_video",
        ),
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["draft"]

    assert draft["asset_type"] == "video"
    assert draft["summary"]
    assert draft["segments"]
    assert set(draft["segments"][0]) >= {
        "start_time_sec",
        "end_time_sec",
        "visible_subjects",
        "actions",
        "scene_state",
        "camera_motion",
        "props",
        "continuity_anchors",
        "drift_risks",
        "usable_reference_frames",
    }

    promoted = client.post(
        f"/projects/{project_id}/video-assets/promote",
        json={
            "source_video_artifact_id": "art_video_123",
            "label": draft["label_suggestion"],
            "summary": draft["summary"],
            "segments": draft["segments"],
            "feature_card": draft["feature_card"],
            "source_node_id": "node-draft",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-17T09:15:00+08:00",
        },
    )
    assert promoted.status_code == 200
    payload = promoted.json()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["asset"]["asset_kind"] == "video_asset"
    assert payload["asset"]["status"] == "fixed"
    assert payload["asset"]["summary"] == draft["summary"]
    assert payload["asset"]["segments"][0]["actions"]
    assert "provider raw" not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
