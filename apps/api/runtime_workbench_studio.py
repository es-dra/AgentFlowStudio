from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import NON_CLAIMS, list_value


def build_studio_workspace(
    *,
    project: dict[str, Any],
    asset_library: dict[str, Any],
    creation_workspace: dict[str, Any],
    memory_workspace: dict[str, Any],
    operations_workspace: dict[str, Any],
    command_hub: dict[str, Any],
) -> dict[str, Any]:
    provider_gate = _object(operations_workspace.get("provider_gate"))
    return {
        "status": _status(asset_library, creation_workspace, memory_workspace, operations_workspace),
        "title": "Studio workspace",
        "summary": _summary(asset_library, creation_workspace, memory_workspace, operations_workspace),
        "active_project": _active_project(project),
        "primary_command": _primary_command(command_hub),
        "provider_status": str(provider_gate.get("status") or "ready_not_run"),
        "counts": _counts(asset_library, creation_workspace, memory_workspace, operations_workspace),
        "canvas": {
            "selected_card_id": str(creation_workspace.get("selected_card_id") or ""),
            "cards": list_value(creation_workspace.get("canvas_cards")),
        },
        "inspector": _object(creation_workspace.get("inspector")),
        "run_controls": _object(creation_workspace.get("run_controls")),
        "filmstrip": list_value(creation_workspace.get("filmstrip")),
        "side_rail": {
            "assets": list_value(asset_library.get("items"))[:6],
            "style_profile": _object(memory_workspace.get("style_profile")),
            "review_candidates": list_value(memory_workspace.get("candidates"))[:4],
            "next_round_controls": _object(memory_workspace.get("next_round_controls")),
        },
        "operations_summary": _operations_summary(operations_workspace),
        "non_claims": NON_CLAIMS,
    }


def _active_project(project: dict[str, Any]) -> dict[str, str]:
    return {
        "project_id": str(project.get("project_id") or ""),
        "goal": str(project.get("goal") or ""),
        "status": str(project.get("status") or "not_started"),
        "artifact_id": str(project.get("artifact_id") or ""),
    }


def _primary_command(command_hub: dict[str, Any]) -> dict[str, Any]:
    command = _object(command_hub.get("primary_command"))
    return {
        "backend_action": str(command.get("backend_action") or ""),
        "label": str(command.get("label") or "Continue"),
        "ui_action": str(command.get("ui_action") or ""),
        "view": str(command.get("view") or "Create"),
        "summary": str(command.get("summary") or ""),
        "enabled": command.get("enabled") is True,
        "blocked_reason": str(command.get("blocked_reason") or ""),
        "requires_input": [str(item) for item in list_value(command.get("requires_input"))],
    }


def _counts(
    asset_library: dict[str, Any],
    creation_workspace: dict[str, Any],
    memory_workspace: dict[str, Any],
    operations_workspace: dict[str, Any],
) -> dict[str, int]:
    asset_counts = _object(asset_library.get("counts"))
    creation_counts = _object(creation_workspace.get("counts"))
    memory_counts = _object(memory_workspace.get("counts"))
    operations_counts = _object(operations_workspace.get("counts"))
    return {
        "assets": int(asset_counts.get("total") or 0),
        "canvas_cards": int(creation_counts.get("canvas_cards") or 0),
        "filmstrip_items": int(creation_counts.get("filmstrip_items") or 0),
        "review_candidates": int(memory_counts.get("candidates") or 0),
        "runtime_jobs": int(operations_counts.get("jobs") or 0),
        "provider_blockers": int(operations_counts.get("provider_blockers") or 0),
        "reusable_preferences": int(memory_counts.get("reusable_preferences") or 0),
    }


def _operations_summary(operations_workspace: dict[str, Any]) -> dict[str, Any]:
    provider_gate = _object(operations_workspace.get("provider_gate"))
    return {
        "status": str(operations_workspace.get("status") or "not_started"),
        "selected_job_id": str(operations_workspace.get("selected_job_id") or ""),
        "counts": _object(operations_workspace.get("counts")),
        "primary_artifact_id": str(provider_gate.get("primary_artifact_id") or ""),
        "provider_blockers": list_value(provider_gate.get("blockers")),
    }


def _status(
    asset_library: dict[str, Any],
    creation_workspace: dict[str, Any],
    memory_workspace: dict[str, Any],
    operations_workspace: dict[str, Any],
) -> str:
    operations_status = str(operations_workspace.get("status") or "not_started")
    creation_status = str(creation_workspace.get("status") or "not_started")
    memory_status = str(memory_workspace.get("status") or "not_started")
    asset_status = str(asset_library.get("status") or "needs_assets")
    if operations_status in {"blocked", "failed", "running"}:
        return operations_status
    if creation_status in {"blocked", "failed", "running", "needs_cards"}:
        return creation_status
    if asset_status == "needs_assets":
        return "needs_assets"
    if memory_status in {"ready", "needs_review"}:
        return memory_status
    return creation_status


def _summary(
    asset_library: dict[str, Any],
    creation_workspace: dict[str, Any],
    memory_workspace: dict[str, Any],
    operations_workspace: dict[str, Any],
) -> str:
    status = _status(asset_library, creation_workspace, memory_workspace, operations_workspace)
    if status == "needs_assets":
        return "Start from safe source summaries, then build the production canvas."
    if status == "blocked":
        return "The studio is waiting on a visible blocker before the next production action."
    if status == "ready":
        return "Review evidence and style memory are ready for the next production pass."
    return str(creation_workspace.get("summary") or "Continue the current production workspace.")


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = ("build_studio_workspace",)
