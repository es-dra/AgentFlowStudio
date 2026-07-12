from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app
from tests.runtime_main_loop_e2e_support import build_main_loop_e2e_state


def test_real_baseline_script_runs_provider_closed_main_loop_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_main_loop_e2e_baseline"
    state = build_main_loop_e2e_state(client, project_id)
    payload = state.storyboard_payload
    candidate = state.candidate
    gate_decision = state.gate_payload["human_gate_decision"]["decision"]
    feedback_candidate = state.feedback_candidate
    overlay = state.overlay
    preflight_payload = state.preflight_payload
    labels_by_type = {(asset["label"], asset["asset_type"]) for asset in payload["asset_graph"]["assets"]}
    checks = {item["id"]: item for item in payload["content_quality_report"]["checks"]}
    graph_relationships = {item["relationship_type"] for item in payload["production_graph"]["relationships"]}
    ledger_roles = {item["artifact_role"] for item in payload["evidence_ledger"]["evidence_items"]}
    low, high = state.case["expected_shot_range"]
    serialized = json.dumps(
        {
            "storyboard": payload,
            "gate": state.gate_payload,
            "feedback": state.feedback_payload,
            "promotion": state.promotion_payload,
            "overlay": state.overlay_response_payload,
            "preflight": preflight_payload,
        },
        ensure_ascii=False,
    ).lower()

    assert low <= len(payload["shots"]) <= high
    assert payload["provider_calls_started"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["writes_company_kb"] is False
    assert payload["content_quality_report"]["summary"]["human_review_needed"] is True
    assert checks["script_source_grounding"]["status"] == "passed"
    assert checks["dynamic_shot_count"]["status"] == "passed"
    assert checks["asset_evidence"]["status"] == "passed"
    assert {("林晚", "character"), ("办公室", "scene")} <= labels_by_type
    assert ("地图", "prop") not in labels_by_type
    assert payload["production_graph"]["summary"]["fixed_visual_asset_count"] == 1
    assert payload["safe_manifest"]["fixed_visual_asset_source_evidence_count"] == 1
    assert "script_can_reuse_fixed_asset" in graph_relationships
    assert {
        "storyboard_breakdown_safe_manifest",
        "asset_graph",
        "content_quality_report",
        "production_graph_snapshot",
        "asset_card_candidates",
    } <= ledger_roles
    assert payload["evidence_ledger"]["provider_evidence"]["provider_gate"]["status"] in {"blocked", "ready_not_run"}
    assert candidate["reuse_policy"]["suggested_reuse_scope"] == "project_reuse_candidate"
    assert candidate["asset_memory_policy"]["writes_fixed_asset"] is False

    assert gate_decision["target_id"] == candidate["candidate_id"]
    assert gate_decision["promotes_fixed_asset"] is False
    assert gate_decision["provider_calls_started"] is False

    assert feedback_candidate["candidate_scope"] == "asset_graph_feedback_candidate"
    assert feedback_candidate["scope_policy"]["global_scope_allowed"] is False
    assert feedback_candidate["conflict_summary"]["status"] == "conflict_signal_present"
    assert feedback_candidate["provider_calls_started"] is False

    assert preflight_payload["provider_calls_started"] is False
    assert preflight_payload["included_asset_source_evidence_count"] == 1
    assert preflight_payload["included_asset_source_evidence_refs"][0]["source_asset_card_candidate_id"] == (
        "asset_card_candidate:graph_character_林晚"
    )
    assert preflight_payload["feedback_context_overlays"][0]["overlay_id"] == overlay["overlay_id"]
    assert preflight_payload["feedback_context_overlays"][0]["context_overlay_consumed"] is True
    assert preflight_payload["context_bundle"]["trace_summary"]["feedback_context_overlay_selected_ids"] == [
        overlay["overlay_id"]
    ]
    for safe_projection in (
        payload["production_graph"],
        payload["evidence_ledger"],
        state.gate_payload["human_gate_decision"],
        feedback_candidate,
        overlay,
        preflight_payload["included_asset_source_evidence_refs"],
        preflight_payload["feedback_context_overlays"],
    ):
        assert response_contains_unsafe_marker(safe_projection) is False
    assert '"provider_raw"' not in serialized
    assert '"signed_url"' not in serialized
    assert "data_base64" not in serialized
    assert "d:\\" not in serialized
