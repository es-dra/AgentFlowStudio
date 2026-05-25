from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratostudio.posterflow.schemas import (
    ContextBundle,
    NextRoundPrompt,
    PosterBrief,
    PosterRawFeedbackEvent,
    PosterFeedbackSignal,
    PosterFeedbackSignalLog,
    PosterMemoryCandidate,
    PosterMemoryCandidates,
    PosterMemoryDecision,
    PosterMemoryDecisions,
    PosterMemoryReviewEvent,
    PosterPlan,
    PosterPreferenceProfile,
    PosterPromptPack,
)


def load_poster_brief(path: str | Path) -> PosterBrief:
    return PosterBrief.model_validate(_read_json(path))


def build_poster_plan(brief: PosterBrief, run_id: str) -> PosterPlan:
    visual = brief.visual_requirements
    text = brief.text_requirements
    constraints = brief.constraints
    negative_rules = list(visual.get("negative_visuals", [])) + list(constraints.get("must_avoid", []))
    return PosterPlan(
        project_id=brief.project_id,
        run_id=run_id,
        design_intent=f"Create a {brief.platform} poster for {brief.theme}: {brief.content_goal}",
        layout_plan={
            "layout_type": "single_character_centered",
            "subject_position": "center",
            "text_position": "top_and_bottom",
            "safe_area_notes": "Keep title and subtitle away from the main face area.",
        },
        visual_plan={
            "main_subject": ", ".join(visual.get("main_subject", constraints.get("must_include", []))),
            "style_tags": visual.get("style_keywords", []),
            "composition": visual.get("composition_preferences", []),
            "mood": brief.business_goal,
        },
        color_plan={
            "palette": visual.get("color_preferences", ["blue-black", "cold gold"]),
            "saturation": "low",
            "contrast": "medium_high",
        },
        text_plan={
            "title": text.get("title", ""),
            "subtitle": text.get("subtitle", ""),
            "text_density": text.get("text_density", "low"),
        },
        negative_rules=negative_rules,
        planner_notes="Initial PosterFlow demo plan; remote image generation remains explicit opt-in.",
    )


def build_poster_prompt_pack(plan: PosterPlan) -> PosterPromptPack:
    style_tags = ", ".join(plan.visual_plan.get("style_tags", []))
    colors = ", ".join(plan.color_plan.get("palette", []))
    negative = ", ".join(plan.negative_rules)
    title = plan.text_plan.get("title", "")
    subtitle = plan.text_plan.get("subtitle", "")
    return PosterPromptPack(
        project_id=plan.project_id,
        run_id=plan.run_id,
        prompt_id=f"{plan.run_id}_poster_prompt_001",
        target_model_family="openai_compatible_image",
        prompt_language="en",
        positive_prompt=(
            "premium cinematic short drama poster, single clear main character, "
            f"{style_tags}, {colors}, low saturation, elegant composition, "
            f"clean title space for Chinese text '{title}' and subtitle '{subtitle}', "
            f"{plan.design_intent}"
        ),
        negative_prompt=negative,
        prompt_sections={
            "subject": str(plan.visual_plan.get("main_subject", "")),
            "style": style_tags,
            "composition": str(plan.visual_plan.get("composition", "")),
            "color": colors,
        },
        model_params={"size": "1024x1536", "num_candidates": 3, "seed_policy": "provider_default"},
        context_usage={"project_prefix_used": False, "preference_profile_used": False, "memory_refs": []},
        source_refs={"poster_plan": "poster_plan.json"},
    )


def build_feedback_signal_log(
    feedback_path: str | Path,
    *,
    project_id: str,
    run_id: str,
) -> PosterFeedbackSignalLog:
    payload = _read_json(feedback_path)
    raw_signals = payload.get("signals") if isinstance(payload.get("signals"), list) else []
    signals = [PosterFeedbackSignal.model_validate(item) for item in raw_signals]
    return PosterFeedbackSignalLog(
        project_id=project_id,
        run_id=run_id,
        source_of_truth="poster_feedback.jsonl",
        signals=signals,
    )


def build_raw_feedback_events(
    feedback: PosterFeedbackSignalLog,
    *,
    created_at: str,
) -> list[PosterRawFeedbackEvent]:
    return [
        PosterRawFeedbackEvent(
            feedback_id=signal.feedback_id,
            project_id=feedback.project_id,
            run_id=feedback.run_id,
            source=signal.source,
            target_id=signal.candidate_id,
            decision=signal.decision,
            reason_tags=signal.reason_tags,
            user_note=signal.user_note,
            created_at=created_at,
        )
        for signal in feedback.signals
    ]


def extract_memory_candidates(feedback: PosterFeedbackSignalLog) -> PosterMemoryCandidates:
    preferred_tags: list[str] = []
    rejected_tags: list[str] = []
    for signal in feedback.signals:
        if signal.decision in {"preferred", "accepted"}:
            preferred_tags.extend(signal.reason_tags)
        if signal.decision == "rejected":
            rejected_tags.extend(signal.reason_tags)
    candidates: list[PosterMemoryCandidate] = []
    if preferred_tags:
        candidates.append(
            PosterMemoryCandidate(
                memory_candidate_id=f"{feedback.run_id}_visual_preference",
                memory_type="visual_style_preference",
                claim=f"Project prefers: {', '.join(_unique(preferred_tags))}.",
                evidence_refs=["poster_feedback_signal_log.json"],
                confidence=0.78,
            )
        )
    if rejected_tags:
        candidates.append(
            PosterMemoryCandidate(
                memory_candidate_id=f"{feedback.run_id}_negative_visual_preference",
                memory_type="negative_visual_preference",
                claim=f"Project should avoid: {', '.join(_unique(rejected_tags))}.",
                evidence_refs=["poster_feedback_signal_log.json"],
                confidence=0.82,
            )
        )
    return PosterMemoryCandidates(project_id=feedback.project_id, run_id=feedback.run_id, candidates=candidates)


def build_memory_review_events(decisions: PosterMemoryDecisions) -> list[PosterMemoryReviewEvent]:
    return [
        PosterMemoryReviewEvent(
            review_id=decision.decision_id,
            project_id=decisions.project_id,
            run_id=decisions.run_id,
            memory_candidate_id=decision.memory_candidate_id,
            decision=decision.decision,
            reason=decision.reason,
        )
        for decision in decisions.decisions
    ]


def accept_memory_candidates(memory: PosterMemoryCandidates) -> PosterMemoryDecisions:
    return PosterMemoryDecisions(
        project_id=memory.project_id,
        run_id=memory.run_id,
        decisions=[
            PosterMemoryDecision(
                decision_id=f"{candidate.memory_candidate_id}_decision",
                memory_candidate_id=candidate.memory_candidate_id,
                decision="accepted",
                reason="Demo human review gate accepts this candidate for project-scoped prompt reuse.",
            )
            for candidate in memory.candidates
        ],
    )


def build_preference_profile(
    memory: PosterMemoryCandidates,
    decisions: PosterMemoryDecisions,
) -> PosterPreferenceProfile:
    accepted_ids = {decision.memory_candidate_id for decision in decisions.decisions if decision.decision == "accepted"}
    accepted = [candidate for candidate in memory.candidates if candidate.memory_candidate_id in accepted_ids]
    positive = [candidate.claim for candidate in accepted if candidate.memory_type == "visual_style_preference"]
    negative = [candidate.claim for candidate in accepted if candidate.memory_type == "negative_visual_preference"]
    return PosterPreferenceProfile(
        project_id=memory.project_id,
        visual_preferences=positive,
        negative_visual_preferences=negative,
        layout_preferences=["Keep the main character readable and avoid cluttered backgrounds."],
        text_preferences=["Use low text density and leave clean title/subtitle areas."],
        prompt_rules=[
            "Positive prompt should preserve cinematic poster, low saturation, premium composition.",
            "Negative prompt should preserve rejected visual tags from accepted memory candidates.",
        ],
        source_memory_candidates=[candidate.memory_candidate_id for candidate in accepted],
    )


def build_project_prefix(profile: PosterPreferenceProfile) -> str:
    return "\n".join(
        [
            f"# Project Prefix: {profile.project_id}",
            "",
            "## Visual Preferences",
            *_markdown_items(profile.visual_preferences),
            "",
            "## Negative Visuals",
            *_markdown_items(profile.negative_visual_preferences),
            "",
            "## Prompt Rules",
            *_markdown_items(profile.prompt_rules),
            "",
        ]
    )


def build_next_round_prompt(
    prompt_pack: PosterPromptPack,
    profile: PosterPreferenceProfile,
    context_bundle: ContextBundle | None = None,
) -> NextRoundPrompt:
    positive_memory = " ".join(profile.visual_preferences + profile.layout_preferences)
    negative_memory = " ".join(profile.negative_visual_preferences)
    return NextRoundPrompt(
        project_id=profile.project_id,
        new_run_id=f"{prompt_pack.run_id}_next",
        based_on_profile_version=profile.profile_version,
        memory_context={
            "project_prefix_path": "project_prefix.md",
            "preference_profile_path": "poster_preference_profile.json",
            "context_bundle_path": "context_bundle.json" if context_bundle else None,
            "memory_refs": profile.source_memory_candidates,
            "rag_refs": [],
            "cache_key": context_bundle.cache_plan["cache_key"] if context_bundle else None,
        },
        task_delta={
            "new_request": "Next PosterFlow demo round should reuse confirmed project preferences.",
            "changed_elements": ["story_event"],
            "unchanged_elements": ["visual_style", "negative_constraints", "platform"],
        },
        composed_positive_prompt=f"{prompt_pack.positive_prompt} {positive_memory}".strip(),
        composed_negative_prompt=f"{prompt_pack.negative_prompt}, {negative_memory}".strip(", "),
        diff_from_previous_prompt={
            "kept": ["cinematic poster", "low saturation", "premium composition"],
            "added": profile.source_memory_candidates,
            "removed": [],
        },
    )


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _markdown_items(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None"]
