from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_card_utils import blocker as _blocker
from apps.api.runtime_workbench_card_utils import card as _card
from apps.api.runtime_workbench_support import list_value as _list


def build_content_cards(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    content_cards = [item for item in _list(manifest.get("content_cards")) if isinstance(item, dict)]
    if not content_cards:
        return [
            _card(
                "content-cards",
                "content_board",
                "Scene cards",
                "blocked",
                "Add scene cards so the creation canvas has user-facing work items.",
                None,
                ["add_scene_card"],
                blockers=[
                    _blocker(
                        "content_cards_missing",
                        "Add at least one scene or content card.",
                        user_action="add_scene_card",
                        source="creation_canvas",
                    )
                ],
            )
        ]
    return [
        _card(
            str(item.get("card_id") or f"scene-{index}"),
            "scene_card",
            str(item.get("title") or f"Scene {index}"),
            str(item.get("status") or "ready_not_run"),
            str(item.get("summary") or "Scene card is ready for planning."),
            None,
            ["edit_scene_card", "start_first_generation_check", "record_review_note"],
            refs=[
                {
                    "label": str(item.get("target_platform") or "target"),
                    "artifact_id": str(item.get("card_id") or ""),
                    "artifact_type": str(item.get("card_type") or "scene"),
                    "summary": str(item.get("summary") or ""),
                }
            ],
            inspector=_inspector(item),
        )
        for index, item in enumerate(content_cards, start=1)
    ]


def build_filmstrip(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card_id": str(item.get("card_id") or ""),
            "title": str(item.get("title") or item.get("card_id") or "Scene"),
            "status": str(item.get("status") or "ready_not_run"),
            "summary": str(item.get("summary") or ""),
        }
        for item in _list(manifest.get("content_cards"))
        if isinstance(item, dict)
    ]


def _inspector(item: dict[str, Any]) -> dict[str, str]:
    value = item.get("inspector")
    if not isinstance(value, dict):
        return {}
    return {
        "prompt": str(value.get("prompt") or ""),
        "reference_summary": str(value.get("reference_summary") or ""),
        "style_direction": str(value.get("style_direction") or ""),
        "retry_intent": str(value.get("retry_intent") or ""),
    }

__all__ = ("build_content_cards", "build_filmstrip")
