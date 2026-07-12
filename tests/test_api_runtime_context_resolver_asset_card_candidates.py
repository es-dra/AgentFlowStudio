from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_context_resolver_excludes_unconfirmed_asset_card_candidates(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_context_candidate_boundary"
    client.post("/projects", json={"project_id": project_id, "goal": "Candidate context boundary"})

    storyboard = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_context_candidate_boundary",
            "script_text": (
                "林晚在海边灯塔下发现一封旧信。"
                "她把旧信放进防水盒，抬头看见远处海面上的信号灯。"
            ),
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-30T15:00:00+08:00",
        },
    )
    assert storyboard.status_code == 200
    candidate_id = storyboard.json()["asset_card_candidates"]["candidates"][0]["candidate_id"]

    preflight = client.post(
        f"/projects/{project_id}/keyframe-generations/preflight",
        json={
            "node_id": "target-keyframe",
            "prompt_text": "Draw the candidate character near the lighthouse.",
            "optimized_prompt": "Draw the candidate character near the lighthouse.",
            "context_subgraph": {
                "target_node_id": "target-keyframe",
                "runtime_work_mode": "context_generate",
                "nodes": [
                    {"id": "target-keyframe", "type": "image", "title": "Target", "prompt": "Draw", "visual_asset_ids": []},
                    {
                        "id": "candidate-card-node",
                        "type": "image",
                        "title": "Unconfirmed candidate",
                        "prompt": "Candidate only",
                        "visual_asset_ids": [candidate_id],
                    },
                ],
                "edges": [
                    {
                        "id": "edge-candidate",
                        "from": "candidate-card-node",
                        "to": "target-keyframe",
                        "relation_type": "reference",
                    }
                ],
            },
            "generated_at": "2026-06-30T15:05:00+08:00",
        },
    )

    assert preflight.status_code == 200
    payload = preflight.json()
    excluded = {item["asset_id"]: item for item in payload["excluded_assets"]}

    assert payload["provider_calls_started"] is False
    assert payload["included_assets"] == []
    assert payload["reference_image_channel"] == []
    assert payload["subject_reference_asset_id"] is None
    assert excluded[candidate_id]["reason"] == "asset_card_candidate_unconfirmed"
    assert payload["context_bundle"]["trace_summary"]["draft_assets_rejected"] is True
