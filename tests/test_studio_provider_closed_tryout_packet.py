from __future__ import annotations

import json
from pathlib import Path

from tools import studio_provider_closed_tryout_packet as packet_tool


def test_tryout_packet_preserves_provider_closed_non_claims() -> None:
    packet = packet_tool.build_tryout_packet(_readiness_report(), readiness_report_path="runs/t50.json")
    serialized = json.dumps(packet, ensure_ascii=False)

    assert packet["artifact_type"] == "afs_provider_closed_internal_tryout_packet"
    assert packet["evidence_state"] == "provider_closed_internal_tryout_packet_structure_verified"
    assert packet["source_verdict"] == "internal_provider_closed_tryout_ready"
    assert packet["tryout_verdict"] == "internal_provider_closed_tryout_ready"
    assert packet["provider_calls_started"] is False
    assert packet["provider_smoke_claimed"] is False
    assert packet["generated_media_claimed"] is False
    assert packet["human_creative_acceptance_claimed"] is False
    assert packet["business_validation_claimed"] is False
    assert packet["public_legal_patent_claimed"] is False
    assert packet["deploy_runtime_health_claimed"] is False
    assert packet["cos_active_rule_promotion_claimed"] is False
    assert packet["source_artifacts"]["screenshot"] == "runs/t50_studio_main_path_delivery_readiness.png"
    assert packet["source_artifacts"]["accepted_generation_plan_preview_artifact_id"] == "artifact_accepted_plan_preview"
    assert packet["accepted_generation_plan_bridge"]["preview_status"] == "blocked"
    assert packet["accepted_generation_plan_bridge"]["job_status"] == "blocked"
    assert packet["accepted_generation_plan_bridge"]["accepted"] is False
    assert packet["accepted_generation_plan_bridge"]["provider_calls_started"] is False
    assert "not_product_readiness" in packet["accepted_generation_plan_bridge"]["explicit_non_claims"]
    assert {item["summary_id"] for item in packet["source_evidence_summary"]} == {
        "storyboard_content_quality",
        "asset_candidate_fixed_asset_path",
        "production_graph_fixed_asset_reuse",
        "keyframe_request_preflight_blocked_bridge",
        "feedback_overlay_context",
        "provider_closed_browser_runtime",
        "accepted_generation_plan_bridge",
    }
    assert {item["gate_id"] for item in packet["remaining_gate_non_claims"]} >= {
        "provider_smoke",
        "generated_media_quality",
        "product_readiness",
        "human_creative_acceptance",
        "business_validation",
        "public_legal_patent",
        "deploy_runtime_health",
        "cos_active_rule_promotion",
    }
    assert "D:\\private\\runtime" not in serialized
    assert "signed_url" not in serialized
    assert "provider_raw" not in serialized


def test_tryout_packet_rejects_provider_call_signals() -> None:
    report = _readiness_report()
    report["provider_calls_started"] = True

    try:
        packet_tool.build_tryout_packet(report)
    except packet_tool.PacketError as exc:
        assert "provider_calls_started=false" in str(exc)
    else:
        raise AssertionError("provider-started report should fail closed")


def test_tryout_packet_requires_remaining_gate_non_claims() -> None:
    report = _readiness_report()
    report["delivery_readiness"]["remaining_gates"].remove("human_creative_acceptance_not_claimed")

    try:
        packet_tool.build_tryout_packet(report)
    except packet_tool.PacketError as exc:
        assert "human_creative_acceptance_not_claimed" in str(exc)
    else:
        raise AssertionError("missing remaining gate should fail closed")


def test_tryout_packet_rejects_accepted_generation_plan_claim_collapse() -> None:
    report = _readiness_report()
    for item in report["delivery_readiness"]["checks"]:
        if item["check_id"] == "accepted_generation_plan_default_blocked_preview":
            item["evidence"]["product_readiness_claimed"] = True
            break

    try:
        packet_tool.build_tryout_packet(report)
    except packet_tool.PacketError as exc:
        assert "accepted generation plan bridge" in str(exc)
        assert "product_readiness_claimed" in str(exc)
    else:
        raise AssertionError("accepted-plan claim collapse should fail closed")


def test_tryout_packet_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    report_path = tmp_path / "readiness.json"
    output_path = tmp_path / "packet.json"
    markdown_path = tmp_path / "packet.md"
    report_path.write_text(json.dumps(_readiness_report(), ensure_ascii=False), encoding="utf-8")

    exit_code = packet_tool.main([
        "--readiness-report",
        str(report_path),
        "--output",
        str(output_path),
        "--markdown",
        str(markdown_path),
    ])

    assert exit_code == 0
    packet = json.loads(output_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert packet["source_verdict"] == "internal_provider_closed_tryout_ready"
    assert packet["provider_calls_started"] is False
    assert "# AFS Provider-Closed Internal Tryout Packet" in markdown
    assert "Provider calls started: `false`" in markdown
    assert "human_creative_acceptance" in markdown


def test_tryout_packet_tool_stays_provider_closed() -> None:
    source = (Path(__file__).resolve().parents[1] / "tools" / "studio_provider_closed_tryout_packet.py").read_text(encoding="utf-8")

    assert "AFS_ALLOW_REMOTE" not in source
    assert "allow_live_provider" not in source
    assert "provider_calls_started\": False" in source
    assert "continue_to_provider_smoke_authorization_review" in source


def _readiness_report() -> dict:
    return {
        "artifact_type": "studio_main_path_browser_qa_report",
        "schema_version": "0.2.0",
        "status": "passed",
        "project_id": "studio-main-path-browser-qa-seed",
        "case_id": "multi_role_prop_exchange_chase",
        "runtime_root": "D:\\private\\runtime",
        "screenshot": str(Path.cwd() / "runs" / "t50_studio_main_path_delivery_readiness.png"),
        "fixed_asset_id": "visual_asset:lin_wan",
        "production_graph_artifact_id": "artifact_production_graph_seed",
        "overlay_id": "runtime-feedback-context-overlay:seed",
        "first_bridge_artifact_id": "artifact_keyframe_bridge_first",
        "second_bridge_artifact_id": "artifact_keyframe_bridge_second",
        "second_request_plan_artifact_id": "artifact_keyframe_request_plan_second",
        "feedback_overlay_decision_recorded": True,
        "provider_calls_started": False,
        "console_error_count": 0,
        "response_error_count": 0,
        "accepted_generation_plan_modal": _accepted_generation_plan_modal(),
        "delivery_readiness": {
            "artifact_type": "afs_provider_closed_delivery_readiness_gate",
            "schema_version": "0.1.0",
            "verdict": "internal_provider_closed_tryout_ready",
            "product_readiness": "not_product_readiness_provider_closed_tryout_only",
            "quality_evidence": "real_script_runtime_studio_main_path_and_plan_modal_structure_verified",
            "governance_evidence": "provider_closed_non_claims_preserved",
            "checks": [
                _check("real_script_input", "multi_role_prop_exchange_chase"),
                _check("storyboard_content_quality", {"shot_count": 6, "human_review_needed": True}),
                _check("asset_candidate_fixed_asset_path", {"asset_card_candidate_count": 9, "fixed_asset_id": "visual_asset:lin_wan"}),
                _check("production_graph_fixed_asset_reuse", {"production_graph_artifact_id": "artifact_production_graph_seed", "fixed_visual_asset_count": 1}),
                _check("keyframe_preflight_blocked_bridge", {"second_request_plan_artifact_id": "artifact_keyframe_request_plan_second", "second_bridge_artifact_id": "artifact_keyframe_bridge_second"}),
                _check("feedback_overlay_human_gate_non_claim", {"overlay_id": "runtime-feedback-context-overlay:seed", "feedback_overlay_decision_recorded": True}),
                _check("provider_closed_browser_runtime", {"provider_calls_started": False, "console_error_count": 0, "response_error_count": 0}),
                _check("accepted_generation_plan_default_blocked_preview", _accepted_generation_plan_modal()),
            ],
            "remaining_gates": [
                "provider_smoke_requires_explicit_authorization",
                "generated_media_quality_requires_provider_run_and_review",
                "product_readiness_not_claimed",
                "human_creative_acceptance_not_claimed",
                "business_validation_not_claimed",
                "public_legal_patent_claim_not_made",
                "deploy_server_sync_runtime_health_not_claimed",
                "cos_active_rule_promotion_not_made",
            ],
        },
    }


def _accepted_generation_plan_modal() -> dict:
    return {
        "modal_opened": True,
        "default_fixture_mode": "default_unconfirmed",
        "preview_status": "blocked",
        "job_status": "blocked",
        "packet_state": "blocked_pending_generation_plan_prerequisites",
        "accepted": False,
        "source_mode": "fixture_demo",
        "fixture_demo_non_acceptance": True,
        "provider_calls_started": False,
        "provider_gate": "closed",
        "provider_smoke_claimed": False,
        "generated_media_quality_claimed": False,
        "product_readiness_claimed": False,
        "human_creative_acceptance_claimed": False,
        "business_validation_claimed": False,
        "deploy_runtime_health_claimed": False,
        "cos_active_rule_promotion_claimed": False,
        "explicit_non_claims": [
            "not_provider_smoke",
            "not_generated_media_qa",
            "not_product_readiness",
            "not_human_creative_acceptance",
            "not_business_validation",
            "not_deploy_runtime_health",
            "fixture_demo_not_acceptance",
        ],
        "artifact_id": "artifact_accepted_plan_preview",
        "job_id": "job_accepted_plan_preview",
        "rendered_blocked_status": True,
        "rendered_provider_not_started": True,
        "rendered_product_readiness_not_claimed": True,
    }


def _check(check_id: str, evidence: object) -> dict:
    return {"check_id": check_id, "status": "passed", "evidence": evidence}
