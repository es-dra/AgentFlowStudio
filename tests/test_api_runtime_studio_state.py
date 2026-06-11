from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_studio_state import sanitize_studio_state


def test_studio_state_can_save_and_restore_safe_canvas(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio state test"})
    state = {
        "meta": {"projectName": "AFS Studio", "canvasName": "画布 1", "seq": 9},
        "viewport": {"x": -120, "y": 80, "scale": 0.82},
        "nodes": {
            "director_1": {
                "id": "director_1",
                "type": "director",
                "title": "二维导演台",
                "x": 10,
                "y": 20,
                "prompt": "",
                "params": {
                    "directorSetup": {
                        "view": "top_down_2d",
                        "cameras": [{"name": "A Cam", "fov": 45}],
                        "subjects": [{"name": "男孩", "x": 44, "y": 52}],
                        "lights": [{"name": "Key Light", "intensity": 72}],
                    },
                    "uploads": [{
                        "asset_id": "img_safe_reference_001",
                        "role": "generated_keyframe_reference",
                        "filename": "candidate_001.png",
                        "mime_type": "image/png",
                        "byte_count": 68,
                        "sha256": "abc123",
                        "width": 1,
                        "height": 1,
                        "aspect_ratio": "1:1",
                        "preview_url": "/projects/studio-state-demo/image-assets/img_safe_reference_001/preview",
                    }],
                    "previewAspectRatio": "1:1",
                },
            },
            "image_2": {"id": "image_2", "type": "image", "title": "关键帧", "x": 360, "y": 20, "prompt": "昏暗房间"},
        },
        "edges": {"edge_3": {"id": "edge_3", "from": "director_1", "to": "image_2", "relation_type": "director"}},
        "order": ["director_1", "image_2"],
        "assets": [
            {
                "id": "asset_1",
                "kind": "director_setup",
                "title": "夜间卧室布光",
                "safe_summary": "1 个机位 / 1 个主体 / 3 盏灯",
                "thumbnail_ref": "director-board",
                "source_node_id": "director_1",
            }
        ],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    assert saved.status_code == 200
    payload = saved.json()
    assert payload["saved"] is True
    assert payload["state"]["edges"]["edge_3"]["relation_type"] == "director"
    assert payload["state"]["assets"][0]["source_node_id"] == "director_1"

    restored = client.get(f"/projects/{project_id}/studio-state")
    assert restored.status_code == 200
    assert restored.json()["source"] == "runtime"
    restored_params = restored.json()["state"]["nodes"]["director_1"]["params"]
    assert restored_params["directorSetup"]["view"] == "top_down_2d"
    assert restored_params["uploads"][0]["asset_id"] == "img_safe_reference_001"
    assert restored_params["previewAspectRatio"] == "1:1"


def test_studio_state_rejects_secrets_local_paths_and_provider_raw(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-unsafe"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio state safety test"})
    unsafe_payloads = [
        {"nodes": {"a": {"prompt": "sk-test-secret", "api_key": "x"}}},
        {"nodes": {"a": {"prompt": "C:\\Users\\secret\\image.png"}}},
        {"assets": [{"id": "a", "provider_raw": {"text": "raw"}}]},
        {"nodes": {"a": {"params": {"provider_config": "unsafe"}}}},
        {"nodes": {"a": {"params": {"signed_url": "https://example.invalid/signed"}}}},
    ]

    for state in unsafe_payloads:
        response = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
        assert response.status_code == 400


def test_sanitize_studio_state_keeps_only_safe_node_and_asset_fields() -> None:
    sanitized = sanitize_studio_state(
        {
            "nodes": {
                "node 1": {
                    "type": "image",
                    "title": "关键帧",
                    "x": 1,
                    "y": 2,
                    "params": {
                        "model": "safe-model",
                        "draft": "ignored",
                        "styleRef": "电影感",
                        "uploads": [{"asset_id": "img_safe"}],
                        "previewAspectRatio": "1:1",
                    },
                    "private": "ignored",
                }
            },
            "edges": {"edge 1": {"from": "node 1", "to": "node 2", "relation_type": "reference"}},
            "assets": [{"id": "asset 1", "kind": "keyframe", "title": "镜头 1", "summary": "安全摘要"}],
        }
    )

    node = next(iter(sanitized["nodes"].values()))
    assert node["params"] == {
        "model": "safe-model",
        "styleRef": "电影感",
        "uploads": [{"asset_id": "img_safe"}],
        "previewAspectRatio": "1:1",
    }
    assert "private" not in node
    assert next(iter(sanitized["edges"].values()))["relation_type"] == "reference"
    assert sanitized["assets"][0]["safe_summary"] == "安全摘要"
