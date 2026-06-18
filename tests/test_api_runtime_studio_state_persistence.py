from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_studio_state_prunes_runtime_bundle_details_before_safety_scan(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-runtime-result"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio failed result persistence"})

    state = {
        "nodes": {
            "image_1": {
                "type": "image",
                "title": "generated candidate",
                "prompt": "A character walks through a desert.",
                "result": "Gate blocked\nReason: image provider gate is closed.",
                "params": {
                    "model": "minimax-image-01",
                    "temporaryLockOverrides": [{"asset_id": "va_1", "lock_text": "keep black hair"}],
                    "lastContextBundle": {
                        "trace_summary": "not persisted in studio state",
                        "included_assets": [{"asset_id": "va_1"}],
                    },
                    "visualAssets": [{"asset_id": "va_fixed_1", "label": "Zhou Tong"}],
                },
            }
        },
        "order": ["image_1"],
    }

    response = client.put(f"/projects/{project_id}/studio-state", json={"state": state})

    assert response.status_code == 200
    params = response.json()["state"]["nodes"]["image_1"]["params"]
    assert params["lastContextBundle"]["included_assets"] == [{"asset_id": "va_1"}]
    assert "trace_summary" not in params["lastContextBundle"]
    assert "temporaryLockOverrides" not in params
    assert params["visualAssets"][0]["asset_id"] == "va_fixed_1"


def test_projects_list_includes_studio_state_meta_and_preview_url_persists(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-project-persist"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio project persistence"})

    preview_url = f"/projects/{project_id}/image-assets/img_abc123/preview"
    state = {
        "meta": {
            "projectName": "Kling Test Project",
            "canvasName": "Video Board",
            "seq": 7,
            "updated_at": "2026-06-13T10:00:00+08:00",
        },
        "nodes": {
            "image_1": {
                "type": "image",
                "title": "first frame",
                "previewUrl": preview_url,
                "params": {
                    "uploads": [{"asset_id": "img_abc123", "preview_url": preview_url}],
                    "previewAspectRatio": "9:16",
                },
            }
        },
        "order": ["image_1"],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    assert saved.status_code == 200

    loaded = client.get(f"/projects/{project_id}/studio-state").json()["state"]
    assert loaded["nodes"]["image_1"]["previewUrl"] == preview_url
    assert loaded["nodes"]["image_1"]["params"]["uploads"][0]["preview_url"] == preview_url

    projects = client.get("/projects").json()["projects"]
    item = next(project for project in projects if project["project_id"] == project_id)
    assert item["studio_state_meta"]["projectName"] == "Kling Test Project"
    assert item["studio_state_meta"]["canvasName"] == "Video Board"
    assert item["studio_state_meta"]["seq"] == 7
    assert item["studio_state_meta"]["updated_at"] == "2026-06-13T10:00:00+08:00"
    assert item["studio_state_meta"]["state_version"]
    assert item["studio_state_meta"]["saved_at"]


def test_studio_state_rejects_unsafe_preview_url(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-preview-safety"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio preview safety"})

    response = client.put(
        f"/projects/{project_id}/studio-state",
        json={
            "state": {
                "nodes": {
                    "image_1": {
                        "type": "image",
                        "title": "unsafe preview",
                        "previewUrl": "https://signed.example/private.png?token=secret",
                    }
                },
                "order": ["image_1"],
            }
        },
    )

    assert response.status_code == 400
    assert "preview" in response.json()["detail"]


def test_image_asset_list_returns_public_metadata_only(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-image-list"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio image asset list"})

    upload = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "image_1",
            "filename": "first-frame.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "reference_image",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )
    assert upload.status_code == 200

    listed = client.get(f"/projects/{project_id}/image-assets").json()
    serialized = str(listed).lower()
    assert listed["project_id"] == project_id
    assert len(listed["assets"]) == 1
    assert listed["assets"][0]["asset_id"] == upload.json()["asset"]["asset_id"]
    assert listed["assets"][0]["preview_url"].startswith(f"/projects/{project_id}/image-assets/")
    assert "source.png" not in serialized
    assert "data/processed/runs" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
