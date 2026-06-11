from __future__ import annotations

from agentflow.knowledge.creative_prompt_rules import (
    assert_knowledgebase_in_sync,
    load_creative_prompt_rules,
    select_creative_prompt_rules,
)


NODE_COVERAGE = {
    "text": {
        "generation_target": "prompt",
        "slots": {"language": "zh", "intent": "text", "subject": "少年", "scene": "房间", "style": "电影感"},
        "domains": {"directing", "cinematography", "lighting", "character_consistency", "negative_constraints"},
    },
    "image": {
        "generation_target": "image",
        "slots": {"language": "zh", "subject": "少年", "scene": "房间", "lighting": "低照度", "style": "写实"},
        "domains": {"cinematography", "lighting", "production_design", "character_consistency", "negative_constraints"},
    },
    "video": {
        "generation_target": "video",
        "slots": {"language": "zh", "subject": "少年", "scene": "房间", "motion": "缓慢推进", "camera": "推镜"},
        "domains": {"video_motion", "cinematography", "lighting", "negative_constraints"},
    },
    "audio": {
        "generation_target": "audio",
        "slots": {"language": "zh", "intent": "旁白", "action": "讲述", "emotion": "克制", "style": "温暖"},
        "domains": {"audio_design", "negative_constraints"},
    },
    "script": {
        "generation_target": "script",
        "slots": {"language": "zh", "intent": "分镜脚本", "action": "发现线索", "subject": "侦探"},
        "domains": {"short_video_script", "storyboard", "negative_constraints"},
    },
    "director": {
        "generation_target": "video",
        "slots": {"language": "zh", "director_setup": "characters=A;lights=Key;cameras=Camera A", "camera": "低角度"},
        "domains": {"director_setup_2d", "cinematography", "lighting", "negative_constraints"},
    },
}


def test_knowledgebase_covers_all_prompt_optimizer_node_types() -> None:
    rules = load_creative_prompt_rules()

    for node_type, case in NODE_COVERAGE.items():
        selected = select_creative_prompt_rules(
            rules,
            node_type=node_type,
            generation_target=case["generation_target"],
            target_platform="short_video",
            slots=case["slots"],
        )
        selected_domains = {rule["domain"] for rule in selected}
        selected_ids = {rule["rule_id"] for rule in selected}

        assert case["domains"].issubset(selected_domains), node_type
        assert all(rule_id.endswith("_v1") for rule_id in selected_ids)
        assert all(rule.get("match_reason") for rule in selected)


def test_audio_rules_are_explainable_professional_rules() -> None:
    audio_rules = [rule for rule in load_creative_prompt_rules() if rule["domain"] == "audio_design"]

    assert len(audio_rules) >= 4
    assert {rule["prompt_transform"]["output_section"] for rule in audio_rules} >= {
        "Action/Beat",
        "Motion/Temporal Progression",
        "Continuity",
        "Negative Constraints",
    }
    assert all(rule["priority"] == "professional_knowledge_base" for rule in audio_rules)
    assert all(rule["quality_checks"] for rule in audio_rules)


def test_knowledgebase_external_copy_stays_in_sync_after_audio_coverage() -> None:
    assert_knowledgebase_in_sync()
