from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS, PASSED
from agentflow.memory.production_asset_feedback import ASSET_FEEDBACK_EVENT_KIND
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.harness.json_io import write_json

ASSET_PROFILE_UPDATE_CANDIDATE_KIND = "agentflow_production_memory_asset_profile_update_candidate"
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


def load_asset_feedback_event(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("asset feedback event must be a JSON object")
    validate_asset_feedback_event(payload)
    return payload


def build_asset_profile_update_candidate(event: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    """Draft a profile update candidate from asset feedback without applying it."""
    validate_asset_feedback_event(event)
    _require_text({"generated_at": generated_at}, "generated_at")

    feedback_id = str(event["feedback_event_id"])
    patch_ops = _patch_ops(event)
    candidate = {
        "kind": ASSET_PROFILE_UPDATE_CANDIDATE_KIND,
        "artifact_type": ASSET_PROFILE_UPDATE_CANDIDATE_KIND,
        "schema_version": event.get("schema_version", SCHEMA_VERSION),
        "candidate_id": _safe_id(
            "asset-profile-update-candidate",
            str(event["profile_id"]),
            str(event["review_dimension"]),
            generated_at,
        ),
        "generated_at": generated_at,
        "candidate_generation_status": _candidate_status(event, patch_ops),
        "project_id": event.get("project_id", "unknown"),
        "source_feedback_event_id": feedback_id,
        "source_feedback_input_type": event.get("source_feedback_input_type", "unknown"),
        "source_test_package_ref": event.get("source_test_package_ref", "unknown"),
        "source_readiness_ref": event.get("source_readiness_ref", "unknown"),
        "source_readiness_status": event.get("source_readiness_status", "unknown"),
        "profile_id": event.get("profile_id"),
        "profile_kind": event.get("profile_kind"),
        "target_profile_status": event.get("target_profile_status", "unknown"),
        "target_profile_context_eligible": event.get("target_profile_context_eligible") is True,
        "target_profile_next_context_unlocked": False,
        "review_dimension": event.get("review_dimension"),
        "review_result": event.get("review_result"),
        "review_result_effect": event.get("review_result_effect"),
        "failure_attribution": event.get("failure_attribution", "unknown"),
        "suggested_next_state": event.get("suggested_next_state", "unknown"),
        "drift_observations": list(_list(event.get("drift_observations"))),
        "violated_constraints": list(_list(event.get("violated_constraints"))),
        "evidence_refs": _candidate_evidence_refs(event),
        "proposed_profile_patch": {
            "patch_strategy": "operator_review_required",
            "patch_ops": patch_ops,
            "applies_profile_version": False,
        },
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "feedback_is_memory": False,
        "source_feedback_is_memory": False,
        "candidate_is_promoted_memory": False,
        "candidate_is_promoted_profile": False,
        "creates_promotion_decision": False,
        "applies_profile_version": False,
        "redaction_checks": {
            "status": PASSED,
            "blocked_fragments": [],
            "checked_fields": ["feedback event", "patch ops", "evidence refs"],
        },
        "claim_boundaries": _claim_boundaries(),
        "non_claims": _non_claims(),
    }
    _reject_unsafe(candidate)
    return candidate


def validate_asset_feedback_event(event: dict[str, Any]) -> None:
    if event.get("kind") != ASSET_FEEDBACK_EVENT_KIND:
        raise ValueError(f"asset profile update candidate requires kind {ASSET_FEEDBACK_EVENT_KIND}")
    for field in ("feedback_event_id", "project_id", "profile_id", "profile_kind", "review_dimension", "review_result"):
        _require_text(event, field)
    if event.get("provider_mode") != "no-provider":
        raise ValueError("asset profile update candidate requires no-provider feedback")
    if event.get("provider_calls_started") is not False:
        raise ValueError("asset profile update candidate requires provider_calls_started false")
    if event.get("writes_long_term_memory") is not False:
        raise ValueError("asset profile update candidate requires writes_long_term_memory false")
    if event.get("writes_company_kb") is not False:
        raise ValueError("asset profile update candidate requires writes_company_kb false")
    if event.get("feedback_is_memory") is not False:
        raise ValueError("asset profile update candidate requires feedback_is_memory false")
    if event.get("creates_memory_candidate") is not False:
        raise ValueError("asset profile update candidate requires source feedback to create no memory candidate")
    if event.get("creates_promotion_decision") is not False:
        raise ValueError("asset profile update candidate requires source feedback to create no promotion decision")
    _reject_unsafe(event)


def write_asset_profile_update_candidate(candidate: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "asset_profile_update_candidate.json", candidate)
    md_path = output_root / "asset_profile_update_candidate.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_asset_profile_update_candidate_markdown(candidate), encoding="utf-8")
    return [json_path, md_path]


def render_asset_profile_update_candidate_markdown(candidate: dict[str, Any]) -> str:
    patch = _dict(candidate.get("proposed_profile_patch"))
    return "\n".join(
        [
            "# Production Memory Asset Profile Update Candidate",
            "",
            f"Status: {candidate.get('candidate_generation_status', 'unknown')}",
            f"Profile: {candidate.get('profile_id', 'unknown')}",
            f"Review result: {candidate.get('review_result', 'unknown')}",
            f"Patch ops: {len(_list(patch.get('patch_ops')))}",
            "Provider calls: not started",
            "Creates promotion decision: false",
            "Applies profile version: false",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
        ]
    )


def _patch_ops(event: dict[str, Any]) -> list[dict[str, Any]]:
    if event.get("review_result") == "cannot_judge":
        return []
    if event.get("review_result") == "kept" and event.get("suggested_next_state") == "no_change":
        return []

    feedback_id = str(event["feedback_event_id"])
    ops = [
        {
            "op": "add_unique",
            "path": "/negative_constraints/-",
            "value": str(item),
            "rationale": "Tester reported this violated constraint.",
            "evidence_refs": [feedback_id],
        }
        for item in _dedupe(_list(event.get("violated_constraints")))
    ]
    if ops:
        ops.append(
            {
                "op": "add_unique",
                "path": "/evidence_refs/-",
                "value": feedback_id,
                "rationale": "Link profile update candidate to the tester feedback event.",
                "evidence_refs": [feedback_id],
            }
        )
    return ops


def _candidate_status(event: dict[str, Any], patch_ops: list[dict[str, Any]]) -> str:
    if event.get("review_result") == "cannot_judge":
        return "blocked_cannot_judge"
    if event.get("review_result") == "kept" and not patch_ops:
        return "no_update_recommended"
    if not patch_ops:
        return "blocked_missing_patch_ops"
    return "candidate_only"


def _candidate_evidence_refs(event: dict[str, Any]) -> list[str]:
    refs = [str(item) for item in _list(event.get("evidence_refs"))]
    refs.append(str(event["feedback_event_id"]))
    return _dedupe(refs)


def _claim_boundaries() -> dict[str, str]:
    return {
        "human_acceptance": "not_claimed",
        "business_validation": "not_validated",
        "provider_success": "not_attempted",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
        "profile_promotion": "not_performed",
        "profile_versioning": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "not a profile version",
        "not a profile promotion decision",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
        "not human acceptance",
        "not business validation",
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
        raise ValueError("asset profile update candidate contains private fragments, media bytes, provider URL, or secret")


def _require_text(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"asset profile update candidate requires {field}")


def _dedupe(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value)
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
