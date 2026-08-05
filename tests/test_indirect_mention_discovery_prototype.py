from __future__ import annotations

from tools.indirect_mention_discovery import discover_indirect_mention_candidates


def test_discovery_finds_quoted_and_cued_names_without_open_ner_noise() -> None:
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
    # Open NER noise should stay out (cue/quote gated).
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
