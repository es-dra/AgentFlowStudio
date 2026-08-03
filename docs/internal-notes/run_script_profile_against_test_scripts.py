#!/usr/bin/env python3
"""Local acceptance run for the design-stage ScriptProfile schema.

Does not import apps/api. Verifies:
  1) six current scripts mostly yield missing profile facets (honest fail-closed)
  2) labeled control sample yields present facets
  3) human edit_confirm on a missing genre slot promotes via existing loop
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from draft_candidate_confirmation_loop_20260802 import (  # noqa: E402
    FactLedger,
    ReviewDecision,
    accept_candidate,
    edit_and_confirm_candidate,
    list_current_authoritative,
    on_script_revision_changed,
)
from draft_candidate_fact_status_model_20260802 import (  # noqa: E402
    CandidateStatus,
    PromotionError,
    promote_candidate_fact,
)
from draft_script_profile_schema_20260803 import (  # noqa: E402
    build_script_profile_entity,
    facet_status_table,
    script_profile_version_to_candidate_facts,
)


SCRIPTS = _HERE / "test-scripts-character-scene"
SCRIPT_FILES = tuple(sorted(SCRIPTS.glob("[0-9][0-9]_*.txt")))
FINDINGS_PATH = _HERE / "script-profile-findings-20260803.md"


def _ok(name: str, cond: bool, detail: str = "") -> bool:
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def _head(entity):
    return next(item for item in entity.versions if item.version_id == entity.head_version_id)


def evaluate_six_scripts() -> tuple[bool, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    ok = len(SCRIPT_FILES) == 6
    for path in SCRIPT_FILES:
        source = path.read_text(encoding="utf-8")
        entity = build_script_profile_entity(
            source,
            project_id="proj_profile_demo",
            source_revision_id=f"scrrev_{path.stem}",
            title_hint=path.stem,
        )
        version = _head(entity)
        table = facet_status_table(version)
        present = [name for name, row in table.items() if row["status"] == "present"]
        missing = [name for name, row in table.items() if row["status"] == "missing"]
        # Honest expectation: unlabeled short scripts → all five missing.
        passed = len(present) == 0 and len(missing) == 5
        ok = ok and passed
        rows.append(
            {
                "file": path.name,
                "present": present,
                "missing": missing,
                "facets": table,
                "pass": passed,
            }
        )
    return ok, rows


def evaluate_labeled_control() -> tuple[bool, dict[str, object]]:
    source = (
        "标题：控制样本\n"
        "主题：等待与释然\n"
        "类型：悬疑、情感\n"
        "受众：成年观众\n"
        "叙事目标：让观众体会未送达的告别\n"
        "风格要求：克制对白，冷暖光对比\n"
        "\n"
        "第一场 - 内景 - 房间 - 夜\n"
        "角色坐着。\n"
    )
    entity = build_script_profile_entity(
        source,
        project_id="proj_profile_control",
        source_revision_id="scrrev_profile_control",
        title_hint="控制样本",
    )
    table = facet_status_table(_head(entity))
    passed = (
        table["theme"]["status"] == "present"
        and table["theme"]["text"] == "等待与释然"
        and table["genre"]["status"] == "present"
        and table["genre"]["text"] == ["悬疑", "情感"]
        and table["audience"]["status"] == "present"
        and table["narrative_goals"]["status"] == "present"
        and table["style_requirements"]["status"] == "present"
    )
    return passed, table


def evaluate_human_genre_confirmation() -> dict[str, bool]:
    """Missing genre slot → edit_confirm('悬疑') → authoritative; accept blocked."""

    source = (SCRIPTS / "02_industry_standard_letter_by_the_sea.txt").read_text(
        encoding="utf-8"
    )
    entity = build_script_profile_entity(
        source,
        project_id="proj_profile_human",
        source_revision_id="scrrev_sea_profile_v1",
        title_hint="海边的信",
    )
    version = _head(entity)
    facts = script_profile_version_to_candidate_facts(version)
    genre_missing = next(
        fact for fact in facts if fact.field_path == "script_profile.genre"
    )
    checks: dict[str, bool] = {}
    checks["genre_starts_missing"] = genre_missing.status == CandidateStatus.MISSING

    # Direct promote must fail
    blocked = False
    try:
        promote_candidate_fact(genre_missing, authoritative_fact_id="auth_should_not")
    except PromotionError:
        blocked = True
    checks["missing_cannot_promote"] = blocked

    ledger = FactLedger(
        project_id="proj_profile_human",
        current_revision_id=version.source_revision_id,
        current_revision_digest=version.source_revision_digest,
        candidates={fact.fact_id: fact for fact in facts},
        review_decisions={fact.fact_id: ReviewDecision.PENDING for fact in facts},
    )

    accept_blocked = False
    try:
        accept_candidate(
            ledger,
            genre_missing.fact_id,
            human_id="user_creator",
            reason="should fail",
        )
    except Exception:
        accept_blocked = True
    checks["accept_missing_blocked"] = accept_blocked

    record = edit_and_confirm_candidate(
        ledger,
        genre_missing.fact_id,
        new_text="悬疑",
        human_id="user_creator",
        reason="human judgment: tone reads as suspense; not stated in text",
        source_text=source,  # "悬疑" not in source → human-supplied evidence span
    )
    checks["edit_confirm_promotes"] = (
        record.fact.text == "悬疑"
        and record.fact.entity_kind == "script_profile"
        and record.fact.promotion_kind == "human_confirmation"
        and record.fact.field_path == "script_profile.genre"
    )
    current = list_current_authoritative(ledger)
    checks["authoritative_has_genre"] = any(
        row.text == "悬疑" and row.entity_kind == "script_profile" for row in current
    )

    # Other missing facets remain non-authoritative
    checks["other_facets_not_auto_promoted"] = all(
        row.field_path == "script_profile.genre" for row in current
    )

    # Revision change invalidates
    on_script_revision_changed(
        ledger,
        new_revision_id="scrrev_sea_profile_v2",
        new_source_text=source + "\n\n（修订说明）\n",
        actor_id="system",
    )
    after = list_current_authoritative(ledger)
    checks["revision_invalidates_authority"] = after == []
    return checks


def write_findings(six_rows: list[dict[str, object]], control: dict[str, object]) -> None:
    lines = [
        "# ScriptProfile Schema 设计与本地验证（2026-08-03）",
        "",
        "状态：设计草稿；未接入 `apps/api`、M6、Production Graph 或 Studio Runtime。",
        "",
        "## 结论",
        "",
        "`ScriptProfileVersion` / `ScriptProfileEntity` 可以沿用 Character/Scene/Beat 的",
        "`ClaimedText`、候选状态机和人工确认闭环；`entity_kind=\"script_profile\"`，",
        "每个 script revision 通常只有一份 profile。",
        "",
        "现有 6 份短篇测试剧本**都没有**显式写出主题/类型/受众/叙事目标/风格要求",
        "标签。确定性提取器因此对 6 份剧本全部返回 **5 个 facet = missing**。",
        "这是预期中的诚实结果，不是抽取失败。",
        "",
        "## 复用链路",
        "",
        "```text",
        "labeled-only extract (or all-missing profile)",
        "  -> ScriptProfileVersion / ScriptProfileEntity",
        "  -> script_profile_version_to_candidate_facts",
        "  -> CandidateFact(entity_kind=\"script_profile\")",
        "  -> accept / edit_confirm / reject（同一套确认函数）",
        "  -> promote_candidate_fact（原函数未改）",
        "  -> AuthoritativeScriptFact(entity_kind=\"script_profile\")",
        "  -> script revision invalidation（原函数未改）",
        "```",
        "",
        "本次只在 `docs/internal-notes` 草稿层把 `entity_kind` 扩展到 `script_profile`。",
        "生产模块 `apps/api/runtime_candidate_fact_status.py` 仍保持既有范围。",
        "",
        "## Schema 决策",
        "",
        "- `theme` / `audience` / `narrative_goals` / `style_requirements`：",
        "  `SingleClaimFacet` = `present|missing` + optional `ClaimedText`",
        "- `genre`：`GenreFacet`，允许 `ClaimedText` 列表（显式「悬疑、情感」）",
        "- 确定性提取**只认标签行**（`主题：` / `类型：` / `受众：` /",
        "  `叙事目标：` / `风格要求：` 等），禁止从剧情“读出类型”",
        "- missing 槽位不能 `accept`；人工可用 `edit_confirm` 写入判断并晋升",
        "",
        "## 六剧本实测（全部 missing = 预期）",
        "",
        "| 剧本 | theme | genre | audience | narrative_goals | style_requirements |",
        "|---|---|---|---|---|---|",
    ]
    for row in six_rows:
        facets = row["facets"]  # type: ignore[index]
        cells = [
            facets[name]["status"]  # type: ignore[index]
            for name in (
                "theme",
                "genre",
                "audience",
                "narrative_goals",
                "style_requirements",
            )
        ]
        lines.append(f"| {row['file']} | " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "### 为什么 missing（共性）",
            "",
            "- 这些素材是 Character/Scene/Beat 验证用短篇，正文没有 metadata 标签。",
            "- 「看起来像悬疑/像亲情」属于解读，不是文本证据；按纪律不得标 present。",
            "- `audience` 尤其几乎从不在剧本正文出现，missing 是常态。",
            "",
            "## 正向控制样本",
            "",
            "显式写入五类标签后，提取器应全部 `present`（genre 拆成列表）：",
            "",
            "```json",
            json.dumps(control, ensure_ascii=False, indent=2),
            "```",
            "",
            "## 人工确认路径（无文本类型标签）",
            "",
            "对《海边的信》缺失的 `script_profile.genre`：",
            "1. `promote` 直接失败（missing）",
            "2. `accept` 被确认环拒绝（必须 edit_confirm）",
            "3. `edit_confirm(new_text=\"悬疑\")` → `AuthoritativeScriptFact`",
            "   （`promotion_kind=human_confirmation`，`entity_kind=script_profile`）",
            "4. 换 revision → 权威失效",
            "",
            "这说明：人工可以补充文本未写明的类型判断，但必须走确认闭环，",
            "不能靠置信度或模型“感觉”自动晋升。",
            "",
            "## 现实难度（主观性）",
            "",
            "主题、叙事目标、风格比 Character 姓名/Scene 地点更依赖解读：",
            "- 同一剧本可能被合理标成「亲情」或「成长」或「告别」；",
            "- 类型常是营销/平台标签，不一定写在稿纸上；",
            "- 受众几乎总是制作侧信息，不在对白里。",
            "",
            "因此确定性层只做标签抽取；任何内容推断若引入，只能作为",
            "`model_inferred` 候选并强制人工确认，不能假装容易。",
            "",
            "## 验证命令",
            "",
            "```bash",
            ".venv/bin/python docs/internal-notes/run_script_profile_against_test_scripts.py",
            "```",
            "",
            "## 下一阶段集成条件",
            "",
            "只有确认 Runtime 集成时，才应同步扩展生产 `CandidateFact.entity_kind`、",
            "confirmation API 与（可选）Production Graph feed；在此之前保持草稿隔离。",
            "",
        ]
    )
    FINDINGS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    print("=== ScriptProfile six-script honest missing check ===")
    six_ok, six_rows = evaluate_six_scripts()
    for row in six_rows:
        _ok(
            row["file"],  # type: ignore[arg-type]
            bool(row["pass"]),
            f"present={row['present']} missing={row['missing']}",
        )

    print("\n=== Labeled control sample ===")
    control_ok, control_table = evaluate_labeled_control()
    _ok("labeled control all present", control_ok, json.dumps(control_table, ensure_ascii=False))

    print("\n=== Human genre confirmation reuse ===")
    human_checks = evaluate_human_genre_confirmation()
    human_ok = True
    for name, passed in human_checks.items():
        human_ok = _ok(name, passed) and human_ok

    write_findings(six_rows, control_table)
    print(f"\nWrote {FINDINGS_PATH.relative_to(_HERE.parent.parent)}")

    all_ok = six_ok and control_ok and human_ok
    print("\nALL PASS" if all_ok else "\nFAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
