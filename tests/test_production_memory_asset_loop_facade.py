from __future__ import annotations

from agentflow.memory import production_asset_loop as facade


def test_production_asset_loop_facade_exposes_stage_order_and_kinds() -> None:
    assert facade.asset_loop_stage_ids() == (
        "profile_readiness",
        "feedback_intake",
        "update_candidate",
        "promotion_versioning",
        "context_projection",
        "consistency_review",
    )

    kind_index = facade.asset_loop_kind_index()
    assert kind_index[facade.ASSET_TEST_PACKAGE_KIND] == "profile_readiness"
    assert kind_index[facade.ASSET_FEEDBACK_EVENT_KIND] == "feedback_intake"
    assert kind_index[facade.ASSET_PROFILE_UPDATE_CANDIDATE_KIND] == "update_candidate"
    assert kind_index[facade.ASSET_PROFILE_VERSION_KIND] == "promotion_versioning"
    assert kind_index[facade.ASSET_PROFILE_CONTEXT_PROJECTION_KIND] == "context_projection"
    assert kind_index[facade.ASSET_CONSISTENCY_REVIEW_KIND] == "consistency_review"


def test_production_asset_loop_facade_exports_core_builders_without_provider_clients() -> None:
    assert callable(facade.build_asset_profile_test_package)
    assert callable(facade.build_asset_feedback_event)
    assert callable(facade.build_asset_profile_update_candidate)
    assert callable(facade.build_asset_profile_promotion_review)
    assert callable(facade.build_asset_profile_context_projection)
    assert callable(facade.build_asset_consistency_review)
    assert callable(facade.write_asset_feedback_event)
    assert callable(facade.write_asset_profile_context_projection)
    assert "character" in facade.PROFILE_KINDS
    assert "scene" in facade.PROFILE_KINDS


def test_production_asset_loop_facade_keeps_non_claim_kinds_visible() -> None:
    exported = set(facade.__all__)

    assert "PROVIDER_VALIDATION_RESULT_KIND" in exported
    assert "build_asset_profile_test_package" in exported
    assert "build_asset_consistency_review" in exported
    assert facade.PROVIDER_VALIDATION_RESULT_KIND == "agentflow_production_memory_asset_provider_validation_result"
