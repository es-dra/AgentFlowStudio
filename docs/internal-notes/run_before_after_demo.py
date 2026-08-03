#!/usr/bin/env python3
"""Before vs After demo — 《海边的信》, real local Runtime API.

Part 1: flags off → legacy junk characters still PASS.
Part 2: flags on → Script Truth → shadow extract → candidate loop →
         human confirm → Production Graph provenance → revision invalidation.

Usage (from repo root):
  .venv/bin/python docs/internal-notes/run_before_after_demo.py

Always uses a fresh tempfile runtime root — never /opt or production data.
Does not enable AFS_ALLOW_REMOTE_LLM.
"""

from __future__ import annotations

import json
import logging
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
from apps.api.runtime_candidate_confirmation import (  # noqa: E402
    CONFIRMATION_LOOP_ENV,
    inject_raw_junk_candidate,
    load_ledger,
    save_ledger,
)
from apps.api.runtime_m6_script_plan_asset_bible import (  # noqa: E402
    IMPROVED_EXTRACTION_ENV,
    M6_REUSE_SCRIPT_TRUTH_REVISION_ENV,
)
from apps.api.runtime_service import create_runtime_app  # noqa: E402
from apps.api.runtime_store import RuntimeStore  # noqa: E402

HERE = Path(__file__).resolve().parent
SEA_PATH = HERE / "test-scripts-character-scene" / "02_industry_standard_letter_by_the_sea.txt"
REPORT_PATH = HERE / "before-after-demo-20260803.md"
EVIDENCE_PATH = HERE / "before-after-demo-20260803.evidence.json"

EXPECTED_CHARS = ["苏晴", "老王", "林悦"]
EXPECTED_SCENES = ["老式邮局", "海边礁石", "苏晴的房间"]
LEGACY_JUNK_CHARS = ["苏晴没", "从远处", "道他可能"]

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


def _set_flags(**values: str) -> None:
    _clear_flags()
    for key, value in values.items():
        os.environ[key] = value


def _client(runtime_root: Path) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=runtime_root))


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post("/projects", json={"project_id": project_id, "goal": f"{project_id} story"})
    if response.status_code != 200:
        raise RuntimeError(f"create project failed: {response.status_code} {response.text}")


def _create_revision(
    client: TestClient,
    project_id: str,
    text: str,
    *,
    parent: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"source_kind": "script", "source_text": text}
    if parent:
        payload["parent_revision_id"] = parent
    response = client.post(f"/projects/{project_id}/script-revisions", json=payload)
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
            "title_hint": "海边的信",
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


def _snip(value: Any, *, max_chars: int = 2400) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    if len(text) > max_chars:
        return text[: max_chars - 20] + "\n  … (truncated)\n}"
    return text


def _md_code(value: Any, *, max_chars: int = 2400) -> str:
    return "```json\n" + _snip(value, max_chars=max_chars) + "\n```"


def run_demo() -> dict[str, Any]:
    sea = SEA_PATH.read_text(encoding="utf-8")
    evidence: dict[str, Any] = {
        "script": "02_industry_standard_letter_by_the_sea.txt",
        "title": "海边的信",
        "part1_legacy": {},
        "part2_new_system": {},
        "assertions": [],
    }

    def assert_true(name: str, cond: bool, detail: str = "") -> None:
        evidence["assertions"].append({"name": name, "ok": bool(cond), "detail": detail})
        if not cond:
            raise AssertionError(f"{name}: {detail}")

    # ------------------------------------------------------------------ Part 1
    _clear_flags()
    with tempfile.TemporaryDirectory(prefix="afs-before-after-legacy-") as tmp:
        client = _client(Path(tmp))
        project_id = "demo_sea_legacy"
        _create_project(client, project_id)
        rev = _create_revision(client, project_id, sea)
        run = _m6_preview(client, project_id, sea, rev, client_request_id="demo-legacy-sea-v1")
        preview = _preview_payload(run)
        chars = [row["display_name"] for row in preview["candidate"]["characters"]]
        scenes = [row["name"] for row in preview["candidate"]["scenes"]]
        validation = preview["validation"]
        evidence["part1_legacy"] = {
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
            "candidate_revision_id": preview["candidate"]["script_revision"]["revision_id"],
        }
        assert_true(
            "legacy still extracts junk characters",
            all(name in chars for name in LEGACY_JUNK_CHARS),
            f"got {chars}",
        )
        assert_true(
            "legacy validation still PASS despite junk",
            validation.get("verdict") == "PASS" and validation.get("P0") == 0,
            str(evidence["part1_legacy"]["validation"]),
        )
        assert_true(
            "shadow extraction absent when flag off",
            "shadow_extraction" not in preview,
            "shadow_extraction unexpectedly present",
        )

    # ------------------------------------------------------------------ Part 2
    _set_flags(
        **{
            IMPROVED_EXTRACTION_ENV: "true",
            CONFIRMATION_LOOP_ENV: "true",
            M6_REUSE_SCRIPT_TRUTH_REVISION_ENV: "true",
            FEED_PRODUCTION_GRAPH_ENV: "true",
            NAMESPACED_REVISION_NODES_ENV: "true",
        }
    )
    part2: dict[str, Any] = {"flags": {key: os.environ.get(key) for key in ALL_DEMO_FLAGS}}

    with tempfile.TemporaryDirectory(prefix="afs-before-after-new-") as tmp:
        runtime = Path(tmp)
        client = _client(runtime)
        store = RuntimeStore(runtime)
        project_id = "demo_sea_closed_loop"
        _create_project(client, project_id)

        # Step 1 — Script Truth
        rev1 = _create_revision(client, project_id, sea)
        part2["step1_script_truth"] = {
            "revision_id": rev1["revision_id"],
            "source_digest": rev1["source_digest"],
        }
        assert_true(
            "script truth revision id is scrrev_*",
            str(rev1["revision_id"]).startswith("scrrev_"),
            rev1["revision_id"],
        )

        # Step 2 — shadow extraction (candidate still legacy)
        run = _m6_preview(client, project_id, sea, rev1, client_request_id="demo-new-sea-shadow")
        preview = _preview_payload(run)
        shadow = preview.get("shadow_extraction") or {}
        improved_chars = [row["text"] for row in (shadow.get("improved") or {}).get("characters") or []]
        improved_scenes = [row["text"] for row in (shadow.get("improved") or {}).get("scenes") or []]
        legacy_chars = (shadow.get("legacy") or {}).get("characters") or []
        candidate_chars = [row["display_name"] for row in preview["candidate"]["characters"]]
        part2["step2_shadow_extraction"] = {
            "legacy_characters": legacy_chars,
            "legacy_scenes": (shadow.get("legacy") or {}).get("scenes") or [],
            "improved_characters": improved_chars,
            "improved_scenes": improved_scenes,
            "diff": shadow.get("diff"),
            "candidate_still_uses_legacy_characters": candidate_chars,
            "validation_verdict": preview["validation"].get("verdict"),
            "affects_production_graph": shadow.get("affects_production_graph"),
            "embedded_script_revision_id": preview["candidate"]["script_revision"]["revision_id"],
        }
        assert_true("improved shadow characters are 苏晴/老王/林悦", improved_chars == EXPECTED_CHARS, str(improved_chars))
        assert_true("improved shadow scenes are expected", improved_scenes == EXPECTED_SCENES, str(improved_scenes))
        assert_true(
            "candidate path still legacy until confirmation (shadow-only)",
            candidate_chars == LEGACY_JUNK_CHARS,
            str(candidate_chars),
        )
        assert_true(
            "reuse flag embeds scrrev_* in M6 candidate",
            preview["candidate"]["script_revision"]["revision_id"] == rev1["revision_id"],
            preview["candidate"]["script_revision"]["revision_id"],
        )

        # Step 3 — confirmation refresh + junk inject
        refreshed = _refresh(client, project_id, rev1)
        items = refreshed["bundle"]["items"]
        by_text = {item["text"]: item for item in items if not item.get("is_missing_slot")}
        part2["step3_candidates_after_refresh"] = {
            "candidate_texts": sorted(by_text),
            "authoritative_before_human": [row.get("text") for row in refreshed.get("authoritative") or []],
            "sample_items": [
                {
                    "text": item["text"],
                    "entity_kind": item["entity_kind"],
                    "status": item["status"],
                    "confidence": item["confidence"],
                    "review_decision": item["review_decision"],
                    "is_missing_slot": item["is_missing_slot"],
                }
                for item in items
                if item["text"] in EXPECTED_CHARS or item["entity_kind"] == "scene"
            ][:8],
        }
        assert_true(
            "refresh surfaces real character candidates",
            all(name in by_text for name in EXPECTED_CHARS),
            sorted(by_text),
        )
        assert_true("no automatic authoritative facts yet", refreshed.get("authoritative") == [], str(refreshed.get("authoritative")))

        ledger = load_ledger(store, project_id)
        junk = inject_raw_junk_candidate(
            ledger,
            junk_text="苏晴没",
            evidence_quote="苏晴没说话",
            confidence=0.96,
        )
        save_ledger(store, ledger)
        review = client.get(f"/projects/{project_id}/candidate-facts/review")
        if review.status_code != 200:
            raise RuntimeError(f"review failed: {review.status_code} {review.text}")
        junk_item = next(item for item in review.json()["bundle"]["items"] if item["fact_id"] == junk.fact_id)
        part2["step3_junk_injected"] = {
            "fact_id": junk.fact_id,
            "text": junk_item["text"],
            "status": junk_item["status"],
            "confidence": junk_item["confidence"],
            "review_decision": junk_item["review_decision"],
            "uncertainty_note": junk_item.get("uncertainty_note"),
            "authoritative_still_empty": review.json().get("authoritative") == [],
            "why_not_auto_authoritative": (
                "status=extracted_from_text + high confidence is still a CandidateFact; "
                "promote_candidate_fact requires human_confirmed (or a named deterministic check). "
                "Confidence alone never promotes."
            ),
        }
        assert_true(
            "junk stays pending candidate with high confidence",
            junk_item["text"] == "苏晴没"
            and junk_item["review_decision"] == "pending"
            and junk_item["confidence"] >= 0.9
            and review.json().get("authoritative") == [],
            _snip(part2["step3_junk_injected"], max_chars=600),
        )

        # Step 4 — human reject + accept
        reject_body = _action(
            client,
            project_id,
            rev1,
            action="reject",
            fact_id=junk.fact_id,
            reason="fragment not a character name (day-1 regression)",
        )
        accept_bodies = [
            _action(
                client,
                project_id,
                rev1,
                action="accept",
                fact_id=by_text[name]["fact_id"],
                reason=f"confirm character {name}",
            )
            for name in EXPECTED_CHARS
        ]
        scene_accepts = []
        for name in EXPECTED_SCENES:
            scene_item = next(
                item
                for item in refreshed["bundle"]["items"]
                if item["text"] == name and item["entity_kind"] == "scene"
            )
            scene_accepts.append(
                _action(
                    client,
                    project_id,
                    rev1,
                    action="accept",
                    fact_id=scene_item["fact_id"],
                    reason=f"confirm scene {name}",
                )
            )
        last = scene_accepts[-1]
        resolved = last["resolved"]
        auth_texts = [row["text"] for row in last["authoritative"]]
        part2["step4_human_actions"] = {
            "reject_junk": {
                "action": reject_body["action"],
                "affects_production_graph": reject_body.get("affects_production_graph"),
                "graph_feed": reject_body.get("graph_feed"),
                "result": reject_body.get("result"),
            },
            "accepted_characters": EXPECTED_CHARS,
            "accepted_scenes": EXPECTED_SCENES,
            "authoritative_texts": auth_texts,
            "resolved_for_downstream": resolved,
            "sample_accept_graph_feed": accept_bodies[0].get("graph_feed"),
            "sample_authoritative_fact": next(row for row in last["authoritative"] if row["text"] == "苏晴"),
        }
        assert_true("junk never appears in authoritative", "苏晴没" not in auth_texts, str(auth_texts))
        assert_true(
            "downstream resolve has correct characters",
            resolved.get("characters") == EXPECTED_CHARS,
            str(resolved.get("characters")),
        )
        assert_true(
            "downstream resolve has correct scenes",
            resolved.get("scenes") == EXPECTED_SCENES,
            str(resolved.get("scenes")),
        )

        # Step 5 — Production Graph
        graph_resp = client.get(f"/projects/{project_id}/m4/production-graph")
        if graph_resp.status_code != 200:
            raise RuntimeError(f"get graph failed: {graph_resp.status_code} {graph_resp.text}")
        graph = graph_resp.json()["graph"]
        authfact_nodes = {
            node_id: node
            for node_id, node in (graph.get("nodes") or {}).items()
            if str(node_id).startswith("authfact-")
        }
        revision_nodes = {
            node_id: node
            for node_id, node in (graph.get("nodes") or {}).items()
            if node.get("category") == "revision"
        }
        provenance_rows = [
            {
                "node_id": node_id,
                "category": node.get("category"),
                "text": (node.get("metadata") or {}).get("text"),
                "authoritative_fact_id": (node.get("metadata") or {}).get("authoritative_fact_id"),
                "source_candidate_fact_id": (node.get("metadata") or {}).get("source_candidate_fact_id"),
                "source_revision_id": (node.get("metadata") or {}).get("source_revision_id"),
                "promotion_kind": (node.get("metadata") or {}).get("promotion_kind"),
                "human_confirmed_by": (node.get("metadata") or {}).get("human_confirmed_by"),
                "source": (node.get("metadata") or {}).get("source"),
            }
            for node_id, node in sorted(authfact_nodes.items())
        ]
        part2["step5_production_graph"] = {
            "graph_version": graph.get("version"),
            "authfact_node_count": len(authfact_nodes),
            "revision_node_ids": sorted(revision_nodes),
            "namespaced_revision_prefix_ok": all(
                str(node_id).startswith("scripttruth-revision-") for node_id in revision_nodes
            ),
            "provenance_rows": provenance_rows,
            "sample_authfact_node": next(iter(authfact_nodes.values()), None),
            "sample_revision_node": next(iter(revision_nodes.values()), None),
        }
        graph_texts = {row["text"] for row in provenance_rows}
        assert_true(
            "graph contains confirmed character nodes",
            set(EXPECTED_CHARS) <= graph_texts,
            str(sorted(graph_texts)),
        )
        assert_true("graph does not contain junk 苏晴没", "苏晴没" not in graph_texts, str(sorted(graph_texts)))
        assert_true(
            "revision nodes are namespaced (no silent collision key)",
            part2["step5_production_graph"]["namespaced_revision_prefix_ok"],
            str(sorted(revision_nodes)),
        )
        assert_true(
            "every authfact node has full provenance",
            all(
                row["authoritative_fact_id"]
                and row["source_candidate_fact_id"]
                and row["source_revision_id"] == rev1["revision_id"]
                and row["promotion_kind"] == "human_confirmation"
                for row in provenance_rows
            ),
            _snip(provenance_rows[:2], max_chars=800),
        )

        # Step 6 — revision invalidation + change_log retained
        before_ledger = load_ledger(store, project_id)
        before_change_ids = [row.change_id for row in before_ledger.change_log]
        before_active = [r for r in before_ledger.authoritative_records if r.validity.value == "active"]
        sea_v2 = sea.replace("老式邮局", "海边老式邮局")
        rev2 = _create_revision(client, project_id, sea_v2, parent=rev1["revision_id"])
        refreshed2 = _refresh(client, project_id, rev2)
        after_ledger = load_ledger(store, project_id)
        after_change_ids = [row.change_id for row in after_ledger.change_log]
        invalidated = [
            {
                "text": r.fact.text,
                "validity": r.validity.value,
                "invalidated_by_revision_id": r.invalidated_by_revision_id,
                "source_revision_id": r.fact.source_revision_id,
            }
            for r in after_ledger.authoritative_records
            if r.validity.value == "invalidated_by_revision"
        ]
        change_reasons = [row.reason for row in after_ledger.change_log]
        part2["step6_revision_invalidation"] = {
            "old_revision_id": rev1["revision_id"],
            "new_revision_id": rev2["revision_id"],
            "active_authoritative_after_refresh": refreshed2.get("authoritative"),
            "invalidated_count": len(invalidated),
            "invalidated_sample": invalidated[:5],
            "change_log_before_count": len(before_change_ids),
            "change_log_after_count": len(after_change_ids),
            "prior_change_ids_retained": all(cid in after_change_ids for cid in before_change_ids),
            "has_script_revision_changed_reason": "script_revision_changed" in change_reasons,
            "new_candidate_scene_present": any(
                "海边老式邮局" in (item.get("text") or "") for item in refreshed2["bundle"]["items"]
            ),
        }
        assert_true(
            "old authoritative facts invalidated on revision change",
            len(invalidated) == len(before_active) and refreshed2.get("authoritative") == [],
            f"invalidated={len(invalidated)} before_active={len(before_active)}",
        )
        assert_true(
            "change_log accumulates across revision refresh",
            part2["step6_revision_invalidation"]["prior_change_ids_retained"]
            and len(after_change_ids) > len(before_change_ids),
            f"before={len(before_change_ids)} after={len(after_change_ids)}",
        )
        assert_true(
            "new revision needs re-confirmation (no auto authority)",
            refreshed2.get("authoritative") == [],
            str(refreshed2.get("authoritative")),
        )

    evidence["part2_new_system"] = part2
    return evidence


def render_report(evidence: dict[str, Any]) -> str:
    p1 = evidence["part1_legacy"]
    p2 = evidence["part2_new_system"]
    assertions = evidence["assertions"]
    failed = [row for row in assertions if not row["ok"]]
    status = "ALL ASSERTIONS PASSED" if not failed else f"{len(failed)} ASSERTION(S) FAILED"

    lines = [
        "# 之前 vs 之后：以《海边的信》为例",
        "",
        "> 本报告由 `docs/internal-notes/run_before_after_demo.py` **实际跑本地临时 Runtime API** 生成，",
        "> 不是设计文档。可重复执行脚本复现同一结论。",
        "",
        f"- 脚本：`02_industry_standard_letter_by_the_sea.txt`",
        f"- 生成状态：**{status}**（{len(assertions)} checks）",
        f"- 配套证据 JSON：`before-after-demo-20260803.evidence.json`",
        "",
        "---",
        "",
        "## 问题（复现，证明现在依然存在）",
        "",
        "所有新开关保持**默认关闭**，走现有 M6 preview API。",
        "legacy 正则仍然把「苏晴没 / 从远处 / 道他可能」当成人物，validation 仍然 **PASS**。",
        "",
        "### 实际结果（Part 1）",
        "",
        f"- Script Truth revision：`{p1['source_revision_id']}`",
        f"- 识别出的人物：`{p1['character_display_names']}`",
        f"- 识别出的场景：`{p1['scene_names']}`",
        f"- validation：`{p1['validation']}`",
        f"- shadow_extraction 是否出现：`{p1['shadow_extraction_present']}`（关开关时应为 false）",
        "",
        _md_code(
            {
                "character_display_names": p1["character_display_names"],
                "scene_names": p1["scene_names"],
                "validation": p1["validation"],
                "shadow_extraction_present": p1["shadow_extraction_present"],
            },
            max_chars=1200,
        ),
        "",
        "### 为什么这是个问题",
        "",
        "1. **内容错了还 PASS**：校验器检查结构完备性，不检查「名字是不是真人物」。",
        "2. **没有人工确认门槛**：高置信度提取会被当成可用结果继续往下走。",
        "3. **关掉新开关后问题立刻回来**——不是「代码碰巧修好了」，必须显式打开旁路能力。",
        "",
        "---",
        "",
        "## 解决方案的完整旅程",
        "",
        "打开相关开关（仅本演示临时 Runtime）：",
        "",
        _md_code(p2["flags"], max_chars=800),
        "",
        "### 步骤 1：提交剧本 → Script Truth revision",
        "",
        "真实 API：`POST /projects/{id}/script-revisions`",
        "",
        _md_code(p2["step1_script_truth"], max_chars=800),
        "",
        "### 步骤 2：改进提取（shadow-only）",
        "",
        "打开 `AFS_USE_IMPROVED_EXTRACTION` 后再次跑 M6 preview。",
        "**候选 candidate 仍是 legacy 垃圾**（旁路不偷偷改主路径），",
        "但 `shadow_extraction.improved` 给出正确人物/场景。",
        "",
        _md_code(
            {
                "legacy_characters": p2["step2_shadow_extraction"]["legacy_characters"],
                "improved_characters": p2["step2_shadow_extraction"]["improved_characters"],
                "legacy_scenes": p2["step2_shadow_extraction"]["legacy_scenes"],
                "improved_scenes": p2["step2_shadow_extraction"]["improved_scenes"],
                "candidate_still_uses_legacy_characters": p2["step2_shadow_extraction"][
                    "candidate_still_uses_legacy_characters"
                ],
                "validation_verdict": p2["step2_shadow_extraction"]["validation_verdict"],
                "affects_production_graph": p2["step2_shadow_extraction"]["affects_production_graph"],
                "embedded_script_revision_id": p2["step2_shadow_extraction"]["embedded_script_revision_id"],
                "diff": p2["step2_shadow_extraction"]["diff"],
            },
            max_chars=2200,
        ),
        "",
        "### 步骤 3：候选确认闭环 + 垃圾注入",
        "",
        "打开 `AFS_USE_CANDIDATE_CONFIRMATION_LOOP`，`POST .../candidate-facts/review/refresh`。",
        "此时 **authoritative 仍为空**。故意注入「苏晴没」（置信度 0.96）只能停在候选态：",
        "",
        _md_code(p2["step3_junk_injected"], max_chars=1600),
        "",
        "刷新后的真实候选（节选）：",
        "",
        _md_code(
            {
                "candidate_texts": p2["step3_candidates_after_refresh"]["candidate_texts"],
                "authoritative_before_human": p2["step3_candidates_after_refresh"]["authoritative_before_human"],
                "sample_items": p2["step3_candidates_after_refresh"]["sample_items"],
            },
            max_chars=2200,
        ),
        "",
        "### 步骤 4：人工拒绝垃圾、确认真实人物/场景",
        "",
        "- `reject`「苏晴没」→ 不进 authoritative，也不写 Graph",
        "- `accept` 苏晴 / 老王 / 林悦 + 三个场景",
        "- `resolved` 下游读到人工确认后的正确名单",
        "",
        _md_code(
            {
                "reject_junk": p2["step4_human_actions"]["reject_junk"],
                "authoritative_texts": p2["step4_human_actions"]["authoritative_texts"],
                "resolved_for_downstream": p2["step4_human_actions"]["resolved_for_downstream"],
                "sample_authoritative_fact": p2["step4_human_actions"]["sample_authoritative_fact"],
                "sample_accept_graph_feed": p2["step4_human_actions"]["sample_accept_graph_feed"],
            },
            max_chars=2800,
        ),
        "",
        "### 步骤 5：权威事实写入 Production Graph（可溯源）",
        "",
        "打开 `AFS_CANDIDATE_FACTS_FEED_PRODUCTION_GRAPH` + `AFS_CANDIDATE_FACTS_USE_NAMESPACED_REVISION_NODES`。",
        "accept 后写入 Graph；`GET /projects/{id}/m4/production-graph` 读回。",
        "revision 节点使用 `scripttruth-revision-{scrrev_*}-{digest16}`，避免与 M6 candidate 静默抢 key。",
        "",
        _md_code(
            {
                "graph_version": p2["step5_production_graph"]["graph_version"],
                "authfact_node_count": p2["step5_production_graph"]["authfact_node_count"],
                "revision_node_ids": p2["step5_production_graph"]["revision_node_ids"],
                "namespaced_revision_prefix_ok": p2["step5_production_graph"]["namespaced_revision_prefix_ok"],
                "provenance_rows": p2["step5_production_graph"]["provenance_rows"],
            },
            max_chars=3200,
        ),
        "",
        "单节点样例（含溯源字段）：",
        "",
        _md_code(p2["step5_production_graph"]["sample_authfact_node"], max_chars=1800),
        "",
        "### 步骤 6：换剧本版本 → 旧权威失效，审计保留",
        "",
        "把「老式邮局」改成「海边老式邮局」，创建新 revision 并 refresh。",
        "旧 authoritative 全部 `invalidated_by_revision`；当前 authoritative 为空；",
        "`change_log` **累加保留**（含先前 accept/reject）。",
        "",
        _md_code(p2["step6_revision_invalidation"], max_chars=2200),
        "",
        "---",
        "",
        "## 关键证明点",
        "",
        "| 证明点 | 证据 |",
        "|---|---|",
        f"| 垃圾数据被拦住 | 注入「苏晴没」后仍 pending；reject 后 authoritative 无此名，Graph 亦无 |",
        f"| 人工确认后下游正确 | `resolved.characters={p2['step4_human_actions']['resolved_for_downstream'].get('characters')}` / `scenes={p2['step4_human_actions']['resolved_for_downstream'].get('scenes')}` |",
        f"| 溯源链路完整 | Graph 节点带 `authoritative_fact_id` / `source_candidate_fact_id` / `source_revision_id={p2['step1_script_truth']['revision_id']}` / `promotion_kind=human_confirmation` |",
        f"| 换版本旧数据失效 | invalidated={p2['step6_revision_invalidation']['invalidated_count']}；refresh 后 authoritative=`[]`；change_log {p2['step6_revision_invalidation']['change_log_before_count']}→{p2['step6_revision_invalidation']['change_log_after_count']} 且旧 id 保留 |",
        f"| 默认关闭仍坏 | Part 1 characters=`{p1['character_display_names']}` + verdict=`{p1['validation'].get('verdict')}` |",
        "",
        "### 断言清单",
        "",
    ]
    for row in assertions:
        mark = "PASS" if row["ok"] else "FAIL"
        detail = f" — {row['detail']}" if row.get("detail") else ""
        lines.append(f"- [{mark}] {row['name']}{detail}")
    lines.extend(
        [
            "",
            "---",
            "",
            "## 如何自己复现",
            "",
            "```bash",
            "cd /path/to/repo",
            ".venv/bin/python docs/internal-notes/run_before_after_demo.py",
            "```",
            "",
            "脚本会：",
            "1. 用 tempfile 建本地 Runtime（不碰 /opt / 线上）",
            "2. 走真实 FastAPI TestClient 路由（与 Scenario A/B/C 同模式）",
            "3. 重写本报告与 `before-after-demo-20260803.evidence.json`",
            "4. 断言失败则以非零退出码退出",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    print("Running before/after demo against ephemeral local Runtime…", flush=True)
    evidence = run_demo()
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(render_report(evidence), encoding="utf-8")
    failed = [row for row in evidence["assertions"] if not row["ok"]]
    print(f"Wrote {REPORT_PATH.relative_to(_REPO)}", flush=True)
    print(f"Wrote {EVIDENCE_PATH.relative_to(_REPO)}", flush=True)
    print(f"Assertions: {len(evidence['assertions'])} total, {len(failed)} failed", flush=True)
    if failed:
        for row in failed:
            print(f"  FAIL: {row['name']} — {row.get('detail')}", flush=True)
        return 1
    print("ALL ASSERTIONS PASSED", flush=True)
    p1 = evidence["part1_legacy"]
    p2 = evidence["part2_new_system"]
    print("\n--- digest ---", flush=True)
    print("BEFORE characters:", p1["character_display_names"], "verdict=", p1["validation"]["verdict"], flush=True)
    print("AFTER improved shadow:", p2["step2_shadow_extraction"]["improved_characters"], flush=True)
    print("AFTER resolved:", p2["step4_human_actions"]["resolved_for_downstream"], flush=True)
    print(
        "AFTER graph authfacts:",
        len(p2["step5_production_graph"]["provenance_rows"]),
        "namespaced=",
        p2["step5_production_graph"]["namespaced_revision_prefix_ok"],
        flush=True,
    )
    print(
        "AFTER rev2 invalidated:",
        p2["step6_revision_invalidation"]["invalidated_count"],
        "changelog retained=",
        p2["step6_revision_invalidation"]["prior_change_ids_retained"],
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        _clear_flags()
