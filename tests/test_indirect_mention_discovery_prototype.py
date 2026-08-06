from __future__ import annotations

from tools.indirect_mention_discovery import discover_indirect_mention_candidates


def test_discovery_uses_broad_structural_recall_without_open_ner() -> None:
    source = """标题：探针

第一场

人物：顾晚

顾晚拆开：里面是一张旧式汇款单复印件，收款人是「顾衡」，金额空白。

方糖
顾衡是谁？你亲戚？

顾晚
我爸顾衡以前也上夜班。

她想起他昨天说起了陈默。窗外雨还在下。

何婶
你爸顾衡以前也上夜班。
"""
    discoveries = discover_indirect_mention_candidates(source)
    names = {item["mention"] for item in discoveries}
    assert "顾衡" in names
    assert "陈默" in names
    # Deterministic extractor already owns speaker/label spans; discovery should
    # not re-propose those evidenced occurrences as I1 hits for 顾晚.
    assert "顾晚" not in names
    # Open NER noise should stay out; quoted/cued structure should still enter.
    assert "金额空白" not in names
    assert "旧式汇款" not in names


def test_discovery_skips_speaker_cue_span_even_if_quoted_elsewhere_is_kept() -> None:
    source = """苏晴
我爸以前也住过这栋楼。

杂音里仿佛有人喊了一声「苏衡」，随后恢复死寂。
"""
    discoveries = discover_indirect_mention_candidates(source)
    by_name = {item["mention"]: item for item in discoveries}
    assert "苏衡" in by_name
    assert by_name["苏衡"]["discovery_method"] == "quoted_name"
    assert by_name["苏衡"]["source_span"]["quote"] == "苏衡"


def test_discovery_keeps_quoted_noise_for_llm_judgment() -> None:
    source = """苏晴撬开床头板——是陈默白天说过的「别自己拆」让她反而去找接缝。

巷口有辆面包车，车侧喷着「默记修缮」。

她数了数柜台上的「留局待领」格。

标题含「夜班邮筒」「失踪汇款」。

赵石做了个「晚上见」的手势。

何婶只记得车门上喷过「默记」两个字。

收款人是「顾衡」。
收件人写着「晚晚」。
录音里的「悦安」让林悦脸色发白。
又把「陈默」三个字写在草稿上划掉。
"""
    discoveries = discover_indirect_mention_candidates(source)
    names = {item["mention"] for item in discoveries}
    assert "顾衡" in names
    assert "晚晚" in names
    assert "悦安" in names
    assert "陈默" in names
    assert "别自己拆" in names
    assert "默记修缮" in names
    assert "留局待领" in names
    assert "夜班邮筒" in names
    assert "失踪汇款" in names
    assert "晚上见" in names
    assert "默记" in names


def test_discovery_finds_new_generalization_gold_cases() -> None:
    source = """照片背面写着「沈岚」，日期是三年前的入职周。

电话那头传来断续的呼吸声，随即一个很轻的问句，只听清两个字：「江澄」。

墙上的电子告示滚动两行：「样本冷藏」「权限不足」。
"""
    discoveries = discover_indirect_mention_candidates(source)
    names = {item["mention"] for item in discoveries}
    assert "沈岚" in names
    assert "江澄" in names
    assert "样本冷藏" in names
    assert "权限不足" in names
