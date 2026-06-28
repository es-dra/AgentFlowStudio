from __future__ import annotations

from typing import Any


EXPERT_DOMAINS = (
    "camera",
    "lighting",
    "depth_of_field",
    "editing_pacing",
    "art_direction",
    "motion_design",
    "continuity",
)


def expert_knowledge_from_text(
    text: str,
    *,
    node_type: str,
    generation_target: str,
    target_platform: str = "short_video",
) -> dict[str, Any]:
    tags = _tags(text, node_type=node_type, generation_target=generation_target)
    domains = {
        "camera": _camera(tags),
        "lighting": _lighting(tags),
        "depth_of_field": _depth_of_field(tags),
        "editing_pacing": _editing_pacing(tags, target_platform),
        "art_direction": _art_direction(tags),
        "motion_design": _motion_design(tags),
        "continuity": _continuity(tags),
    }
    return {
        "artifact_type": "agentflow_expert_knowledge_context",
        "schema_version": "0.1.0",
        "node_type": node_type,
        "generation_target": generation_target,
        "target_platform": target_platform,
        "tags": tags,
        "domains": domains,
        "selection_reasons": [f"detected_{tag}" for tag in tags] or ["fallback_expert_baseline"],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def format_expert_knowledge_reference(context: dict[str, Any], *, domains: list[str] | None = None) -> str:
    selected = domains or list(EXPERT_DOMAINS)
    domain_map = context.get("domains") if isinstance(context, dict) else {}
    if not isinstance(domain_map, dict):
        return ""
    lines = ["Expert knowledge reference:"]
    for domain in selected:
        section = domain_map.get(domain)
        if not isinstance(section, dict):
            continue
        decision = str(section.get("decision") or "").strip()
        must = "; ".join(str(item) for item in (section.get("must_include") or [])[:3])
        avoid = "; ".join(str(item) for item in (section.get("avoid") or [])[:2])
        if decision:
            line = f"- {domain}: {decision}"
            if must:
                line += f"; include {must}"
            if avoid:
                line += f"; avoid {avoid}"
            lines.append(line)
    return "\n".join(lines) if len(lines) > 1 else ""


def _tags(text: str, *, node_type: str, generation_target: str) -> list[str]:
    source = str(text or "").lower()
    original = str(text or "")
    mapping = {
        "night": ("night", "star", "moon", "星", "夜", "月"),
        "rooftop": ("rooftop", "roof", "屋顶", "天台"),
        "rural": ("rural", "village", "countryside", "农村", "乡村"),
        "robot": ("robot", "android", "机器人"),
        "observational": ("watch", "observe", "look", "看", "仰望", "凝视"),
        "action": ("fight", "battle", "chase", "run", "战", "冲突", "追逐"),
        "product": ("product", "dashboard", "app", "software", "产品", "界面", "仪表盘"),
        "portrait": ("face", "portrait", "emotion", "脸", "表情", "情绪"),
        "low_key": ("low key", "dark", "shadow", "低照度", "昏暗"),
        "interior": ("interior", "room", "office", "室内", "房间", "办公室"),
    }
    tags = [tag for tag, patterns in mapping.items() if any(pattern in source or pattern in original for pattern in patterns)]
    if generation_target == "video" or node_type == "video":
        tags.append("video")
    if generation_target in {"image", "keyframe"} or node_type == "image":
        tags.append("single_frame")
    return sorted(set(tags))


def _camera(tags: list[str]) -> dict[str, Any]:
    if {"night", "rooftop", "observational"}.issubset(tags):
        return _section(
            "stable medium or rear three-quarter framing that preserves subject, rooftop boundary, and sky scale",
            ["camera height at or slightly below subject shoulder", "stable horizon or rooftop edge", "one subtle breath or push"],
            ["cutting away from the sky", "new high-angle roof geometry"],
        )
    if "action" in tags:
        return _section(
            "single readable action vector with camera movement subordinated to subject clarity",
            ["screen direction", "impact/reaction space", "subject scale continuity"],
            ["stacked camera moves", "motion blur hiding identity"],
        )
    if "product" in tags:
        return _section(
            "locked or slow product-screen framing that keeps UI or object state legible",
            ["product silhouette", "task-result relationship", "controlled perspective"],
            ["fast handheld movement", "tiny unreadable UI"],
        )
    return _section(
        "camera choice must name shot size, height, subject priority, and movement purpose",
        ["shot scale", "camera height", "movement intent"],
        ["generic cinematic phrasing", "conflicting angles inside one clip"],
    )


def _lighting(tags: list[str]) -> dict[str, Any]:
    if "night" in tags and "rooftop" in tags:
        return _section(
            "motivated moon/star ambience plus distant practical spill and subtle rim separation",
            ["source direction", "edge readability", "controlled color temperature"],
            ["daylight-bright exposure", "unmotivated spotlight"],
        )
    if "low_key" in tags or "interior" in tags:
        return _section(
            "motivated key/fill/back separation tied to window, lamp, screen, or doorway",
            ["key direction", "fill ratio", "shadow detail"],
            ["flat fill", "random neon color without source"],
        )
    return _section(
        "light must specify source, direction, contrast, color temperature, and atmosphere",
        ["motivated source", "contrast level", "subject readability"],
        ["style adjectives without source", "lighting that breaks continuity"],
    )


def _depth_of_field(tags: list[str]) -> dict[str, Any]:
    if "night" in tags and "rooftop" in tags:
        return _section(
            "moderate-to-deep depth so the subject remains primary while the star field stays legible",
            ["sharp subject silhouette", "readable sky layer", "distant environment cue"],
            ["heavy bokeh erasing stars", "flat focus with no subject separation"],
        )
    if "portrait" in tags:
        return _section(
            "shallow-to-moderate depth only when face or emotion is the beat priority",
            ["sharp identity features", "soft identifiable environment", "stable eye/face plane"],
            ["blurred defining features", "macro depth on full-body shots"],
        )
    return _section(
        "depth follows the subject-environment hierarchy instead of default lens jargon",
        ["subject plane", "background readability", "separation method"],
        ["default shallow depth", "depth choice that hides story context"],
    )


def _editing_pacing(tags: list[str], target_platform: str) -> dict[str, Any]:
    if "video" in tags and "observational" in tags:
        return _section(
            "slow short-video continuity: anchor first frame, add one micro action, settle clearly",
            ["first second visual anchor", "middle micro action", "final readable hold"],
            ["extra plot event", "large composition jump"],
        )
    if "video" in tags and "action" in tags:
        return _section(
            "one action beat with a readable acceleration, impact, and reaction rather than multiple fights",
            ["start pose", "single vector", "held reaction"],
            ["multi-beat choreography in 5s", "unreadable impact"],
        )
    return _section(
        f"{target_platform} pacing should protect comprehension before adding motion density",
        ["one beat objective", "clear beginning-middle-end", "settled final state"],
        ["rewritten story", "too many actions for duration"],
    )


def _art_direction(tags: list[str]) -> dict[str, Any]:
    if "robot" in tags:
        return _section(
            "surface material, silhouette, joints, and signature features are treated as locked art-direction facts",
            ["head shell material", "body proportion", "joint layout"],
            ["changing character category", "new costume layer unless scripted"],
        )
    if "rooftop" in tags:
        return _section(
            "scene dressing must preserve approved rooftop platform geometry and only add scripted set pieces",
            ["roof boundary", "surface material", "approved background"],
            ["unapproved eaves", "unapproved chair or stool"],
        )
    return _section(
        "art direction separates character, prop, scene, palette, and material decisions into editable facts",
        ["material", "signature silhouette", "approved set dressing"],
        ["untracked prop insertion", "style drift between nodes"],
    )


def _motion_design(tags: list[str]) -> dict[str, Any]:
    if {"robot", "observational"}.issubset(tags):
        return _section(
            "mechanical micro motion: subtle head tilt, sensor glow, small posture shift, and no human-like exaggeration",
            ["joint-consistent movement", "small gaze change", "restrained body shift"],
            ["rubber-limb deformation", "large unscripted walk cycle"],
        )
    if "action" in tags:
        return _section(
            "motion should expose intent, vector, contact, and recovery with identity still readable",
            ["anticipation", "clean vector", "settle/reaction"],
            ["constant high-speed blur", "new weapon or opponent"],
        )
    return _section(
        "motion must be one controllable continuation from the first frame",
        ["start pose continuity", "primary movement", "settled end pose"],
        ["looping random motion", "scene-changing transition"],
    )


def _continuity(tags: list[str]) -> dict[str, Any]:
    avoid = ["identity drift", "new characters", "new props", "text/watermark/UI"]
    if "rooftop" in tags:
        avoid.extend(["unapproved eaves", "unapproved chair or stool"])
    return _section(
        "continuity tracks identity, wardrobe/material, prop geometry, scene layout, light direction, and camera composition",
        ["asset locks", "negative locks", "first-frame anchor"],
        avoid,
    )


def _section(decision: str, must_include: list[str], avoid: list[str]) -> dict[str, Any]:
    return {
        "decision": decision,
        "must_include": must_include,
        "avoid": avoid,
        "quality_checks": [
            "guidance is visible in the generated frame or clip",
            "constraint can be checked against upstream assets",
        ],
    }


__all__ = ("EXPERT_DOMAINS", "expert_knowledge_from_text", "format_expert_knowledge_reference")
