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
    duplicate_without_intent = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(second_image, label="Lin Wan"),
    )
    duplicate = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(second_image, label="Lin Wan", reuse_intent="create_new"),
    )

    assert rejected.status_code == 200
    assert rejected.json()["asset"]["status"] == "rejected"
    assert fixed.status_code == 200
    assert duplicate_without_intent.status_code == 422
    assert duplicate.status_code == 200
    assert duplicate.json()["warnings"][0]["warning_id"] == "duplicate_visual_asset_label"
    assert duplicate.json()["warnings"][0]["warning_code"] == "fixed_asset_reuse_intent_recorded"
    assert duplicate.json()["warnings"][0]["required_intents"] == ["link_existing", "replace", "create_new"]

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


def test_visual_asset_detail_returns_safe_card_and_locks(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_visual_asset_detail"
    image_id = _upload_image(client, project_id, "node-detail")
    promoted = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(image_id, label="Detail Lin"),
    )
    assert promoted.status_code == 200
    asset_id = promoted.json()["asset"]["asset_id"]

    detail = client.get(f"/projects/{project_id}/visual-assets/{asset_id}")
    missing = client.get(f"/projects/{project_id}/visual-assets/vas_missing")

    assert detail.status_code == 200
    payload = detail.json()["asset"]
    serialized = json.dumps(detail.json(), ensure_ascii=False).lower()

    assert payload["asset_id"] == asset_id
    assert payload["feature_card"] == {"appearance": "young woman with black short hair"}
    assert payload["negative_locks"] == ["keep black short hair", "do not remove brow scar"]
    assert payload["promotion_review"]["human_confirmed"] is True
    assert payload["media_bytes_returned_by_api"] is False
    assert payload["provider_raw_response_stored"] is False
    assert "data_base64" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert missing.status_code == 404


def test_visual_asset_promote_accepts_prop_assets(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_visual_prop_asset"
    image_id = _upload_image(client, project_id, "node-prop")

    promoted = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(
            image_id,
            asset_type="prop",
            label="Brass Compass",
            signature="aged brass compass with scratched glass and red thread",
            feature_card={
                "category": "hand prop",
                "appearance": "aged brass compass with scratched glass",
                "usage": "held by Lin Wan when reading direction",
            },
            negative_locks=["keep scratched glass", "keep brass body"],
        ),
    )

    assert promoted.status_code == 200
    payload = promoted.json()["asset"]

    assert payload["status"] == "fixed"
    assert payload["asset_type"] == "prop"
    assert payload["label"] == "Brass Compass"
    assert payload["image_asset_refs"] == [image_id]


def test_visual_asset_duplicate_intent_link_and_replace_are_explicit(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_visual_asset_duplicate_intent"
    first_image = _upload_image(client, project_id, "node-a")
    second_image = _upload_image(client, project_id, "node-b")
    third_image = _upload_image(client, project_id, "node-c")

    fixed = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(first_image, label="Lin Wan"),
    )
    assert fixed.status_code == 200
    fixed_id = fixed.json()["asset"]["asset_id"]

    link_existing = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(
            second_image,
            label="Lin Wan",
            reuse_intent="link_existing",
            link_existing_asset_id=fixed_id,
        ),
    )
    replace = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(
            third_image,
            label="Lin Wan",
            reuse_intent="replace",
            supersedes_asset_id=fixed_id,
        ),
    )
    bad_link = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json=_promote_payload(
            third_image,
            label="Lin Wan",
            reuse_intent="link_existing",
            link_existing_asset_id="vas_missing",
        ),
    )

    assert link_existing.status_code == 200
    assert link_existing.json()["asset"]["asset_id"] == fixed_id
    assert link_existing.json()["warnings"][0]["reuse_intent"] == "link_existing"
    assert replace.status_code == 200
    assert replace.json()["asset"]["supersedes_asset_id"] == fixed_id
    assert replace.json()["asset"]["reuse_intent"] == "replace"
    assert bad_link.status_code == 422
