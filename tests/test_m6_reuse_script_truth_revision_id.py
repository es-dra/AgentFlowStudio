"""Feature-flagged reuse of Script Truth scrrev_* as M6 script_revision.revision_id."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from apps.api import runtime_m6_server_codex_planner as server_codex_planner
from apps.api.runtime_film_production_graph import compile_film_candidate
from apps.api.runtime_m6_script_plan_asset_bible import (
    M6_REUSE_SCRIPT_TRUTH_REVISION_ENV,
    M6PlanningError,
    build_m6_script_plan_asset_bible,
    m6_reuse_script_truth_revision_id_enabled,
    resolve_m6_script_revision_id,
)
from tests.test_runtime_m6_script_plan_asset_bible import _single_scope_server_codex_payload


SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "internal-notes"
    / "test-scripts-character-scene"
)
DAY_ONE_CASES = (
    ("01_industry_standard_last_light.txt", "scrrev_72ae32029f274e74"),
    ("02_industry_standard_letter_by_the_sea.txt", "scrrev_9f3d686832b74175"),
    ("03_labeled_fields_homecoming.txt", "scrrev_0ef51148a4f94c59"),
)
HOME = (SCRIPTS / "03_labeled_fields_homecoming.txt").read_text(encoding="utf-8")

CODEX_SOURCE = (
    "程遥在山顶气象站校准一枚黑色风向标。"
    "保持角色名称“程遥”、场景名称“山顶气象站”、道具名称“黑色风向标”不变；"
    "规划3个连续镜头，总时长约21秒。不要新增其他人物、场景或道具。"
)


def _preview(source_text: str, *, source_revision_id: str, source_revision_digest: str | None = None) -> dict:
    digest = source_revision_digest or hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return build_m6_script_plan_asset_bible(
        "proj_rev_unify",
        {
            "source_kind": "script",
            "source_text": source_text,
            "source_revision_id": source_revision_id,
            "source_revision_digest": digest,
            "revision_instruction": "",
            "parent_candidate_digest": "",
        },
    )


def _codex_candidate(*, body: dict, source_digest: str = "a" * 64) -> dict:
    """Build a Server Codex candidate from a fake provider payload — no remote LLM."""

    payload = _single_scope_server_codex_payload("程遥", "山顶气象站", "黑色风向标")
    timing_semantics = [
        ("建立气象站工作台与风向标的初始方位。", "交代空间、人物和待修道具的起始状态。", "需要完整看清方位读数与人物检查动作。"),
        ("程遥拆开轴承并清除阻塞的砂粒。", "呈现修复难点以及道具状态的可见变化。", "拆解、清理和复查必须在一个连续动作内完成。"),
        ("重新安装风向标并确认指针恢复转动。", "以修复结果收束行动并建立后续连续性。", "需要保留指针启动和人物确认反应的时间。"),
    ]
    for shot, (intent, purpose, reason) in zip(payload["shots"], timing_semantics, strict=True):
        shot["duration_seconds"] = 7
        shot["intent"] = intent
        shot["narrative_purpose"] = purpose
        shot["content_driven_duration_reason"] = reason
    return server_codex_planner._candidate_from_provider_payload(
        project_id="proj_codex_rev",
        body=body,
        payload=payload,
        source_digest=source_digest,
        dispatch_id="m6_codex_rev_dispatch",
        schema_digest="b" * 64,
        prompt_chars=1000,
        parent_candidate_digest="",
        revision_instruction="",
    )


def test_reuse_flag_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, raising=False)
    assert m6_reuse_script_truth_revision_id_enabled() is False
    revision_id = resolve_m6_script_revision_id(
        {"source_revision_id": "scrrev_deadbeefdeadbeef"},
        candidate_key="abcdef123456",
    )
    assert revision_id == "m6-script-abcdef123456"


def test_flag_off_still_invents_m6_script_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, raising=False)
    truth_id = "scrrev_0ef51148a4f94c59"
    default_preview = _preview(HOME, source_revision_id=truth_id)
    monkeypatch.setenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, "false")
    preview = _preview(HOME, source_revision_id=truth_id)
    embedded = preview["candidate"]["script_revision"]["revision_id"]
    lineage = preview["candidate"]["brief"]["lineage"]["source_revision_id"]
    assert preview == default_preview
    assert embedded.startswith("m6-script-")
    assert embedded != truth_id
    assert lineage == truth_id
    assert lineage != embedded
    assert "script_revision_id_source" not in preview["candidate"]["brief"]["lineage"]


@pytest.mark.parametrize(("filename", "truth_id"), DAY_ONE_CASES)
def test_flag_on_reuses_script_truth_revision_id_for_day_one_scripts(
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    truth_id: str,
) -> None:
    monkeypatch.setenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, "true")
    source_text = (SCRIPTS / filename).read_text(encoding="utf-8")
    preview = _preview(source_text, source_revision_id=truth_id)
    candidate = preview["candidate"]
    embedded = candidate["script_revision"]["revision_id"]
    lineage = candidate["brief"]["lineage"]["source_revision_id"]
    assert embedded == truth_id
    assert lineage == truth_id
    assert embedded == lineage
    assert not embedded.startswith("m6-script-")
    assert all(row.get("lineage") == [truth_id] for row in candidate["scenes"])
    assert all(
        any(
            ref.get("source_kind") == "script_revision" and ref.get("source_id") == truth_id
            for ref in row.get("source_evidence_refs") or []
        )
        for row in candidate["shots"]
    )

    # Compile only: prove graph identities and references close without writing.
    events = compile_film_candidate("proj_rev_unify", candidate)
    revision_nodes = [
        event["node"]
        for event in events
        if event.get("type") == "node_upserted"
        and event.get("node", {}).get("category") == "revision"
    ]
    assert revision_nodes == [
        {
            "node_id": truth_id,
            "category": "revision",
            "metadata": {"source_digest": candidate["source_digest"]},
        }
    ]


def test_flag_on_without_source_revision_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, "true")
    with pytest.raises(M6PlanningError, match="requires source_revision_id from Script Truth"):
        build_m6_script_plan_asset_bible(
            "proj_idea",
            {"source_kind": "idea", "source_text": HOME},
        )


def test_server_codex_flag_off_still_invents_m6_codex_revision_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, raising=False)
    monkeypatch.delenv(server_codex_planner.REMOTE_LLM_ENV, raising=False)
    truth_id = "scrrev_codex_truth_aaaaaaaa"
    candidate = _codex_candidate(
        body={
            "source_kind": "idea",
            "source_text": CODEX_SOURCE,
            "source_revision_id": truth_id,
        }
    )
    embedded = candidate["script_revision"]["revision_id"]
    assert "m6-codex-revision-" in embedded
    assert embedded != truth_id
    assert candidate["brief"]["lineage"]["source_revision_id"] == truth_id
    # Id resolution must not require remote LLM gate.
    assert server_codex_planner.server_codex_m6_enabled() is False


def test_server_codex_flag_on_reuses_script_truth_revision_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, "true")
    monkeypatch.delenv(server_codex_planner.REMOTE_LLM_ENV, raising=False)
    truth_id = "scrrev_codex_truth_bbbbbbbb"
    candidate = _codex_candidate(
        body={
            "source_kind": "idea",
            "source_text": CODEX_SOURCE,
            "source_revision_id": truth_id,
            "source_revision_digest": "c" * 64,
        }
    )
    embedded = candidate["script_revision"]["revision_id"]
    lineage = candidate["brief"]["lineage"]["source_revision_id"]
    assert embedded == truth_id
    assert lineage == truth_id
    assert "m6-codex-revision-" not in embedded
    assert all(row.get("lineage") == [truth_id] for row in candidate["scenes"])
    assert server_codex_planner.server_codex_m6_enabled() is False


def test_server_codex_flag_on_without_source_revision_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, "true")
    monkeypatch.delenv(server_codex_planner.REMOTE_LLM_ENV, raising=False)
    with pytest.raises(M6PlanningError, match="requires source_revision_id from Script Truth"):
        _codex_candidate(body={"source_kind": "idea", "source_text": CODEX_SOURCE})
    assert server_codex_planner.server_codex_m6_enabled() is False


def test_resolve_keeps_planner_specific_invented_ids_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(M6_REUSE_SCRIPT_TRUTH_REVISION_ENV, raising=False)
    invented = "proj-m6-codex-revision-1-abcdef123456"
    assert (
        resolve_m6_script_revision_id(
            {"source_revision_id": "scrrev_ignored"},
            candidate_key="abcdef123456",
            invented=invented,
        )
        == invented
    )
