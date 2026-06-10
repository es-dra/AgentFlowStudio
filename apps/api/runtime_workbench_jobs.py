from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import artifact_ids, event_title, status


def build_job_center(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    items = [_job_item(job) for job in jobs]
    counts = _counts(items)
    return {
        "status": _center_status(counts),
        "title": "任务中心",
        "summary": _summary(counts),
        "counts": counts,
        "items": items,
        "polling": {
            "enabled": True,
            "manual_refresh_action": "refresh",
            "suggested_interval_ms": 5000,
            "scope": "current_project_jobs",
        },
        "non_claims": ["runtime verification is not human acceptance", "provider preflight is not provider smoke"],
    }


def _job_item(job: dict[str, Any]) -> dict[str, Any]:
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    ids = artifact_ids(job)
    item_status = status(job)
    return {
        "job_id": str(job.get("job_id") or ""),
        "action": str(job.get("action") or "runtime_event"),
        "title": event_title(job),
        "status": item_status,
        "stage": str(progress.get("stage") or job.get("action") or ""),
        "percent": int(progress.get("percent") or 0),
        "terminal": progress.get("terminal") is True,
        "primary_artifact_id": ids[0] if ids else "",
        "artifact_ids": ids,
        "artifact_count": len(ids),
        "guidance": _guidance(str(job.get("action") or ""), item_status, str(job.get("error") or "")),
    }


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(items), "running": 0, "blocked": 0, "failed": 0, "succeeded": 0}
    for item in items:
        item_status = item["status"]
        if item_status in counts:
            counts[item_status] += 1
    return counts


def _center_status(counts: dict[str, int]) -> str:
    if counts["failed"]:
        return "failed"
    if counts["blocked"]:
        return "blocked"
    if counts["running"]:
        return "running"
    if counts["succeeded"]:
        return "succeeded"
    return "not_started"


def _summary(counts: dict[str, int]) -> str:
    if not counts["total"]:
        return "暂无运行任务。"
    return (
        f"{counts['total']} 个任务：{counts['succeeded']} 个已完成，"
        f"{counts['blocked']} 个阻塞，{counts['failed']} 个失败。"
    )


def _guidance(action: str, item_status: str, error: str) -> str:
    if item_status == "failed":
        return error or "重试前先打开运行详情并检查错误。"
    if action == "provider_validation_plan" and item_status == "blocked":
        return "Provider 仍处于闸门关闭状态；真实模型试跑前必须显式授权对应能力。"
    if action == "llm_script_draft_plan" and item_status == "blocked":
        return "LLM 脚本纵切只创建了安全计划；真实文本 provider 试跑前必须显式启用 AFS_ALLOW_REMOTE_LLM。"
    if action == "asset_test_run" and item_status == "blocked":
        return "打开首轮检查报告，补齐缺失的项目素材后再重试。"
    if action == "two_round_validate" and item_status == "blocked":
        return "打开下一轮报告，处理被阻塞的上下文引用。"
    if action == "record_review_decision":
        return "审片决定只是证据，不会自动成为长期记忆。"
    if action == "record_feedback":
        return "原始反馈会作为证据保存，供后续审查。"
    if item_status == "succeeded":
        return "打开安全 artifact 查看生成证据。"
    return "刷新工作台以更新运行状态。"


__all__ = ("build_job_center",)
