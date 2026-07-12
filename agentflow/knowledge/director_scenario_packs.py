from __future__ import annotations

from typing import Any


SECTION_FIELDS = {
    "Intent": ("scenario_goal", "hook_patterns", "platform_rules"),
    "Scene/Production Design": ("asset_strategy", "quality_checks"),
    "Action/Beat": ("hook_patterns", "timeline_template"),
    "Camera/Framing": ("camera_rules",),
    "Lighting": ("lighting_rules",),
    "Motion/Temporal Progression": ("timeline_template", "sound_rules"),
    "Continuity": ("continuity_rules", "quality_checks"),
    "Negative Constraints": ("negative_constraints",),
}


DIRECTOR_SCENARIO_PACKS: tuple[dict[str, Any], ...] = (
    {
        "scenario_id": "faceless_channel",
        "label": "Faceless Channel",
        "trigger_terms": (
            "faceless",
            "no face",
            "voiceover",
            "narration",
            "finance",
            "explainer",
            "b-roll",
            "anonymous",
            "\u65e0\u8138",
            "\u65c1\u767d",
            "\u8d22\u7ecf",
            "\u89e3\u8bf4",
        ),
        "scenario_goal": "convert an idea or narration into visual proof, not a presenter-dependent scene",
        "hook_patterns": [
            "first two seconds expose a contrast, data point, or consequence",
            "show the result before the explanation when the topic allows it",
        ],
        "timeline_template": [
            "0.0s-0.7s: visual hook or contradiction",
            "0.7s-3.5s: one evidence beat with supporting visual motion",
            "3.5s-5.0s: payoff, implication, or next question",
        ],
        "camera_rules": [
            "prioritize readable objects, locations, diagrams, or hands over talking-head framing",
            "use locked or slow lateral movement so narration remains easy to follow",
        ],
        "lighting_rules": [
            "keep information surfaces legible before mood",
            "motivate contrast from practical lights, windows, screens, or environment",
        ],
        "sound_rules": [
            "voiceover leads the timing; visual beats should land on sentence turns",
            "sound effects mark evidence changes, not every small object movement",
        ],
        "asset_strategy": [
            "seed reusable topic props, data surfaces, locations, and symbolic objects as editable assets",
            "do not invent a host face unless the user explicitly asks for one",
        ],
        "platform_rules": ["short-video retention depends on a clear first visual claim"],
        "continuity_rules": ["keep evidence objects and scene logic stable across shots"],
        "quality_checks": ["hook is visible without reading generated text", "narration and image answer the same question"],
        "negative_constraints": ["no unrequested presenter face", "no provider-rendered captions or UI text"],
    },
    {
        "scenario_id": "saas_launch",
        "label": "SaaS Launch",
        "trigger_terms": (
            "saas",
            "software",
            "app",
            "product launch",
            "dashboard",
            "workflow",
            "feature",
            "demo",
            "screen",
            "startup",
            "landing page",
            "\u8f6f\u4ef6",
            "\u5e94\u7528",
            "\u754c\u9762",
            "\u4eea\u8868\u76d8",
            "\u529f\u80fd",
            "\u53d1\u5e03",
        ),
        "scenario_goal": "turn product value into a visible before-after workflow",
        "hook_patterns": [
            "open with the painful state or finished outcome, then reveal the product action",
            "focus on one feature result per short clip",
        ],
        "timeline_template": [
            "0.0s-0.8s: problem or outcome state",
            "0.8s-2.5s: one interface or workflow transformation",
            "2.5s-4.2s: proof state, saved time, or clearer result",
            "4.2s-5.0s: settle on final product state",
        ],
        "camera_rules": [
            "use stable product-screen framing or clean over-shoulder context",
            "avoid fast camera moves that make UI state unreadable",
        ],
        "lighting_rules": [
            "use clean practical or screen-motivated light",
            "separate product surface from background without decorative glare",
        ],
        "sound_rules": [
            "motion accents should mark task completion or state change",
            "voiceover should state the user benefit before naming the feature",
        ],
        "asset_strategy": [
            "treat dashboard, device, cursor/action handoff, and result screen as separate editable assets",
            "keep UI text out of provider-generated pixels unless a later overlay system owns it",
        ],
        "platform_rules": ["short demos need one job-to-be-done and one proof point"],
        "continuity_rules": ["screen state must progress logically and not reset between beats"],
        "quality_checks": ["user benefit is visible", "screen geometry remains readable"],
        "negative_constraints": ["no fake brand claims", "no tiny unreadable UI text", "no unrelated stock-office filler"],
    },
    {
        "scenario_id": "podcast_visual",
        "label": "Podcast Visual",
        "trigger_terms": (
            "podcast",
            "interview",
            "audio clip",
            "quote",
            "transcript",
            "speaker",
            "audiogram",
            "\u64ad\u5ba2",
            "\u8bbf\u8c08",
            "\u97f3\u9891",
            "\u91d1\u53e5",
            "\u91c7\u8bbf",
        ),
        "scenario_goal": "translate a spoken moment into a visible speaker, reaction, or metaphor beat",
        "hook_patterns": [
            "start on the strongest sentence or reaction instead of studio atmosphere",
            "visualize the claim when the speaker is not the main asset",
        ],
        "timeline_template": [
            "0.0s-0.6s: speaker, quote setup, or visual metaphor hook",
            "0.6s-3.8s: hold the core quote with subtle reaction or metaphor motion",
            "3.8s-5.0s: settle on the emotional or conceptual takeaway",
        ],
        "camera_rules": [
            "use close or medium framing only when speaker identity matters",
            "reserve clean negative space for captions owned by the editing layer",
        ],
        "lighting_rules": [
            "favor warm practical studio light or source-motivated contrast",
            "keep faces readable if the speaker is an approved asset",
        ],
        "sound_rules": [
            "spoken cadence determines visual beat spacing",
            "music bed must not fight the quote or interview rhythm",
        ],
        "asset_strategy": [
            "separate speaker identity, microphone/studio props, and metaphor b-roll as editable assets",
            "do not render quote text inside generated image or video pixels",
        ],
        "platform_rules": ["the first line should be understandable even before captions are added"],
        "continuity_rules": ["speaker identity and studio layout remain stable across quote beats"],
        "quality_checks": ["quote focus is clear", "visual rhythm follows spoken cadence"],
        "negative_constraints": ["no invented speaker identity", "no provider-rendered subtitles", "no random studio props"],
    },
)


AUXILIARY_PACKS: tuple[dict[str, Any], ...] = (
    {
        "scenario_id": "viral_hook",
        "label": "Viral Hook",
        "trigger_terms": ("viral", "hook", "retention", "tiktok", "reels", "shorts", "\u7206\u6b3e", "\u94a9\u5b50", "\u7559\u5b58"),
        "scenario_goal": "compress the opening into a curiosity, stakes, or result-first beat",
        "hook_patterns": ["first two seconds must create a visible reason to keep watching"],
        "timeline_template": ["0.0s-2.0s: hook; 2.0s-end: prove or extend the hook"],
        "camera_rules": ["use one strong visual priority instead of multiple competing movements"],
        "lighting_rules": ["make the hook readable before adding style"],
        "sound_rules": ["sound onset should support the hook, not distract from it"],
        "asset_strategy": ["only use hook assets that already belong to the story or product"],
        "platform_rules": ["optimize for short-video retention without rewriting the story"],
        "continuity_rules": ["the hook must still connect to downstream shots"],
        "quality_checks": ["opening beat is visually testable", "no clickbait object unrelated to the story"],
        "negative_constraints": ["no unrelated shock prop", "no misleading generated text"],
    },
)


DEFAULT_PACK = {
    "scenario_id": "general_short_video",
    "label": "General Short Video",
    "scenario_goal": "convert the request into one clear visual beat with controllable continuity",
    "hook_patterns": ["open on the strongest subject-environment relationship"],
    "timeline_template": [
        "0.0s-1.0s: anchor the subject, layout, and emotional direction",
        "1.0s-3.5s: advance one readable action",
        "3.5s-5.0s: settle into a clear end state",
    ],
    "camera_rules": ["choose one camera intention: reveal, follow, hold, or push"],
    "lighting_rules": ["name light source, direction, contrast, and mood"],
    "sound_rules": ["sound should support the visual beat when audio exists"],
    "asset_strategy": ["separate subject, prop, and scene cards so users can edit constraints"],
    "platform_rules": ["short-video output should stay understandable in one pass"],
    "continuity_rules": ["carry identity, scene geometry, lighting, and camera composition forward"],
    "quality_checks": ["one primary beat", "no hidden second story inside a 5s clip"],
    "negative_constraints": ["no unrelated asset insertion", "no provider-rendered text"],
}


__all__ = (
    "AUXILIARY_PACKS",
    "DEFAULT_PACK",
    "DIRECTOR_SCENARIO_PACKS",
    "SECTION_FIELDS",
)
