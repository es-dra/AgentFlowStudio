from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS, FAILED, PASSED
from agentflow.memory.production_asset_profile_constants import (
    ASSET_PROFILE_KIND,
    ASSET_PROFILE_READINESS_KIND,
    ASSET_PROFILE_SEED_KIND,
    ASSET_TEST_PACKAGE_KIND,
    CONTEXT_ELIGIBILITY,
    PROFILE_KINDS,
    PROFILE_STATUSES,
)
from agentflow.memory.production_asset_profile_context import (
    context_index,
    load_operator_context,
    profile_blocked_refs,
    profiles_have_promotion_refs_for_memory,
)
from agentflow.memory.production_asset_profile_io import write_asset_profile_test_package
from agentflow.memory.production_asset_profile_provider import (
    build_provider_validation_plan,
    provider_status,
    provider_validation_blockers,
    run_provider_validation as execute_provider_validation,
)
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND
from agentflow.memory.production_operator_run_package import OPERATOR_RUN_PACKAGE_KIND


def load_asset_profile_seed(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("asset profile seed must be a JSON object")
    validate_asset_profile_seed(payload)
    return payload


def validate_asset_profile_seed(seed: dict[str, Any]) -> None:
    if seed.get("kind") != ASSET_PROFILE_SEED_KIND:
        raise ValueError(f"asset profile seed requires kind {ASSET_PROFILE_SEED_KIND}")
    if seed.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"asset profile seed requires schema_version {SCHEMA_VERSION}")
    if _has_private_fragment(seed):
        raise ValueError("asset profile seed must not include private paths or secrets")
    profiles = _list(seed.get("profiles"))
    if not profiles:
        raise ValueError("asset profile seed requires at least one profile")
    for profile in profiles:
        _validate_profile_seed(_dict(profile))


def build_asset_profile_test_package(
    *,
    operator_artifact_path: Path,
    asset_profile_seed: dict[str, Any],
    generated_at: str,
    project_materials_path: Path | None = None,
    character_reference_image_path: Path | None = None,
    provider_config_path: Path | None = None,
    run_provider_validation: bool = False,
    image_service: str = "minimax_image",
    video_service: str = "kling_i2v",
) -> dict[str, Any]:
    validate_asset_profile_seed(asset_profile_seed)
    operator_context = load_operator_context(operator_artifact_path)
    profiles = [_build_profile(_dict(item), asset_profile_seed, operator_context) for item in asset_profile_seed["profiles"]]
    readiness = _build_readiness(asset_profile_seed, operator_context, profiles, generated_at=generated_at)
    provider_plan = build_provider_validation_plan(
        asset_profile_seed,
        generated_at=generated_at,
        run_provider_validation=run_provider_validation,
        provider_config_path=provider_config_path,
        project_materials_path=project_materials_path,
        character_reference_image_path=character_reference_image_path,
        image_service=image_service,
        video_service=video_service,
    )
    blockers = provider_validation_blockers(
        provider_plan,
        provider_config_path=provider_config_path,
        character_reference_image_path=character_reference_image_path,
        image_service=image_service,
    )
    result = None
    if run_provider_validation and not blockers:
        result = execute_provider_validation(
            asset_profile_seed,
            provider_config_path=provider_config_path,
            character_reference_image_path=character_reference_image_path,
            image_service=image_service,
            video_service=video_service,
        )
        if result.get("status") != "succeeded":
            blockers = result.get("blockers", [])
    return {
        "asset_profiles": profiles,
        "readiness": readiness,
        "test_package": _build_test_package(
            asset_profile_seed,
            operator_context,
            readiness,
            profiles,
            provider_plan,
            blockers,
            generated_at=generated_at,
        ),
        "provider_validation_plan": provider_plan,
        "provider_validation_blockers": blockers,
        "provider_validation_result": result,
    }


def _build_profile(seed_profile: dict[str, Any], seed: dict[str, Any], operator_context: dict[str, Any]) -> dict[str, Any]:
    blocked_refs = profile_blocked_refs(seed_profile, operator_context)
    usable = (
        seed_profile.get("profile_status") == "promoted"
        and seed_profile.get("context_eligibility") == "included"
        and not blocked_refs
    )
    return {
        "kind": ASSET_PROFILE_KIND,
        "artifact_type": ASSET_PROFILE_KIND,
        "schema_version": SCHEMA_VERSION,
        "profile_id": seed_profile.get("profile_id"),
        "profile_kind": seed_profile.get("profile_kind"),
        "display_name": seed_profile.get("display_name"),
        "project_id": seed.get("project_id", "unknown"),
        "profile_scope": seed_profile.get("profile_scope", "project"),
        "profile_version": seed_profile.get("profile_version", "v1"),
        "supersedes_profile_id": seed_profile.get("supersedes_profile_id"),
        "profile_status": seed_profile.get("profile_status", "candidate"),
        "context_eligibility": seed_profile.get("context_eligibility", "not_requested"),
        "usable_for_next_context": usable,
        "allowed_variations": list(_list(seed_profile.get("allowed_variations"))),
        "negative_constraints": list(_list(seed_profile.get("negative_constraints"))),
        "evidence_refs": list(_list(seed_profile.get("evidence_refs"))),
        "promotion_decision_refs": list(_list(seed_profile.get("promotion_decision_refs"))),
        "blockers": blocked_refs,
        "confidence": seed_profile.get("confidence", "tester_review_required"),
        "evidence_strength": seed_profile.get("evidence_strength", "unknown"),
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _build_readiness(
    seed: dict[str, Any],
    operator_context: dict[str, Any],
    profiles: list[dict[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    blocked_refs = _dedupe_blockers([item for profile in profiles for item in _list(profile.get("blockers"))])
    controls = _readiness_controls(seed, operator_context, profiles, blocked_refs)
    failed = any(item["status"] == FAILED for item in controls)
    status = "blocked_invalid_refs" if blocked_refs else "blocked_invalid_profile_seed" if failed else "ready_for_tester_review"
    return {
        "kind": ASSET_PROFILE_READINESS_KIND,
        "artifact_type": ASSET_PROFILE_READINESS_KIND,
        "schema_version": SCHEMA_VERSION,
        "readiness_id": f"asset-profile-readiness:{seed.get('seed_id', 'unknown')}",
        "generated_at": generated_at,
        "project_id": seed.get("project_id", "unknown"),
        "operator_artifact_kind": operator_context["artifact_kind"],
        "readiness_status": status,
        "profile_count": len(profiles),
        "ready_profile_count": len([item for item in profiles if item.get("usable_for_next_context") is True]),
        "blocked_refs": blocked_refs,
        "controls": controls,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _build_test_package(
    seed: dict[str, Any],
    operator_context: dict[str, Any],
    readiness: dict[str, Any],
    profiles: list[dict[str, Any]],
    provider_plan: dict[str, Any],
    provider_blockers: list[dict[str, str]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    ready = readiness.get("readiness_status") == "ready_for_tester_review"
    return {
        "kind": ASSET_TEST_PACKAGE_KIND,
        "artifact_type": ASSET_TEST_PACKAGE_KIND,
        "schema_version": SCHEMA_VERSION,
        "package_id": f"asset-test-package:{seed.get('seed_id', 'unknown')}",
        "generated_at": generated_at,
        "project_id": seed.get("project_id", "unknown"),
        "source_operator_artifact_kind": operator_context["artifact_kind"],
        "package_status": "ready_for_tester_review" if ready else "blocked",
        "profile_ids": [str(item.get("profile_id")) for item in profiles],
        "readiness_status": readiness.get("readiness_status"),
        "tester_outputs": [
            "asset_profiles.json",
            "asset_profile_readiness.json",
            "asset_consistency_rubric.md",
            "tester_feedback_template.md",
        ],
        "provider_validation": {
            "status": provider_status(provider_plan, provider_blockers),
            "plan_ref": "provider_validation_plan.json",
            "blockers_ref": "provider_validation_blockers.json",
        },
        "local_input_policy": {
            "project_material_paths_persisted": False,
            "character_reference_image_path_persisted": False,
            "provider_config_path_persisted": False,
        },
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": [
            "not human acceptance",
            "not business validation",
            "not durable memory",
            "not Company KB promotion",
            "not provider success unless provider_validation_result.json says succeeded",
        ],
    }


def _readiness_controls(
    seed: dict[str, Any],
    operator_context: dict[str, Any],
    profiles: list[dict[str, Any]],
    blocked_refs: list[dict[str, str]],
) -> list[dict[str, str]]:
    context = context_index(operator_context)
    return [
        _control("operator_artifact_loaded", operator_context["artifact_kind"] in {OPERATOR_LOOP_KIND, OPERATOR_RUN_PACKAGE_KIND}),
        _control("asset_profile_seed_loaded", seed.get("kind") == ASSET_PROFILE_SEED_KIND),
        _control("profiles_present", bool(profiles)),
        _control("profile_refs_resolve", not blocked_refs),
        _control("feedback_is_not_memory", not any(ref.startswith("feedback:") for ref in context["allowed"])),
        _control("candidate_is_not_promoted_memory", profiles_have_promotion_refs_for_memory(profiles)),
        _control("profile_writes_no_durable_memory", all(item.get("writes_long_term_memory") is False for item in profiles)),
        _control("profile_writes_no_company_kb", all(item.get("writes_company_kb") is False for item in profiles)),
    ]


def _validate_profile_seed(profile: dict[str, Any]) -> None:
    if not profile.get("profile_id"):
        raise ValueError("asset profile seed profile requires profile_id")
    if profile.get("profile_kind") not in PROFILE_KINDS:
        raise ValueError("asset profile seed profile_kind must be character or scene")
    if profile.get("profile_status") not in PROFILE_STATUSES:
        raise ValueError("asset profile seed profile_status is unsupported")
    if profile.get("context_eligibility") not in CONTEXT_ELIGIBILITY:
        raise ValueError("asset profile seed context_eligibility is unsupported")
    if not _list(profile.get("allowed_variations")):
        raise ValueError("asset profile seed requires allowed_variations")
    if not _list(profile.get("negative_constraints")):
        raise ValueError("asset profile seed requires negative_constraints")
    if not _list(profile.get("evidence_refs")):
        raise ValueError("asset profile seed requires evidence_refs")


def _dedupe_blockers(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for item in items:
        key = (str(item.get("ref_id", "")), str(item.get("reason", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append({"ref_id": key[0], "reason": key[1]})
    return result


def _has_private_fragment(payload: Any) -> bool:
    raw_text = str(payload).lower()
    return any(fragment.lower() in raw_text for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS)


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "ASSET_PROFILE_KIND",
    "ASSET_PROFILE_READINESS_KIND",
    "ASSET_PROFILE_SEED_KIND",
    "ASSET_TEST_PACKAGE_KIND",
    "build_asset_profile_test_package",
    "load_asset_profile_seed",
    "validate_asset_profile_seed",
    "write_asset_profile_test_package",
)
