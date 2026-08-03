#!/usr/bin/env python3
"""Run improved extraction draft against the 5 character/scene test scripts.

Usage (from repo root or this directory):
  python docs/internal-notes/run_improved_extraction_against_test_scripts.py

Does not import apps/api. Exit code 0 only if all cases meet expectations.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a script without installing a package.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from draft_improved_extraction_20260802 import (  # noqa: E402
    ExtractStatus,
    extract_characters_and_scenes,
    legacy_m6_characters,
    legacy_m6_scenes,
)


SCRIPTS_DIR = _HERE / "test-scripts-character-scene"

# Expectations from test-scripts-character-scene/README.md
CASES: list[dict] = [
    {
        "file": "01_industry_standard_last_light.txt",
        "title": "最后的光",
        "expected_characters": {"玛雅"},
        "expected_scenes": {"废弃灯塔", "灯塔阳台"},
        "expect_character_missing": False,
        "expect_scene_missing": False,
        "forbidden_characters": {"颤抖", "灯上"},
        "forbidden_scenes": {"颤抖", "灯上"},
    },
    {
        "file": "02_industry_standard_letter_by_the_sea.txt",
        "title": "海边的信",
        "expected_characters": {"苏晴", "老王", "林悦"},
        "expected_scenes": {"老式邮局", "海边礁石", "苏晴的房间"},
        "expect_character_missing": False,
        "expect_scene_missing": False,
        "forbidden_characters": {"苏晴没", "从信封", "道他可能", "从远处"},
        "forbidden_scenes": {"柜台前", "柜台上", "礁石上", "她身边坐下", "书桌前", "一叠信纸上"},
    },
    {
        "file": "03_labeled_fields_homecoming.txt",
        "title": "归途",
        "expected_characters": {"陈浩", "林秀"},
        "expected_scenes": {"小镇火车站", "陈浩家中的老屋"},
        "expect_character_missing": False,
        "expect_scene_missing": False,
        "forbidden_characters": set(),
        "forbidden_scenes": set(),
    },
    {
        "file": "04_mixed_format_old_photo.txt",
        "title": "旧照片",
        "expected_characters": {"周明", "母亲"},
        "expected_scenes": {"阁楼", "厨房"},
        "expect_character_missing": False,
        "expect_scene_missing": False,
        "forbidden_characters": set(),
        "forbidden_scenes": set(),
    },
    {
        "file": "05_missing_info_unknown_call.txt",
        "title": "陌生来电",
        "expected_characters": set(),
        "expected_scenes": set(),
        "expect_character_missing": True,
        "expect_scene_missing": True,
        # Must not invent proper names / concrete places
        "forbidden_characters": {"女人", "来电者", "陌生人"},
        "forbidden_scenes": {"房间", "昏暗的房间"},
    },
]


def _fmt_items(items) -> str:
    if not items:
        return "(none)"
    parts = []
    for it in items:
        parts.append(f"{it.text} [{it.status.value}|conf={it.confidence:.2f}|{it.method}]")
    return "; ".join(parts)


def evaluate(case: dict, text: str):
    result = extract_characters_and_scenes(text)
    got_chars = set(result.character_texts())
    got_scenes = set(result.scene_texts())
    errors: list[str] = []

    if case["expect_character_missing"]:
        if result.character_name_status != ExtractStatus.MISSING:
            errors.append(
                f"character_name_status want missing, got {result.character_name_status.value}"
            )
        if got_chars:
            errors.append(f"expected no proper character names, got {sorted(got_chars)}")
    else:
        missing = case["expected_characters"] - got_chars
        extra = got_chars - case["expected_characters"]
        if missing:
            errors.append(f"missing characters: {sorted(missing)}")
        if extra:
            errors.append(f"unexpected characters: {sorted(extra)}")

    if case["expect_scene_missing"]:
        if result.scene_status != ExtractStatus.MISSING:
            errors.append(f"scene_status want missing, got {result.scene_status.value}")
        if got_scenes:
            errors.append(f"expected no concrete scenes, got {sorted(got_scenes)}")
    else:
        missing = case["expected_scenes"] - got_scenes
        extra = got_scenes - case["expected_scenes"]
        if missing:
            errors.append(f"missing scenes: {sorted(missing)}")
        if extra:
            errors.append(f"unexpected scenes: {sorted(extra)}")

    bad_c = got_chars & case["forbidden_characters"]
    bad_s = got_scenes & case["forbidden_scenes"]
    if bad_c:
        errors.append(f"forbidden characters present: {sorted(bad_c)}")
    if bad_s:
        errors.append(f"forbidden scenes present: {sorted(bad_s)}")

    return (not errors), errors, result


def main() -> int:
    print(f"scripts_dir: {SCRIPTS_DIR}")
    print("=" * 72)
    all_ok = True

    for case in CASES:
        path = SCRIPTS_DIR / case["file"]
        text = path.read_text(encoding="utf-8")
        ok, errors, result = evaluate(case, text)
        all_ok = all_ok and ok

        legacy_c = legacy_m6_characters(text)
        legacy_s = legacy_m6_scenes(text)

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['file']}  《{case['title']}》")
        print(f"  expected chars : {sorted(case['expected_characters']) or ['⟨missing⟩']}")
        print(f"  improved chars : {_fmt_items(result.characters)}")
        print(f"  char slot      : {result.character_name_status.value}")
        print(f"  legacy M6 chars: {legacy_c or ['(none)']}")
        print(f"  expected scenes: {sorted(case['expected_scenes']) or ['⟨missing⟩']}")
        print(f"  improved scenes: {_fmt_items(result.scenes)}")
        print(f"  scene slot     : {result.scene_status.value}")
        print(f"  legacy M6 scene: {legacy_s or ['(none)']}")
        if result.notes:
            print(f"  notes          : {', '.join(result.notes)}")
        if errors:
            for err in errors:
                print(f"  !! {err}")
        print("-" * 72)

    print("ALL PASS" if all_ok else "SOME FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
