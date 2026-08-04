#!/usr/bin/env python3
"""Full-pipeline before/after demo — three original scripts via real local API.

Compares:
  Legacy  = all new flags off (today's default / online-like path)
  New     = improved extraction + confirmation loop + graph feed flags on

Scripts:
  01 最后的光 / 03 归途 / 02 海边的信

Usage (from repo root):
  .venv/bin/python docs/internal-notes/run_full_pipeline_demo.py

Always uses a fresh tempfile runtime root — never /opt or production data.
Does not enable AFS_ALLOW_REMOTE_LLM.
Does not invent Beat labels; missing Beats are recorded honestly.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from apps.api.runtime_authoritative_facts_graph import (  # noqa: E402
    FEED_PRODUCTION_GRAPH_ENV,
    NAMESPACED_REVISION_NODES_ENV,
)
from apps.api.runtime_candidate_confirmation import CONFIRMATION_LOOP_ENV  # noqa: E402
from apps.api.runtime_m6_script_plan_asset_bible import (  # noqa: E402
    IMPROVED_EXTRACTION_ENV,
    M6_REUSE_SCRIPT_TRUTH_REVISION_ENV,
)
from apps.api.runtime_service import create_runtime_app  # noqa: E402

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE / "test-scripts-character-scene"
REPORT_PATH = HERE / "before-after-full-pipeline-20260804.md"
EVIDENCE_PATH = HERE / "before-after-full-pipeline-20260804.evidence.json"

CASES: tuple[dict[str, Any], ...] = (
    {
        "key": "last_light",
        "title": "最后的光",
        "file": "01_industry_standard_last_light.txt",
        "expected_new_chars": ["玛雅"],
        "expected_new_scenes": ["废弃灯塔", "灯塔阳台"],
        "expected_format_style": "industry_heading",
        "expected_scene_count": 2,
        # Soft expectations for legacy (document, fail closed only if wildly off).
        "legacy_scene_junk_subset": ["颤抖", "灯上"],
    },
    {
        "key": "homecoming",
        "title": "归途",
        "file": "03_labeled_fields_homecoming.txt",
        "expected_new_chars": ["陈浩", "林秀"],
        "expected_new_scenes": ["小镇火车站", "陈浩家中的老屋"],
        "expected_format_style": "labeled",
        "expected_scene_count": 2,
        "legacy_scene_junk_subset": [],
    },
    {
        "key": "letter_by_sea",
        "title": "海边的信",
        "file": "02_industry_standard_letter_by_the_sea.txt",
        "expected_new_chars": ["苏晴", "老王", "林悦"],
        "expected_new_scenes": ["老式邮局", "海边礁石", "苏晴的房间"],
        "expected_format_style": "industry_heading",
        "expected_scene_count": 3,
        "legacy_junk_chars": ["苏晴没", "从远处", "道他可能"],
        "legacy_scene_junk_subset": [],
    },
)

ALL_DEMO_FLAGS = (
    IMPROVED_EXTRACTION_ENV,
    CONFIRMATION_LOOP_ENV,
    M6_REUSE_SCRIPT_TRUTH_REVISION_ENV,
    FEED_PRODUCTION_GRAPH_ENV,
    NAMESPACED_REVISION_NODES_ENV,
)


def _clear_flags() -> None:
    for key in (*ALL_DEMO_FLAGS, "AFS_ALLOW_REMOTE_LLM", "AFS_CANDIDATE_FACTS_RECOVERABLE_GRAPH_FEED"):
        os.environ.pop(key, None)


def _set_new_system_flags() -> None:
    _clear_flags()
    os.environ[IMPROVED_EXTRACTION_ENV] = "true"
    os.environ[CONFIRMATION_LOOP_ENV] = "true"
    os.environ[M6_REUSE_SCRIPT_TRUTH_REVISION_ENV] = "true"
    os.environ[FEED_PRODUCTION_GRAPH_ENV] = "true"
    os.environ[NAMESPACED_REVISION_NODES_ENV] = "true"


def _client(runtime_root: Path) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=runtime_root))


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post("/projects", json={"project_id": project_id, "goal": f"{project_id} story"})
    if response.status_code != 200:
        raise RuntimeError(f"create project failed: {response.status_code} {response.text}")


def _create_revision(client: TestClient, project_id: str, text: str) -> dict[str, Any]:
    response = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": text},
    )
    if response.status_code != 200:
        raise RuntimeError(f"create revision failed: {response.status_code} {response.text}")
    return response.json()["revision"]


def _m6_preview(
    client: TestClient,
    project_id: str,
    source_text: str,
    revision: dict[str, Any],
    *,
    client_request_id: str,
) -> dict[str, Any]:
    response = client.post(
        f"/projects/{project_id}/m6/script-plan-asset-bible/preview",
        headers={"X-Client-Request-ID": client_request_id},
        json={
            "source_kind": "script",
            "source_text": source_text,
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"m6 preview failed: {response.status_code} {response.text}")
    run = response.json()
    for _ in range(400):
        if run.get("phase") in {"succeeded", "failed", "cancelled"}:
            break
        time.sleep(0.05)
        loaded = client.get(
            f"/projects/{project_id}/m6/script-plan-asset-bible/preview-runs/{run['run_id']}"
        )
        if loaded.status_code != 200:
            raise RuntimeError(f"m6 preview poll failed: {loaded.status_code} {loaded.text}")
        run = loaded.json()
    if run.get("phase") != "succeeded":
        raise RuntimeError(f"m6 preview did not succeed: {json.dumps(run, ensure_ascii=False)[:800]}")
    return run


def _preview_payload(run: dict[str, Any]) -> dict[str, Any]:
    preview = run.get("preview")
    if not isinstance(preview, dict):
        raise RuntimeError("m6 preview payload missing")
    return preview


def _refresh(client: TestClient, project_id: str, revision: dict[str, Any]) -> dict[str, Any]:
    response = client.post(
        f"/projects/{project_id}/candidate-facts/review/refresh",
        json={
            "source_revision_id": revision["revision_id"],
            "source_revision_digest": revision["source_digest"],
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"refresh failed: {response.status_code} {response.text}")
    return response.json()


def _action(
    client: TestClient,
    project_id: str,
    revision: dict[str, Any],
    *,
    action: str,
    fact_id: str,
    reason: str = "",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "action": action,
        "fact_id": fact_id,
        "source_revision_id": revision["revision_id"],
        "source_revision_digest": revision["source_digest"],
    }
    if reason:
        body["reason"] = reason
    response = client.post(f"/projects/{project_id}/candidate-facts/actions", json=body)
    if response.status_code != 200:
        raise RuntimeError(f"action {action} failed: {response.status_code} {response.text}")
    return response.json()


def _group_candidates(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_kind.setdefault(item["entity_kind"], []).append(
            {
                "text": item["text"],
                "field_path": item["field_path"],
                "status": item["status"],
                "is_missing_slot": item.get("is_missing_slot"),
                "fact_id": item["fact_id"],
                "entity_id": item["entity_id"],
                "uncertainty_note": item.get("uncertainty_note"),
            }
        )
    profile = {
        row["field_path"].split(".", 1)[-1]: {
            "text": row["text"],
            "status": row["status"],
        }
        for row in by_kind.get("script_profile", [])
    }
    format_profile = {
        row["field_path"].split(".", 1)[-1]: {
            "text": row["text"],
            "status": row["status"],
        }
        for row in by_kind.get("script_format_profile", [])
    }
    beats = by_kind.get("beat", [])
    beat_boundaries = [row for row in beats if str(row["field_path"]).endswith(".boundary")]
    beat_facets = [row for row in beats if not str(row["field_path"]).endswith(".boundary")]
    return {
        "kinds_present": sorted(by_kind),
        "characters": [row["text"] for row in by_kind.get("character", []) if row["status"] != "missing"],
        "scenes": [row["text"] for row in by_kind.get("scene", []) if row["status"] != "missing"],
        "script_profile": profile,
        "script_format_profile": format_profile,
        "beat_boundary_count": len(beat_boundaries),
        "beat_facet_count": len(beat_facets),
        "beat_items": beats,
        "raw_counts": {kind: len(rows) for kind, rows in by_kind.items()},
    }


def _run_legacy(case: dict[str, Any], source_text: str) -> dict[str, Any]:
    _clear_flags()
    with tempfile.TemporaryDirectory(prefix=f"afs-full-demo-legacy-{case['key']}-") as tmp:
        client = _client(Path(tmp))
        project_id = f"demo_{case['key']}_legacy"
        _create_project(client, project_id)
        rev = _create_revision(client, project_id, source_text)
        run = _m6_preview(
            client,
            project_id,
            source_text,
            rev,
            client_request_id=f"full-demo-legacy-{case['key']}",
        )
        preview = _preview_payload(run)
        chars = [row["display_name"] for row in preview["candidate"]["characters"]]
        scenes = [row["name"] for row in preview["candidate"]["scenes"]]
        validation = preview["validation"]
        return {
            "project_id": project_id,
            "source_revision_id": rev["revision_id"],
            "flags": {key: os.environ.get(key) for key in ALL_DEMO_FLAGS},
            "character_display_names": chars,
            "scene_names": scenes,
            "validation": {
                "verdict": validation.get("verdict"),
                "P0": validation.get("P0"),
                "P1": validation.get("P1"),
            },
            "shadow_extraction_present": "shadow_extraction" in preview,
        }


def _run_new_system(case: dict[str, Any], source_text: str) -> dict[str, Any]:
    _set_new_system_flags()
    notes: list[str] = []
    with tempfile.TemporaryDirectory(prefix=f"afs-full-demo-new-{case['key']}-") as tmp:
        client = _client(Path(tmp))
        project_id = f"demo_{case['key']}_new"
        _create_project(client, project_id)
        rev = _create_revision(client, project_id, source_text)

        # Shadow path still leaves M6 candidate on legacy extract (by design).
        run = _m6_preview(
            client,
            project_id,
            source_text,
            rev,
            client_request_id=f"full-demo-new-shadow-{case['key']}",
        )
        preview = _preview_payload(run)
        shadow = preview.get("shadow_extraction") or {}
        improved = shadow.get("improved") or {}
        shadow_chars = [row["text"] for row in improved.get("characters") or []]
        shadow_scenes = [row["text"] for row in improved.get("scenes") or []]

        refreshed = _refresh(client, project_id, rev)
        items = refreshed["bundle"]["items"]
        missing_slots = refreshed["bundle"].get("missing_slots") or []
        grouped = _group_candidates(items)
        beat_missing_slots = [
            {
                "field_path": slot["field_path"],
                "message": slot.get("message"),
                "status": slot.get("status"),
            }
            for slot in missing_slots
            if slot.get("entity_kind") == "beat"
        ]

        # Honest Beat expectation: no explicit labels → no beat candidates.
        if grouped["beat_boundary_count"] != 0 or grouped["beat_facet_count"] != 0:
            notes.append(
                f"UNEXPECTED: Beat candidates appeared without labels "
                f"(boundaries={grouped['beat_boundary_count']}, facets={grouped['beat_facet_count']})"
            )

        # Accept real present candidates: all characters, all scenes, format facets that are present.
        accepted: list[dict[str, Any]] = []
        last_body: dict[str, Any] | None = None
        for item in items:
            if item.get("is_missing_slot") or item["status"] == "missing":
                continue
            if item["entity_kind"] not in {
                "character",
                "scene",
                "script_format_profile",
            }:
                continue
            # Skip Beat even if somehow present — do not invent confirmation of beats.
            if item["entity_kind"] == "beat":
                continue
            body = _action(
                client,
                project_id,
                rev,
                action="accept",
                fact_id=item["fact_id"],
                reason=f"demo confirm {item['entity_kind']} {item['field_path']}",
            )
            accepted.append(
                {
                    "entity_kind": item["entity_kind"],
                    "field_path": item["field_path"],
                    "text": item["text"],
                }
            )
            last_body = body

        # ScriptProfile facets are expected missing on unlabeled scripts — do not edit_confirm
        # invent theme/genre for demo polish.
        profile_statuses = {
            facet: row["status"] for facet, row in grouped["script_profile"].items()
        }
        if any(status != "missing" for status in profile_statuses.values()):
            notes.append(
                f"NOTE: unlabeled script unexpectedly produced present ScriptProfile facets: {profile_statuses}"
            )

        graph_resp = client.get(f"/projects/{project_id}/m4/production-graph")
        if graph_resp.status_code != 200:
            raise RuntimeError(f"get graph failed: {graph_resp.status_code} {graph_resp.text}")
        graph = graph_resp.json()["graph"]
        nodes = graph.get("nodes") or {}
        authfact_nodes = {
            node_id: node
            for node_id, node in nodes.items()
            if str(node_id).startswith("authfact-")
        }
        kind_counts: dict[str, int] = {}
        provenance = []
        for node_id, node in sorted(authfact_nodes.items()):
            meta = node.get("metadata") or {}
            kind = meta.get("entity_kind") or "unknown"
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            provenance.append(
                {
                    "node_id": node_id,
                    "entity_kind": kind,
                    "field_path": meta.get("field_path"),
                    "text": meta.get("text") or meta.get("value") or meta.get("display_name") or meta.get("name"),
                    "source_revision_id": meta.get("source_revision_id"),
                    "promotion_kind": meta.get("promotion_kind"),
                }
            )

        resolved = (last_body or {}).get("resolved") or {}
        return {
            "project_id": project_id,
            "source_revision_id": rev["revision_id"],
            "source_revision_digest": rev["source_digest"],
            "flags": {key: os.environ.get(key) for key in ALL_DEMO_FLAGS},
            "shadow_improved_characters": shadow_chars,
            "shadow_improved_scenes": shadow_scenes,
            "m6_candidate_still_legacy_characters": [
                row["display_name"] for row in preview["candidate"]["characters"]
            ],
            "candidates": grouped,
            "beat_missing_slots": beat_missing_slots,
            "accepted": accepted,
            "accepted_count": len(accepted),
            "authoritative_texts": [row.get("text") for row in (last_body or {}).get("authoritative") or []],
            "resolved": {
                "characters": resolved.get("characters"),
                "scenes": resolved.get("scenes"),
                "script_profile": resolved.get("script_profile"),
                "script_format_profile": resolved.get("script_format_profile"),
                "beats": resolved.get("beats"),
                "beat_facets": resolved.get("beat_facets"),
            },
            "graph": {
                "version": graph.get("version"),
                "authfact_node_count": len(authfact_nodes),
                "entity_kind_counts": kind_counts,
                "provenance_sample": provenance[:12],
                "all_texts": sorted(
                    {
                        str(row["text"])
                        for row in provenance
                        if row.get("text")
                    }
                ),
            },
            "notes": notes,
        }


def _assert_case(case: dict[str, Any], legacy: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        rows.append({"case": case["key"], "name": name, "ok": bool(cond), "detail": detail})
        if not cond:
            raise AssertionError(f"{case['key']}/{name}: {detail}")

    check(
        "legacy validation present",
        legacy["validation"]["verdict"] in {"PASS", "FAIL", "WARN"} or legacy["validation"]["verdict"] is not None,
        str(legacy["validation"]),
    )
    check("legacy has no shadow_extraction", legacy["shadow_extraction_present"] is False, "")

    junk_chars = case.get("legacy_junk_chars") or []
    if junk_chars:
        check(
            "legacy still extracts known junk characters",
            all(name in legacy["character_display_names"] for name in junk_chars),
            str(legacy["character_display_names"]),
        )

    junk_scenes = case.get("legacy_scene_junk_subset") or []
    if junk_scenes:
        check(
            "legacy still extracts known junk scenes",
            all(name in legacy["scene_names"] for name in junk_scenes),
            str(legacy["scene_names"]),
        )

    check(
        "new system improved characters match expected",
        new["shadow_improved_characters"] == case["expected_new_chars"],
        str(new["shadow_improved_characters"]),
    )
    check(
        "new system candidate characters match expected",
        new["candidates"]["characters"] == case["expected_new_chars"],
        str(new["candidates"]["characters"]),
    )
    check(
        "new system candidate scenes match expected",
        new["candidates"]["scenes"] == case["expected_new_scenes"],
        str(new["candidates"]["scenes"]),
    )

    fmt = new["candidates"]["script_format_profile"]
    check(
        "format_style present and expected",
        fmt.get("format_style", {}).get("text") == case["expected_format_style"]
        and fmt.get("format_style", {}).get("status") == "extracted_from_text",
        str(fmt.get("format_style")),
    )
    check(
        "scene_boundary_count present and expected",
        fmt.get("scene_boundary_count", {}).get("text") == str(case["expected_scene_count"]),
        str(fmt.get("scene_boundary_count")),
    )
    cleaning = fmt.get("cleaning_notes", {}).get("text")
    check(
        "cleaning_notes empty list JSON",
        cleaning == "[]",
        str(cleaning),
    )

    profile = new["candidates"]["script_profile"]
    check(
        "script_profile facets all missing on unlabeled scripts",
        bool(profile)
        and all(row.get("status") == "missing" for row in profile.values())
        and set(profile) >= {"theme", "genre", "audience", "narrative_goals", "style_requirements"},
        str(profile),
    )

    check(
        "no Beat candidates without explicit labels",
        new["candidates"]["beat_boundary_count"] == 0
        and new["candidates"]["beat_facet_count"] == 0,
        str(new["candidates"].get("beat_items")),
    )
    check(
        "beat missing_slots recorded",
        len(new["beat_missing_slots"]) >= 1,
        str(new["beat_missing_slots"]),
    )

    check("accepted at least one character/scene/format fact", new["accepted_count"] >= 1, str(new["accepted_count"]))
    check(
        "graph has authfact nodes after confirm",
        new["graph"]["authfact_node_count"] >= 1,
        str(new["graph"]),
    )
    check(
        "graph includes character and script_format_profile kinds",
        new["graph"]["entity_kind_counts"].get("character", 0) >= 1
        and new["graph"]["entity_kind_counts"].get("script_format_profile", 0) >= 1,
        str(new["graph"]["entity_kind_counts"]),
    )
    check(
        "graph does not invent beat nodes",
        new["graph"]["entity_kind_counts"].get("beat", 0) == 0,
        str(new["graph"]["entity_kind_counts"]),
    )
    check("no unexpected notes", new["notes"] == [], str(new["notes"]))
    return rows


def run_demo() -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "generated_by": "docs/internal-notes/run_full_pipeline_demo.py",
        "cases": {},
        "assertions": [],
        "findings": [],
    }
    for case in CASES:
        source = (SCRIPTS / case["file"]).read_text(encoding="utf-8")
        legacy = _run_legacy(case, source)
        new = _run_new_system(case, source)
        evidence["cases"][case["key"]] = {
            "title": case["title"],
            "file": case["file"],
            "legacy": legacy,
            "new_system": new,
        }
        evidence["assertions"].extend(_assert_case(case, legacy, new))

        # Capture noteworthy honest deltas for the report.
        if case["key"] == "last_light":
            if legacy["character_display_names"] == ["玛雅"]:
                evidence["findings"].append(
                    {
                        "severity": "info",
                        "case": "last_light",
                        "message": (
                            "Legacy characters for《最后的光》are now just ['玛雅'] "
                            "(correct); junk remains on scenes ['颤抖','灯上']. "
                            "Earlier day-1 notes that mentioned character junk "
                            "'颤抖'/'灯上' are outdated for the character slot."
                        ),
                    }
                )
        if case["key"] == "homecoming":
            if set(legacy["character_display_names"]) == set(case["expected_new_chars"]):
                evidence["findings"].append(
                    {
                        "severity": "info",
                        "case": "homecoming",
                        "message": (
                            "《归途》legacy characters already match improved extract "
                            "(labeled cast list). New-system value is ScriptFormatProfile "
                            "+ confirmation/Graph provenance, not character rescue."
                        ),
                    }
                )
    return evidence


def _fmt_list(values: list[Any]) -> str:
    return "`" + json.dumps(values, ensure_ascii=False) + "`"


def render_report(evidence: dict[str, Any]) -> str:
    assertions = evidence["assertions"]
    failed = [row for row in assertions if not row["ok"]]
    status = "ALL ASSERTIONS PASSED" if not failed else f"{len(failed)} ASSERTION(S) FAILED"
    lines: list[str] = [
        "# 完整链路之前/之后对比：三份原始剧本",
        "",
        "> 本报告由 `docs/internal-notes/run_full_pipeline_demo.py` **实际跑本地临时 Runtime API** 生成，",
        "> 不是设计文档。可重复执行脚本复现同一结论。不碰 `/opt` 或线上数据。",
        "",
        f"- 生成状态：**{status}**（{len(assertions)} checks）",
        f"- 配套证据 JSON：`before-after-full-pipeline-20260804.evidence.json`",
        f"- 新系统开关：`{', '.join(ALL_DEMO_FLAGS)}`",
        "",
        "## 发现（跑演示时如实记录）",
        "",
    ]
    findings = evidence.get("findings") or []
    if findings:
        for row in findings:
            lines.append(f"- **{row['case']}**: {row['message']}")
    else:
        lines.append("- （无额外发现）")
    lines.extend(["", "---", ""])

    summary_rows: list[str] = []

    for case in CASES:
        block = evidence["cases"][case["key"]]
        legacy = block["legacy"]
        new = block["new_system"]
        cand = new["candidates"]
        profile = cand["script_profile"]
        fmt = cand["script_format_profile"]
        lines.extend(
            [
                f"## 《{case['title']}》",
                "",
                f"脚本：`{case['file']}`",
                "",
                "### Legacy（开关全关）",
                "",
                f"- Script Truth revision：`{legacy['source_revision_id']}`",
                f"- 人物：{_fmt_list(legacy['character_display_names'])}",
                f"- 场景：{_fmt_list(legacy['scene_names'])}",
                f"- validation：`{json.dumps(legacy['validation'], ensure_ascii=False)}`",
                f"- shadow_extraction 出现：`{legacy['shadow_extraction_present']}`",
                "",
                "```json",
                json.dumps(
                    {
                        "characters": legacy["character_display_names"],
                        "scenes": legacy["scene_names"],
                        "validation": legacy["validation"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
                "### 完整新系统（相关开关全开）",
                "",
                f"- Script Truth revision：`{new['source_revision_id']}`",
                f"- shadow improved 人物：{_fmt_list(new['shadow_improved_characters'])}",
                f"- shadow improved 场景：{_fmt_list(new['shadow_improved_scenes'])}",
                f"- M6 candidate 仍走 legacy 人物（shadow-only 旁路）：{_fmt_list(new['m6_candidate_still_legacy_characters'])}",
                "",
                "#### 候选事实（refresh）",
                "",
                f"- Character：{_fmt_list(cand['characters'])}",
                f"- Scene：{_fmt_list(cand['scenes'])}",
                f"- ScriptProfile：`{json.dumps(profile, ensure_ascii=False)}`",
                f"- ScriptFormatProfile：`{json.dumps(fmt, ensure_ascii=False)}`",
                f"- Beat boundaries：`{cand['beat_boundary_count']}`；Beat facets：`{cand['beat_facet_count']}`",
                f"- Beat missing_slots：`{len(new['beat_missing_slots'])}`（无显式节拍标签 → 诚实 missing，未编造）",
                "",
                "```json",
                json.dumps(
                    {
                        "characters": cand["characters"],
                        "scenes": cand["scenes"],
                        "script_profile": profile,
                        "script_format_profile": fmt,
                        "beat_boundary_count": cand["beat_boundary_count"],
                        "beat_facet_count": cand["beat_facet_count"],
                        "beat_missing_slots": new["beat_missing_slots"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
                "#### 人工确认",
                "",
                f"- 确认条数：`{new['accepted_count']}`（Character / Scene / present ScriptFormatProfile；不确认 missing ScriptProfile，不编造 Beat）",
                f"- 确认明细：`{json.dumps(new['accepted'], ensure_ascii=False)}`",
                f"- resolved.characters：{_fmt_list(new['resolved'].get('characters') or [])}",
                f"- resolved.scenes：{_fmt_list(new['resolved'].get('scenes') or [])}",
                f"- resolved.script_format_profile：`{json.dumps(new['resolved'].get('script_format_profile'), ensure_ascii=False)}`",
                f"- resolved.beats：{_fmt_list(new['resolved'].get('beats') or [])}",
                "",
                "#### Production Graph",
                "",
                f"- authfact 节点数：`{new['graph']['authfact_node_count']}`",
                f"- 按 entity_kind：`{json.dumps(new['graph']['entity_kind_counts'], ensure_ascii=False)}`",
                f"- 节点 texts：{_fmt_list(new['graph']['all_texts'])}",
                "",
                "```json",
                json.dumps(new["graph"]["provenance_sample"], ensure_ascii=False, indent=2),
                "```",
                "",
                "---",
                "",
            ]
        )
        profile_summary = (
            "all missing"
            if profile and all(row.get("status") == "missing" for row in profile.values())
            else "mixed/present"
        )
        beat_summary = (
            "missing (0 candidates)"
            if cand["beat_boundary_count"] == 0
            else f"{cand['beat_boundary_count']} boundaries"
        )
        summary_rows.append(
            "| "
            + " | ".join(
                [
                    case["title"],
                    ", ".join(legacy["character_display_names"]) or "—",
                    ", ".join(cand["characters"]) or "—",
                    ", ".join(legacy["scene_names"]) or "—",
                    ", ".join(cand["scenes"]) or "—",
                    profile_summary,
                    beat_summary,
                    str(new["graph"]["authfact_node_count"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "## 总结表格",
            "",
            "| 剧本 | Legacy 人物 | 新系统人物 | Legacy 场景 | 新系统场景 | ScriptProfile | Beat | Graph 节点数 |",
            "|---|---|---|---|---|---|---|---|",
            *summary_rows,
            "",
            "## 怎么复现",
            "",
            "```bash",
            ".venv/bin/python docs/internal-notes/run_full_pipeline_demo.py",
            "```",
            "",
            "每次运行使用全新 tempfile Runtime；结果结构应一致（revision id / fact id 会变）。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    evidence = run_demo()
    REPORT_PATH.write_text(render_report(evidence), encoding="utf-8")
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    failed = [row for row in evidence["assertions"] if not row["ok"]]
    print(f"Wrote {REPORT_PATH.relative_to(_REPO)}")
    print(f"Wrote {EVIDENCE_PATH.relative_to(_REPO)}")
    print(f"assertions={len(evidence['assertions'])} failed={len(failed)}")
    for row in evidence.get("findings") or []:
        print(f"FINDING[{row['severity']}/{row['case']}]: {row['message']}")
    if failed:
        for row in failed:
            print(f"FAIL {row['case']}/{row['name']}: {row['detail']}")
        return 1
    print("ALL ASSERTIONS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
