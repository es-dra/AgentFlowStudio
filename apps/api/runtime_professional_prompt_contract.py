from __future__ import annotations

from typing import Any

from apps.api.runtime_models import PromptOptimizationRequest


ZH_SUBJECTS = (
    "女生",
    "女孩",
    "少女",
    "女人",
    "女性",
    "男生",
    "男孩",
    "少年",
    "男人",
    "角色",
    "主角",
)
ZH_EMOTIONS = (
    ("微笑", "soft smile"),
    ("开心", "subtle happiness"),
    ("笑", "soft smile"),
    ("紧张", "tension"),
    ("悲伤", "sadness"),
    ("难过", "sadness"),
    ("害怕", "fear"),
    ("生气", "anger"),
)
ZH_SCENES = (
    ("雨夜街道", "rainy night street"),
    ("雨夜", "rainy night environment"),
    ("街道", "street"),
    ("房间", "room"),
    ("室内", "interior"),
    ("天台", "rooftop"),
    ("森林", "forest"),
    ("海边", "seaside"),
    ("教室", "classroom"),
    ("办公室", "office"),
)
ZH_MOTIONS = (
    ("慢慢回头", "slow head turn"),
    ("回头", "head turn"),
    ("走", "walk"),
    ("奔跑", "run"),
    ("抬头", "look up"),
    ("低头", "look down"),
)


def apply_professional_slot_overrides(
    request: PromptOptimizationRequest,
    slots: dict[str, str],
) -> dict[str, str]:
    prompt = request.prompt_text.strip()
    if not _contains_zh(prompt + request.style):
        return slots
    updated = dict(slots)
    subject = _first_term(prompt, ZH_SUBJECTS)
    scene = _first_pair(prompt, ZH_SCENES)
    emotion = _first_emotion(prompt)
    motion = _first_pair(prompt, ZH_MOTIONS)
    if subject:
        updated["subject"] = subject
    if scene:
        updated["scene"] = scene[0]
    if emotion:
        updated["emotion"] = emotion[0]
    if motion:
        updated["motion"] = motion[1]
    if prompt:
        updated["action"] = _action_summary(prompt, subject, emotion, motion)
    if scene and ("雨夜" in scene[0] or "街道" in scene[0]):
        updated["lighting"] = "rainy night practical street light"
        updated["camera"] = "stable medium shot with controlled depth"
    return updated


def professional_section_details(
    request: PromptOptimizationRequest,
    slots: dict[str, str],
) -> dict[str, str]:
    if not _is_visual_target(request):
        return {}
    emotion = slots.get("emotion") or "emotion implied by the prompt"
    expression = _expression_cue(emotion)
    body_carrier = _body_carrier(emotion)
    scene = slots.get("scene") or "Primary scene"
    scene_label = _scene_label(scene)
    duration = _duration_text(request.node_parameters or {})
    source = _source_contract(request)
    is_video = request.node_type in {"video", "video_merge"} or request.generation_target == "video"

    details = {
        "Subject/Character": (
            f"Professional visual contract: subject identity = {slots.get('subject') or 'Primary character'}; "
            f"restrained realistic expression cues = {expression}; decompose expression before action; "
            f"body carrier = {body_carrier}."
        ),
        "Scene/Production Design": (
            f"Professional scene grounding: grounded scene = {scene_label}; define foreground, midground, and background, "
            "stable props, atmosphere, and a usable production-design anchor."
        ),
        "Action/Beat": (
            f"Expression mechanism first: {expression}; then visible action = {slots.get('action')}. "
            f"Use body carrier through {body_carrier}; keep performance realistic and restrained."
        ),
        "Camera/Framing": (
            "Professional camera details: choose shot scale, lens feel, angle, composition, subject position, "
            "and negative space for controllable image/video generation."
        ),
        "Lighting": (
            "Professional light details: specify motivated light source, direction, contrast, color temperature, "
            "atmosphere, and readable face/body planes."
        ),
        "Continuity": source or (
            "Continuity contract: preserve source/asset identity when available; keep character, composition, "
            "scene geography, light direction, camera relation, and provenance constraints stable."
        ),
        "Negative Constraints": (
            "Professional negative constraints: avoid exaggerated grin, avoid oversaturation, strong flares, "
            "melodramatic acting, identity drift, face/body distortion, watermark, text artifacts, "
            "random extra characters, and unsupported provider-execution claims."
        ),
    }
    if is_video:
        details["Motion/Temporal Progression"] = (
            f"Video temporalization: Start state: {_start_state(slots, source)}. "
            f"Transition: {slots.get('motion') or slots.get('action') or request.prompt_text}; movement/body carrier = {body_carrier}; "
            f"camera/environment motion stays coherent. End state: {_end_state(slots)}. "
            f"Duration/beat language: {duration}; not a static image-edit prompt."
        )
    else:
        details["Motion/Temporal Progression"] = (
            "Single-frame image/keyframe contract: hold one decisive moment; imply micro-motion through posture, "
            "breathing, fabric, hair, light, and environment while keeping the output image-focused."
        )
    return details


def _is_visual_target(request: PromptOptimizationRequest) -> bool:
    return request.node_type in {"image", "video", "director", "video_merge"} or request.generation_target in {
        "image",
        "keyframe",
        "video",
    }


def _source_contract(request: PromptOptimizationRequest) -> str:
    params = request.node_parameters or {}
    source = params.get("input_source") or params.get("videoInputSource") or {}
    if isinstance(source, dict) and source.get("source_asset_id"):
        bits = [
            f"first-frame source {source.get('source_mode')}",
            f"asset {source.get('source_asset_id')}",
        ]
        if source.get("source_node_id"):
            bits.append(f"source node {source.get('source_node_id')}")
        if source.get("source_job_id"):
            bits.append(f"source job {source.get('source_job_id')}")
        return (
            "Source Continuity: "
            + ", ".join(bits)
            + "; preserve identity, first-frame composition, scene/light/camera relation, and provenance constraints; "
            "for image-to-video use motion-first continuation and avoid restating the whole image."
        )
    first_frame = str(params.get("first_frame_image_asset_id") or "").strip()
    if first_frame:
        return (
            f"Source Continuity: first-frame source asset {first_frame}; preserve identity, first-frame composition, "
            "scene/light/camera relation, and provenance constraints; use motion-first continuation and avoid restating the whole image."
        )
    if request.asset_refs:
        return (
            "Source Continuity: preserve connected asset identity, composition, provenance, and source constraints; "
            f"asset refs = {', '.join(request.asset_refs[:4])}."
        )
    return ""


def _expression_cue(emotion: str) -> str:
    if emotion in {"笑", "微笑"}:
        return "soft smile, relaxed eyes, gently lifted cheeks, mouth corners raised without exaggerated grin"
    if emotion == "开心":
        return "subtle happiness, relaxed brow, softened eyes, small controlled smile"
    if emotion == "紧张":
        return "tension, held breath, tightened shoulders, cautious gaze, small facial restraint"
    if emotion in {"悲伤", "难过"}:
        return "sadness, lowered gaze, softened mouth, reduced muscle tension, quiet posture"
    if emotion == "害怕":
        return "fear, widened attention, shallow breath, guarded shoulders, restrained movement"
    if emotion == "生气":
        return "anger, tightened jaw, focused eyes, controlled shoulders, no theatrical overacting"
    return "restrained realistic expression"


def _body_carrier(emotion: str) -> str:
    if emotion in {"笑", "微笑", "开心"}:
        return "shoulders, breathing, eye focus, cheek tension, and relaxed hands/posture"
    if emotion == "紧张":
        return "shoulders, breath, hands, neck tension, and guarded stance"
    if emotion in {"悲伤", "难过"}:
        return "downward gaze, shoulders, slow breathing, and reduced gesture"
    return "eyes, breath, shoulders, hands, posture, and movement amplitude"


def _start_state(slots: dict[str, str], source: str) -> str:
    if source:
        return "begin from the first-frame source pose, composition, light, and identity"
    return f"begin with {slots.get('subject') or 'the subject'} in {slots.get('scene') or 'the grounded scene'}"


def _end_state(slots: dict[str, str]) -> str:
    emotion = slots.get("emotion")
    if emotion in {"笑", "微笑", "开心"}:
        return "settle into a restrained smile with stable identity and composition"
    if emotion == "紧张":
        return "hold visible tension without a sudden scene or identity change"
    if emotion in {"悲伤", "难过"}:
        return "settle into a quiet sad beat without melodrama"
    return "finish on a stable readable emotional beat"


def _duration_text(params: dict[str, Any]) -> str:
    for key in ("duration", "duration_sec"):
        value = str(params.get(key) or "").strip()
        if value:
            return value
    return "short controlled beat"


def _action_summary(
    prompt: str,
    subject: str,
    emotion: tuple[str, str] | None,
    motion: tuple[str, str] | None,
) -> str:
    if motion and emotion:
        return f"{motion[1]} into {emotion[1]}"
    if emotion:
        who = subject or "subject"
        return f"{who} expresses {emotion[1]}"
    return prompt


def _scene_label(scene: str) -> str:
    for zh, en in ZH_SCENES:
        if zh == scene:
            return en
    return scene


def _first_emotion(text: str) -> tuple[str, str] | None:
    matches = [(text.find(term), term, label) for term, label in ZH_EMOTIONS if term in text]
    matches = [item for item in matches if item[0] >= 0]
    if not matches:
        return None
    _, term, label = min(matches, key=lambda item: item[0])
    return term, label


def _first_pair(text: str, pairs: tuple[tuple[str, str], ...]) -> tuple[str, str] | None:
    matches = [(text.find(term), term, label) for term, label in pairs if term in text]
    matches = [item for item in matches if item[0] >= 0]
    if not matches:
        return None
    _, term, label = min(matches, key=lambda item: item[0])
    return term, label


def _first_term(text: str, terms: tuple[str, ...]) -> str:
    matches = [(text.find(term), term) for term in terms if term in text]
    matches = [item for item in matches if item[0] >= 0]
    return min(matches, key=lambda item: item[0])[1] if matches else ""


def _contains_zh(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


__all__ = ("apply_professional_slot_overrides", "professional_section_details")
