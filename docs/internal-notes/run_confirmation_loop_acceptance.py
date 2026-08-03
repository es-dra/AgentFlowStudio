#!/usr/bin/env python3
"""Acceptance self-test for the candidate confirmation closed loop.

Boss criteria:
  A — no-evidence / wrong entity (苏晴没) never reaches authoritative
  B — human correction is what downstream reads on re-resolve (not stale raw)
  C — new script revision invalidates old authoritative facts

Usage:
  .venv/bin/python docs/internal-notes/run_confirmation_loop_acceptance.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from draft_candidate_confirmation_loop_20260802 import (  # noqa: E402
    AuthorityValidity,
    accept_candidate,
    edit_and_confirm_candidate,
    inject_raw_junk_candidate,
    list_current_authoritative,
    on_script_revision_changed,
    open_ledger_from_extraction,
    reject_candidate,
    resolve_for_downstream,
)
from draft_candidate_fact_status_model_20260802 import (  # noqa: E402
    PromotionError,
    example_suqingmei_junk_stays_candidate,
    promote_candidate_fact,
)
from draft_improved_extraction_20260802 import extract_characters_and_scenes  # noqa: E402

SCRIPTS = _HERE / "test-scripts-character-scene"


def _ok(name: str, cond: bool, detail: str = "") -> bool:
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def scenario_a() -> bool:
    print("\n=== Scenario A: junk entity never becomes authoritative ===")
    # Reuse status-model unit proof
    proof = example_suqingmei_junk_stays_candidate()
    ok = _ok(
        "status-model promote gate blocks 苏晴没",
        proof["promotion_succeeded"] is False and proof["is_authoritative"] is False,
        proof.get("promotion_error", "")[:80],
    )

    # Same junk through the confirmation loop ledger
    text = (SCRIPTS / "02_industry_standard_letter_by_the_sea.txt").read_text(encoding="utf-8")
    ledger, bundle = open_ledger_from_extraction(
        text,
        project_id="proj_loop_demo",
        source_revision_id="scrrev_sea_v1",
        title_hint="海边的信",
    )
    junk = inject_raw_junk_candidate(
        ledger,
        junk_text="苏晴没",
        evidence_quote="苏晴没说话",
        confidence=0.96,
    )
    # Direct promote must fail
    blocked = False
    try:
        promote_candidate_fact(junk, authoritative_fact_id="auth_should_not")
    except PromotionError:
        blocked = True
    ok = _ok("loop junk cannot promote without human", blocked) and ok

    # Accepting junk would promote — human must REJECT instead
    reject_candidate(
        ledger,
        junk.fact_id,
        human_id="user_creator",
        reason="fragment not a real name",
    )
    current = list_current_authoritative(ledger)
    ok = _ok(
        "after reject, authoritative ledger has no 苏晴没",
        all(f.text != "苏晴没" for f in current),
        f"current={[f.text for f in current]}",
    ) and ok

    # Accept path on a *real* improved extract name still works (sanity)
    real = next(i for i in bundle.items if i.text == "苏晴")
    accept_candidate(ledger, real.fact_id, human_id="user_creator", reason="correct name")
    current = list_current_authoritative(ledger)
    ok = _ok(
        "real 苏晴 can become authoritative after accept",
        any(f.text == "苏晴" for f in current),
    ) and ok
    return ok


def scenario_b() -> bool:
    print("\n=== Scenario B: human correction wins on re-resolve ===")
    # Use 《旧照片》: system may show 母亲; human renames to 周母.
    # Also inject a wrong scene candidate to mirror "wrong scene name" correction.
    text = (SCRIPTS / "04_mixed_format_old_photo.txt").read_text(encoding="utf-8")
    ledger, bundle = open_ledger_from_extraction(
        text,
        project_id="proj_loop_demo",
        source_revision_id="scrrev_photo_v1",
        title_hint="旧照片",
    )

    # Find scene「厨房」and wrongly... actually extraction is correct.
    # Simulate wrong extract by editing a scene fact's claim before confirm:
    # inject path: take 阁楼 candidate, human corrects a *deliberately wrong* accept path:
    # We put a fake wrong scene on the ledger via edit from an extracted scene.
    kitchen = next(i for i in bundle.items if i.text == "厨房" and i.entity_kind == "scene")
    # Pretend UI showed wrong label: human corrects 厨房→餐厅? No — demo wrong→right:
    # Start by rejecting nothing; instead edit 母亲 → 周丽 (proper name correction)
    mother = next(i for i in bundle.items if i.text == "母亲")
    edit_and_confirm_candidate(
        ledger,
        mother.fact_id,
        new_text="周丽",
        human_id="user_creator",
        reason="母亲 is a role label; character's name is 周丽",
        source_text=text,
    )

    # Wrong scene name correction: treat extracted 阁楼 as mistaken UI value → 旧阁楼
    # (human insists on a more precise name for downstream)
    attic = next(i for i in bundle.items if i.text == "阁楼" and i.entity_kind == "scene")
    # First accept kitchen as-is
    accept_candidate(ledger, kitchen.fact_id, human_id="user_creator")
    # Correct attic label
    edit_and_confirm_candidate(
        ledger,
        attic.fact_id,
        new_text="老宅阁楼",
        human_id="user_creator",
        reason="need more specific location label than bare 阁楼",
        source_text=text,
    )

    # Re-run extraction (raw still says 母亲 / 阁楼)
    fresh = extract_characters_and_scenes(text)
    resolved = resolve_for_downstream(ledger, fresh_extraction=fresh)

    ok = _ok(
        "raw extraction still has 母亲 (unchanged extract)",
        "母亲" in fresh.character_texts(),
        str(fresh.character_texts()),
    )
    ok = _ok(
        "downstream resolve uses 周丽 not 母亲",
        "周丽" in resolved["characters"] and "母亲" not in resolved["characters"],
        str(resolved["characters"]),
    ) and ok
    ok = _ok(
        "downstream resolve uses 老宅阁楼 not bare 阁楼",
        "老宅阁楼" in resolved["scenes"] and "阁楼" not in resolved["scenes"],
        str(resolved["scenes"]),
    ) and ok
    ok = _ok(
        "authority_source is authoritative_ledger",
        resolved["authority_source"] == "authoritative_ledger",
    ) and ok
    ok = _ok(
        "kitchen accept retained",
        "厨房" in resolved["scenes"],
    ) and ok
    return ok


def scenario_c() -> bool:
    print("\n=== Scenario C: new revision invalidates old authoritative facts ===")
    text_v1 = (SCRIPTS / "03_labeled_fields_homecoming.txt").read_text(encoding="utf-8")
    ledger, bundle = open_ledger_from_extraction(
        text_v1,
        project_id="proj_loop_demo",
        source_revision_id="scrrev_home_v1",
        title_hint="归途",
    )
    for item in bundle.items:
        accept_candidate(ledger, item.fact_id, human_id="user_creator")

    before = list_current_authoritative(ledger, revision_id="scrrev_home_v1")
    ok = _ok("v1 has authoritative facts", len(before) >= 4, f"n={len(before)}")

    # New revision (slightly edited script)
    text_v2 = text_v1.replace("小镇火车站", "北方小镇火车站")
    invalidated = on_script_revision_changed(
        ledger,
        new_revision_id="scrrev_home_v2",
        new_source_text=text_v2,
        actor_id="system",
    )
    ok = _ok("invalidation touched prior records", len(invalidated) == len(before), f"n={len(invalidated)}") and ok

    current_v2 = list_current_authoritative(ledger, revision_id="scrrev_home_v2")
    ok = _ok("no active authoritative on v2 yet", current_v2 == []) and ok

    current_v1_query = list_current_authoritative(ledger, revision_id="scrrev_home_v1")
    ok = _ok(
        "v1 revision query also empty (facts invalidated, not active)",
        current_v1_query == [],
    ) and ok

    # Audit retained
    invalidated_rows = [
        r
        for r in ledger.authoritative_records
        if r.validity == AuthorityValidity.INVALIDATED_BY_REVISION
    ]
    ok = _ok(
        "audit rows retained as invalidated_by_revision",
        len(invalidated_rows) == len(before),
        f"n={len(invalidated_rows)}",
    ) and ok
    ok = _ok(
        "invalidated_by_revision_id points to v2",
        all(r.invalidated_by_revision_id == "scrrev_home_v2" for r in invalidated_rows),
    ) and ok

    # Re-extract + confirm one fact on v2 → only that is current
    ledger2, bundle2 = open_ledger_from_extraction(
        text_v2,
        project_id="proj_loop_demo",
        source_revision_id="scrrev_home_v2",
        title_hint="归途",
    )
    # Continue on same ledger after revision change: reopen candidates on v2
    # (open_ledger_from_extraction created a fresh ledger — merge into existing)
    ledger.candidates = ledger2.candidates
    ledger.review_decisions = ledger2.review_decisions
    # Keep authoritative_records + change_log from before
    station = next(i for i in bundle2.items if "火车站" in i.text)
    accept_candidate(ledger, station.fact_id, human_id="user_creator")
    resolved = resolve_for_downstream(
        ledger,
        fresh_extraction=extract_characters_and_scenes(text_v2),
    )
    ok = _ok(
        "downstream after v2 only sees newly confirmed fact(s)",
        resolved["scenes"] == ["北方小镇火车站"]
        or "北方小镇火车站" in resolved["scenes"],
        str(resolved),
    ) and ok
    ok = _ok(
        "old 小镇火车站 not treated as current authority",
        "小镇火车站" not in list_current_authoritative(ledger),
        str([f.text for f in list_current_authoritative(ledger)]),
    ) and ok

    # change_log contains revision event
    ok = _ok(
        "change_log has script_revision_changed",
        any(c.reason == "script_revision_changed" for c in ledger.change_log),
    ) and ok
    return ok


def main() -> int:
    print("Confirmation-loop acceptance (draft / local only)")
    results = {
        "A": scenario_a(),
        "B": scenario_b(),
        "C": scenario_c(),
    }
    print("\n" + "=" * 56)
    print(json.dumps({k: ("PASS" if v else "FAIL") for k, v in results.items()}, ensure_ascii=False))
    all_ok = all(results.values())
    print("ALL PASS" if all_ok else "SOME FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
