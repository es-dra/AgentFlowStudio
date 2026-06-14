from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


def _fixed_asset(client: TestClient, project_id: str) -> dict:
    upload = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "lin-node",
            "filename": "lin.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-12T11:00:00+08:00",
        },
    )
    image_id = upload.json()["asset"]["asset_id"]
    promoted = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_id],
            "asset_type": "character",
            "label": "Lin Wan",
            "signature": "Lin Wan signature",
            "feature_card": {"identity": "Lin Wan identity"},
            "negative_locks": ["keep Lin Wan identity"],
            "source_node_id": "lin-node",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-12T11:05:00+08:00",
        },
    )
    return promoted.json()["asset"]


def test_generation_comparison_report_defines_a_b_c_arms_without_gate_network(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_generation_compare"
    asset = _fixed_asset(client, project_id)
    graph = {
        "target_node_id": "target-node",
        "runtime_work_mode": "comparison_qa",
        "nodes": [
            {"id": "target-node", "type": "image", "title": "Target", "prompt": "Lin Wan on rooftop."},
            {"id": "lin-node", "type": "image", "title": "Lin Wan", "prompt": "", "visual_asset_ids": [asset["asset_id"]]},
        ],
        "edges": [{"id": "e1", "from": "lin-node", "to": "target-node", "relation_type": "reference"}],
    }

    response = client.post(
        f"/projects/{project_id}/generation-comparisons",
        json={
            "node_id": "target-node",
            "prompt_text": "Lin Wan on rooftop.",
            "optimized_prompt": "A controlled rooftop keyframe.",
            "context_subgraph": graph,
            "generated_at": "2026-06-12T11:10:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    report = payload["report"]
    arms = {item["arm_id"]: item for item in report["arms"]}

    assert report["status"] == "blocked"
    assert report["provider_calls_started"] is False
    assert arms["A"]["context_path"] == "legacy_asset_refs"
    assert arms["A"]["retry_count"] == 0
    assert arms["A"]["blocks"][0]["block_id"] == "remote_image_gate_closed"
    assert arms["A"]["reference_images"] == []
    assert "keep Lin Wan identity" not in arms["A"]["provider_prompt"]
    assert arms["B"]["context_path"] == "context_subgraph_v0.1"
    assert arms["B"]["fixed_asset_injection"] is False
    assert arms["B"]["retry_count"] == 0
    assert arms["B"]["blocks"][0]["block_id"] == "remote_image_gate_closed"
    assert "keep Lin Wan identity" not in arms["B"]["provider_prompt"]
    assert arms["C"]["fixed_asset_injection"] is True
    assert arms["C"]["retry_count"] == 0
    assert arms["C"]["blocks"][0]["block_id"] == "remote_image_gate_closed"
    assert "keep Lin Wan identity" in arms["C"]["provider_prompt"]
    assert arms["C"]["subject_reference_asset_id"] == asset["asset_id"]
    assert report["arm_definitions"]["A"].startswith("original prompt")
