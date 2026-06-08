from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_loop import SCHEMA_VERSION

REAL_ASSET_TEST_HARNESS_KIND = "agentflow_real_asset_test_run_harness"
REVIEW_SCREEN_SELECTED_FILES_KIND = "agentflow_web_review_screen_selected_files"


def build_real_asset_test_report(
    *,
    output_root: Path,
    bundle: dict[str, Any],
    feedback_event: dict[str, Any],
    candidate: dict[str, Any],
    promotion_decision_payload: dict[str, Any],
    profile_version: dict[str, Any] | None,
    context_projection: dict[str, Any] | None,
    consistency_review: dict[str, Any] | None,
    project_materials_path: Path | None,
    character_reference_image_path: Path | None,
) -> dict[str, Any]:
    blocks = _blocks(
        project_materials_path=project_materials_path,
        profile_version=profile_version,
        context_projection=context_projection,
        consistency_review=consistency_review,
    )
    return {
        "kind": REAL_ASSET_TEST_HARNESS_KIND,
        "artifact_type": REAL_ASSET_TEST_HARNESS_KIND,
        "schema_version": SCHEMA_VERSION,
        "run_id": f"real-asset-test-run:{bundle['test_package'].get('project_id', 'unknown')}:round-1",
        "run_status": "completed_with_blocks" if blocks else "passed",
        "output_root_ref": output_root.name,
        "project_id": bundle["test_package"].get("project_id", "unknown"),
        "package": _package_summary(bundle),
        "material_evidence": {
            "project_materials_provided": project_materials_path is not None,
            "character_reference_image_provided": character_reference_image_path is not None,
            "private_paths_persisted": False,
            "material_bytes_persisted": False,
        },
        "feedback": {
            "event_id": feedback_event.get("feedback_event_id", "unknown"),
            "result": feedback_event.get("review_result", "unknown"),
            "effect": feedback_event.get("review_result_effect", "unknown"),
            "suggested_next_state": feedback_event.get("suggested_next_state", "unknown"),
            "feedback_is_memory": False,
        },
        "candidate": {
            "candidate_id": candidate.get("candidate_id", "unknown"),
            "status": candidate.get("candidate_generation_status", "unknown"),
            "applies_profile_version": False,
        },
        "promotion": {
            "decision_id": promotion_decision_payload.get("decision_id", "unknown"),
            "decision": promotion_decision_payload.get("decision", "unknown"),
            "creates_profile_version": profile_version is not None,
        },
        "profile_version": _profile_version_summary(profile_version),
        "context_projection": _context_projection_summary(context_projection),
        "consistency_review": _consistency_review_summary(consistency_review),
        "passes": _passes(bundle, feedback_event, candidate, promotion_decision_payload, context_projection),
        "blocks": blocks,
        "non_claims": _non_claims(),
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def build_review_screen_selected_files(report: dict[str, Any]) -> dict[str, Any]:
    selected = [
        "asset_profile_context_projection.json",
        "asset_consistency_review.json",
        "asset_profiles.json",
        "asset_profile_readiness.json",
        "asset_feedback_event.json",
        "asset_profile_update_candidate.json",
        "asset_profile_promotion_decision.json",
        "asset_profile_version.json",
        "real_asset_test_report.json",
    ]
    if report["promotion"]["creates_profile_version"] is False:
        selected = [
            item
            for item in selected
            if item not in {"asset_profile_context_projection.json", "asset_consistency_review.json"}
        ]
    return {
        "kind": REVIEW_SCREEN_SELECTED_FILES_KIND,
        "artifact_type": REVIEW_SCREEN_SELECTED_FILES_KIND,
        "schema_version": report.get("schema_version", SCHEMA_VERSION),
        "source_run_id": report.get("run_id", "unknown"),
        "selected_files": selected,
        "ui_policy": "selected local JSON only",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": _non_claims(),
    }


def render_real_asset_test_report_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Real Asset Test Run Report",
            "",
            f"Status: {report.get('run_status', 'unknown')}",
            f"Project: {report.get('project_id', 'unknown')}",
            f"Package: {_dict(report.get('package')).get('status', 'unknown')}",
            f"Feedback: {_dict(report.get('feedback')).get('result', 'unknown')}",
            f"Promotion decision: {_dict(report.get('promotion')).get('decision', 'unknown')}",
            f"Context projection: {_dict(report.get('context_projection')).get('status', 'unknown')}",
            f"Consistency review: {_dict(report.get('consistency_review')).get('status', 'unknown')}",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
            "## Pass",
            "",
            _items(report.get("passes"), key="pass_id"),
            "",
            "## Block",
            "",
            _items(report.get("blocks"), key="block_id"),
            "",
            "## Non-Claim",
            "",
            "\n".join(f"- {item}" for item in _list(report.get("non_claims"))) or "- none",
            "",
        ]
    )


def _package_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": bundle["test_package"].get("package_status", "unknown"),
        "readiness_status": bundle["readiness"].get("readiness_status", "unknown"),
        "profile_count": bundle["readiness"].get("profile_count", 0),
        "ready_profile_count": bundle["readiness"].get("ready_profile_count", 0),
    }


def _passes(
    bundle: dict[str, Any],
    feedback_event: dict[str, Any],
    candidate: dict[str, Any],
    decision: dict[str, Any],
    projection: dict[str, Any] | None,
) -> list[dict[str, str]]:
    return [
        _pass("operator_loop_written", "Operator loop manifest was written under operator_loop/."),
        _pass("asset_package_written", f"Package status: {bundle['test_package'].get('package_status', 'unknown')}."),
        _pass("feedback_recorded_as_raw_evidence", f"Feedback event: {feedback_event.get('feedback_event_id', 'unknown')}."),
        _pass("candidate_is_not_applied", f"Candidate status: {candidate.get('candidate_generation_status', 'unknown')}."),
        _pass("explicit_promotion_decision_recorded", f"Decision: {decision.get('decision', 'unknown')}."),
        _pass("provider_calls_not_started", "No provider capability gate was opened."),
        _pass("context_projection_written", f"Projection: {_dict(projection).get('projection_status', 'not_written')}."),
    ]


def _blocks(
    *,
    project_materials_path: Path | None,
    profile_version: dict[str, Any] | None,
    context_projection: dict[str, Any] | None,
    consistency_review: dict[str, Any] | None,
) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    if project_materials_path is None:
        blocks.append(_block("project_materials_missing", "No explicit local project materials path was provided; fixture-only run."))
    if profile_version is None:
        blocks.append(_block("profile_version_missing", "Promotion decision did not create a profile version."))
    if context_projection is None or context_projection.get("projection_status") != "ready":
        blocks.append(_block("context_projection_not_ready", "No ready context projection was produced."))
    if consistency_review is None or consistency_review.get("review_status") != "ready_for_operator_review":
        blocks.append(_block("consistency_review_not_ready", "No ready consistency review was produced."))
    return blocks


def _profile_version_summary(version: dict[str, Any] | None) -> dict[str, Any]:
    if version is None:
        return {"status": "not_created"}
    return {
        "status": "created",
        "version_id": version.get("version_id", "unknown"),
        "profile_id": version.get("profile_id", "unknown"),
        "profile_version": version.get("profile_version", "unknown"),
        "source_decision_id": version.get("source_decision_id", "unknown"),
    }


def _context_projection_summary(projection: dict[str, Any] | None) -> dict[str, Any]:
    if projection is None:
        return {"status": "not_written", "included_refs": 0, "blocked_refs": 0}
    return {
        "status": projection.get("projection_status", "unknown"),
        "included_refs": len(_list(projection.get("included_refs"))),
        "blocked_refs": len(_list(projection.get("blocked_refs"))),
    }


def _consistency_review_summary(review: dict[str, Any] | None) -> dict[str, Any]:
    if review is None:
        return {"status": "not_written", "overall_result": "unknown"}
    return {
        "status": review.get("review_status", "unknown"),
        "overall_result": review.get("overall_consistency_result", "unknown"),
        "blocked_findings": len(_list(review.get("blocked_findings"))),
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


def _items(value: Any, *, key: str) -> str:
    items = _list(value)
    if not items:
        return "- none"
    return "\n".join(f"- {_dict(item).get(key, 'unknown')}: {_dict(item).get('summary', '')}" for item in items)


def _pass(pass_id: str, summary: str) -> dict[str, str]:
    return {"pass_id": pass_id, "summary": summary}


def _block(block_id: str, summary: str) -> dict[str, str]:
    return {"block_id": block_id, "summary": summary}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = (
    "REAL_ASSET_TEST_HARNESS_KIND",
    "REVIEW_SCREEN_SELECTED_FILES_KIND",
    "build_real_asset_test_report",
    "build_review_screen_selected_files",
    "render_real_asset_test_report_markdown",
)
