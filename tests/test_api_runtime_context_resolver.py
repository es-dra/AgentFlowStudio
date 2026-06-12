from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore
from agentflow.harness.json_io import write_json


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


def _upload(client: TestClient, project_id: str, node_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": node_id,
            "filename": f"{node_id}.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "reference_image",
            "generated_at": "2026-06-12T10:00:00+08:00",
        },
    )
    assert response.status_code == 200
    return response.json()["asset"]["asset_id"]


def _promote(client: TestClient, project_id: str, image_id: str, label: str, asset_type: str = "character") -> dict:
    response = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_id],
            "asset_type": asset_type,
            "label": label,
            "signature": f"{label} signature",
            "feature_card": {"identity": f"{label} identity", "palette": "black and red"},
            "negative_locks": [f"keep {label} identity", "keep black short hair"],
            "source_node_id": f"{label}-node",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-12T10:05:00+08:00",
        },
    )
    assert response.status_code == 200
    return response.json()["asset"]


def _subgraph(target: str, upstream: str, asset_id: str, relation: str = "reference") -> dict:
    return {
        "target_node_id": target,
        "runtime_work_mode": "context_generate",
        "nodes": [
            {"id": target, "type": "image", "title": "Target", "prompt": "target prompt", "visual_asset_ids": []},
            {"id": upstream, "type": "image", "title": "Asset", "prompt": "asset prompt", "visual_asset_ids": [asset_id]},
        ],
        "edges": [{"id": "edge-1", "from": upstream, "to": target, "relation_type": relation}],
    }


def test_optimize_context_injects_only_connected_or_label_matched_signatures(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_optimize_context"
    assets = []
    for index, label in enumerate(["Lin Wan", "Desert Lab", "Rain Alley", "Unused Studio", "Extra Actor"]):
        image_id = _upload(client, project_id, f"node-{index}")
        assets.append(_promote(client, project_id, image_id, label, "scene" if index in {1, 2, 3} else "character"))

    response = client.post(
        f"/projects/{project_id}/prompt-optimizations",
        json={
            "node_id": "target-node",
            "node_type": "image",
            "prompt_text": "Lin Wan walks past Rain Alley at night.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "context_subgraph": _subgraph("target-node", "asset-node", assets[1]["asset_id"]),
            "generated_at": "2026-06-12T10:10:00+08:00",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    bundle = payload["context_bundle"]
    included_ids = [asset["asset_id"] for asset in bundle["included_assets"]]

    assert len(included_ids) <= 4
    assert assets[1]["asset_id"] in included_ids
    assert assets[0]["asset_id"] in included_ids
    assert assets[2]["asset_id"] in included_ids
    assert assets[3]["asset_id"] not in included_ids
    assert "Unused Studio signature" not in payload["optimized_prompt"]
    assert any(item["label"] == "Unused Studio" for item in bundle["available_project_assets"])


def test_generate_context_uses_connected_fixed_assets_and_lock_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_generate_context"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")
    retired_image = _upload(client, project_id, "retired-node")
    retired = _promote(client, project_id, retired_image, "Retired Actor")
    client.post(
        f"/projects/{project_id}/visual-assets/{retired['asset_id']}/retire",
        json={"reason": "not used", "retired_at": "2026-06-12T10:06:00+08:00"},
    )

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "Draw Lin Wan with red long hair.",
            "optimized_prompt": "A rooftop keyframe with Lin Wan.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "context_subgraph": _subgraph("target-node", "char-node", asset["asset_id"]),
            "temporary_lock_overrides": [
                {"asset_id": asset["asset_id"], "lock_text": "keep black short hair", "reason": "one-off variant test"}
            ],
            "generated_at": "2026-06-12T10:20:00+08:00",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    bundle = plan["context_bundle"]
    provider_prompt = plan["provider_prompt"]

    assert payload["job"]["status"] == "blocked"
    assert plan["context_path"] == "context_subgraph_v0.1"
    assert bundle["subject_reference_asset_id"] == asset["asset_id"]
    assert bundle["reference_image_channel"][0]["asset_id"] == image_id
    assert "keep Lin Wan identity" in provider_prompt
    assert "keep black short hair" not in provider_prompt
    assert bundle["temporary_lock_overrides"][0]["lock_text"] == "keep black short hair"
    assert retired["asset_id"] not in {item["asset_id"] for item in bundle["included_assets"]}


def test_scene_asset_never_occupies_subject_reference_and_frontend_asset_text_is_rejected(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_scene_subject_ref"
    scene_image = _upload(client, project_id, "scene-node")
    scene = _promote(client, project_id, scene_image, "Desert Lab", "scene")
    graph = _subgraph("target-node", "scene-node", scene["asset_id"])

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "A quiet desert laboratory.",
            "optimized_prompt": "A quiet desert laboratory.",
            "context_subgraph": graph,
            "generated_at": "2026-06-12T10:30:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    assert plan["subject_reference_asset_id"] is None
    assert plan["context_bundle"]["subject_reference_asset_id"] is None

    graph["nodes"][1]["feature_card"] = {"forged": "frontend must not supply this"}
    rejected = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "A quiet desert laboratory.",
            "optimized_prompt": "A quiet desert laboratory.",
            "context_subgraph": graph,
            "generated_at": "2026-06-12T10:31:00+08:00",
        },
    )
    assert rejected.status_code == 422


def test_legacy_background_context_is_not_consumed_by_context_resolver(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    legacy_dir = tmp_path / "creative_memory" / "proj_legacy_context"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        legacy_dir / "creative_memory_state.json",
        {
            "artifact_type": "agentflow_creative_memory_state",
            "schema_version": "0.1.0",
            "project_id": "proj_legacy_context",
            "characters": [{"memory_type": "character", "label": "Legacy Character"}],
            "scenes": [{"memory_type": "scene", "label": "Legacy Scene"}],
            "style_preferences": [],
            "user_preferences": [],
            "extracted_context": [],
        },
    )
    client = TestClient(create_runtime_app(runtime_root=store.root))
    response = client.post(
        "/projects/proj_legacy_context/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "A new keyframe.",
            "optimized_prompt": "A new keyframe.",
            "context_subgraph": {
                "target_node_id": "target-node",
                "runtime_work_mode": "context_generate",
                "nodes": [{"id": "target-node", "type": "image", "title": "Target", "prompt": "A new keyframe."}],
                "edges": [],
            },
            "generated_at": "2026-06-12T10:40:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    serialized = json.dumps(plan, ensure_ascii=False)

    assert "Legacy Character" not in serialized
    assert "Legacy Scene" not in serialized
    assert plan["context_bundle"]["included_assets"] == []
