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


def test_fixed_asset_source_evidence_flows_into_keyframe_context(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_fixed_asset_source_evidence_context"
    image_asset_id = _upload_image(client, project_id)
    visual_asset = _promote_asset_from_candidate(client, project_id, image_asset_id)

    response = client.post(
        f"/projects/{project_id}/keyframe-generations/preflight",
        json={
            "node_id": "target-node",
            "prompt_text": "Draw Lin Wan in the observatory.",
            "optimized_prompt": "Draw Lin Wan in the observatory.",
            "context_subgraph": _context_subgraph(visual_asset["asset_id"]),
            "generated_at": "2026-06-30T23:40:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    included = payload["included_assets"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert len(included) == 1
    assert included[0]["asset_id"] == visual_asset["asset_id"]
    assert included[0]["source_evidence"] == visual_asset["source_evidence"]
    assert included[0]["source_evidence"]["source_asset_card_candidate_id"] == "asset_card_candidate:main_character"
    assert included[0]["source_evidence"]["provider_calls_started"] is False
    assert included[0]["source_evidence"]["human_creative_acceptance_claimed"] is False
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def _upload_image(client: TestClient, project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "node-ref",
            "filename": "reference.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-30T23:38:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]["asset_id"]


def _promote_asset_from_candidate(client: TestClient, project_id: str, image_asset_id: str) -> dict:
    response = client.post(
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
            "reviewed_at": "2026-06-30T23:39:00+08:00",
        },
    )
    response.raise_for_status()
    return response.json()["asset"]


def _context_subgraph(asset_id: str) -> dict:
    return {
        "target_node_id": "target-node",
        "runtime_work_mode": "context_generate",
        "nodes": [
            {"id": "target-node", "type": "image", "title": "Target", "prompt": "target", "visual_asset_ids": []},
            {"id": "asset-node", "type": "image", "title": "Lin Wan", "prompt": "", "visual_asset_ids": [asset_id]},
        ],
        "edges": [
            {"id": "edge-asset-target", "from": "asset-node", "to": "target-node", "relation_type": "reference"}
        ],
    }
