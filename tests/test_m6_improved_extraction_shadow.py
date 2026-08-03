"""Shadow improved extraction: flag-gated compare path must not alter candidates."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.api.runtime_m6_script_plan_asset_bible import (
    IMPROVED_EXTRACTION_ENV,
    build_m6_script_plan_asset_bible,
    build_m6_shadow_extraction,
    improved_extraction_enabled,
)


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "docs" / "internal-notes" / "test-scripts-character-scene"

SEA_LETTER = (SCRIPTS_DIR / "02_industry_standard_letter_by_the_sea.txt").read_text(encoding="utf-8")

# Existing labeled brief that current M6 tests already rely on.
LABELED_IDEA = """
角色：林澈、唐予。场景：夜晚旧剪辑室、清晨屋顶。道具：场记板、旧镜头。特写：林澈手背的伤痕、时间线上的红色标记。
风格：克制写实冷暖对照。时间：夜晚到清晨。光线：剪辑室屏幕冷光与屋顶晨光。季节：初秋。连续性：旧镜头始终在唐予手边。
目标：林澈想证明被删掉的素材能救回影片。冲突：唐予担心返工会拖垮拍摄预算。关系：两人从互相指责转为共同承担。变化：林澈从逃避失误转为主动承认。
林澈盯着屏幕里的断帧，低声说“如果这一秒还在，结尾就不是谎言”。
唐予把场记板放到桌边，要求他在十分钟内给出能拍的重做方案。
两人带着旧镜头上到屋顶，晨光压住城市噪声，林澈终于说出自己删错素材的真相。
唐予没有责备，只把红色标记改成新的拍摄任务，让林澈先拍自己的手和那支旧镜头。
"""


def _preview(source_text: str) -> dict:
    return build_m6_script_plan_asset_bible(
        "proj_shadow_test",
        {
            "source_kind": "idea",
            "source_text": source_text,
            "revision_instruction": "",
            "parent_candidate_digest": "",
        },
    )


def test_improved_extraction_flag_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(IMPROVED_EXTRACTION_ENV, raising=False)
    assert improved_extraction_enabled() is False
    assert build_m6_shadow_extraction(
        SEA_LETTER,
        legacy_characters=["苏晴没"],
        legacy_scenes=["柜台前"],
    ) is None


def test_flag_off_preview_has_no_shadow_and_matches_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(IMPROVED_EXTRACTION_ENV, raising=False)
    off = _preview(LABELED_IDEA)
    assert "shadow_extraction" not in off
    digest = off["candidate_digest"]
    cast = [row["display_name"] for row in off["candidate"]["characters"]]
    scenes = [row["name"] for row in off["candidate"]["scenes"]]

    # Explicit false must behave the same as unset.
    monkeypatch.setenv(IMPROVED_EXTRACTION_ENV, "false")
    explicit_false = _preview(LABELED_IDEA)
    assert "shadow_extraction" not in explicit_false
    assert explicit_false["candidate_digest"] == digest
    assert [row["display_name"] for row in explicit_false["candidate"]["characters"]] == cast
    assert [row["name"] for row in explicit_false["candidate"]["scenes"]] == scenes


def test_flag_on_records_shadow_but_candidate_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(IMPROVED_EXTRACTION_ENV, raising=False)
    baseline = _preview(SEA_LETTER)
    baseline_digest = baseline["candidate_digest"]
    baseline_chars = [row["display_name"] for row in baseline["candidate"]["characters"]]
    baseline_scenes = [row["name"] for row in baseline["candidate"]["scenes"]]

    monkeypatch.setenv(IMPROVED_EXTRACTION_ENV, "true")
    shadowed = _preview(SEA_LETTER)

    assert shadowed["candidate_digest"] == baseline_digest
    assert [row["display_name"] for row in shadowed["candidate"]["characters"]] == baseline_chars
    assert [row["name"] for row in shadowed["candidate"]["scenes"]] == baseline_scenes
    assert shadowed["validation"]["verdict"] == baseline["validation"]["verdict"]

    shadow = shadowed["shadow_extraction"]
    assert shadow["enabled"] is True
    assert shadow["affects_candidate"] is False
    assert shadow["affects_production_graph"] is False
    assert shadow["gate_env"] == IMPROVED_EXTRACTION_ENV
    assert shadow["legacy"]["characters"] == baseline_chars
    assert shadow["legacy"]["scenes"] == baseline_scenes
    assert shadow["improved"] is not None
    improved_chars = [row["text"] for row in shadow["improved"]["characters"]]
    improved_scenes = [row["text"] for row in shadow["improved"]["scenes"]]
    # Prove the shadow path actually differs on the known junk case.
    assert "苏晴" in improved_chars
    assert "苏晴没" not in improved_chars
    assert "老式邮局" in improved_scenes
    assert "柜台前" in shadow["diff"]["scenes_only_in_legacy"] or "苏晴没" in shadow["diff"]["characters_only_in_legacy"]


def test_shadow_failure_does_not_break_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(IMPROVED_EXTRACTION_ENV, "true")

    def _boom(_text: str):
        raise RuntimeError("shadow extractor exploded")

    monkeypatch.setattr(
        "apps.api.runtime_m6_script_plan_asset_bible.extract_characters_and_scenes",
        _boom,
    )
    preview = _preview(LABELED_IDEA)
    assert preview["candidate_digest"]
    assert "characters" in preview["candidate"]
    shadow = preview["shadow_extraction"]
    assert shadow["improved"] is None
    assert shadow["error"]["type"] == "RuntimeError"
    assert shadow["affects_candidate"] is False
