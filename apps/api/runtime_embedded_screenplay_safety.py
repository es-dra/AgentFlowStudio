"""Screenplay / shot-plan safety validation for embedded creative actions.

Structural extract from runtime_embedded_creative_actions.py — no behavior change.
Owns pure validation of screenplay_candidate and shot_plan payloads, production
brief normalization, duration assessment, and shared text safety helpers used by
those validators.
"""

from __future__ import annotations

import re
import time
from typing import Any

from apps.api.runtime_store import reject_unsafe_payload


UNSAFE_TEXT_FRAGMENTS = (
    "api key",
    "authorization:",
    "bearer ",
    "cookie:",
    "secret",
    "token",
    "signed url",
    "provider raw",
    "\\users\\",
    "/home/",
    "/opt/",
    "/var/lib/",
)
PROMPT_LEAK_FRAGMENTS = (
    "system prompt",
    "developer message",
    "request_json",
    "output.schema",
    "provider raw",
    "api key",
    "authorization",
    "cookie",
)
SPEAKER_DIALOGUE_RE = re.compile(r"^([A-Za-z0-9_\-\u4e00-\u9fff·（）()《》]{1,24})[：:]\s*(.{2,})$")
NON_SPEAKER_LABELS = {
    "场景",
    "动作",
    "对白",
    "转场",
    "镜头",
    "地点",
    "时间",
    "目的",
    "旁注",
    "说明",
}
DEFAULT_SHORT_FILM_DURATION_SECONDS = 120.0
MAX_STORYBOARD_DURATION_SECONDS = 3600.0

def _screenplay_candidate_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "version_label", "logline", "characters", "scenes"],
        "properties": {
            "title": {"type": "string", "minLength": 2},
            "version_label": {"type": "string", "minLength": 1},
            "logline": {"type": "string", "minLength": 12},
            "characters": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "goal", "conflict", "change"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "goal": {"type": "string", "minLength": 4},
                        "conflict": {"type": "string", "minLength": 4},
                        "change": {"type": "string", "minLength": 4},
                    },
                },
            },
            "scenes": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
            "required": ["heading", "space_type", "location", "time_of_day", "purpose", "blocks"],
            "properties": {
                "heading": {"type": "string", "minLength": 4},
                "space_type": {"type": "string", "enum": ["内景", "外景", "INT.", "EXT."]},
                "location": {"type": "string", "minLength": 2},
                "time_of_day": {"type": "string", "minLength": 1},
                "purpose": {"type": "string", "minLength": 6},
                        "blocks": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 36,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["type", "text"],
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["action", "character", "dialogue", "parenthetical", "transition"],
                                    },
                                    "text": {"type": "string", "minLength": 1},
                                },
                            },
                        },
                    },
                },
            },
        },
    }

def _validate_preview_payload(request: Any, value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("structured output is not an object")
    revised_text = _safe_text(value.get("revised_text"), 20000)
    if len(revised_text) < 40 or revised_text.strip() == request.source_text.strip():
        raise ValueError("revised text is empty or unchanged")
    summary = [_safe_text(item, 180) for item in value.get("change_summary") or [] if _safe_text(item, 180)]
    rationale = _safe_text(value.get("rationale"), 420)
    if len(summary) < 2 or len(rationale) < 12:
        raise ValueError("preview is not reviewable")
    preview = {
        "preview_id": f"preview_{int(time.time() * 1000)}",
        "action_type": request.action_type,
        "mode": request.mode,
        "revised_text": revised_text,
        "change_summary": summary[:8],
        "rationale": rationale,
        "unresolved_decisions": [_safe_text(item, 180) for item in value.get("unresolved_decisions") or [] if _safe_text(item, 180)][:6],
        "quality_flags": [_safe_text(item, 180) for item in value.get("quality_flags") or [] if _safe_text(item, 180)][:6],
    }
    if request.action_type == "shot_breakdown":
        plan = value.get("shot_plan")
        if not isinstance(plan, dict):
            raise ValueError("shot plan is missing")
        safe_plan = _safe_shot_plan(plan)
        production_brief = _production_brief_for_request(request)
        preview["shot_plan"] = safe_plan
        preview["production_brief"] = production_brief
        preview["duration_assessment"] = _shot_plan_duration_assessment(safe_plan, production_brief)
    if request.action_type == "script_revision":
        candidate = value.get("screenplay_candidate")
        if not isinstance(candidate, dict):
            raise ValueError("screenplay candidate is missing")
        safe_candidate = _safe_screenplay_candidate(candidate)
        preview["screenplay_candidate"] = safe_candidate
        preview["revised_text"] = _screenplay_text_projection(safe_candidate)
    reject_unsafe_payload(preview)
    return preview


def _safe_screenplay_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    # A long prose story must fail this gate unless it is backed by typed screenplay scenes.
    characters = []
    for item in candidate.get("characters") or []:
        if not isinstance(item, dict):
            continue
        character = {
            "name": _safe_text(item.get("name"), 80),
            "goal": _safe_text(item.get("goal"), 180),
            "conflict": _safe_text(item.get("conflict"), 180),
            "change": _safe_text(item.get("change"), 180),
        }
        if all(character.values()):
            characters.append(character)
    character_names = {item["name"] for item in characters if item.get("name")}
    scenes = []
    has_dialogue = False
    has_action = False
    for scene in candidate.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        blocks = _safe_screenplay_blocks(scene.get("blocks") or [], character_names=character_names)
        has_dialogue = has_dialogue or any(block.get("type") == "dialogue" for block in blocks)
        has_action = has_action or any(block.get("type") == "action" for block in blocks)
        if not _valid_screenplay_block_flow(blocks):
            continue
        location = _safe_text(scene.get("location"), 120)
        time_of_day = _safe_text(scene.get("time_of_day"), 80)
        space_type = _safe_space_type(scene.get("space_type"))
        safe_scene = {
            "heading": _safe_scene_heading(scene.get("heading"), space_type=space_type, location=location, time_of_day=time_of_day),
            "space_type": space_type,
            "location": location,
            "time_of_day": time_of_day,
            "purpose": _safe_text(scene.get("purpose"), 220),
            "blocks": blocks[:36],
        }
        if safe_scene["heading"] and safe_scene["space_type"] and safe_scene["location"] and safe_scene["time_of_day"] and safe_scene["purpose"] and len(safe_scene["blocks"]) >= 2:
            scenes.append(safe_scene)
    if not characters or not scenes or not has_action:
        raise ValueError("screenplay candidate lacks professional scene/action structure")
    if not has_dialogue and len(characters) > 1:
        raise ValueError("screenplay candidate lacks dialogue for multi-character material")
    return {
        "schema_version": "afs.screenplay_candidate.v0.1",
        "title": _safe_text(candidate.get("title"), 120) or "未命名剧本",
        "version_label": _safe_text(candidate.get("version_label"), 80) or "v1",
        "logline": _safe_text(candidate.get("logline"), 360),
        "characters": characters[:12],
        "scenes": scenes[:12],
    }


def _safe_screenplay_blocks(raw_blocks: Any, *, character_names: set[str]) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for block in raw_blocks or []:
        if not isinstance(block, dict):
            continue
        block_type = _safe_token(block.get("type"), 32)
        text = _safe_text(block.get("text"), 600)
        if block_type not in {"action", "character", "dialogue", "parenthetical", "transition"} or not text:
            continue
        if block_type == "action":
            blocks.extend(_split_action_block_with_dialogue_lines(text, character_names=character_names))
            continue
        if block_type == "character":
            split = _speaker_prefixed_dialogue(text, character_names=character_names)
            if split:
                speaker, dialogue = split
                blocks.extend([{"type": "character", "text": speaker}, {"type": "dialogue", "text": dialogue}])
            else:
                blocks.append({"type": block_type, "text": text})
            continue
        if block_type == "dialogue" and not _blocks_expect_dialogue(blocks):
            split = _speaker_prefixed_dialogue(text, character_names=character_names)
            if split:
                speaker, dialogue = split
                blocks.extend([{"type": "character", "text": speaker}, {"type": "dialogue", "text": dialogue}])
                continue
        if block_type == "dialogue" and _blocks_expect_dialogue(blocks):
            split = _speaker_prefixed_dialogue(text, character_names=character_names)
            if split:
                blocks.append({"type": "dialogue", "text": split[1]})
                continue
        blocks.append({"type": block_type, "text": text})
    return blocks


def _split_action_block_with_dialogue_lines(text: str, *, character_names: set[str]) -> list[dict[str, str]]:
    lines = [_safe_text(line, 600) for line in text.splitlines()]
    pieces: list[dict[str, str]] = []
    pending_action: list[str] = []
    saw_dialogue_line = False
    for line in lines:
        if not line:
            continue
        split = _speaker_prefixed_dialogue(line, character_names=character_names, require_known=True)
        if not split:
            pending_action.append(line)
            continue
        saw_dialogue_line = True
        if pending_action:
            pieces.append({"type": "action", "text": "\n".join(pending_action)})
            pending_action = []
        speaker, dialogue = split
        pieces.extend([{"type": "character", "text": speaker}, {"type": "dialogue", "text": dialogue}])
    if pending_action:
        pieces.append({"type": "action", "text": "\n".join(pending_action)})
    return pieces if saw_dialogue_line else [{"type": "action", "text": text}]


def _speaker_prefixed_dialogue(
    text: str,
    *,
    character_names: set[str],
    require_known: bool = False,
) -> tuple[str, str] | None:
    match = SPEAKER_DIALOGUE_RE.match(_safe_text(text, 600))
    if not match:
        return None
    speaker = _safe_text(match.group(1), 80).strip("（）()《》")
    dialogue = _safe_text(match.group(2), 600)
    if not speaker or not dialogue:
        return None
    if not _looks_like_screenplay_speaker(speaker, character_names=character_names, require_known=require_known):
        return None
    return speaker, dialogue


def _looks_like_screenplay_speaker(speaker: str, *, character_names: set[str], require_known: bool) -> bool:
    if speaker in character_names:
        return True
    if speaker in {"旁白", "画外音", "广播声"}:
        return True
    if require_known:
        return False
    if speaker in NON_SPEAKER_LABELS:
        return False
    if any(char.isspace() for char in speaker):
        return False
    return 1 <= len(speaker) <= 12


def _blocks_expect_dialogue(blocks: list[dict[str, str]]) -> bool:
    for block in reversed(blocks):
        block_type = block.get("type")
        if block_type == "character":
            return True
        if block_type == "parenthetical":
            continue
        return False
    return False


def _safe_space_type(value: Any) -> str:
    text = _safe_text(value, 16).upper()
    if text in {"INT.", "INT"}:
        return "INT."
    if text in {"EXT.", "EXT"}:
        return "EXT."
    if str(value or "").strip() in {"内景", "外景"}:
        return str(value).strip()
    return ""


def _safe_scene_heading(value: Any, *, space_type: str, location: str, time_of_day: str) -> str:
    text = _safe_text(value, 160)
    if space_type and location and time_of_day:
        fallback = f"{space_type} - {location} - {time_of_day}"
    else:
        fallback = ""
    if not text:
        return fallback
    upper = text.upper()
    if "内景/外景待定" in text or upper.startswith(("1.", "2.", "3.", "4.", "5.", "6.")):
        return fallback
    normalized = text.replace("—", "-").replace("－", "-")
    parts = [part.strip() for part in normalized.split("-") if part.strip()]
    if parts and parts[0] in {"内景", "外景"}:
        if len(parts) >= 3:
            return f"{parts[0]} - {parts[1]} - {parts[2]}"
        return fallback
    if upper.startswith(("INT.", "EXT.")):
        if len(parts) >= 2 and parts[-1]:
            return text
        return fallback
    return ""


def _valid_screenplay_block_flow(blocks: list[dict[str, str]]) -> bool:
    if not blocks:
        return False
    expecting_dialogue = False
    for block in blocks:
        block_type = block.get("type")
        if block_type == "character":
            if expecting_dialogue:
                return False
            expecting_dialogue = True
        elif block_type == "parenthetical":
            if not expecting_dialogue:
                return False
        elif block_type == "dialogue":
            if not expecting_dialogue:
                return False
            expecting_dialogue = False
        elif block_type in {"action", "transition"}:
            if expecting_dialogue:
                return False
        else:
            return False
    return not expecting_dialogue


def _safe_validation_reason(reason: str) -> str:
    text = _safe_text(reason, 220).lower()
    categories = (
        ("structured output is not an object", "structured_output_not_object"),
        ("revised text is empty or unchanged", "revised_text_empty_or_unchanged"),
        ("preview is not reviewable", "preview_not_reviewable"),
        ("shot plan is missing", "shot_plan_missing"),
        ("shot plan has no shots", "shot_plan_empty"),
        ("screenplay candidate is missing", "screenplay_candidate_missing"),
        ("lacks professional scene/action structure", "screenplay_structure_invalid"),
        ("lacks dialogue", "screenplay_dialogue_missing"),
    )
    for marker, category in categories:
        if marker in text:
            return category
    return "validation_failed"


def _screenplay_text_projection(candidate: dict[str, Any]) -> str:
    lines = [
        f"《{candidate.get('title') or '未命名剧本'}》",
        f"版本：{candidate.get('version_label') or 'v1'}",
        f"一句话梗概：{candidate.get('logline') or ''}",
        "",
        "角色",
    ]
    for character in candidate.get("characters") or []:
        lines.append(
            f"- {character.get('name') or '角色'}：目标 {character.get('goal') or '待定'}；"
            f"冲突 {character.get('conflict') or '待定'}；变化 {character.get('change') or '待定'}"
        )
    for scene in candidate.get("scenes") or []:
        lines.extend(["", scene.get("heading") or "场景", f"场景目的：{scene.get('purpose') or '待定'}", ""])
        for block in scene.get("blocks") or []:
            block_type = block.get("type")
            text = block.get("text") or ""
            if block_type == "action":
                lines.extend([text, ""])
            elif block_type == "character":
                lines.append(text)
            elif block_type == "dialogue":
                lines.extend([text, ""])
            elif block_type == "parenthetical":
                lines.append(f"（{text.strip('（）()')}）")
            elif block_type == "transition":
                lines.extend([f"转场：{text}", ""])
    return "\n".join(lines).strip()


def _safe_shot_plan(plan: dict[str, Any]) -> dict[str, Any]:
    scenes = []
    total = 0
    for scene in plan.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        shots = []
        for shot in scene.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            duration_sec = _safe_number(shot.get("duration_sec"), 0)
            if duration_sec < 1 or duration_sec > MAX_STORYBOARD_DURATION_SECONDS:
                raise ValueError("shot duration is outside the production brief range")
            shots.append({
                "title": _safe_text(shot.get("title"), 120),
                "duration_sec": duration_sec,
                "shot_size": _safe_text(shot.get("shot_size"), 80),
                "camera_angle": _safe_text(shot.get("camera_angle"), 80),
                "movement": _safe_text(shot.get("movement"), 120),
                "blocking": _safe_text(shot.get("blocking"), 180),
                "sound": _safe_text(shot.get("sound"), 120),
                "transition": _safe_text(shot.get("transition"), 80),
                "narrative_purpose": _safe_text(shot.get("narrative_purpose"), 180),
            })
        if not shots:
            continue
        total += len(shots)
        scenes.append({
            "title": _safe_text(scene.get("title"), 120),
            "purpose": _safe_text(scene.get("purpose"), 180),
            "shots": shots[:12],
        })
    if not scenes or total < 1:
        raise ValueError("shot plan has no shots")
    safe_scenes = scenes[:8]
    shot_duration_sum = round(sum(
        shot["duration_sec"] for scene in safe_scenes for shot in scene["shots"]
    ), 2)
    return {
        "scenes": safe_scenes,
        "total_shots": sum(len(scene["shots"]) for scene in safe_scenes),
        "estimated_duration_sec": shot_duration_sum,
        "provider_estimated_duration_sec": max(
            1.0,
            min(MAX_STORYBOARD_DURATION_SECONDS, _safe_number(plan.get("estimated_duration_sec"), shot_duration_sum)),
        ),
        "duration_source": "per_shot_sum",
    }


def _production_brief_for_request(request: Any) -> dict[str, Any]:
    if request.production_brief:
        return _safe_production_brief(request.production_brief)
    return {
        "target_duration_seconds": DEFAULT_SHORT_FILM_DURATION_SECONDS,
        "duration_source": "creator_default",
        "tolerance_seconds": round(DEFAULT_SHORT_FILM_DURATION_SECONDS * 0.1, 2),
        "source_revision_id": _safe_token(request.source_revision_id, 140),
        "source_digest": request.source_digest if re.fullmatch(r"[a-f0-9]{64}", request.source_digest or "") else "",
    }


def _safe_production_brief(value: Any) -> dict[str, Any]:
    # Lazy import avoids an import cycle with the parent route module while
    # preserving the original isinstance(EmbeddedProductionBrief) gate.
    from apps.api.runtime_embedded_creative_actions import EmbeddedProductionBrief

    raw = value.model_dump(mode="json") if isinstance(value, EmbeddedProductionBrief) else dict(value or {})
    target = max(5.0, min(MAX_STORYBOARD_DURATION_SECONDS, _safe_number(
        raw.get("target_duration_seconds"),
        DEFAULT_SHORT_FILM_DURATION_SECONDS,
    )))
    source = _safe_token(raw.get("duration_source"), 40)
    if source not in {"script_explicit", "creator_default", "creator_selected"}:
        source = "creator_default"
    tolerance = max(0.0, min(target, _safe_number(
        raw.get("tolerance_seconds"),
        target * 0.1 if source == "creator_default" else 1.0,
    )))
    digest = str(raw.get("source_digest") or "").lower()
    return {
        "target_duration_seconds": round(target, 2),
        "duration_source": source,
        "tolerance_seconds": round(tolerance, 2),
        "source_revision_id": _safe_token(raw.get("source_revision_id"), 140),
        "source_digest": digest if re.fullmatch(r"[a-f0-9]{64}", digest) else "",
    }


def _shot_plan_duration_assessment(
    shot_plan: dict[str, Any],
    production_brief: Any,
) -> dict[str, Any]:
    brief = _safe_production_brief(production_brief)
    durations = [
        float(shot.get("duration_sec") or 0)
        for scene in shot_plan.get("scenes") or []
        if isinstance(scene, dict)
        for shot in scene.get("shots") or []
        if isinstance(shot, dict)
    ]
    candidate = round(sum(durations), 2)
    target = float(brief["target_duration_seconds"])
    tolerance = float(brief["tolerance_seconds"])
    delta = round(candidate - target, 2)
    within_tolerance = candidate > 0 and abs(delta) <= tolerance
    return {
        **brief,
        "candidate_duration_seconds": candidate,
        "provider_estimated_duration_seconds": round(float(
            shot_plan.get("provider_estimated_duration_sec")
            or shot_plan.get("estimated_duration_sec")
            or 0
        ), 2),
        "duration_delta_seconds": delta,
        "within_tolerance": within_tolerance,
        "apply_allowed": within_tolerance,
        "status": "within_target" if within_tolerance else "outside_target",
    }


def _safe_number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_token(value: Any, limit: int) -> str:
    return "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "_-:.").strip()[:limit]


def _safe_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if _contains_unsafe_fragment(text) or _contains_prompt_leak_fragment(text):
        raise ValueError("unsafe text")
    return text[:limit]


def _contains_unsafe_fragment(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(fragment in lowered for fragment in UNSAFE_TEXT_FRAGMENTS)


def _contains_prompt_leak_fragment(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(fragment in lowered for fragment in PROMPT_LEAK_FRAGMENTS)
