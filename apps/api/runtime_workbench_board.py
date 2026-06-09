from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_readiness import ACTION_LABELS
from apps.api.runtime_workbench_support import artifact_ids, jobs_by_action, latest, list_value, status


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]


def build_production_board(
    manifest: dict[str, Any],
    jobs: list[dict[str, Any]],
    provider_gate: dict[str, Any],
    project_readiness: dict[str, Any],
) -> dict[str, Any]:
    grouped = jobs_by_action(jobs)
    asset_job = latest(grouped, "asset_test_run")
    draft_job = latest(grouped, "draft_canvas")
    feedback_job = latest(grouped, "record_feedback") or latest(grouped, "record_review_decision")
    next_round_job = latest(grouped, "two_round_validate")
    provider_job = latest(grouped, "provider_validation_plan")

    source_ready = bool(list_value(manifest.get("source_assets"))) or bool(asset_job)
    draft_ready = bool(list_value(manifest.get("content_cards"))) or bool(draft_job) or bool(asset_job)
    feedback_ready = bool(list_value(manifest.get("feedback_refs"))) or bool(feedback_job)
    style_ready = bool(list_value(manifest.get("profile_version_refs")))
    provider_status = str(provider_gate.get("status") or "ready_not_run")
    current_action = str(project_readiness.get("current_action") or "add_reference")

    lanes = [
        _lane("source", "Source", "succeeded" if source_ready else "blocked", "add_reference", "Safe materials", None),
        _lane("draft", "Draft", _draft_status(source_ready, draft_ready), "draft_canvas", "Reviewable canvas", draft_job),
        _lane(
            "first_check",
            "First Check",
            status(asset_job) if asset_job else ("ready_not_run" if draft_ready else "not_started"),
            "start_first_generation_check",
            "Deterministic asset check",
            asset_job,
        ),
        _lane("review", "Review", _review_status(asset_job, feedback_ready), "record_review_note", "Human feedback evidence", feedback_job),
        _lane("style_memory", "Style Memory", "succeeded" if style_ready else "not_started", "open_style_memory", "Reusable project preference", None),
        _lane(
            "next_round",
            "Next Round",
            status(next_round_job) if next_round_job else ("ready_not_run" if feedback_ready else "not_started"),
            "start_next_round",
            "Context reuse check",
            next_round_job,
        ),
        _lane("provider_gate", "Provider Gate", provider_status, "run_provider_preflight", "Capability preflight", provider_job),
    ]
    return {
        "status": _board_status(current_action, lanes),
        "title": "Production board",
        "summary": _summary(current_action),
        "current_action": current_action,
        "current_action_label": ACTION_LABELS.get(current_action, "Continue"),
        "lanes": lanes,
        "non_claims": NON_CLAIMS,
    }


def _lane(
    lane_id: str,
    label: str,
    lane_status: str,
    action: str,
    summary: str,
    job: dict[str, Any] | None,
) -> dict[str, Any]:
    ids = artifact_ids(job or {})
    return {
        "lane_id": lane_id,
        "label": label,
        "status": lane_status,
        "summary": summary,
        "action": action,
        "action_label": ACTION_LABELS.get(action, "Continue"),
        "primary_artifact_id": _primary_artifact_id(job, ids),
        "artifact_count": len(ids),
    }


def _primary_artifact_id(job: dict[str, Any] | None, ids: list[str]) -> str:
    artifacts = job.get("artifacts", {}) if job and isinstance(job.get("artifacts"), dict) else {}
    for role in (
        "provider_safe_manifest",
        "real_asset_test_report",
        "two_round_context_runtime_report",
        "runtime_feedback_event",
        "runtime_review_decision",
    ):
        artifact_ref = artifacts.get(role)
        if isinstance(artifact_ref, dict) and artifact_ref.get("artifact_id"):
            return str(artifact_ref["artifact_id"])
    return ids[0] if ids else ""


def _draft_status(source_ready: bool, draft_ready: bool) -> str:
    if draft_ready:
        return "succeeded"
    return "ready_not_run" if source_ready else "not_started"


def _review_status(asset_job: dict[str, Any] | None, feedback_ready: bool) -> str:
    if feedback_ready:
        return "succeeded"
    return "needs_review" if asset_job else "not_started"


def _board_status(current_action: str, lanes: list[dict[str, Any]]) -> str:
    if any(lane["status"] == "failed" for lane in lanes):
        return "failed"
    if any(lane["status"] == "blocked" for lane in lanes):
        return "needs_assets" if current_action == "add_reference" else "blocked"
    if current_action in {"start_next_round", "run_provider_preflight"}:
        return "ready_for_next_step"
    return "in_progress"


def _summary(current_action: str) -> str:
    return {
        "add_reference": "Start with safe source summaries.",
        "draft_canvas": "Turn source material into a reviewable canvas.",
        "start_first_generation_check": "Run the first deterministic content check.",
        "record_review_note": "Capture review evidence before the next pass.",
        "start_next_round": "Reuse accepted context in the next round.",
        "run_provider_preflight": "Check provider readiness before real model smoke.",
        "resolve_provider_preflight": "Provider remains blocked by explicit capability gates.",
    }.get(current_action, "Continue the production flow.")


__all__ = ("build_production_board",)
