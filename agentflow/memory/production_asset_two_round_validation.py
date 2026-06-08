from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_asset_consistency_review import (
    build_asset_consistency_review,
    load_asset_consistency_review_fixture,
    write_asset_consistency_review,
)
from agentflow.memory.production_asset_profile_context_projection import (
    build_asset_profile_context_projection,
    write_asset_profile_context_projection,
)
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.harness.json_io import write_json

TWO_ROUND_CONTEXT_RUNTIME_REPORT_KIND = "agentflow_two_round_context_runtime_report"
NO_IMPROVEMENT_REASONS = frozenset(
    {
        "context_insufficient",
        "feedback_unclear",
        "profile_granularity_wrong",
        "test_materials_insufficient",
        "provider_or_output_randomness_too_high",
        "cannot_judge",
    }
)


def run_two_round_context_runtime_validation(
    *,
    round_1_dir: Path,
    output_dir: Path,
    consistency_review_json_path: Path,
    generated_at: str,
    reviewed_at: str,
) -> dict[str, Any]:
    _require_text("generated_at", generated_at)
    _require_text("reviewed_at", reviewed_at)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    round_1_report = _read_json(Path(round_1_dir) / "real_asset_test_report.json")
    version = _read_json(Path(round_1_dir) / "asset_profile_version.json")
    projection = build_asset_profile_context_projection(
        asset_profile_versions=[version],
        generated_at=generated_at,
    )
    write_asset_profile_context_projection(projection, output_root)
    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=load_asset_consistency_review_fixture(Path(consistency_review_json_path)),
        reviewed_at=reviewed_at,
    )
    write_asset_consistency_review(review, output_root)

    report = build_two_round_context_runtime_report(
        round_1_report=round_1_report,
        round_1_profile_version=version,
        round_2_context_projection=projection,
        round_2_consistency_review=review,
        generated_at=generated_at,
        reviewed_at=reviewed_at,
    )
    write_json(output_root / "two_round_context_runtime_report.json", report)
    (output_root / "two_round_context_runtime_report.md").write_text(
        render_two_round_context_runtime_report_markdown(report),
        encoding="utf-8",
    )
    return report


def build_two_round_context_runtime_report(
    *,
    round_1_report: dict[str, Any],
    round_1_profile_version: dict[str, Any],
    round_2_context_projection: dict[str, Any],
    round_2_consistency_review: dict[str, Any],
    generated_at: str,
    reviewed_at: str,
) -> dict[str, Any]:
    included = _trace_inclusions(round_2_context_projection)
    blocked = _list(round_2_context_projection.get("blocked_refs"))
    controls = _controls(round_2_context_projection, round_2_consistency_review, included, blocked)
    runtime_status = "verified" if all(item["status"] == PASSED for item in controls) else "blocked"
    assessment, reason = _improvement_assessment(round_1_report, runtime_status, round_2_consistency_review)
    return {
        "kind": TWO_ROUND_CONTEXT_RUNTIME_REPORT_KIND,
        "artifact_type": TWO_ROUND_CONTEXT_RUNTIME_REPORT_KIND,
        "schema_version": SCHEMA_VERSION,
        "report_id": f"two-round-context-runtime:{round_2_context_projection.get('project_id', 'unknown')}",
        "generated_at": generated_at,
        "reviewed_at": reviewed_at,
        "project_id": round_2_context_projection.get("project_id", "unknown"),
        "round_1": {
            "run_id": round_1_report.get("run_id", "unknown"),
            "run_status": round_1_report.get("run_status", "unknown"),
            "profile_version_id": round_1_profile_version.get("version_id", "unknown"),
            "profile_version": round_1_profile_version.get("profile_version", "unknown"),
        },
        "round_2": {
            "context_projection_ref": round_2_context_projection.get("projection_id", "unknown"),
            "context_projection_status": round_2_context_projection.get("projection_status", "unknown"),
            "consistency_review_ref": round_2_consistency_review.get("review_id", "unknown"),
            "consistency_review_status": round_2_consistency_review.get("review_status", "unknown"),
            "overall_consistency_result": round_2_consistency_review.get("overall_consistency_result", "unknown"),
        },
        "round_2_context_inclusions": included,
        "round_2_blocked_refs": blocked,
        "runtime_verification_status": runtime_status,
        "improvement_assessment": assessment,
        "reason_if_not_improved": reason,
        "controls": controls,
        "claim_boundaries": _claim_boundaries(),
        "non_claims": _non_claims(),
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def render_two_round_context_runtime_report_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Two-Round Context Runtime Report",
            "",
            f"Runtime verification: {report.get('runtime_verification_status', 'unknown')}",
            f"Improvement assessment: {report.get('improvement_assessment', 'unknown')}",
            f"Reason if not improved: {report.get('reason_if_not_improved', 'none')}",
            "Provider calls: not started",
            "Human acceptance: not claimed",
            "Business validation: not validated",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
            "## Round 2 Included Context",
            "",
            _included_table(report.get("round_2_context_inclusions")),
            "",
            "## Round 2 Blocked Refs",
            "",
            _blocked_table(report.get("round_2_blocked_refs")),
            "",
        ]
    )


def _trace_inclusions(projection: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "ref_id": str(item.get("ref_id", "unknown")),
            "profile_kind": item.get("profile_kind", "unknown"),
            "profile_version": item.get("profile_version", "unknown"),
            "source_profile_id": item.get("source_profile_id", "unknown"),
            "source_profile_version_id": item.get("source_version_id", "unknown"),
            "source_decision_id": item.get("source_decision_id", "unknown"),
            "evidence_refs": [str(ref) for ref in _list(item.get("evidence_refs"))],
            "version_change_summary": _dict(item.get("version_change_summary")),
        }
        for item in _list(projection.get("included_refs"))
    ]


def _controls(
    projection: dict[str, Any],
    review: dict[str, Any],
    included: list[dict[str, Any]],
    blocked: list[Any],
) -> list[dict[str, str]]:
    included_ids = {str(item.get("ref_id")) for item in included}
    blocked_ids = {str(_dict(item).get("ref_id")) for item in blocked}
    return [
        _control("round_2_context_projection_ready", projection.get("projection_status") == "ready"),
        _control("round_2_consistency_review_ready", review.get("review_status") == "ready_for_operator_review"),
        _control("included_refs_traceable", _included_refs_traceable(included)),
        _control("blocked_refs_excluded", not (included_ids & blocked_ids)),
        _control("provider_calls_not_started", True),
        _control("writes_no_long_term_memory", True),
        _control("writes_no_company_kb", True),
    ]


def _improvement_assessment(
    round_1_report: dict[str, Any],
    runtime_status: str,
    review: dict[str, Any],
) -> tuple[str, str | None]:
    if runtime_status != "verified":
        return "blocked", "context_insufficient"
    material = _dict(round_1_report.get("material_evidence"))
    if material.get("project_materials_provided") is not True:
        return "no_clear_improvement", "test_materials_insufficient"
    if review.get("overall_consistency_result") == "kept":
        return "improved", None
    if review.get("overall_consistency_result") == "cannot_judge":
        return "no_clear_improvement", "cannot_judge"
    return "no_clear_improvement", "feedback_unclear"


def _included_refs_traceable(included: list[dict[str, Any]]) -> bool:
    return all(
        item.get("profile_version")
        and item.get("source_profile_version_id")
        and item.get("source_decision_id")
        and _list(item.get("evidence_refs"))
        for item in included
    )


def _claim_boundaries() -> dict[str, str]:
    return {
        "structure_verification": "verified",
        "runtime_verification": "reported",
        "tester_feedback": "recorded_as_raw_evidence",
        "human_acceptance": "not_claimed",
        "business_validation": "not_validated",
        "durable_memory": "not_written",
        "company_kb_promotion": "not_performed",
        "provider_success": "not_attempted",
    }


def _non_claims() -> list[str]:
    return [
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
        "not provider execution",
    ]


def _included_table(value: Any) -> str:
    items = _list(value)
    if not items:
        return "- none"
    return "\n".join(
        f"- {item.get('ref_id', 'unknown')} | version {item.get('profile_version', 'unknown')} | "
        f"evidence {len(_list(item.get('evidence_refs')))}"
        for item in items
    )


def _blocked_table(value: Any) -> str:
    items = _list(value)
    if not items:
        return "- none"
    return "\n".join(f"- {_dict(item).get('ref_id', 'unknown')}: {_dict(item).get('reason', 'unknown')}" for item in items)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return payload


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _require_text(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = (
    "NO_IMPROVEMENT_REASONS",
    "TWO_ROUND_CONTEXT_RUNTIME_REPORT_KIND",
    "build_two_round_context_runtime_report",
    "render_two_round_context_runtime_report_markdown",
    "run_two_round_context_runtime_validation",
)
