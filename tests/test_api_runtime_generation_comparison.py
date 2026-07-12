from __future__ import annotations

import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from agentflow.harness.json_io import write_json
from apps.api import runtime_generation_comparisons
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


def test_generation_comparison_uses_partial_state_for_mixed_image_arms(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    def fake_build_keyframe_generation(store, project_id, request, output_dir, *, include_fixed_assets=True):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        write_json(
            Path(output_dir) / "keyframe_request_plan.json",
            {
                "artifact_type": "agentflow_keyframe_request_plan",
                "context_path": "context_subgraph_v0.1" if include_fixed_assets else "legacy_asset_refs",
                "provider_prompt": request.optimized_prompt or request.prompt_text,
                "reference_images": [],
            },
        )
        if Path(output_dir).name == "A":
            return {
                "status": "succeeded",
                "provider_gate": {"capability": "image", "env": "AFS_ALLOW_REMOTE_IMAGE", "status": "ready_not_run"},
                "provider_calls_started": True,
                "provider_outputs": [{"candidate_id": "candidate_001", "image_ref": "image_candidates/candidate_001.png"}],
                "safe_manifest": {"retry_count": 0, "blocks": []},
                "tool_gate_state": {},
            }
        return {
            "status": "blocked",
            "provider_gate": {"capability": "image", "env": "AFS_ALLOW_REMOTE_IMAGE", "status": "blocked"},
            "provider_calls_started": False,
            "provider_outputs": [],
            "safe_manifest": {
                "retry_count": 0,
                "blocks": [{"block_id": "remote_image_gate_closed", "reason": "gate closed", "required_gate": "AFS_ALLOW_REMOTE_IMAGE"}],
            },
            "tool_gate_state": {},
        }

    monkeypatch.setattr(runtime_generation_comparisons, "build_keyframe_generation", fake_build_keyframe_generation)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_generation_compare_partial"
    request_payload = {
        "node_id": "target-node",
        "prompt_text": "Lin Wan on rooftop.",
        "optimized_prompt": "A controlled rooftop keyframe.",
        "generated_at": "2026-06-24T12:30:00+08:00",
    }
    preflight = client.post(
        f"/projects/{project_id}/generation-comparisons/preflight",
        json=request_payload,
    )
    assert preflight.status_code == 200
    preflight_payload = preflight.json()
    assert preflight_payload["provider_calls_started"] is False
    assert preflight_payload["provider_submit_preflight"]["required"] is True

    response = client.post(
        f"/projects/{project_id}/generation-comparisons",
        json={**request_payload, "preflight_token": preflight_payload["preflight_token"]},
    )

    assert response.status_code == 200
    payload = response.json()
    report = payload["report"]

    assert payload["job"]["status"] == "partially_complete"
    assert report["status"] == "partially_complete"
    assert report["batch_status"] == "partially_complete"
    assert report["arms"][0]["result_refs"] == [{"candidate_id": "candidate_001", "review_state": "ready_for_review"}]
    assert "image_candidates/candidate_001.png" not in json.dumps(payload, ensure_ascii=False)
    assert payload["runtime_recovery"]["status"] == "partially_complete"
    assert payload["runtime_recovery"]["retry"]["preserved_item_ids"] == ["candidate_001"]
    assert payload["runtime_recovery"]["retry"]["retryable_item_ids"] == ["candidate_002", "candidate_003"]
