from __future__ import annotations

from typing import Any

from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_workbench_card_utils import blocker as _blocker
from apps.api.runtime_workbench_card_utils import blockers as _blockers
from apps.api.runtime_workbench_card_utils import card as _card
from apps.api.runtime_workbench_card_utils import evidence as _evidence
from apps.api.runtime_workbench_content import build_content_cards
from apps.api.runtime_workbench_support import (
    NAVIGATION,
    NON_CLAIMS,
    SAFE_REF_POLICY,
    artifact as _artifact,
    artifact_id as _artifact_id,
    artifact_ids as _artifact_ids,
    event_title as _event_title,
    jobs_by_action as _jobs_by_action,
    latest as _latest,
    list_value as _list,
    payload as _payload,
    status as _status,
    summary as _summary,
)


def build_workbench_cards(
    store: RuntimeStore,
    *,
    manifest: dict[str, Any],
    jobs: list[dict[str, Any]],
    project: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    action_jobs = _jobs_by_action(jobs)
    provider_gate = _provider_gate(_latest(action_jobs, "provider_validation_plan"), store)
    cards = [
        _project_card(project),
        _source_assets_card(manifest),
        *build_content_cards(manifest),
        _asset_test_card(_latest(action_jobs, "asset_test_run"), store),
        _review_card(manifest, _latest(action_jobs, "record_feedback")),
        _style_memory_card(manifest),
        _next_round_card(_latest(action_jobs, "two_round_validate"), store),
        _provider_card(provider_gate),
    ]
    return cards, provider_gate


def build_workbench_events(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": f"job:{index}:{job.get('job_id')}",
            "title": _event_title(job),
            "action": job.get("action"),
            "status": _status(job),
            "job_id": job.get("job_id"),
            "artifact_ids": _artifact_ids(job),
        }
        for index, job in enumerate(jobs, start=1)
    ]


def _project_card(project: dict[str, Any]) -> dict[str, Any]:
    return _card(
        "project",
        "project",
        "项目",
        "succeeded",
        project.get("goal") or "项目已就绪。",
        project.get("artifact_id"),
        ["open_project"],
        evidence={"artifact_ids": [project.get("artifact_id")]},
    )


def _source_assets_card(manifest: dict[str, Any]) -> dict[str, Any]:
    assets = manifest.get("source_assets", [])
    if isinstance(assets, list) and assets:
        return _card(
            "source-assets",
            "asset_collection",
            "素材与参考",
            "succeeded",
            f"已附加 {len(assets)} 条素材摘要。",
            None,
            ["add_reference"],
            refs=[
                {
                    "label": str(item.get("label") or item.get("asset_id") or "asset"),
                    "artifact_id": str(item.get("asset_id") or ""),
                    "artifact_type": str(item.get("asset_type") or "safe_summary"),
                    "summary": str(item.get("summary") or ""),
                }
                for item in assets
                if isinstance(item, dict)
            ],
        )
    return _card(
        "source-assets",
        "asset_collection",
        "素材与参考",
        "blocked",
        "真实生成前先添加脚本、需求、参考或项目素材摘要。",
        None,
        ["add_reference"],
        blockers=[
            _blocker(
                "source_assets_missing",
                "添加项目素材、参考、脚本或需求摘要。",
                user_action="add_reference",
                source="project_setup",
            )
        ],
    )

def _asset_test_card(job: dict[str, Any] | None, store: RuntimeStore) -> dict[str, Any]:
    if not job:
        return _card(
            "first-generation-check",
            "generation_check",
            "首轮检查",
            "ready_not_run",
            "可以运行首轮确定性内容检查。",
            None,
            ["start_first_generation_check"],
        )
    report_ref = _artifact(job, "real_asset_test_report")
    report = _payload(store, report_ref)
    blocked = _status(job) == "blocked"
    return _card(
        "first-generation-check",
        "generation_check",
        "首轮检查",
        _status(job),
        _summary(report, "首轮检查已有运行证据。"),
        _artifact_id(report_ref),
        ["add_project_materials", "open_advanced_details"] if blocked else ["record_review_note"],
        blockers=_blockers(report.get("blocks"), source="first_generation_check"),
        evidence=_evidence(job),
    )


def _review_card(manifest: dict[str, Any], feedback_job: dict[str, Any] | None) -> dict[str, Any]:
    refs = _list(manifest.get("feedback_refs"))
    if not refs:
        return _card("review", "review", "审片记录", "not_started", "尚未记录审片反馈。", None, ["record_review_note"])
    return _card(
        "review",
        "review",
        "审片记录",
        "succeeded",
        f"已记录 {len(refs)} 条审片证据引用。",
        refs[-1].get("artifact_id"),
        ["record_review_note", "start_next_round"],
        evidence=_evidence(feedback_job) if feedback_job else {"artifact_ids": [item.get("artifact_id") for item in refs]},
    )


def _style_memory_card(manifest: dict[str, Any]) -> dict[str, Any]:
    refs = _list(manifest.get("profile_version_refs"))
    if not refs:
        return _card("style-memory", "style_memory", "项目风格记忆", "not_started", "尚未应用项目风格记忆。", None, [])
    return _card(
        "style-memory",
        "style_memory",
        "项目风格记忆",
        "succeeded",
        "已审片的项目风格档案可用于复用。",
        refs[-1].get("artifact_id"),
        ["start_next_round"],
        evidence={"artifact_ids": [item.get("artifact_id") for item in refs]},
    )


def _next_round_card(job: dict[str, Any] | None, store: RuntimeStore) -> dict[str, Any]:
    if not job:
        return _card("next-round", "next_round", "下一轮", "not_started", "尚未运行下一轮验证。", None, ["start_next_round"])
    report_ref = _artifact(job, "two_round_context_runtime_report")
    report = _payload(store, report_ref)
    return _card(
        "next-round",
        "next_round",
        "下一轮",
        _status(job),
        _summary(report, "下一轮已有运行证据。"),
        _artifact_id(report_ref),
        ["open_advanced_details"],
        blockers=_blockers(report.get("blocked_refs"), source="next_round"),
        evidence=_evidence(job),
    )


def _provider_gate(job: dict[str, Any] | None, store: RuntimeStore) -> dict[str, Any]:
    if not job:
        return {
            "status": "ready_not_run",
            "title": "Provider 预检",
            "summary": "Provider 预检尚未运行。",
            "primary_artifact_id": None,
            "blockers": [],
            "actions": ["run_provider_preflight"],
            "evidence": {"job_id": None, "artifact_ids": []},
        }
    gate_summary = dict(dict(job.get("ui_summary", {})).get("provider_gate", {}))
    manifest_ref = _artifact(job, "provider_safe_manifest")
    manifest = _payload(store, manifest_ref)
    blockers = gate_summary.get("blockers") or manifest.get("blockers") or manifest.get("blocks")
    return {
        "status": _status(job),
        "title": "Provider 预检",
        "summary": "Provider 预检已返回安全闸门证据。",
        "primary_artifact_id": _artifact_id(manifest_ref),
        "blockers": _blockers(blockers, source="provider_preflight"),
        "actions": ["run_provider_preflight", "open_advanced_details"],
        "evidence": _evidence(job),
    }


def _provider_card(provider_gate: dict[str, Any]) -> dict[str, Any]:
    return _card(
        "provider-preflight",
        "provider_gate",
        "Provider 预检",
        str(provider_gate["status"]),
        str(provider_gate["summary"]),
        provider_gate.get("primary_artifact_id"),
        list(provider_gate.get("actions", [])),
        blockers=_list(provider_gate.get("blockers")),
        evidence=dict(provider_gate.get("evidence", {})),
    )

__all__ = ("NAVIGATION", "NON_CLAIMS", "SAFE_REF_POLICY", "build_workbench_cards", "build_workbench_events")
