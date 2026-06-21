from __future__ import annotations

import hashlib
import re
from typing import Any

from agentflow.algorithms.provider_gate_manifest import succeeded_manifest


ALGORITHM_ID = "afs.asset_card_drafting.v0.1"
INPUT_CONTRACT = "asset type, safe media artifact refs, prompt text, provider service id"
OUTPUT_CONTRACT = "editable asset card draft with confidence, missing fields, candidate locks, and safe evidence"
FAILURE_MODES = ("vision_gate_closed", "unsupported_asset_type", "missing_media_ref", "unsafe_draft_rejected")
EVIDENCE_BOUNDARY = "draft safe summary only; no fixed asset writes before human confirmation"

ASSET_TYPES = {"character", "scene", "video"}


def draft_asset_card(
    *,
    asset_type: str,
    project_id: str,
    draft_id: str,
    source_image_asset_refs: list[str],
    sampled_image_asset_refs: list[str],
    source_video_artifact_id: str | None,
    prompt_text: str,
    provider_service_id: str,
) -> dict[str, Any]:
    if asset_type not in ASSET_TYPES:
        raise ValueError("asset_type must be character, scene, or video")
    text = _clean_text(prompt_text)
    if asset_type == "character":
        draft = _character_draft(draft_id, project_id, source_image_asset_refs, text)
    elif asset_type == "scene":
        draft = _scene_draft(draft_id, project_id, source_image_asset_refs, text)
    else:
        draft = _video_draft(draft_id, project_id, source_video_artifact_id, sampled_image_asset_refs, text)
    draft["safe_manifest"] = succeeded_manifest(
        action="asset_card_draft",
        capability="vision",
        provider_service_id=provider_service_id,
        evidence=draft["safe_evidence"],
    )
    return draft


def draft_id_from_refs(project_id: str, generated_at: str, refs: list[str]) -> str:
    digest = hashlib.sha256(f"{project_id}:{generated_at}:{'|'.join(refs)}".encode("utf-8")).hexdigest()[:12]
    return f"draft_{digest}"


def _character_draft(draft_id: str, project_id: str, refs: list[str], prompt_text: str) -> dict[str, Any]:
    if _is_animal_subject_text(prompt_text):
        return _animal_subject_draft(draft_id, project_id, refs, prompt_text)
    label = _label_from_prompt(prompt_text, fallback="角色资产草稿")
    card = {
        "identity": _sentence_or_default(prompt_text, "参考图中的主要角色，身份待人工确认"),
        "hair": "发型、发色待人工确认",
        "face": "面部辨识点待人工确认",
        "build": "体态比例待人工确认",
        "wardrobe": "标志性服装待人工确认",
        "palette": "主色调待人工确认",
        "demeanor": "神态气质待人工确认",
    }
    return _base_draft(
        draft_id=draft_id,
        project_id=project_id,
        asset_type="character",
        label=label,
        signature=f"{label}: reference role subject, pending human confirmation",
        feature_card=card,
        candidate_locks=["keep role identity", "keep face recognizability", "keep signature wardrobe"],
        confidence=0.62,
        missing_fields=_missing_fields(card),
        source_image_asset_refs=refs,
        sampled_image_asset_refs=[],
        source_video_artifact_id=None,
        prompt_text=prompt_text,
    )


def _animal_subject_draft(draft_id: str, project_id: str, refs: list[str], prompt_text: str) -> dict[str, Any]:
    label = _animal_label_from_prompt(prompt_text)
    card = {
        "identity": _sentence_or_default(prompt_text, f"参考图中的同一只{label}，身份待人工确认"),
        "hair": "毛色、毛发纹理和斑纹待人工确认",
        "face": "脸部斑纹、眼睛、耳朵和胡须辨识点待人工确认",
        "build": "体型比例、四肢和尾巴形态待人工确认",
        "wardrobe": "默认保持自然动物外观；服装、饰品或拟人化只在用户明确要求时添加",
        "palette": "主体毛色主色调待人工确认",
        "demeanor": "动物神态和姿态待人工确认",
    }
    return _base_draft(
        draft_id=draft_id,
        project_id=project_id,
        asset_type="character",
        label=label,
        signature=f"{label}: reference animal subject, pending confirmation",
        feature_card=card,
        candidate_locks=[
            "keep animal identity",
            "keep fur color and markings",
            "keep eyes ears tail and body ratio",
            "only add human hair clothing or anthropomorphic traits when explicitly requested",
        ],
        confidence=0.62,
        missing_fields=_missing_fields(card),
        source_image_asset_refs=refs,
        sampled_image_asset_refs=[],
        source_video_artifact_id=None,
        prompt_text=prompt_text,
    )


def _scene_draft(draft_id: str, project_id: str, refs: list[str], prompt_text: str) -> dict[str, Any]:
    label = _label_from_prompt(prompt_text, fallback="场景资产草稿")
    card = {
        "location": _sentence_or_default(prompt_text, "场景地点待人工确认"),
        "layout": "空间结构待人工确认",
        "props": "关键道具待人工确认",
        "lighting_mood": "光线和氛围待人工确认",
        "palette": "场景配色待人工确认",
        "time_weather": "时间与天气待人工确认",
    }
    return _base_draft(
        draft_id=draft_id,
        project_id=project_id,
        asset_type="scene",
        label=label,
        signature=f"{label}: reference scene, pending human confirmation",
        feature_card=card,
        candidate_locks=["keep spatial layout", "keep key props", "keep lighting mood"],
        confidence=0.6,
        missing_fields=_missing_fields(card),
        source_image_asset_refs=refs,
        sampled_image_asset_refs=[],
        source_video_artifact_id=None,
        prompt_text=prompt_text,
    )


def _video_draft(
    draft_id: str,
    project_id: str,
    source_video_artifact_id: str | None,
    sampled_refs: list[str],
    prompt_text: str,
) -> dict[str, Any]:
    label = _label_from_prompt(prompt_text, fallback="视频资产草稿")
    segment = {
        "segment_id": "seg_001",
        "start_time_sec": 0.0,
        "end_time_sec": 5.0,
        "visible_subjects": ["primary subject pending confirmation"],
        "actions": [_sentence_or_default(prompt_text, "main action pending confirmation")],
        "scene_state": "scene continuity pending confirmation",
        "camera_motion": _camera_motion(prompt_text),
        "props": [],
        "continuity_anchors": ["first usable frame", "last usable frame"],
        "drift_risks": ["identity drift", "motion drift"],
        "usable_reference_frames": [*sampled_refs[:4]],
    }
    summary = _sentence_or_default(prompt_text, "视频内容摘要待人工确认")
    card = {
        "summary": summary,
        "temporal_scope": "single generated shot",
        "camera_motion": segment["camera_motion"],
        "continuity_anchors": segment["continuity_anchors"],
        "drift_risks": segment["drift_risks"],
    }
    draft = _base_draft(
        draft_id=draft_id,
        project_id=project_id,
        asset_type="video",
        label=label,
        signature=f"{label}: video motion reference, pending human confirmation",
        feature_card=card,
        candidate_locks=["preserve temporal action", "preserve camera motion", "preserve continuity anchors"],
        confidence=0.58,
        missing_fields=_missing_fields(card),
        source_image_asset_refs=[],
        sampled_image_asset_refs=sampled_refs,
        source_video_artifact_id=source_video_artifact_id,
        prompt_text=prompt_text,
    )
    draft["summary"] = summary
    draft["segments"] = [segment]
    return draft


def _base_draft(
    *,
    draft_id: str,
    project_id: str,
    asset_type: str,
    label: str,
    signature: str,
    feature_card: dict[str, Any],
    candidate_locks: list[str],
    confidence: float,
    missing_fields: list[str],
    source_image_asset_refs: list[str],
    sampled_image_asset_refs: list[str],
    source_video_artifact_id: str | None,
    prompt_text: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_asset_card_draft",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "draft_id": draft_id,
        "asset_type": asset_type,
        "status": "draft",
        "label_suggestion": label,
        "signature": signature,
        "feature_card": feature_card,
        "candidate_locks": candidate_locks,
        "confidence": confidence,
        "missing_fields": missing_fields,
        "source_image_asset_refs": list(source_image_asset_refs),
        "sampled_image_asset_refs": list(sampled_image_asset_refs),
        "source_video_artifact_id": source_video_artifact_id,
        "safe_evidence": {
            "source_image_asset_count": len(source_image_asset_refs),
            "sampled_image_asset_count": len(sampled_image_asset_refs),
            "has_video_artifact_ref": bool(source_video_artifact_id),
            "prompt_char_count": len(prompt_text),
            "claim_boundary": "vision_draft_needs_human_confirmation",
        },
        "asset_memory_policy": {
            "writes_fixed_asset": False,
            "included_in_context_before_confirmation": False,
            "requires_human_confirmation": True,
        },
    }


def _label_from_prompt(prompt_text: str, *, fallback: str) -> str:
    text = _clean_text(prompt_text)
    if not text:
        return fallback
    words = re.split(r"\s+", text)
    return " ".join(words[:6]).strip(" ,.;:，。；：")[:80] or fallback


def _animal_label_from_prompt(prompt_text: str) -> str:
    text = _clean_text(prompt_text).casefold()
    if "黑色" in prompt_text and "狸花猫" in prompt_text:
        return "黑色狸花猫"
    if "狸花猫" in prompt_text or "tabby" in text:
        return "狸花猫"
    if "猫" in prompt_text or "cat" in text or "kitten" in text or "feline" in text:
        return "猫主体资产"
    if "狗" in prompt_text or "犬" in prompt_text or "dog" in text or "puppy" in text:
        return "狗主体资产"
    return "动物主体资产"


def _is_animal_subject_text(prompt_text: str) -> bool:
    text = _clean_text(prompt_text).casefold()
    animal_terms = ("猫", "狸花猫", "黑猫", "白猫", "橘猫", "宠物", "动物", "狗", "犬", "cat", "tabby", "kitten", "feline", "dog", "puppy", "animal", "pet")
    human_terms = ("人物", "人像", "真人", "人类", "女孩", "男孩", "女人", "男人", "女性", "男性", "头发", "发型", "校服", "服装", "person", "human", "girl", "boy", "woman", "man", "hair", "wardrobe", "uniform")
    return any(term.casefold() in text for term in animal_terms) and not any(term.casefold() in text for term in human_terms)


def _sentence_or_default(prompt_text: str, fallback: str) -> str:
    text = _clean_text(prompt_text)
    if not text:
        return fallback
    first = re.split(r"[。.!?！？]\s*", text)[0]
    return first[:160] or fallback


def _camera_motion(prompt_text: str) -> str:
    lowered = prompt_text.lower()
    if "push" in lowered or "推进" in lowered:
        return "slow push in"
    if "pan" in lowered or "摇" in lowered:
        return "pan"
    return "camera motion pending confirmation"


def _missing_fields(card: dict[str, Any]) -> list[str]:
    return [key for key, value in card.items() if "待人工确认" in str(value) or "pending confirmation" in str(value)]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())[:2000]


__all__ = (
    "ALGORITHM_ID",
    "ASSET_TYPES",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "draft_asset_card",
    "draft_id_from_refs",
)
