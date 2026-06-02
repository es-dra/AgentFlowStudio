from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS, PASSED
from agentflow.memory.production_asset_profile_constants import ASSET_PROFILE_KIND, ASSET_PROFILE_READINESS_KIND
from agentflow.memory.production_loop import SCHEMA_VERSION
from narratocut.utils import write_json

ASSET_FEEDBACK_FIXTURE_KIND = "agentflow_production_memory_asset_feedback_fixture"
ASSET_FEEDBACK_EVENT_KIND = "agentflow_production_memory_asset_feedback_event"
SUPPORTED_FEEDBACK_INPUT_TYPES = frozenset({"json_fixture", "markdown_derived_fixture"})
REVIEW_DIMENSIONS = frozenset(
    {
        "character_identity",
        "wardrobe_or_body_anchor",
        "scene_spatial_anchor",
        "lighting_or_time_anchor",
        "negative_constraint_violations",
        "allowed_variation_fit",
        "overall_result",
    }
)
REVIEW_RESULTS = frozenset({"kept", "partially_kept", "not_kept", "cannot_judge"})
FAILURE_ATTRIBUTIONS = frozenset(
    {
        "prompt_issue",
        "context_issue",
        "profile_issue",
        "reference_asset_issue",
        "model_capability_issue",
        "style_drift",
        "character_inconsistency",
        "scene_inconsistency",
        "unknown",
    }
)
SUGGESTED_NEXT_STATES = frozenset({"candidate", "promoted", "blocked", "retired", "no_change", "cannot_judge"})
UNSAFE_EXTRA_FRAGMENTS = (
    "http://",
    "https://",
    "file://",
    "data:image/",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".mp4",
    ".mov",
    "private-user-images",
    "authorization",
    "bearer",
    "provider result url",
)


def load_asset_feedback_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("asset feedback fixture must be a JSON object")
    validate_asset_feedback_fixture(payload)
    return payload


def validate_asset_feedback_fixture(fixture: dict[str, Any]) -> None:
    if fixture.get("kind") != ASSET_FEEDBACK_FIXTURE_KIND:
        raise ValueError(f"asset feedback fixture requires kind {ASSET_FEEDBACK_FIXTURE_KIND}")
    if fixture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"asset feedback fixture requires schema_version {SCHEMA_VERSION}")
    _require_text(fixture, "feedback_event_id")
    _require_text(fixture, "project_id")
    _require_text(fixture, "source_test_package_ref")
    _require_text(fixture, "source_readiness_ref")
    _require_text(fixture, "profile_id")
    _require_text(fixture, "profile_kind")
    if fixture.get("source_feedback_input_type") not in SUPPORTED_FEEDBACK_INPUT_TYPES:
        raise ValueError("asset feedback fixture source_feedback_input_type is unsupported")
    if fixture.get("review_dimension") not in REVIEW_DIMENSIONS:
        raise ValueError("asset feedback fixture review_dimension is unsupported")
    if fixture.get("review_result") not in REVIEW_RESULTS:
        raise ValueError("asset feedback fixture review_result is unsupported")
    if fixture.get("failure_attribution") not in FAILURE_ATTRIBUTIONS:
        raise ValueError("asset feedback fixture failure_attribution is unsupported")
    if fixture.get("suggested_next_state") not in SUGGESTED_NEXT_STATES:
        raise ValueError("asset feedback fixture suggested_next_state is unsupported")
    _reject_unsafe(fixture)


def build_asset_feedback_event(
    *,
    asset_profiles: dict[str, Any],
    asset_profile_readiness: dict[str, Any],
    feedback_fixture: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Record tester feedback as evidence only, without promotion side effects."""
    validate_asset_profiles(asset_profiles)
    validate_asset_profile_readiness(asset_profile_readiness)
    validate_asset_feedback_fixture(feedback_fixture)
    _require_text({"generated_at": generated_at}, "generated_at")

    profile = _profile_by_id(asset_profiles, str(feedback_fixture["profile_id"]))
    if profile is None:
        raise ValueError(f"profile_id does not exist in asset_profiles: {feedback_fixture['profile_id']}")
    if profile.get("profile_kind") != feedback_fixture.get("profile_kind"):
        raise ValueError("asset feedback fixture profile_kind does not match target profile")

    event = {
        "kind": ASSET_FEEDBACK_EVENT_KIND,
        "artifact_type": ASSET_FEEDBACK_EVENT_KIND,
        "schema_version": SCHEMA_VERSION,
        "feedback_event_id": _safe_id(
            "asset-feedback",
            str(feedback_fixture["profile_id"]),
            str(feedback_fixture["review_dimension"]),
            generated_at,
        ),
        "source_feedback_fixture_id": feedback_fixture.get("feedback_event_id"),
        "generated_at": generated_at,
        "project_id": feedback_fixture.get("project_id", asset_profile_readiness.get("project_id", "unknown")),
        "source_test_package_ref": feedback_fixture["source_test_package_ref"],
        "source_readiness_ref": feedback_fixture["source_readiness_ref"],
        "source_readiness_status": asset_profile_readiness.get("readiness_status", "unknown"),
        "source_feedback_input_type": feedback_fixture["source_feedback_input_type"],
        "parse_status": "parsed",
        "profile_id": profile.get("profile_id"),
        "profile_kind": profile.get("profile_kind"),
        "target_profile_status": profile.get("profile_status", "unknown"),
        "target_profile_context_eligible": _profile_context_eligible(profile),
        "target_profile_next_context_unlocked": False,
        "review_dimension": feedback_fixture["review_dimension"],
        "review_result": feedback_fixture["review_result"],
        "review_result_effect": _review_result_effect(str(feedback_fixture["review_result"])),
        "drift_observations": list(_list(feedback_fixture.get("drift_observations"))),
        "violated_constraints": list(_list(feedback_fixture.get("violated_constraints"))),
        "failure_attribution": feedback_fixture["failure_attribution"],
        "suggested_next_state": feedback_fixture["suggested_next_state"],
        "evidence_refs": list(_list(feedback_fixture.get("evidence_refs"))),
        "reviewer_role": feedback_fixture.get("reviewer_role", "tester"),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "feedback_is_memory": False,
        "creates_memory_candidate": False,
        "creates_promotion_decision": False,
        "redaction_checks": {
            "status": PASSED,
            "blocked_fragments": [],
            "checked_fields": [
                "source refs",
                "drift observations",
                "violated constraints",
                "evidence refs",
                "reviewer role",
            ],
        },
        "claim_boundaries": _claim_boundaries(),
        "non_claims": _non_claims(),
    }
    _reject_unsafe(event)
    return event


def write_asset_feedback_event(event: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "asset_feedback_event.json", event)
    md_path = output_root / "asset_feedback_event.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_asset_feedback_markdown(event), encoding="utf-8")
    return [json_path, md_path]


def render_asset_feedback_markdown(event: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Production Memory Asset Feedback Event",
            "",
            f"Parse status: {event.get('parse_status', 'unknown')}",
            f"Profile: {event.get('profile_id', 'unknown')}",
            f"Profile kind: {event.get('profile_kind', 'unknown')}",
            f"Review dimension: {event.get('review_dimension', 'unknown')}",
            f"Review result: {event.get('review_result', 'unknown')}",
            f"Result effect: {event.get('review_result_effect', 'unknown')}",
            f"Suggested next state: {event.get('suggested_next_state', 'unknown')}",
            "Provider calls: not started",
            "Feedback is memory: false",
            "Creates promotion decision: false",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
            "## Drift Observations",
            "",
            "\n".join(f"- {item}" for item in _list(event.get("drift_observations"))) or "- none",
            "",
            "## Violated Constraints",
            "",
            "\n".join(f"- {item}" for item in _list(event.get("violated_constraints"))) or "- none",
            "",
        ]
    )


def validate_asset_profiles(asset_profiles: dict[str, Any]) -> None:
    profiles = _list(asset_profiles.get("profiles"))
    if not profiles:
        raise ValueError("asset feedback requires asset_profiles.profiles")
    for profile in profiles:
        item = _dict(profile)
        if item.get("kind") != ASSET_PROFILE_KIND:
            raise ValueError(f"asset feedback profile requires kind {ASSET_PROFILE_KIND}")
        _require_text(item, "profile_id")
        _require_text(item, "profile_kind")
    _reject_unsafe(asset_profiles)


def validate_asset_profile_readiness(readiness: dict[str, Any]) -> None:
    if readiness.get("kind") != ASSET_PROFILE_READINESS_KIND:
        raise ValueError(f"asset feedback readiness requires kind {ASSET_PROFILE_READINESS_KIND}")
    if readiness.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"asset feedback readiness requires schema_version {SCHEMA_VERSION}")
    _require_text(readiness, "project_id")
    _reject_unsafe(readiness)


def _profile_by_id(asset_profiles: dict[str, Any], profile_id: str) -> dict[str, Any] | None:
    for profile in _list(asset_profiles.get("profiles")):
        item = _dict(profile)
        if item.get("profile_id") == profile_id:
            return item
    return None


def _profile_context_eligible(profile: dict[str, Any]) -> bool:
    return profile.get("context_eligibility") == "included" and profile.get("usable_for_next_context") is True


def _review_result_effect(result: str) -> str:
    if result == "kept":
        return "positive_signal"
    if result == "cannot_judge":
        return "neutral"
    return "needs_review"


def _claim_boundaries() -> dict[str, str]:
    return {
        "human_acceptance": "not_claimed",
        "business_validation": "not_validated",
        "provider_success": "not_attempted",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
        "memory_promotion": "not_performed",
        "profile_promotion": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "not memory",
        "not memory candidate",
        "not promotion decision",
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not provider success",
        "not Company KB promotion",
    ]


def _safe_id(*parts: str) -> str:
    raw = ":".join(parts)
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("asset feedback contains private fragments, media bytes, provider URL, or secret")


def _require_text(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"asset feedback requires {field}")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
