from __future__ import annotations

from typing import Final

from agentflow.memory.production_asset_consistency_review import (
    ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
    ASSET_CONSISTENCY_REVIEW_KIND,
    build_asset_consistency_review,
    load_asset_consistency_review_fixture,
    load_asset_profile_context_projection,
    validate_asset_consistency_review_fixture,
    validate_asset_profile_context_projection,
    write_asset_consistency_review,
)
from agentflow.memory.production_asset_feedback import (
    ASSET_FEEDBACK_EVENT_KIND,
    ASSET_FEEDBACK_FIXTURE_KIND,
    build_asset_feedback_event,
    load_asset_feedback_fixture,
    validate_asset_feedback_fixture,
    write_asset_feedback_event,
)
from agentflow.memory.production_asset_profile_constants import (
    ASSET_PROFILE_KIND,
    ASSET_PROFILE_READINESS_KIND,
    ASSET_PROFILE_SEED_KIND,
    ASSET_TEST_PACKAGE_KIND,
    PROFILE_KINDS,
    PROVIDER_VALIDATION_BLOCKERS_KIND,
    PROVIDER_VALIDATION_PLAN_KIND,
    PROVIDER_VALIDATION_RESULT_KIND,
)
from agentflow.memory.production_asset_profile_context_projection import (
    ASSET_PROFILE_CONTEXT_PROJECTION_KIND,
    build_asset_profile_context_projection,
    load_asset_profile_version,
    write_asset_profile_context_projection,
)
from agentflow.memory.production_asset_profile_promotion import (
    ASSET_PROFILE_PROMOTION_DECISION_KIND,
    ASSET_PROFILE_VERSION_KIND,
    build_asset_profile_promotion_review,
    load_asset_profile_update_candidate,
    load_asset_profiles,
    write_asset_profile_promotion_review,
)
from agentflow.memory.production_asset_profile_update_candidate import (
    ASSET_PROFILE_UPDATE_CANDIDATE_KIND,
    build_asset_profile_update_candidate,
    load_asset_feedback_event,
    validate_asset_feedback_event,
    write_asset_profile_update_candidate,
)
from agentflow.memory.production_asset_profiles import (
    build_asset_profile_test_package,
    load_asset_profile_seed,
    validate_asset_profile_seed,
)

ASSET_LOOP_STAGES: Final[tuple[dict[str, str], ...]] = (
    {
        "stage_id": "profile_readiness",
        "input_kind": ASSET_PROFILE_SEED_KIND,
        "output_kind": ASSET_TEST_PACKAGE_KIND,
        "builder": "build_asset_profile_test_package",
        "next_stage_id": "feedback_intake",
    },
    {
        "stage_id": "feedback_intake",
        "input_kind": ASSET_FEEDBACK_FIXTURE_KIND,
        "output_kind": ASSET_FEEDBACK_EVENT_KIND,
        "builder": "build_asset_feedback_event",
        "next_stage_id": "update_candidate",
    },
    {
        "stage_id": "update_candidate",
        "input_kind": ASSET_FEEDBACK_EVENT_KIND,
        "output_kind": ASSET_PROFILE_UPDATE_CANDIDATE_KIND,
        "builder": "build_asset_profile_update_candidate",
        "next_stage_id": "promotion_versioning",
    },
    {
        "stage_id": "promotion_versioning",
        "input_kind": ASSET_PROFILE_UPDATE_CANDIDATE_KIND,
        "output_kind": ASSET_PROFILE_VERSION_KIND,
        "builder": "build_asset_profile_promotion_review",
        "next_stage_id": "context_projection",
    },
    {
        "stage_id": "context_projection",
        "input_kind": ASSET_PROFILE_VERSION_KIND,
        "output_kind": ASSET_PROFILE_CONTEXT_PROJECTION_KIND,
        "builder": "build_asset_profile_context_projection",
        "next_stage_id": "consistency_review",
    },
    {
        "stage_id": "consistency_review",
        "input_kind": ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
        "output_kind": ASSET_CONSISTENCY_REVIEW_KIND,
        "builder": "build_asset_consistency_review",
        "next_stage_id": "",
    },
)


def asset_loop_stage_ids() -> tuple[str, ...]:
    return tuple(stage["stage_id"] for stage in ASSET_LOOP_STAGES)


def asset_loop_kind_index() -> dict[str, str]:
    return {stage["output_kind"]: stage["stage_id"] for stage in ASSET_LOOP_STAGES}


__all__ = (
    "ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND",
    "ASSET_CONSISTENCY_REVIEW_KIND",
    "ASSET_FEEDBACK_EVENT_KIND",
    "ASSET_FEEDBACK_FIXTURE_KIND",
    "ASSET_LOOP_STAGES",
    "ASSET_PROFILE_CONTEXT_PROJECTION_KIND",
    "ASSET_PROFILE_KIND",
    "ASSET_PROFILE_PROMOTION_DECISION_KIND",
    "ASSET_PROFILE_READINESS_KIND",
    "ASSET_PROFILE_SEED_KIND",
    "ASSET_PROFILE_UPDATE_CANDIDATE_KIND",
    "ASSET_PROFILE_VERSION_KIND",
    "ASSET_TEST_PACKAGE_KIND",
    "PROFILE_KINDS",
    "PROVIDER_VALIDATION_BLOCKERS_KIND",
    "PROVIDER_VALIDATION_PLAN_KIND",
    "PROVIDER_VALIDATION_RESULT_KIND",
    "asset_loop_kind_index",
    "asset_loop_stage_ids",
    "build_asset_consistency_review",
    "build_asset_feedback_event",
    "build_asset_profile_context_projection",
    "build_asset_profile_promotion_review",
    "build_asset_profile_test_package",
    "build_asset_profile_update_candidate",
    "load_asset_consistency_review_fixture",
    "load_asset_feedback_event",
    "load_asset_feedback_fixture",
    "load_asset_profile_context_projection",
    "load_asset_profile_seed",
    "load_asset_profile_update_candidate",
    "load_asset_profile_version",
    "load_asset_profiles",
    "validate_asset_consistency_review_fixture",
    "validate_asset_feedback_event",
    "validate_asset_feedback_fixture",
    "validate_asset_profile_context_projection",
    "validate_asset_profile_seed",
    "write_asset_consistency_review",
    "write_asset_feedback_event",
    "write_asset_profile_context_projection",
    "write_asset_profile_promotion_review",
    "write_asset_profile_update_candidate",
)
