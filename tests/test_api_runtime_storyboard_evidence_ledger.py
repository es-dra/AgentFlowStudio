from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


def test_evidence_ledger_algorithm_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import evidence_ledger

    assert "evidence_ledger" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert evidence_ledger.ALGORITHM_ID == "afs.evidence_ledger.v0.1"
    assert evidence_ledger.INPUT_CONTRACT
    assert evidence_ledger.OUTPUT_CONTRACT
    assert evidence_ledger.FAILURE_MODES
    assert evidence_ledger.EVIDENCE_BOUNDARY


def test_storyboard_breakdown_writes_safe_evidence_ledger(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_storyboard_evidence_ledger"
    client.post("/projects", json={"project_id": project_id, "goal": "Evidence ledger contract"})

    response = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_evidence_ledger_001",
            "script_text": (
                "林晚在废弃车站找到一只银色怀表。"
                "她躲到候车厅柱子后，听见远处铁轨传来脚步声。"
                "林晚握紧怀表，看见站台尽头亮起一盏红灯。"
            ),
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-30T16:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    ledger = payload["evidence_ledger"]
    serialized = json.dumps(ledger, ensure_ascii=False).lower()

    assert ledger["artifact_type"] == "agentflow_evidence_ledger"
    assert ledger["ledger_stage"] == "storyboard_to_asset_candidate"
    assert ledger["summary"]["project_id"] == project_id
    assert ledger["summary"]["script_node_id"] == "script_evidence_ledger_001"
    assert ledger["summary"]["evidence_state"] == "structure_verified_needs_human_review"
    assert ledger["summary"]["provider_calls_started"] is False
    assert ledger["summary"]["human_review_needed"] is True
    assert ledger["summary"]["provider_smoked"] is False
    assert ledger["summary"]["human_accepted"] is False
    assert ledger["summary"]["business_validated"] is False
    assert ledger["writes_long_term_memory"] is False
    assert ledger["writes_company_kb"] is False

    item_roles = {item["artifact_role"] for item in ledger["evidence_items"]}
    expected_roles = {
        "storyboard_breakdown_request_plan",
        "storyboard_breakdown_safe_artifact",
        "storyboard_breakdown_safe_manifest",
        "asset_graph",
        "content_quality_report",
        "production_graph_snapshot",
        "asset_card_candidates",
    }
    assert expected_roles <= item_roles
    assert ledger["asset_evidence"]["candidate_asset_count"] == payload["asset_graph"]["asset_count"]
    assert ledger["asset_evidence"]["asset_card_candidate_count"] == len(payload["asset_card_candidates"]["candidates"])
    assert ledger["provider_evidence"]["provider_gate"]["status"] == "blocked"
    assert ledger["provider_evidence"]["raw_provider_response_stored"] is False
    assert ledger["provider_evidence"]["generated_media_bytes_stored"] is False

    assert payload["safe_manifest"]["evidence_ledger_entry_count"] == len(ledger["evidence_items"])
    assert "evidence_ledger" in payload["artifacts"]
    assert response_contains_unsafe_marker(ledger) is False
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
    assert "data_base64" not in serialized
    assert "d:\\" not in serialized
