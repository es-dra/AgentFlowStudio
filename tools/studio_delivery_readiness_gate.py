from __future__ import annotations

from typing import Any


ACCEPTED_GENERATION_PLAN_CHECK_ID = "accepted_generation_plan_default_blocked_preview"


def build_delivery_readiness(report: dict[str, Any], seed: dict[str, Any]) -> dict[str, Any]:
    accepted_plan_evidence = _accepted_generation_plan_preview_evidence(report)
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
        _check(
            ACCEPTED_GENERATION_PLAN_CHECK_ID,
            _accepted_generation_plan_preview_passed(accepted_plan_evidence),
            accepted_plan_evidence,
        ),
    ]
    verdict = "internal_provider_closed_tryout_ready" if all(item["status"] == "passed" for item in checks) else "not_ready_with_blockers"
    return {
        "artifact_type": "afs_provider_closed_delivery_readiness_gate",
        "schema_version": "0.1.0",
        "verdict": verdict,
        "product_readiness": "not_product_readiness_provider_closed_tryout_only",
        "quality_evidence": "real_script_runtime_studio_main_path_and_plan_modal_structure_verified",
        "governance_evidence": "provider_closed_non_claims_preserved",
        "checks": checks,
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
    }


def _check(check_id: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"check_id": check_id, "status": "passed" if passed else "blocked", "evidence": evidence}


def _accepted_generation_plan_preview_evidence(report: dict[str, Any]) -> dict[str, Any]:
    source = report.get("accepted_generation_plan_modal")
    source = source if isinstance(source, dict) else {}
    explicit_non_claims = source.get("explicit_non_claims") if isinstance(source.get("explicit_non_claims"), list) else []
    return {
        "modal_opened": source.get("modal_opened") is True,
        "default_fixture_mode": source.get("default_fixture_mode", ""),
        "preview_status": source.get("preview_status", ""),
        "job_status": source.get("job_status", ""),
        "packet_state": source.get("packet_state", ""),
        "accepted": source.get("accepted"),
        "source_mode": source.get("source_mode", ""),
        "fixture_demo_non_acceptance": source.get("fixture_demo_non_acceptance"),
        "provider_calls_started": source.get("provider_calls_started"),
        "provider_gate": source.get("provider_gate", ""),
        "provider_smoke_claimed": source.get("provider_smoke_claimed"),
        "generated_media_quality_claimed": source.get("generated_media_quality_claimed"),
        "product_readiness_claimed": source.get("product_readiness_claimed"),
        "human_creative_acceptance_claimed": source.get("human_creative_acceptance_claimed"),
        "business_validation_claimed": source.get("business_validation_claimed"),
        "deploy_runtime_health_claimed": source.get("deploy_runtime_health_claimed"),
        "cos_active_rule_promotion_claimed": source.get("cos_active_rule_promotion_claimed"),
        "explicit_non_claims": explicit_non_claims,
        "artifact_id": source.get("artifact_id", ""),
        "job_id": source.get("job_id", ""),
        "rendered_blocked_status": source.get("rendered_blocked_status") is True,
        "rendered_provider_not_started": source.get("rendered_provider_not_started") is True,
        "rendered_product_readiness_not_claimed": source.get("rendered_product_readiness_not_claimed") is True,
    }


def _accepted_generation_plan_preview_passed(evidence: dict[str, Any]) -> bool:
    required_non_claims = {
        "not_provider_smoke",
        "not_generated_media_qa",
        "not_product_readiness",
        "not_human_creative_acceptance",
        "not_business_validation",
        "not_deploy_runtime_health",
        "fixture_demo_not_acceptance",
    }
    explicit_non_claims = set(evidence.get("explicit_non_claims") or [])
    claim_values = (
        evidence.get("provider_smoke_claimed"),
        evidence.get("generated_media_quality_claimed"),
        evidence.get("product_readiness_claimed"),
        evidence.get("human_creative_acceptance_claimed"),
        evidence.get("business_validation_claimed"),
        evidence.get("deploy_runtime_health_claimed"),
        evidence.get("cos_active_rule_promotion_claimed"),
    )
    return (
        evidence.get("modal_opened") is True
        and evidence.get("default_fixture_mode") == "default_unconfirmed"
        and evidence.get("preview_status") == "blocked"
        and evidence.get("job_status") == "blocked"
        and evidence.get("accepted") is False
        and evidence.get("source_mode") == "fixture_demo"
        and evidence.get("fixture_demo_non_acceptance") is True
        and evidence.get("provider_calls_started") is False
        and evidence.get("provider_gate") == "closed"
        and all(item is False for item in claim_values)
        and required_non_claims.issubset(explicit_non_claims)
        and evidence.get("artifact_id")
        and evidence.get("job_id")
        and evidence.get("rendered_blocked_status") is True
        and evidence.get("rendered_provider_not_started") is True
        and evidence.get("rendered_product_readiness_not_claimed") is True
    )
