from __future__ import annotations

from typing import Any


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]


def build_canvas_draft(manifest: dict[str, Any], *, generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_assets = [item for item in manifest.get("source_assets", []) if isinstance(item, dict)]
    if not source_assets:
        raise ValueError("source assets are required before drafting a canvas")

    brief = _summary_for(source_assets, "brief") or str(manifest.get("goal") or "Project goal")
    reference = _summary_for(source_assets, "reference") or "Use approved safe reference summaries."
    script = _summary_for(source_assets, "script") or "Shape the story into hook, proof, and close."
    source_ids = [str(item.get("asset_id") or item.get("label") or "source") for item in source_assets]

    cards = [
        _card(
            "draft-hook",
            "Hook",
            f"Open with the audience problem and project promise: {brief}",
            reference,
            "Establish the first three seconds before any provider smoke.",
            source_ids,
        ),
        _card(
            "draft-proof",
            "Proof",
            f"Show the concrete product or story proof: {script}",
            reference,
            "Check clarity and visual continuity before next round.",
            source_ids,
        ),
        _card(
            "draft-cta",
            "CTA",
            f"Close with a simple next step that matches the project goal: {brief}",
            reference,
            "Keep the ending calm, specific, and reviewable.",
            source_ids,
        ),
    ]
    draft = {
        "artifact_type": "agentflow_runtime_canvas_draft",
        "schema_version": "0.1.0",
        "project_id": str(manifest["project_id"]),
        "generated_at": generated_at,
        "draft_mode": "three_act_short_video",
        "source_summary_count": len(source_assets),
        "content_card_ids": [card["card_id"] for card in cards],
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }
    return draft, cards


def _summary_for(source_assets: list[dict[str, Any]], asset_type: str) -> str:
    for item in source_assets:
        if str(item.get("asset_type") or "").lower() == asset_type:
            return str(item.get("summary") or item.get("label") or "")
    return ""


def _card(
    card_id: str,
    title: str,
    summary: str,
    reference_summary: str,
    retry_intent: str,
    source_ids: list[str],
) -> dict[str, Any]:
    return {
        "card_id": card_id,
        "card_type": "scene",
        "title": title,
        "summary": summary,
        "target_platform": "short_video",
        "status": "ready_not_run",
        "ref_kind": "content_card_summary",
        "source_asset_ids": source_ids,
        "does_not_store_private_asset_bytes": True,
        "inspector": {
            "prompt": summary,
            "reference_summary": reference_summary,
            "style_direction": "Product workbench draft; refine before provider smoke.",
            "retry_intent": retry_intent,
            "ref_kind": "scene_inspector_summary",
        },
    }


__all__ = ("NON_CLAIMS", "build_canvas_draft")
