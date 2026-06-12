from __future__ import annotations

from apps.api.runtime_attribute_vocabulary import attribute_values_in_text, find_lock_conflicts
from apps.api.runtime_context_budget import (
    SEGMENT_CAPS,
    TOTAL_PROMPT_BUDGET,
    VISIBLE_PROMPT_FLOOR,
    apply_context_budget,
)


def test_vocabulary_detects_en_hair_conflicts_with_window_match() -> None:
    conflicts = find_lock_conflicts("keep black short hair", "Draw Lin Wan with red long hair.")
    assert {"attribute": "hair_color", "lock_value": "black", "prompt_value": "red"} in conflicts
    assert {"attribute": "hair_length", "lock_value": "short", "prompt_value": "long"} in conflicts


def test_vocabulary_detects_zh_hair_conflicts() -> None:
    conflicts = find_lock_conflicts("保持黑色短发", "她染了红色长发走进房间")
    attributes = {item["attribute"] for item in conflicts}
    assert "hair_color" in attributes
    assert "hair_length" in attributes


def test_vocabulary_same_value_and_unrelated_text_do_not_conflict() -> None:
    assert find_lock_conflicts("保持红色风衣", "穿红色风衣的女人") == []
    assert find_lock_conflicts("keep black short hair", "she walks in the desert at noon") == []
    # word boundary: "along" must not register as "long"
    assert find_lock_conflicts("keep short hair", "walking along the shore") == []


def test_vocabulary_color_window_does_not_cross_unrelated_words() -> None:
    values = attribute_values_in_text("keep black coat and red hair")
    assert values.get("hair_color") == {"red"}
    assert values.get("outfit_color") == {"black"}


def test_budget_generate_keeps_short_segments_untouched() -> None:
    text = {
        "visible_prompt": "v" * 100,
        "asset_identity_segment": "i" * 120,
        "scene_director_segment": "s" * 50,
        "upstream_summary_segment": "u" * 40,
        "preference_segment": "p" * 20,
    }
    final, report = apply_context_budget("generate", text)
    assert final["visible_prompt"] == text["visible_prompt"]
    assert final["asset_identity_segment"] == text["asset_identity_segment"]
    assert report["enforcement_applied"] is True
    assert report["overflow_beyond_total"] is False


def test_budget_generate_truncates_long_visible_but_keeps_floor_and_locks() -> None:
    text = {
        "visible_prompt": "v" * 3000,
        "asset_identity_segment": "i" * 300,
        "scene_director_segment": "s" * 400,
        "upstream_summary_segment": "u" * 400,
        "preference_segment": "p" * 200,
    }
    final, report = apply_context_budget("generate", text)
    assert len(final["asset_identity_segment"]) == 300
    assert report["segments"]["lock_identity"]["truncated"] is False
    assert VISIBLE_PROMPT_FLOOR <= len(final["visible_prompt"]) <= TOTAL_PROMPT_BUDGET - 300
    assert report["total_used"] <= TOTAL_PROMPT_BUDGET
    assert report["segments"]["visible_prompt"]["truncated"] is True


def test_budget_generate_overflow_keeps_identity_and_visible_floor() -> None:
    text = {
        "visible_prompt": "v" * 800,
        "asset_identity_segment": "i" * 1300,
        "scene_director_segment": "s" * 100,
        "upstream_summary_segment": "",
        "preference_segment": "",
    }
    final, report = apply_context_budget("generate", text)
    assert len(final["asset_identity_segment"]) == 1300
    assert len(final["visible_prompt"]) == VISIBLE_PROMPT_FLOOR
    assert final["scene_director_segment"] == ""
    assert report["overflow_beyond_total"] is True


def test_budget_generate_caps_low_priority_segments() -> None:
    text = {
        "visible_prompt": "v" * 400,
        "asset_identity_segment": "i" * 200,
        "scene_director_segment": "s" * 600,
        "upstream_summary_segment": "u" * 500,
        "preference_segment": "p" * 300,
    }
    final, _ = apply_context_budget("generate", text)
    assert len(final["scene_director_segment"]) == SEGMENT_CAPS["scene_director"]
    assert len(final["upstream_summary_segment"]) == SEGMENT_CAPS["upstream_summary"]
    assert len(final["preference_segment"]) == SEGMENT_CAPS["preference"]


def test_budget_optimize_mode_is_report_only() -> None:
    text = {
        "visible_prompt": "v" * 3000,
        "asset_identity_segment": "",
        "scene_director_segment": "",
        "upstream_summary_segment": "",
        "preference_segment": "",
    }
    final, report = apply_context_budget("optimize", text)
    assert final["visible_prompt"] == text["visible_prompt"]
    assert report["enforcement_applied"] is False
