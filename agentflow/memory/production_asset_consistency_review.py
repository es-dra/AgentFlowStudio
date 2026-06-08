from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.harness.json_io import write_json
from agentflow.memory.production_asset_consistency_review_render import render_asset_consistency_review_markdown
from agentflow.memory.production_asset_consistency_review_validation import (
    ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
    dict_value,
    reject_unsafe,
    require_text,
    validate_asset_consistency_review_fixture,
    validate_asset_profile_context_projection,
)
from agentflow.memory.production_asset_profile_promotion_utils import list_value
from agentflow.memory.production_loop import SCHEMA_VERSION

ASSET_CONSISTENCY_REVIEW_KIND = "agentflow_production_memory_asset_consistency_review"


def load_asset_consistency_review_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("asset consistency review fixture must be a JSON object")
    validate_asset_consistency_review_fixture(payload)
    return payload


def load_asset_profile_context_projection(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("asset profile context projection must be a JSON object")
    validate_asset_profile_context_projection(payload)
    return payload


def build_asset_consistency_review(
    *,
    asset_profile_context_projection: dict[str, Any],
    consistency_fixture: dict[str, Any],
    reviewed_at: str,
) -> dict[str, Any]:
    validate_asset_profile_context_projection(asset_profile_context_projection)
    validate_asset_consistency_review_fixture(consistency_fixture)
    require_text({"reviewed_at": reviewed_at}, "reviewed_at")
    if consistency_fixture["source_context_projection_ref"] != asset_profile_context_projection["projection_id"]:
        raise ValueError("asset consistency review source_context_projection_ref does not match projection_id")
    if consistency_fixture["project_id"] != asset_profile_context_projection["project_id"]:
        raise ValueError("asset consistency review project_id does not match projection project_id")

    included_by_ref = _refs_by_id(asset_profile_context_projection.get("included_refs"))
    blocked_by_ref = _refs_by_id(asset_profile_context_projection.get("blocked_refs"))
    findings: list[dict[str, Any]] = []
    blocked_findings: list[dict[str, Any]] = []
    for item in list_value(consistency_fixture.get("review_items")):
        item_obj = dict_value(item)
        profile_ref = str(item_obj.get("profile_ref", "unknown"))
        if profile_ref in included_by_ref:
            finding = _finding(item_obj, included_by_ref[profile_ref])
            if finding["profile_kind"] != item_obj.get("profile_kind"):
                blocked_findings.append(_blocked_finding(item_obj, "profile_kind_mismatch"))
            else:
                findings.append(finding)
        elif profile_ref in blocked_by_ref:
            blocked_findings.append(
                _blocked_finding(
                    item_obj,
                    "blocked_profile_ref",
                    source_block_reason=str(blocked_by_ref[profile_ref].get("reason", "blocked")),
                )
            )
        else:
            blocked_findings.append(_blocked_finding(item_obj, "unknown_profile_ref"))

    controls = _controls(asset_profile_context_projection, consistency_fixture, findings, blocked_findings)
    review_status = "ready_for_operator_review" if all(control["status"] == PASSED for control in controls) else "blocked"
    review = {
        "kind": ASSET_CONSISTENCY_REVIEW_KIND,
        "artifact_type": ASSET_CONSISTENCY_REVIEW_KIND,
        "schema_version": asset_profile_context_projection.get("schema_version", SCHEMA_VERSION),
        "review_id": _safe_id("asset-consistency-review", consistency_fixture["fixture_id"], reviewed_at),
        "reviewed_at": reviewed_at,
        "project_id": consistency_fixture["project_id"],
        "source_context_projection_ref": consistency_fixture["source_context_projection_ref"],
        "source_result_ref": consistency_fixture["source_result_ref"],
        "source_feedback_input_type": consistency_fixture["source_feedback_input_type"],
        "comparison_scope": consistency_fixture["comparison_scope"],
        "review_status": review_status,
        "overall_consistency_result": _overall_result(findings, blocked_findings),
        "included_profile_refs": list_value(asset_profile_context_projection.get("included_refs")),
        "blocked_profile_refs": list_value(asset_profile_context_projection.get("blocked_refs")),
        "consistency_findings": findings,
        "blocked_findings": blocked_findings,
        "context_trace": {
            "projection_policy": dict_value(asset_profile_context_projection.get("context_payload")).get(
                "context_projection_policy",
                "unknown",
            ),
            "included_profile_ref_count": len(included_by_ref),
            "blocked_profile_ref_count": len(blocked_by_ref),
            "fixture_review_item_count": len(list_value(consistency_fixture.get("review_items"))),
        },
        "controls": controls,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "creates_asset_feedback_event": False,
        "creates_profile_update_candidate": False,
        "creates_promotion_decision": False,
        "redaction_checks": {
            "status": PASSED,
            "blocked_fragments": [],
            "checked_fields": ["source refs", "output refs", "drift observations", "violated constraints"],
        },
        "claim_boundaries": _claim_boundaries(),
        "non_claims": _non_claims(),
    }
    reject_unsafe(review)
    return review


def write_asset_consistency_review(review: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "asset_consistency_review.json", review)
    md_path = output_root / "asset_consistency_review.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_asset_consistency_review_markdown(review), encoding="utf-8")
    return [json_path, md_path]


def _finding(item: dict[str, Any], included_ref: dict[str, Any]) -> dict[str, Any]:
    review_result = str(item["review_result"])
    return {
        "profile_ref": item["profile_ref"],
        "profile_kind": included_ref.get("profile_kind", item.get("profile_kind", "unknown")),
        "profile_version": included_ref.get("profile_version", "unknown"),
        "source_version_id": included_ref.get("source_version_id", "unknown"),
        "output_refs": [str(ref) for ref in list_value(item.get("output_refs"))],
        "review_dimension": item["review_dimension"],
        "review_result": review_result,
        "review_result_effect": _review_result_effect(review_result),
        "failure_attribution": item["failure_attribution"],
        "drift_observations": [str(value) for value in list_value(item.get("drift_observations"))],
        "violated_constraints": [str(value) for value in list_value(item.get("violated_constraints"))],
        "evidence_refs": [str(value) for value in list_value(item.get("evidence_refs"))],
        "suggested_next_state": item["suggested_next_state"],
    }


def _blocked_finding(item: dict[str, Any], reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "profile_ref": str(item.get("profile_ref", "unknown")),
        "profile_kind": str(item.get("profile_kind", "unknown")),
        "output_refs": [str(ref) for ref in list_value(item.get("output_refs"))],
        "reason": reason,
        **extra,
    }


def _controls(
    projection: dict[str, Any],
    fixture: dict[str, Any],
    findings: list[dict[str, Any]],
    blocked_findings: list[dict[str, Any]],
) -> list[dict[str, str]]:
    return [
        _control("source_projection_ready", projection.get("projection_status") == "ready"),
        _control("included_profile_refs_present", bool(list_value(projection.get("included_refs")))),
        _control("review_items_present", bool(list_value(fixture.get("review_items")))),
        _control("no_blocked_or_unknown_profile_refs_used", not blocked_findings),
        _control("consistency_findings_present", bool(findings)),
        _control("provider_calls_not_started", True),
        _control("asset_feedback_not_auto_created", True),
        _control("profile_update_candidate_not_auto_created", True),
        _control("promotion_decision_not_auto_created", True),
        _control("writes_no_long_term_memory", True),
        _control("writes_no_company_kb", True),
    ]


def _overall_result(findings: list[dict[str, Any]], blocked_findings: list[dict[str, Any]]) -> str:
    if blocked_findings:
        return "blocked"
    results = [str(item.get("review_result")) for item in findings]
    if not results:
        return "blocked"
    if "not_kept" in results:
        return "not_kept"
    if "partially_kept" in results:
        return "partially_kept"
    if all(result == "cannot_judge" for result in results):
        return "cannot_judge"
    if "cannot_judge" in results:
        return "partially_kept"
    return "kept"


def _review_result_effect(result: str) -> str:
    if result == "kept":
        return "positive_signal"
    if result == "cannot_judge":
        return "neutral"
    return "needs_profile_review"


def _refs_by_id(value: Any) -> dict[str, dict[str, Any]]:
    return {str(item.get("ref_id")): item for item in list_value(value) if isinstance(item, dict)}


def _claim_boundaries() -> dict[str, str]:
    return {
        "human_acceptance": "not_claimed",
        "business_validation": "not_validated",
        "provider_success": "not_attempted",
        "durable_memory_runtime": "not_implemented",
        "asset_feedback": "not_created",
        "profile_update_candidate": "not_created",
        "profile_promotion": "not_performed",
        "company_kb_promotion": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
        "not next-pass execution",
        "not automatic asset feedback",
        "not automatic profile update",
    ]


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _safe_id(*parts: str) -> str:
    raw = ":".join(parts)
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


__all__ = (
    "ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND",
    "ASSET_CONSISTENCY_REVIEW_KIND",
    "build_asset_consistency_review",
    "load_asset_consistency_review_fixture",
    "load_asset_profile_context_projection",
    "render_asset_consistency_review_markdown",
    "write_asset_consistency_review",
)
