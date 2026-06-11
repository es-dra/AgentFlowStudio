from __future__ import annotations

from typing import Any

from apps.api.runtime_store import RuntimeStore


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]
ACTION_LABELS = {
    "add_reference": "Add reference material",
    "draft_canvas": "Draft canvas",
    "start_first_generation_check": "Run first generation check",
    "record_review_note": "Record review note",
    "start_next_round": "Start next round",
    "run_provider_preflight": "Run provider preflight",
}


def build_flow_summary(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    manifest = store.ensure_project_manifest(project_id)
    jobs = store.list_project_jobs(project_id)
    project_status = str(manifest.get("status") or "in_progress")
    provider_status = _provider_status(jobs)
    current_action = _current_action(manifest, jobs, provider_status)
    return {
        "project_id": str(manifest.get("project_id") or project_id),
        "target_status": "ready_for_next_round",
        "target_achieved": project_status == "ready_for_next_round",
        "project_status": project_status,
        "readiness_status": _readiness_status(current_action, provider_status),
        "current_action": current_action,
        "current_action_label": ACTION_LABELS.get(current_action, "Continue"),
        "next_command": _command(current_action),
        "studio_status": _studio_status(manifest, jobs),
        "provider_status": provider_status,
        "non_claims": NON_CLAIMS,
    }


def _command(current_action: str) -> dict[str, Any]:
    return {
        "backend_action": current_action,
        "label": ACTION_LABELS.get(current_action, "Continue"),
        "ui_action": _ui_action(current_action),
        "view": "Studio",
        "enabled": current_action != "run_provider_preflight",
        "blocked_reason": "remote providers remain gated" if current_action == "run_provider_preflight" else "",
        "requires_input": _requires_input(current_action),
    }


def _current_action(manifest: dict[str, Any], jobs: list[dict[str, Any]], provider_status: str) -> str:
    if provider_status == "blocked":
        return "run_provider_preflight"
    if not _list(manifest.get("source_assets")):
        return "add_reference"
    if not _list(manifest.get("content_cards")):
        return "draft_canvas"
    if not _has_job(jobs, {"asset_test_run", "keyframe_generation"}):
        return "start_first_generation_check"
    if str(manifest.get("status") or "") == "ready_for_next_round":
        return "start_next_round"
    return "record_review_note"


def _provider_status(jobs: list[dict[str, Any]]) -> str:
    provider_jobs = [
        job
        for job in jobs
        if str(job.get("action") or "") in {"provider_validation_plan", "keyframe_generation"}
    ]
    if not provider_jobs:
        return "blocked_by_default"
    latest = provider_jobs[-1]
    status = str(latest.get("status") or "blocked")
    if status == "succeeded":
        return "succeeded"
    if status == "blocked":
        return "blocked"
    return "ready_not_run"


def _readiness_status(current_action: str, provider_status: str) -> str:
    if provider_status == "blocked":
        return "blocked"
    return {
        "add_reference": "needs_assets",
        "draft_canvas": "needs_canvas",
        "start_first_generation_check": "ready_for_generation_check",
        "record_review_note": "needs_review",
        "start_next_round": "ready_for_next_round",
        "run_provider_preflight": "blocked",
    }.get(current_action, "in_progress")


def _studio_status(manifest: dict[str, Any], jobs: list[dict[str, Any]]) -> str:
    if _list(manifest.get("content_cards")):
        return "ready"
    if _has_job(jobs, {"draft_canvas", "prompt_optimization", "keyframe_generation"}):
        return "in_progress"
    return "not_started"


def _ui_action(current_action: str) -> str:
    return {
        "add_reference": "open_asset_library",
        "draft_canvas": "draft_canvas",
        "start_first_generation_check": "open_studio_canvas",
        "record_review_note": "open_review_panel",
        "start_next_round": "open_studio_canvas",
        "run_provider_preflight": "open_provider_gate",
    }.get(current_action, "")


def _requires_input(current_action: str) -> list[str]:
    return {
        "add_reference": ["source_asset_summary"],
        "draft_canvas": ["source_assets"],
        "start_first_generation_check": ["node_prompt"],
        "record_review_note": ["review_decision"],
        "start_next_round": ["next_prompt"],
        "run_provider_preflight": ["explicit_provider_gate_authorization"],
    }.get(current_action, [])


def _has_job(jobs: list[dict[str, Any]], actions: set[str]) -> bool:
    return any(str(job.get("action") or "") in actions for job in jobs)


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = ("build_flow_summary",)
