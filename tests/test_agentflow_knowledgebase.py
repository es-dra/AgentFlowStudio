from __future__ import annotations

import json
import re
from pathlib import Path

from agentflow.knowledge.creative_prompt_rules import (
    EXTERNAL_KNOWLEDGE_ROOT,
    REPO_KNOWLEDGE_ROOT,
    assert_knowledgebase_in_sync,
    load_creative_prompt_rules,
    normalized_knowledgebase_hash,
    select_creative_prompt_rules,
    validate_creative_prompt_rule,
)


def test_creative_prompt_knowledgebase_schema_registry_and_sync() -> None:
    assert REPO_KNOWLEDGE_ROOT.exists()
    assert EXTERNAL_KNOWLEDGE_ROOT.exists()

    repo_rules = load_creative_prompt_rules(REPO_KNOWLEDGE_ROOT)
    external_rules = load_creative_prompt_rules(EXTERNAL_KNOWLEDGE_ROOT)
    rule_ids = [rule["rule_id"] for rule in repo_rules]

    assert len(repo_rules) >= 40
    assert len(rule_ids) == len(set(rule_ids))
    assert {rule["domain"] for rule in repo_rules} >= {
        "directing",
        "cinematography",
        "lighting",
        "production_design",
        "storyboard",
        "short_video_script",
        "character_consistency",
        "keyframe_continuity",
        "video_motion",
        "director_setup_2d",
        "negative_constraints",
    }
    assert [rule["rule_id"] for rule in external_rules] == rule_ids
    assert normalized_knowledgebase_hash(REPO_KNOWLEDGE_ROOT) == normalized_knowledgebase_hash(EXTERNAL_KNOWLEDGE_ROOT)
    assert_knowledgebase_in_sync()


def test_creative_prompt_rules_are_traceable_and_safe() -> None:
    unsafe_pattern = re.compile(r"(api_key|bearer\s|signed_url|provider_config|[a-z]:\\|data/processed/runs)", re.I)

    for rule in load_creative_prompt_rules(REPO_KNOWLEDGE_ROOT):
        validate_creative_prompt_rule(rule)
        serialized = json.dumps(rule, ensure_ascii=False)
        assert not unsafe_pattern.search(serialized)
        assert rule["priority"] == "professional_knowledge_base"
        assert rule["source_refs"]
        assert rule["prompt_transform"]["output_section"] in {
            "Intent",
            "Subject/Character",
            "Scene/Production Design",
            "Action/Beat",
            "Camera/Framing",
            "Lighting",
            "Motion/Temporal Progression",
            "Continuity",
            "Negative Constraints",
        }


def test_selector_prioritizes_professional_rules_for_video_prompt() -> None:
    rules = load_creative_prompt_rules(REPO_KNOWLEDGE_ROOT)
    selected = select_creative_prompt_rules(
        rules,
        node_type="video",
        generation_target="video",
        target_platform="short_video",
        slots={
            "language": "zh",
            "subject": "一个男孩",
            "scene": "昏暗房间",
            "action": "情绪低落地看向墙上海报",
            "lighting": "低照度室内光线",
            "camera": "缓慢推进",
            "motion": "轻微呼吸和抬头",
        },
    )
    selected_ids = {rule["rule_id"] for rule in selected}

    assert len(selected) >= 8
    assert "video_motion_temporal_progression_v1" in selected_ids
    assert "cinematography_camera_movement_v1" in selected_ids
    assert "lighting_motivated_low_key_v1" in selected_ids
    assert "negative_no_provider_claim_v1" in selected_ids
    assert all(rule["priority"] == "professional_knowledge_base" for rule in selected)
    assert all(rule["match_reason"] for rule in selected)


def test_knowledgebase_paths_do_not_overlap_unrelated_learning_notes_state() -> None:
    assert EXTERNAL_KNOWLEDGE_ROOT == Path(
        "D:/Learning materials/Learning_notes/10-Startup/70-Projects/AgentFlow-Studio/knowledgebase"
    )
    assert REPO_KNOWLEDGE_ROOT == Path("agentflow/knowledge")


def test_professional_reference_context_selects_rooftop_night_video_guidance() -> None:
    from agentflow.knowledge.professional_reference import format_professional_reference, professional_reference_from_text

    context = professional_reference_from_text(
        "A future robot watches stars on a rural rooftop platform.",
        node_type="video",
        generation_target="video",
    )

    assert {"night", "observational", "robot", "rooftop", "rural", "video"} <= set(context["tags"])
    assert "moon/stars" in context["lighting"]["decision"]
    assert "moderate-to-deep" in context["depth_of_field"]["decision"]
    assert context["pacing"]["must_include"][0].startswith("0-1s")
    assert "unapproved chair or stool" in context["scene_continuity"]["avoid"]
    assert context["writes_company_kb"] is False
    assert "Professional reference:" in format_professional_reference(context, "Camera/Framing")


def test_director_scenario_context_selects_saas_launch_pack_and_auxiliary_hook() -> None:
    from agentflow.knowledge.director_scenarios import (
        director_scenario_from_text,
        format_director_scenario_reference,
    )

    context = director_scenario_from_text(
        "Create a SaaS product launch video showing an app dashboard workflow demo.",
        node_type="video",
        generation_target="video",
        target_platform="short_video",
    )

    selected_ids = [pack["scenario_id"] for pack in context["selected_packs"]]
    assert context["primary_scenario"] == "saas_launch"
    assert "viral_hook" in selected_ids
    assert context["external_source_copied"] is False
    assert context["writes_company_kb"] is False
    assert "screen geometry remains readable" in context["quality_checks"]
    assert "Director scenario:" in format_director_scenario_reference(context, "Motion/Temporal Progression")


def test_director_scenario_context_selects_faceless_and_podcast_packs() -> None:
    from agentflow.knowledge.director_scenarios import director_scenario_from_text

    faceless = director_scenario_from_text(
        "A faceless finance narration uses b-roll and data surfaces.",
        node_type="script",
        generation_target="video",
    )
    podcast = director_scenario_from_text(
        "Turn a podcast interview quote into a short visual clip.",
        node_type="script",
        generation_target="video",
    )

    assert faceless["primary_scenario"] == "faceless_channel"
    assert "no unrequested presenter face" in faceless["negative_constraints"]
    assert podcast["primary_scenario"] == "podcast_visual"
    assert "quote focus is clear" in podcast["quality_checks"]
