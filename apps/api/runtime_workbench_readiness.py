from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import jobs_by_action, latest, list_value, status


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]

ACTION_LABELS = {
    "add_reference": "Add source materials",
    "draft_canvas": "Draft Canvas",
    "start_first_generation_check": "Run first generation check",
    "record_review_note": "Record review feedback",
    "start_next_round": "Start next round",
    "run_provider_preflight": "Run provider preflight",
    "resolve_provider_preflight": "Resolve provider gate",
}


def build_project_readiness(
    manifest: dict[str, Any],
    jobs: list[dict[str, Any]],
    provider_gate: dict[str, Any],
) -> dict[str, Any]:
    grouped = jobs_by_action(jobs)
    asset_job = latest(grouped, "asset_test_run")
    draft_job = latest(grouped, "draft_canvas")
    feedback_job = latest(grouped, "record_feedback") or latest(grouped, "record_review_decision")
    next_round_job = latest(grouped, "two_round_validate")

    source_ready = _has_source_materials(manifest) or bool(asset_job)
    canvas_ready = _has_content_cards(manifest) or bool(draft_job)
    feedback_ready = _has_feedback(manifest) or bool(feedback_job)
    provider_status = str(provider_gate.get("status") or "ready_not_run")
    current_action = _current_action(
        source_ready=source_ready,
        canvas_ready=canvas_ready,
        feedback_ready=feedback_ready,
        asset_job=asset_job,
        next_round_job=next_round_job,
        provider_status=provider_status,
    )
    return {
        "status": _readiness_status(current_action, provider_status),
        "title": "Project readiness",
        "summary": _summary(current_action),
        "current_action": current_action,
        "current_action_label": ACTION_LABELS[current_action],
        "steps": [
            _step("source_materials", "Source materials", "succeeded" if source_ready else "blocked", "add_reference"),
            _step("canvas_draft", "Draft canvas", _canvas_status(source_ready, canvas_ready), "draft_canvas"),
            _step(
                "first_generation_check",
                "First generation check",
                status(asset_job) if asset_job else ("ready_not_run" if canvas_ready else "not_started"),
                "start_first_generation_check",
            ),
            _step("review_feedback", "Review feedback", _feedback_status(asset_job, feedback_ready), "record_review_note"),
            _step(
                "next_round",
                "Next round",
                status(next_round_job) if next_round_job else ("ready_not_run" if feedback_ready else "not_started"),
                "start_next_round",
            ),
            _step("provider_preflight", "Provider preflight", provider_status, "run_provider_preflight"),
        ],
        "non_claims": NON_CLAIMS,
    }


def _has_source_materials(manifest: dict[str, Any]) -> bool:
    return bool(list_value(manifest.get("source_assets")))


def _has_content_cards(manifest: dict[str, Any]) -> bool:
    return bool(list_value(manifest.get("content_cards")))


def _has_feedback(manifest: dict[str, Any]) -> bool:
    return bool(list_value(manifest.get("feedback_refs")))


def _current_action(
    *,
    source_ready: bool,
    canvas_ready: bool,
    feedback_ready: bool,
    asset_job: dict[str, Any] | None,
    next_round_job: dict[str, Any] | None,
    provider_status: str,
) -> str:
    if provider_status == "blocked":
        return "resolve_provider_preflight"
    if not source_ready:
        return "add_reference"
    if not canvas_ready and not asset_job:
        return "draft_canvas"
    if not asset_job:
        return "start_first_generation_check"
    if not feedback_ready:
        return "record_review_note"
    if not next_round_job:
        return "start_next_round"
    if provider_status != "succeeded":
        return "run_provider_preflight"
    return "start_first_generation_check"


def _readiness_status(current_action: str, provider_status: str) -> str:
    if provider_status == "blocked":
        return "provider_blocked"
    return {
        "add_reference": "needs_assets",
        "draft_canvas": "ready_to_draft",
        "start_first_generation_check": "ready_for_first_check",
        "record_review_note": "needs_review",
        "start_next_round": "ready_for_next_round",
        "run_provider_preflight": "ready_for_provider_preflight",
    }.get(current_action, "in_progress")


def _canvas_status(source_ready: bool, canvas_ready: bool) -> str:
    if canvas_ready:
        return "succeeded"
    return "ready_not_run" if source_ready else "not_started"


def _feedback_status(asset_job: dict[str, Any] | None, feedback_ready: bool) -> str:
    if feedback_ready:
        return "succeeded"
    return "needs_review" if asset_job else "not_started"


def _summary(current_action: str) -> str:
    return {
        "add_reference": "Add safe source summaries before drafting or checking content.",
        "draft_canvas": "Source material is ready; draft a first reviewable canvas.",
        "start_first_generation_check": "Canvas content is ready for the first deterministic check.",
        "record_review_note": "Runtime evidence exists; record review feedback before the next round.",
        "start_next_round": "Review evidence is ready for the next runtime pass.",
        "run_provider_preflight": "Deterministic work is ready; run provider preflight before real smoke.",
        "resolve_provider_preflight": "Provider remains gated; resolve the exact blocked capability before real smoke.",
    }[current_action]


def _step(step_id: str, label: str, step_status: str, action: str) -> dict[str, str]:
    return {
        "step_id": step_id,
        "label": label,
        "status": step_status,
        "action": action,
        "action_label": ACTION_LABELS[action],
    }


__all__ = ("build_project_readiness",)
