from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_image_asset_routes_are_private_studio_runtime_contract_not_public_openapi(tmp_path) -> None:
    schema = create_runtime_app(runtime_root=tmp_path).openapi()

    assert "/projects/{project_id}/image-assets" not in schema["paths"]
    assert "/projects/{project_id}/image-assets/{asset_id}" not in schema["paths"]
    assert "/projects/{project_id}/image-assets/{asset_id}/preview" not in schema["paths"]


def test_image_asset_contract_returns_safe_metadata_and_preview_bytes_only_on_preview_route(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "media-contract"
    client.post("/projects", json={"project_id": project_id, "goal": "Runtime media contract"})

    uploaded = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "image_1",
            "filename": r"C:\private\reference.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "reference_image",
            "generated_at": "2026-06-30T12:00:00+08:00",
        },
    )

    assert uploaded.status_code == 200, uploaded.text
    payload = uploaded.json()
    asset = payload["asset"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["media_bytes_returned"] is False
    assert payload["provider_raw_response_stored"] is False
    assert set(asset) == {
        "asset_id",
        "source_node_id",
        "role",
        "filename",
        "mime_type",
        "byte_count",
        "sha256",
        "width",
        "height",
        "aspect_ratio",
        "preview_url",
    }
    assert asset["filename"] == "reference.png"
    assert asset["mime_type"] == "image/png"
    assert asset["byte_count"] == len(PNG_BYTES)
    assert asset["width"] == 1
    assert asset["height"] == 1
    assert asset["aspect_ratio"] == "1:1"
    assert asset["preview_url"] == f"/projects/{project_id}/image-assets/{asset['asset_id']}/preview"
    assert "data_base64" not in serialized
    assert base64.b64encode(PNG_BYTES).decode("ascii").lower() not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert "data/processed/runs" not in serialized
    assert "signed_url" not in serialized

    listed = client.get(f"/projects/{project_id}/image-assets")
    assert listed.status_code == 200
    assert listed.json()["assets"] == [asset]

    preview = client.get(asset["preview_url"])
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/png")
    assert preview.headers["cache-control"] == "no-store"
    assert preview.content == PNG_BYTES

    deleted = client.delete(f"/projects/{project_id}/image-assets/{asset['asset_id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {
        "project_id": project_id,
        "asset_id": asset["asset_id"],
        "deleted": True,
        "media_bytes_returned": False,
        "provider_raw_response_stored": False,
    }
    assert client.get(asset["preview_url"]).status_code == 404
