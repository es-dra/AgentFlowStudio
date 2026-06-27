from __future__ import annotations

from typing import Any

from agentflow.knowledge.director_scenario_packs import (
    AUXILIARY_PACKS,
    DEFAULT_PACK,
    DIRECTOR_SCENARIO_PACKS,
    SECTION_FIELDS,
)


def director_scenario_context(
    *,
    slots: dict[str, str] | None = None,
    text: str = "",
    node_type: str,
    generation_target: str,
    target_platform: str = "short_video",
    style: str | None = None,
    node_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = _combined_text(slots, text, style, node_parameters)
    scored = [_score_pack(pack, source, node_type, generation_target, target_platform) for pack in DIRECTOR_SCENARIO_PACKS]
    scored.sort(key=lambda item: (-item["score"], item["scenario_id"]))
    selected = [_public_pack(item["pack"], item) for item in scored if item["score"] > 0]
    primary = selected[0] if selected else _public_pack(DEFAULT_PACK, {"score": 0, "match_terms": [], "selection_reason": "fallback"})

    selected_ids = {primary["scenario_id"]}
    packs = [primary]
    for item in _auxiliary_scores(source, node_type, generation_target, target_platform):
        public = _public_pack(item["pack"], item, role="auxiliary")
        if public["scenario_id"] not in selected_ids and item["score"] > 0:
            packs.append(public)
            selected_ids.add(public["scenario_id"])
    for item in selected[1:3]:
        if item["scenario_id"] not in selected_ids:
            packs.append(item)
            selected_ids.add(item["scenario_id"])

    return {
        "artifact_type": "agentflow_director_scenario_context",
        "schema_version": "0.1.0",
        "node_type": node_type,
        "generation_target": generation_target,
        "target_platform": target_platform,
        "primary_scenario": primary["scenario_id"],
        "selected_packs": packs[:3],
        "scenario_scores": [
            {
                "scenario_id": item["scenario_id"],
                "score": item["score"],
                "match_terms": item["match_terms"][:6],
                "selection_reason": item["selection_reason"],
            }
            for item in scored
        ],
        "quality_checks": _dedupe([check for pack in packs for check in pack["quality_checks"]]),
        "negative_constraints": _dedupe([constraint for pack in packs for constraint in pack["negative_constraints"]]),
        "source_boundary": "mechanism_absorbed_not_copied",
        "external_source_copied": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def director_scenario_from_text(
    text: str,
    *,
    node_type: str,
    generation_target: str,
    target_platform: str = "short_video",
    style: str | None = None,
    node_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return director_scenario_context(
        text=text,
        node_type=node_type,
        generation_target=generation_target,
        target_platform=target_platform,
        style=style,
        node_parameters=node_parameters,
    )


def format_director_scenario_reference(context: dict[str, Any], output_section: str) -> str:
    fields = SECTION_FIELDS.get(output_section)
    if not fields:
        return ""
    chunks: list[str] = []
    packs = context.get("selected_packs") if isinstance(context, dict) else []
    for pack in packs if isinstance(packs, list) else []:
        if not isinstance(pack, dict):
            continue
        refs: list[str] = []
        for field in fields:
            value = pack.get(field)
            if isinstance(value, list):
                refs.extend(str(item) for item in value[:2])
            elif value:
                refs.append(str(value))
        if refs:
            chunks.append(f"[{pack.get('label')}] " + "; ".join(refs[:4]))
    return "Director scenario: " + " ".join(chunks) if chunks else ""


def _combined_text(
    slots: dict[str, str] | None,
    text: str,
    style: str | None,
    node_parameters: dict[str, Any] | None,
) -> str:
    parts: list[str] = [text or "", style or ""]
    if slots:
        parts.extend(str(value or "") for value in slots.values())
    if node_parameters:
        for key in sorted(node_parameters):
            value = node_parameters.get(key)
            if isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}: {value}")
    return "\n".join(part for part in parts if str(part or "").strip()).lower()


def _score_pack(
    pack: dict[str, Any],
    source: str,
    node_type: str,
    generation_target: str,
    target_platform: str,
) -> dict[str, Any]:
    match_terms = [str(term) for term in pack.get("trigger_terms", ()) if str(term).lower() in source]
    score = len(match_terms) * 2
    if target_platform in {"short_video", "tiktok", "reels", "shorts"}:
        score += 1
    if generation_target in {"script", "video", "keyframe"}:
        score += 1
    if node_type in {"script", "video", "director"}:
        score += 1
    if not match_terms:
        score = 0
    return {
        "pack": pack,
        "scenario_id": str(pack["scenario_id"]),
        "score": score,
        "match_terms": match_terms,
        "selection_reason": "matched_terms" if match_terms else "no_match",
    }


def _auxiliary_scores(
    source: str,
    node_type: str,
    generation_target: str,
    target_platform: str,
) -> list[dict[str, Any]]:
    items = []
    for pack in AUXILIARY_PACKS:
        item = _score_pack(pack, source, node_type, generation_target, target_platform)
        if target_platform == "short_video" and generation_target in {"script", "video", "keyframe"}:
            item["score"] = max(item["score"], 1)
            item["selection_reason"] = item["selection_reason"] if item["match_terms"] else "short_video_default"
        items.append(item)
    items.sort(key=lambda item: (-item["score"], item["scenario_id"]))
    return items


def _public_pack(pack: dict[str, Any], score: dict[str, Any], *, role: str = "primary") -> dict[str, Any]:
    return {
        "scenario_id": str(pack["scenario_id"]),
        "label": str(pack["label"]),
        "role": role,
        "score": int(score.get("score") or 0),
        "match_terms": list(score.get("match_terms") or []),
        "selection_reason": str(score.get("selection_reason") or "matched_terms"),
        "scenario_goal": str(pack["scenario_goal"]),
        "hook_patterns": list(pack["hook_patterns"]),
        "timeline_template": list(pack["timeline_template"]),
        "camera_rules": list(pack["camera_rules"]),
        "lighting_rules": list(pack["lighting_rules"]),
        "sound_rules": list(pack["sound_rules"]),
        "asset_strategy": list(pack["asset_strategy"]),
        "platform_rules": list(pack["platform_rules"]),
        "continuity_rules": list(pack["continuity_rules"]),
        "quality_checks": list(pack["quality_checks"]),
        "negative_constraints": list(pack["negative_constraints"]),
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = str(item)
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


__all__ = (
    "director_scenario_context",
    "director_scenario_from_text",
    "format_director_scenario_reference",
)
