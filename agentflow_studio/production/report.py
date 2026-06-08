from __future__ import annotations

from agentflow_studio.production.schemas import (
    CreativeBrief,
    ProductionHandoff,
    PromptPack,
    ScenePlan,
    ShotPlan,
    StoryBible,
)


def render_production_report(
    brief: CreativeBrief,
    bible: StoryBible,
    scene_plan: ScenePlan,
    shot_plan: ShotPlan,
    prompt_pack: PromptPack,
    handoff: ProductionHandoff,
) -> str:
    risks = handoff.open_risks or ["No blocking risk captured in the brief."]
    return "\n".join(
        [
            f"# {brief.project_title} Production Handoff",
            "",
            "## Positioning",
            "",
            "AgentFlow Production MVP is a provider-gated structured production handoff generator.",
            "",
            f"- Content mode: {brief.content_mode}",
            f"- Target audience: {brief.target_audience}",
            f"- Platform: {brief.platform}",
            f"- Tone: {brief.tone}",
            "",
            "## Story Rules",
            "",
            *_bullets(bible.style_rules),
            "",
            "## Production Scope",
            "",
            f"- Scenes: {len(scene_plan.scenes)}",
            f"- Shots: {len(shot_plan.shots)}",
            f"- Prompts: {len(prompt_pack.prompts)}",
            f"- Ready for: {', '.join(handoff.ready_for)}",
            "",
            "## Open Risks",
            "",
            *_bullets(risks),
            "",
            "## Machine Artifacts",
            "",
            *_bullets(f"{name}: {path}" for name, path in handoff.artifact_refs.items()),
            "- production_handoff: production_handoff.json",
        ]
    )


def _bullets(items: object) -> list[str]:
    return [f"- {item}" for item in items]
