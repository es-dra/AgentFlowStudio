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


def test_visual_asset_promotion_records_safe_human_gate_provenance(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_visual_asset_promotion_gate"
    image_asset_id = _upload_image(client, project_id)

    promoted = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_asset_id],
            "asset_type": "character",
            "label": "Lin Wan",
            "signature": "black short hair, red trench coat, scar above left brow",
            "feature_card": {"appearance": "young woman with black short hair"},
            "negative_locks": ["keep black short hair"],
            "source_node_id": "node-ref",
            "source_human_gate_id": "runtime-human-gate:demo:accepted",
            "source_asset_card_candidate_id": "asset_card_candidate:main_character",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-30T19:20:00+08:00",
        },
    )

    assert promoted.status_code == 200
    asset = promoted.json()["asset"]
    gate = asset["promotion_gate"]
    serialized = json.dumps(promoted.json(), ensure_ascii=False).lower()

    assert gate == {
        "scope": "manual_fixed_asset_promotion",
        "source_contract": "runtime_human_gate_decision",
        "source_human_gate_id": "runtime-human-gate:demo:accepted",
        "source_asset_card_candidate_id": "asset_card_candidate:main_character",
        "provider_calls_started": False,
        "generated_media_claimed": False,
        "human_creative_acceptance_claimed": False,
        "business_validation_claimed": False,
    }
    assert asset["status"] == "fixed"
    assert asset["image_asset_refs"] == [image_asset_id]
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized

    detail = client.get(f"/projects/{project_id}/visual-assets/{asset['asset_id']}")
    assert detail.status_code == 200
    assert detail.json()["asset"]["promotion_gate"] == gate


def test_visual_asset_promotion_gate_fields_are_public_openapi_contract(tmp_path) -> None:
    schema = create_runtime_app(runtime_root=tmp_path).openapi()
    request_schema = schema["components"]["schemas"]["VisualAssetPromoteRequest"]

    assert "/projects/{project_id}/visual-assets/promote" in schema["paths"]
    assert "source_human_gate_id" in request_schema["properties"]
    assert "source_asset_card_candidate_id" in request_schema["properties"]
    assert "source_human_gate_id" not in request_schema["required"]
    assert "source_asset_card_candidate_id" not in request_schema["required"]


def _upload_image(client: TestClient, project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "node-ref",
            "filename": "reference.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-30T19:10:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]["asset_id"]
