from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

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
            "role": "character_reference",
            "generated_at": "2026-06-12T09:00:00+08:00",
        },
    )
    assert response.status_code == 200
    return response.json()["asset"]["asset_id"]


def _promote_payload(asset_id: str, **overrides):
    payload = {
        "source_image_asset_refs": [asset_id],
        "asset_type": "character",
        "label": "Lin Wan",
        "signature": "black short hair, red trench coat, scar above left brow",
        "feature_card": {"appearance": "young woman with black short hair"},
        "negative_locks": ["keep black short hair", "do not remove brow scar"],
        "source_node_id": "node-ref",
        "review_decision": "fixed",
        "reviewed_at": "2026-06-12T09:10:00+08:00",
    }
    payload.update(overrides)
    return payload


def test_visual_asset_promote_validates_card_and_needs_no_llm_gate(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    asset_id = _upload_image(client, "proj_visual_asset_validate")

    empty_signature = client.post(
        "/projects/proj_visual_asset_validate/visual-assets/promote",
        json=_promote_payload(asset_id, signature=""),
    )
    empty_card = client.post(
        "/projects/proj_visual_asset_validate/visual-assets/promote",
        json=_promote_payload(asset_id, feature_card={}),
    )
    promoted = client.post(
        "/projects/proj_visual_asset_validate/visual-assets/promote",
        json=_promote_payload(asset_id),
    )

    assert empty_signature.status_code == 422
    assert empty_card.status_code == 422
    assert promoted.status_code == 200
    payload = promoted.json()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["asset"]["status"] == "fixed"
    assert payload["asset"]["version"] == 1
    assert payload["asset"]["signature"].startswith("black short hair")
    assert payload["asset"]["image_asset_refs"] == [asset_id]
    assert payload["asset"]["server_recorded_at"]
    assert payload["warnings"] == []
    assert "feature_card" not in payload["asset"]
    assert "negative_locks" not in payload["asset"]
    assert "data_base64" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_visual_asset_rejected_default_list_retire_and_duplicate_warning(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_visual_asset_lifecycle"
    first_image = _upload_image(client, project_id, "node-a")
    second_image = _upload_image(client, project_id, "node-b")

    rejected = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(first_image, review_decision="rejected", label="Rejected Lin"),
    )
    fixed = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(first_image, label="Lin Wan"),
    )
    duplicate = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(second_image, label="Lin Wan"),
    )

    assert rejected.status_code == 200
    assert rejected.json()["asset"]["status"] == "rejected"
    assert fixed.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.json()["warnings"][0]["warning_id"] == "duplicate_visual_asset_label"

    default_list = client.get(f"/projects/{project_id}/visual-assets")
    rejected_list = client.get(f"/projects/{project_id}/visual-assets?status=rejected")
    assert [asset["status"] for asset in default_list.json()["assets"]] == ["fixed", "fixed"]
    assert [asset["label"] for asset in rejected_list.json()["assets"]] == ["Rejected Lin"]

    asset_id = fixed.json()["asset"]["asset_id"]
    retired = client.post(
        f"/projects/{project_id}/visual-assets/{asset_id}/retire",
        json={"reason": "typo in feature card", "retired_at": "2026-06-12T09:30:00+08:00"},
    )
    assert retired.status_code == 200
    assert retired.json()["asset"]["status"] == "retired"
    assert asset_id not in {asset["asset_id"] for asset in client.get(f"/projects/{project_id}/visual-assets").json()["assets"]}
