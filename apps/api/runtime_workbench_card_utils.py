from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import artifact_ids as _artifact_ids
from apps.api.runtime_workbench_support import list_value as _list


USER_BLOCKER_MESSAGES = {
    "project_materials_missing": "Add project materials before running a real generation pass.",
    "source_assets_missing": "Add project assets, references, script, or brief.",
    "image_gate_unset": "Enable the image provider gate before live image smoke.",
    "video_gate_unset": "Enable the video provider gate before live video smoke.",
    "provider_config_missing": "Configure provider credentials before live provider smoke.",
    "character_reference_image_missing": "Add a character reference image before live provider smoke.",
}


def card(
    card_id: str,
    kind: str,
    title: str,
    status: str,
    summary: str,
    primary_artifact_id: Any,
    actions: list[str],
    *,
    blockers: list[dict[str, Any]] | None = None,
    evidence: dict[str, Any] | None = None,
    refs: list[dict[str, Any]] | None = None,
    inspector: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "card_id": card_id,
        "kind": kind,
        "title": title,
        "status": status,
        "summary": summary,
        "primary_artifact_id": primary_artifact_id,
        "actions": actions,
        "blockers": blockers or [],
        "evidence": evidence or {"artifact_ids": []},
        "refs": refs or [],
        "inspector": inspector or {},
    }


def blockers(values: Any, *, source: str) -> list[dict[str, Any]]:
    return [_normalize_blocker(value, source=source) for value in _list(values) if isinstance(value, dict)]


def blocker(blocker_id: str, message: str, *, user_action: str, source: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "blocked", "message": message, "user_action": user_action, "source": source}


def evidence(job: dict[str, Any] | None) -> dict[str, Any]:
    if not job:
        return {"job_id": None, "artifact_ids": []}
    return {"job_id": job.get("job_id"), "artifact_ids": _artifact_ids(job), "has_advanced_details": True}


def _normalize_blocker(value: dict[str, Any], *, source: str) -> dict[str, Any]:
    blocker_id = str(value.get("blocker_id") or value.get("block_id") or value.get("reason") or value.get("ref") or "blocked")
    message = USER_BLOCKER_MESSAGES.get(
        blocker_id,
        str(value.get("message") or value.get("summary") or value.get("reason") or blocker_id),
    )
    return {
        "blocker_id": blocker_id,
        "severity": "blocked",
        "message": message,
        "user_action": _user_action(blocker_id),
        "source": source,
    }


def _user_action(blocker_id: str) -> str:
    if "provider_config" in blocker_id:
        return "configure_provider"
    if "image_gate" in blocker_id or "video_gate" in blocker_id:
        return "enable_provider_gate"
    if "reference_image" in blocker_id:
        return "add_reference"
    if "materials" in blocker_id or "assets" in blocker_id:
        return "add_project_materials"
    return "open_advanced_details"


__all__ = ("blocker", "blockers", "card", "evidence")
