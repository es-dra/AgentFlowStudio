from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import NON_CLAIMS, list_value


def build_memory_workspace(
    *,
    manifest: dict[str, Any],
    review_room: dict[str, Any],
    style_memory: dict[str, Any],
    command_hub: dict[str, Any],
) -> dict[str, Any]:
    candidates = [item for item in list_value(review_room.get("candidates")) if isinstance(item, dict)]
    latest_decisions = [item for item in list_value(review_room.get("latest_decisions")) if isinstance(item, dict)]
    style_profile = _style_profile(style_memory)
    selected = _selected_candidate(candidates)
    return {
        "status": _status(candidates, style_profile),
        "title": "Memory workspace",
        "summary": _summary(candidates, style_profile),
        "selected_candidate_id": str(selected.get("candidate_id") or ""),
        "counts": _counts(manifest, candidates, latest_decisions, style_profile),
        "candidates": candidates,
        "decision_counts": _decision_counts(review_room.get("decision_counts")),
        "latest_decisions": latest_decisions[-5:],
        "style_profile": style_profile,
        "feedback_controls": _feedback_controls(command_hub, enabled=bool(candidates)),
        "next_round_controls": _command_controls(command_hub, "start_next_round"),
        "non_claims": NON_CLAIMS,
    }


def _status(candidates: list[dict[str, Any]], style_profile: dict[str, Any]) -> str:
    if style_profile["status"] == "ready":
        return "ready"
    if candidates:
        return "needs_review"
    return "not_started"


def _summary(candidates: list[dict[str, Any]], style_profile: dict[str, Any]) -> str:
    if style_profile["status"] == "ready":
        return "Project review evidence has produced a reusable style profile for the next pass."
    if candidates:
        return f"{len(candidates)} review candidates are ready for feedback before memory reuse."
    return "Run or draft reviewable output before building project memory."


def _selected_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    for candidate in candidates:
        if candidate.get("artifact_id"):
            return candidate
    return candidates[0] if candidates else {}


def _style_profile(style_memory: dict[str, Any]) -> dict[str, Any]:
    preferences = [str(item) for item in list_value(style_memory.get("reusable_preferences"))]
    return {
        "status": str(style_memory.get("status") or "not_started"),
        "title": str(style_memory.get("title") or "Project style memory"),
        "summary": str(style_memory.get("summary") or ""),
        "latest_profile_artifact_id": str(style_memory.get("latest_profile_artifact_id") or ""),
        "profile_version_count": int(style_memory.get("profile_version_count") or 0),
        "feedback_count": int(style_memory.get("feedback_count") or 0),
        "reusable_preferences": preferences,
        "next_pass_usage": str(style_memory.get("next_pass_usage") or ""),
    }


def _counts(
    manifest: dict[str, Any],
    candidates: list[dict[str, Any]],
    latest_decisions: list[dict[str, Any]],
    style_profile: dict[str, Any],
) -> dict[str, int]:
    return {
        "candidates": len(candidates),
        "decisions": len(latest_decisions),
        "feedback_refs": len(list_value(manifest.get("feedback_refs"))),
        "profile_versions": int(style_profile.get("profile_version_count") or 0),
        "reusable_preferences": len(list_value(style_profile.get("reusable_preferences"))),
    }


def _decision_counts(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    return {
        "keep": int(source.get("keep") or 0),
        "revise": int(source.get("revise") or 0),
        "reject": int(source.get("reject") or 0),
    }


def _feedback_controls(command_hub: dict[str, Any], *, enabled: bool) -> dict[str, Any]:
    control = _command_controls(command_hub, "record_review_note")
    return {**control, "enabled": enabled and bool(control["ui_action"])}


def _command_controls(command_hub: dict[str, Any], action: str) -> dict[str, Any]:
    command = _command(command_hub, action)
    return {
        "primary_action": action,
        "primary_label": str(command.get("label") or "Continue"),
        "ui_action": str(command.get("ui_action") or ""),
        "enabled": command.get("enabled") is True,
        "handoff_view": str(command.get("view") or "Review"),
        "summary": str(command.get("summary") or ""),
        "blocked_reason": str(command.get("blocked_reason") or ""),
        "requires_input": [str(item) for item in list_value(command.get("requires_input"))],
    }


def _command(command_hub: dict[str, Any], action: str) -> dict[str, Any]:
    for command in list_value(command_hub.get("commands")):
        if isinstance(command, dict) and command.get("backend_action") == action:
            return command
    return {}


__all__ = ("build_memory_workspace",)
