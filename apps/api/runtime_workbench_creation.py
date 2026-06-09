from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import NON_CLAIMS, list_value


CREATE_KINDS = {"content_board", "scene_card", "generation_check"}


def build_creation_workspace(
    *,
    manifest: dict[str, Any],
    cards: list[dict[str, Any]],
    filmstrip: list[dict[str, Any]],
    project_readiness: dict[str, Any],
    command_hub: dict[str, Any],
) -> dict[str, Any]:
    canvas_cards = [_safe_card(card) for card in cards if str(card.get("kind") or "") in CREATE_KINDS]
    selected = _selected_card(canvas_cards)
    return {
        "status": _workspace_status(manifest, canvas_cards, project_readiness),
        "title": "Creation workspace",
        "summary": "Plan, inspect, and run the current production canvas from safe project refs.",
        "selected_card_id": selected.get("card_id", ""),
        "counts": _counts(canvas_cards, filmstrip),
        "canvas_cards": canvas_cards,
        "inspector": _inspector(selected),
        "filmstrip": filmstrip,
        "run_controls": _run_controls(command_hub.get("primary_command")),
        "non_claims": NON_CLAIMS,
    }


def _safe_card(card: dict[str, Any]) -> dict[str, Any]:
    refs = [_safe_ref(ref) for ref in list_value(card.get("refs")) if isinstance(ref, dict)]
    artifact_refs = _artifact_refs(card)
    return {
        "card_id": str(card.get("card_id") or ""),
        "kind": str(card.get("kind") or ""),
        "title": str(card.get("title") or "Untitled"),
        "status": str(card.get("status") or "not_started"),
        "summary": str(card.get("summary") or ""),
        "primary_artifact_id": str(card.get("primary_artifact_id") or ""),
        "actions": [str(item) for item in list_value(card.get("actions"))],
        "blockers": [_safe_blocker(item) for item in list_value(card.get("blockers"))],
        "refs": refs,
        "artifact_refs": artifact_refs,
        "inspector": _safe_inspector(card.get("inspector")),
    }


def _safe_ref(value: dict[str, Any]) -> dict[str, str]:
    return {
        "label": str(value.get("label") or "ref"),
        "artifact_id": str(value.get("artifact_id") or ""),
        "artifact_type": str(value.get("artifact_type") or ""),
        "summary": str(value.get("summary") or ""),
    }


def _safe_blocker(value: Any) -> dict[str, str]:
    source = value if isinstance(value, dict) else {}
    if not source:
        text = str(value or "blocked")
        return {"blocker_id": text, "message": text, "user_action": ""}
    return {
        "blocker_id": str(source.get("blocker_id") or source.get("block_id") or source.get("reason") or "blocked"),
        "message": str(source.get("message") or source.get("summary") or source.get("reason") or "blocked"),
        "user_action": str(source.get("user_action") or ""),
    }


def _safe_inspector(value: Any) -> dict[str, str]:
    source = value if isinstance(value, dict) else {}
    return {
        "prompt": str(source.get("prompt") or ""),
        "reference_summary": str(source.get("reference_summary") or ""),
        "style_direction": str(source.get("style_direction") or ""),
        "retry_intent": str(source.get("retry_intent") or ""),
    }


def _selected_card(cards: list[dict[str, Any]]) -> dict[str, Any]:
    for card in cards:
        if card["kind"] == "scene_card":
            return card
    for card in cards:
        if card["primary_artifact_id"]:
            return card
    return cards[0] if cards else {}


def _inspector(card: dict[str, Any]) -> dict[str, Any]:
    mode = "scene" if card.get("kind") == "scene_card" else "setup"
    return {
        "card_id": str(card.get("card_id") or ""),
        "mode": mode,
        "title": str(card.get("title") or "No card selected"),
        "status": str(card.get("status") or "not_started"),
        "summary": str(card.get("summary") or ""),
        "primary_artifact_id": str(card.get("primary_artifact_id") or ""),
        "fields": _safe_inspector(card.get("inspector")),
        "actions": [str(item) for item in list_value(card.get("actions"))],
        "refs": list_value(card.get("refs")),
        "blockers": [_safe_blocker(item) for item in list_value(card.get("blockers"))],
    }


def _artifact_refs(card: dict[str, Any]) -> list[str]:
    evidence = card.get("evidence") if isinstance(card.get("evidence"), dict) else {}
    refs: list[str] = []
    for item in [card.get("primary_artifact_id"), *list_value(evidence.get("artifact_ids"))]:
        ref = str(item or "")
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _counts(cards: list[dict[str, Any]], filmstrip: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "canvas_cards": len(cards),
        "filmstrip_items": len(filmstrip),
        "editable_scene_cards": sum(1 for card in cards if card["kind"] == "scene_card"),
        "artifact_refs": sum(len(card["artifact_refs"]) for card in cards),
    }


def _run_controls(value: Any) -> dict[str, Any]:
    command = value if isinstance(value, dict) else {}
    view = str(command.get("view") or "Create")
    ui_action = str(command.get("ui_action") or "")
    blocked_reason = str(command.get("blocked_reason") or "")
    return {
        "primary_action": str(command.get("backend_action") or ""),
        "primary_label": str(command.get("label") or "Continue"),
        "ui_action": ui_action,
        "enabled": command.get("enabled") is True and view == "Create" and bool(ui_action) and not blocked_reason,
        "handoff_view": view,
        "summary": str(command.get("summary") or ""),
        "blocked_reason": blocked_reason,
        "requires_input": [str(item) for item in list_value(command.get("requires_input"))],
    }


def _workspace_status(
    manifest: dict[str, Any],
    cards: list[dict[str, Any]],
    project_readiness: dict[str, Any],
) -> str:
    if not list_value(manifest.get("source_assets")) and not list_value(manifest.get("runs")):
        return "needs_assets"
    for card in cards:
        if card["card_id"] == "first-generation-check" and card["status"] in {"running", "blocked", "failed", "succeeded"}:
            return card["status"]
    if not list_value(manifest.get("content_cards")):
        return "needs_cards"
    status = str(project_readiness.get("status") or "not_started")
    return "blocked" if status == "provider_blocked" else status


__all__ = ("build_creation_workspace",)
