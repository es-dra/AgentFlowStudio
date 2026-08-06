"""Unit tests for paid indirect-mention proposal builder (mocked LLM).

COST: production path is paid remote LLM. These tests inject a fake judge and
never call a provider.
"""

from __future__ import annotations

from apps.api.runtime_script_indirect_mention_proposals import (
    COST_CLASS_PAID,
    INDIRECT_MENTION_PROPOSALS_ENV,
    build_indirect_mention_proposals,
    parse_judgment,
)


def _indirect_judge(_text: str, mention: str, _output_dir) -> dict:
    # Mimic validated split-field behavior for a few known mentions.
    if mention in {"顾衡", "沈岚", "江澄", "柯衡"}:
        return {
            "refers_to_real_character": True,
            "refers_to_real_character_confidence": 0.95,
            "refers_to_real_character_reason": f"{mention} 是真实人物姓名",
            "is_present_in_scene": False,
            "is_present_in_scene_confidence": 0.9,
            "is_present_in_scene_reason": "仅被提及，未出场",
            "is_indirect_mention": True,
        }
    if mention in {"别自己拆", "默记修缮", "晚上见"}:
        return {
            "refers_to_real_character": False,
            "refers_to_real_character_confidence": 0.95,
            "refers_to_real_character_reason": "噪声短语",
            "is_present_in_scene": False,
            "is_present_in_scene_confidence": 0.95,
            "is_present_in_scene_reason": "非人物",
            "is_indirect_mention": False,
        }
    return {
        "refers_to_real_character": False,
        "refers_to_real_character_confidence": 0.5,
        "refers_to_real_character_reason": "unknown",
        "is_present_in_scene": False,
        "is_present_in_scene_confidence": 0.5,
        "is_present_in_scene_reason": "unknown",
        "is_indirect_mention": False,
    }


def test_parse_judgment_derives_indirect_mention() -> None:
    parsed = parse_judgment(
        '{"refers_to_real_character": true, "refers_to_real_character_confidence": 0.9,'
        ' "refers_to_real_character_reason": "人名",'
        ' "is_present_in_scene": false, "is_present_in_scene_confidence": 0.8,'
        ' "is_present_in_scene_reason": "未出场"}'
    )
    assert parsed["is_indirect_mention"] is True


def test_builder_emits_only_indirect_mentions_and_marks_cost_class() -> None:
    source = """标题：探针

第一场

人物：顾晚

顾晚拆开：里面是一张旧式汇款单复印件，收款人是「顾衡」，金额空白。

方糖
顾衡是谁？你亲戚？

她想起他昨天说起了「别自己拆」。巷口有辆面包车，车侧喷着「默记修缮」。
"""
    bundle = build_indirect_mention_proposals(source, judge=_indirect_judge, max_calls=12)
    mentions = {item["mention"] for item in bundle["proposals"]}
    assert "顾衡" in mentions
    assert "别自己拆" not in mentions
    assert "默记修缮" not in mentions
    assert bundle["cost_class"] == COST_CLASS_PAID
    assert bundle["provider_dispatch_count"] == bundle["judged_count"] > 0
    for proposal in bundle["proposals"]:
        assert proposal["status"] == "candidate"
        assert proposal["authority"] == "non_authoritative_proposal"
        assert proposal["cost_class"] == COST_CLASS_PAID
        assert proposal["is_indirect_mention"] is True
        assert proposal["refers_to_real_character"] is True
        assert proposal["is_present_in_scene"] is False
        assert proposal["review_action"] == "use_core_asset_command_create_manual_character"


def test_builder_rejects_non_person_shaped_mentions_even_if_llm_says_refers() -> None:
    source = """抽屉有一份备忘：「第七格——顾衡案——不得夜班单独开启。」\n收款人是「顾衡」。\n"""

    def judge(_text: str, mention: str, _output_dir) -> dict:
        return {
            "refers_to_real_character": True,
            "refers_to_real_character_confidence": 0.9,
            "refers_to_real_character_reason": "forced",
            "is_present_in_scene": False,
            "is_present_in_scene_confidence": 0.9,
            "is_present_in_scene_reason": "forced",
            "is_indirect_mention": True,
        }

    bundle = build_indirect_mention_proposals(source, judge=judge, max_calls=12)
    mentions = {item["mention"] for item in bundle["proposals"]}
    assert "顾衡" in mentions
    assert "第七格——顾衡案——不得夜班单独开启。" not in mentions


def test_builder_budget_skip_is_explicit_not_silent() -> None:
    source = """收款人是「顾衡」。
收件人写着「晚晚」。
录音里的「悦安」让林悦脸色发白。
又把「陈默」三个字写在草稿上划掉。
照片背面写着「沈岚」。
电话里说「江澄」。
"""
    bundle = build_indirect_mention_proposals(source, judge=_indirect_judge, max_calls=2)
    assert bundle["judged_count"] == 2
    assert bundle["provider_dispatch_count"] == 2
    assert len(bundle["budget_skipped"]) == bundle["discovered_count"] - len(
        bundle["suppressed_known_identity"]
    ) - 2
    assert bundle["budget_skipped"]
    for skipped in bundle["budget_skipped"]:
        assert skipped["status"] == "budget_skipped_unjudged"
        assert skipped["cost_class"] == COST_CLASS_PAID
        assert "Exceeded" in skipped["reason"]
        assert INDIRECT_MENTION_PROPOSALS_ENV  # flag name stays documented


def test_builder_suppresses_already_extracted_canonical_names() -> None:
    source = """标题：回声

人物：苏衡、陈默

苏衡
别回头。

杂音里仿佛有人喊了一声「苏衡」，随后恢复死寂。
草稿上划掉「陈默」。
收款人是「顾衡」。
"""

    def judge(_text: str, mention: str, _output_dir) -> dict:
        return {
            "refers_to_real_character": True,
            "refers_to_real_character_confidence": 0.95,
            "refers_to_real_character_reason": "forced",
            "is_present_in_scene": False,
            "is_present_in_scene_confidence": 0.9,
            "is_present_in_scene_reason": "forced",
            "is_indirect_mention": True,
        }

    bundle = build_indirect_mention_proposals(source, judge=judge, max_calls=12)
    mentions = {item["mention"] for item in bundle["proposals"]}
    suppressed = {item["mention"] for item in bundle["suppressed_known_identity"]}
    assert "苏衡" in suppressed
    assert "陈默" in suppressed
    assert "苏衡" not in mentions
    assert "陈默" not in mentions
    assert "顾衡" in mentions
    assert all(item["status"] == "suppressed_known_identity" for item in bundle["suppressed_known_identity"])
    # Known identities must not consume paid LLM budget.
    assert all(item["mention"] not in {"苏衡", "陈默"} for item in bundle["budget_skipped"])


def test_builder_suppresses_confirmed_alias_surfaces_when_provided() -> None:
    source = """录音里的「悦安」让林悦脸色发白。\n收款人是「顾衡」。\n"""

    def judge(_text: str, mention: str, _output_dir) -> dict:
        return {
            "refers_to_real_character": True,
            "refers_to_real_character_confidence": 0.95,
            "refers_to_real_character_reason": "forced",
            "is_present_in_scene": False,
            "is_present_in_scene_confidence": 0.9,
            "is_present_in_scene_reason": "forced",
            "is_indirect_mention": True,
        }

    bundle = build_indirect_mention_proposals(
        source,
        judge=judge,
        max_calls=12,
        known_identity_surfaces={"悦安"},
    )
    mentions = {item["mention"] for item in bundle["proposals"]}
    suppressed = {item["mention"] for item in bundle["suppressed_known_identity"]}
    assert "悦安" in suppressed
    assert "悦安" not in mentions
    assert "顾衡" in mentions
