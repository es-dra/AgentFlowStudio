from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


def test_asset_card_candidates_algorithm_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import asset_card_candidates

    assert "asset_card_candidates" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert asset_card_candidates.ALGORITHM_ID == "afs.asset_card_candidates.v0.1"
    assert asset_card_candidates.INPUT_CONTRACT
    assert asset_card_candidates.OUTPUT_CONTRACT
    assert asset_card_candidates.FAILURE_MODES
    assert asset_card_candidates.EVIDENCE_BOUNDARY


def test_storyboard_breakdown_writes_safe_asset_card_candidates(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VISION", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_asset_card_candidates"
    client.post("/projects", json={"project_id": project_id, "goal": "Asset card candidate contract"})

    response = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_asset_card_candidates",
            "script_text": (
                "孙悟空和金刚狼站在破碎山巅石台上对峙，云雾从脚边卷过。"
                "孙悟空手持金箍棒压低身形，金刚狼伸出钢爪迎面冲来。"
                "金箍棒与钢爪碰撞，远处山巅石台被雷光照亮。"
            ),
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-30T14:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    candidate_set = payload["asset_card_candidates"]
    candidates = candidate_set["candidates"]
    asset_types = {candidate["asset_type"] for candidate in candidates}
    serialized = json.dumps(candidate_set, ensure_ascii=False).lower()

    assert candidate_set["artifact_type"] == "agentflow_asset_card_candidate_set"
    assert candidate_set["candidate_stage"] == "storyboard_asset_card_candidates"
    assert candidate_set["summary"]["project_id"] == project_id
    assert candidate_set["summary"]["candidate_count"] == payload["asset_graph"]["asset_count"]
    assert candidate_set["summary"]["human_review_needed"] is True
    assert candidate_set["summary"]["writes_fixed_asset"] is False
    assert candidate_set["summary"]["reuse_scope_counts"]["project_reuse_candidate"] >= 1
    assert payload["safe_manifest"]["asset_card_project_reuse_candidate_count"] == candidate_set["summary"]["reuse_scope_counts"]["project_reuse_candidate"]
    assert candidate_set["writes_long_term_memory"] is False
    assert candidate_set["writes_company_kb"] is False

    assert {"character", "scene"} <= asset_types
    assert "prop" not in asset_types
    assert candidates
    for candidate in candidates:
        assert candidate["candidate_id"].startswith("asset_card_candidate:")
        assert candidate["source_graph_asset_id"].startswith("graph:")
        assert candidate["status"] == "candidate"
        assert candidate["confirmation_state"] == "needs_human_confirmation"
        assert candidate["asset_memory_policy"]["writes_fixed_asset"] is False
        assert candidate["asset_memory_policy"]["requires_human_confirmation"] is True
        assert candidate["provider_policy"]["provider_calls_started"] is False
        assert candidate["reuse_policy"]["requires_human_confirmation"] is True
        assert candidate["reuse_policy"]["writes_fixed_asset"] is False
        assert candidate["reuse_policy"]["shot_ref_count"] == len(candidate["safe_evidence"]["shot_refs"])
        assert candidate["reuse_policy"]["suggested_reuse_scope"] in {"project_reuse_candidate", "shot_local_candidate"}
        assert candidate["draft_fields"]["display_name"]
        assert candidate["draft_fields"]["visual_description_seed"]
        assert candidate["safe_evidence"]["shot_refs"]
    assert any(candidate["reuse_policy"]["suggested_reuse_scope"] == "project_reuse_candidate" for candidate in candidates)

    assert payload["safe_manifest"]["asset_card_candidate_count"] == len(candidates)
    assert "asset_card_candidates" in payload["artifacts"]
    assert response_contains_unsafe_marker(candidate_set) is False
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
    assert "data_base64" not in serialized
    assert "d:\\" not in serialized
