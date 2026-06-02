from __future__ import annotations

from agentflow_studio.production.schemas import (
    CONTENT_MODE,
    CostQualityTrace,
    CreativeBrief,
    EpisodeBeat,
    EpisodeOutline,
    FeedbackSignalLog,
    MemoryCandidate,
    MemoryCandidateStore,
    ProductionHandoff,
    PromptItem,
    PromptPack,
    Scene,
    ScenePlan,
    Shot,
    ShotPlan,
    StoryBible,
    Character,
)


def build_story_bible(brief: CreativeBrief) -> StoryBible:
    protagonist = Character(
        character_id="char_protagonist",
        name="Protagonist",
        role="lead",
        motivation=f"Resolve the central tension: {brief.core_theme}.",
        visual_notes=f"{brief.genre} lead, {brief.tone} styling.",
    )
    counterpart = Character(
        character_id="char_counterpart",
        name="Counterpart",
        role="pressure_source",
        motivation="Force the lead to make visible choices.",
        visual_notes="Contrasting silhouette and clearer status signal.",
    )
    return StoryBible(
        story_bible_id=f"{brief.brief_id}_story_bible",
        source_brief_id=brief.brief_id,
        project_title=brief.project_title,
        world_rules=[
            f"Every scene must reinforce: {brief.logline}",
            f"Keep the world readable for {brief.target_audience}.",
        ],
        characters=[protagonist, counterpart],
        style_rules=[
            f"Tone stays {brief.tone}.",
            f"Genre cues stay inside {brief.genre}.",
            "Prefer visible decisions over exposition.",
        ],
        continuity_rules=brief.must_include + brief.constraints,
    )


def build_episode_outline(brief: CreativeBrief, bible: StoryBible) -> EpisodeOutline:
    beats = [
        EpisodeBeat(
            beat_id="beat_001",
            title="Hook",
            purpose="Start with the clearest conflict signal.",
            summary=brief.logline,
        ),
        EpisodeBeat(
            beat_id="beat_002",
            title="Escalation",
            purpose="Turn the theme into a concrete choice.",
            summary=f"The lead tests a risky response to {brief.core_theme}.",
        ),
        EpisodeBeat(
            beat_id="beat_003",
            title="Handoff",
            purpose="Leave a production-ready cliffhanger.",
            summary="The episode closes on a visual decision point.",
        ),
    ]
    return EpisodeOutline(
        episode_outline_id=f"{brief.brief_id}_episode_outline_e01",
        source_brief_id=brief.brief_id,
        story_bible_id=bible.story_bible_id,
        project_title=brief.project_title,
        beats=beats[: max(1, min(brief.episode_count + 2, len(beats)))],
        cliffhanger=f"A final reveal reframes {brief.core_theme}.",
    )


def build_scene_plan(outline: EpisodeOutline) -> ScenePlan:
    scenes = [
        Scene(
            scene_id=f"scene_{index:03d}",
            beat_id=beat.beat_id,
            title=beat.title,
            location="controlled practical set",
            dramatic_purpose=beat.purpose,
            visual_mood="clear contrast, readable action",
        )
        for index, beat in enumerate(outline.beats, start=1)
    ]
    return ScenePlan(
        scene_plan_id=f"{outline.episode_outline_id}_scene_plan",
        episode_outline_id=outline.episode_outline_id,
        scenes=scenes,
    )


def build_shot_plan(scene_plan: ScenePlan, brief: CreativeBrief) -> ShotPlan:
    shots: list[Shot] = []
    per_shot_duration = max(3, min(12, brief.target_episode_duration_sec // max(1, len(scene_plan.scenes) * 2)))
    for scene in scene_plan.scenes:
        shots.append(
            Shot(
                shot_id=f"{scene.scene_id}_shot_001",
                scene_id=scene.scene_id,
                shot_type="wide_establishing",
                description=f"Establish {scene.location} with {scene.visual_mood}.",
                duration_sec=per_shot_duration,
                production_notes=["Keep geography readable."],
            )
        )
        shots.append(
            Shot(
                shot_id=f"{scene.scene_id}_shot_002",
                scene_id=scene.scene_id,
                shot_type="character_decision",
                description=f"Show the character choice behind: {scene.dramatic_purpose}",
                duration_sec=per_shot_duration,
                production_notes=["Prioritize action over dialogue."],
            )
        )
    return ShotPlan(
        shot_plan_id=f"{scene_plan.scene_plan_id}_shot_plan",
        scene_plan_id=scene_plan.scene_plan_id,
        shots=shots,
    )


def build_prompt_pack(shot_plan: ShotPlan, bible: StoryBible) -> PromptPack:
    style = "; ".join(bible.style_rules[:2])
    prompts = [
        PromptItem(
            prompt_id=f"{shot.shot_id}_prompt",
            shot_id=shot.shot_id,
            prompt_text=f"{shot.description} {style}",
            negative_prompt="unreadable action, inconsistent character, cluttered frame",
            intended_use="visual_generation",
        )
        for shot in shot_plan.shots
    ]
    return PromptPack(
        prompt_pack_id=f"{shot_plan.shot_plan_id}_prompt_pack",
        shot_plan_id=shot_plan.shot_plan_id,
        prompts=prompts,
    )


def build_production_handoff(
    brief: CreativeBrief,
    bible: StoryBible,
    outline: EpisodeOutline,
    scene_plan: ScenePlan,
    shot_plan: ShotPlan,
    prompt_pack: PromptPack,
) -> ProductionHandoff:
    return ProductionHandoff(
        handoff_id=f"{brief.brief_id}_production_handoff",
        project_title=brief.project_title,
        source_brief_id=brief.brief_id,
        story_bible_id=bible.story_bible_id,
        episode_outline_id=outline.episode_outline_id,
        scene_plan_id=scene_plan.scene_plan_id,
        shot_plan_id=shot_plan.shot_plan_id,
        prompt_pack_id=prompt_pack.prompt_pack_id,
        ready_for=["visual_generation", "shooting_plan", "editorial_review"],
        open_risks=brief.constraints,
        artifact_refs={
            "creative_brief": "creative_brief.json",
            "story_bible": "story_bible.json",
            "episode_outline": "episode_outline.json",
            "scene_plan": "scene_plan.json",
            "shot_plan": "shot_plan.json",
            "prompt_pack": "prompt_pack.json",
        },
    )


def build_memory_candidates(brief: CreativeBrief, bible: StoryBible, run_id: str) -> MemoryCandidateStore:
    return MemoryCandidateStore(
        run_id=run_id,
        candidates=[
            MemoryCandidate(
                id=f"{brief.brief_id}_style_candidate",
                memory_type="style_preference",
                statement=f"Project favors {brief.tone} {brief.genre} production language.",
                evidence_refs=["creative_brief.json", "story_bible.json"],
                confidence=0.65,
            ),
            MemoryCandidate(
                id=f"{brief.brief_id}_continuity_candidate",
                memory_type="continuity_rule",
                statement=bible.continuity_rules[0] if bible.continuity_rules else "No explicit continuity rule supplied.",
                evidence_refs=["story_bible.json"],
                confidence=0.55,
            ),
        ],
    )


def build_cost_quality_trace(run_id: str) -> CostQualityTrace:
    return CostQualityTrace(
        run_id=run_id,
        provider="local_deterministic",
        execution_mode="local_deterministic",
        estimated_cost=0,
        input_artifacts=["creative_brief.json"],
        output_artifacts=["production_handoff.json", "production_report.md"],
        quality_proxy={"shot_prompt_alignment": 1.0, "schema_validation": 1.0},
        applicable_scenario=CONTENT_MODE,
    )


def build_feedback_signal_log(run_id: str) -> FeedbackSignalLog:
    return FeedbackSignalLog(run_id=run_id, signals=[])
