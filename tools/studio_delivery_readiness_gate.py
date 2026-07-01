from __future__ import annotations

from typing import Any


def build_delivery_readiness(report: dict[str, Any], seed: dict[str, Any]) -> dict[str, Any]:
    checks = [
        _check("real_script_input", seed.get("case_id") == "multi_role_prop_exchange_chase", seed.get("case_id", "")),
        _check(
            "storyboard_content_quality",
            seed.get("shot_count", 0) >= 1 and seed.get("content_quality_human_review_needed") is True,
            {
                "shot_count": seed.get("shot_count", 0),
                "expected_shot_range": seed.get("expected_shot_range", []),
                "human_review_needed": seed.get("content_quality_human_review_needed"),
            },
        ),
        _check(
            "asset_candidate_fixed_asset_path",
            seed.get("asset_card_candidate_count", 0) >= 1 and bool(report.get("fixed_asset_id")),
            {
                "asset_card_candidate_count": seed.get("asset_card_candidate_count", 0),
                "fixed_asset_id": report.get("fixed_asset_id", ""),
            },
        ),
        _check(
            "production_graph_fixed_asset_reuse",
            bool(report.get("production_graph_artifact_id")) and seed.get("fixed_visual_asset_count") == 1,
            {
                "production_graph_artifact_id": report.get("production_graph_artifact_id", ""),
                "relationship_count": seed.get("production_graph_relationship_count", 0),
                "fixed_visual_asset_count": seed.get("fixed_visual_asset_count", 0),
            },
        ),
        _check(
            "keyframe_preflight_blocked_bridge",
            bool(report.get("second_request_plan_artifact_id")) and bool(report.get("second_bridge_artifact_id")),
            {
                "second_request_plan_artifact_id": report.get("second_request_plan_artifact_id", ""),
                "second_bridge_artifact_id": report.get("second_bridge_artifact_id", ""),
            },
        ),
        _check(
            "feedback_overlay_human_gate_non_claim",
            report.get("feedback_overlay_decision_recorded") is True and bool(report.get("overlay_id")),
            {
                "overlay_id": report.get("overlay_id", ""),
                "feedback_overlay_decision_recorded": report.get("feedback_overlay_decision_recorded"),
            },
        ),
        _check(
            "provider_closed_browser_runtime",
            report.get("provider_calls_started") is False and report.get("console_error_count") == 0 and report.get("response_error_count") == 0,
            {
                "provider_calls_started": report.get("provider_calls_started"),
                "console_error_count": report.get("console_error_count"),
                "response_error_count": report.get("response_error_count"),
            },
        ),
    ]
    verdict = "internal_provider_closed_tryout_ready" if all(item["status"] == "passed" for item in checks) else "not_ready_with_blockers"
    return {
        "artifact_type": "afs_provider_closed_delivery_readiness_gate",
        "schema_version": "0.1.0",
        "verdict": verdict,
        "product_readiness": "provider_closed_internal_tryout_path_ready" if verdict == "internal_provider_closed_tryout_ready" else "not_ready",
        "quality_evidence": "real_script_runtime_studio_main_path_structure_verified",
        "governance_evidence": "provider_closed_non_claims_preserved",
        "checks": checks,
        "remaining_gates": [
            "provider_smoke_requires_explicit_authorization",
            "generated_media_quality_requires_provider_run_and_review",
            "human_creative_acceptance_not_claimed",
            "business_validation_not_claimed",
            "public_legal_patent_claim_not_made",
            "cos_active_rule_promotion_not_made",
        ],
    }


def _check(check_id: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"check_id": check_id, "status": "passed" if passed else "blocked", "evidence": evidence}
