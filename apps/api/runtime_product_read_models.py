from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_store import RuntimeStore


ROLE_LABELS = {
    "screenwriter": "编剧组",
    "storyboard": "分镜组",
    "art": "美术组",
    "director": "导演组",
    "continuity": "连贯性检查",
    "qa": "质量审核",
    "audio": "音频组",
    "edit": "后期组",
    "export": "交付组",
}

STAGES = (
    ("brief", "创作简报"),
    ("script", "剧本"),
    ("canon", "角色/场景设定"),
    ("storyboard", "分镜"),
    ("visual", "画面"),
    ("av", "视频/音频"),
    ("decision", "主创决策"),
    ("quality", "质量审核"),
    ("delivery", "交付"),
)


def register_runtime_product_read_model_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    @app.get("/product/workspace-overview", tags=["product"])
    def workspace_overview(request: Request) -> dict[str, Any]:
        user_id = _require_user(auth, request)
        summaries = auth.filter_project_summaries(user_id, store.list_project_summaries())
        projects = [_project_overview(store, summary, user_id=user_id) for summary in summaries]
        projects.sort(key=lambda item: (str(item.get("updated_at") or ""), item["project_id"]), reverse=True)
        return {
            "schema_version": "afs_product_workspace_overview.v0.1",
            "locale": "zh-CN",
            "workspace": {
                "label": "内容制作工作空间",
                "project_count": len(projects),
                "active_project_count": sum(item["status"] != "已交付" for item in projects),
            },
            "projects": projects,
            "decision_count": sum(item["decision_inbox"]["pending_count"] for item in projects),
            "blocked_count": sum(item["crew"]["blocked_count"] for item in projects),
        }

    @app.get("/projects/{project_id}/product-overview", tags=["product"])
    def project_overview(project_id: str, request: Request) -> dict[str, Any]:
        user_id = _require_project_owner(store, auth, request, project_id)
        summary = next(
            (item for item in store.list_project_summaries() if str(item.get("project_id") or "") == project_id),
            None,
        )
        if not summary:
            raise HTTPException(status_code=404, detail="项目不存在或已被移除。")
        return {
            "schema_version": "afs_product_project_overview.v0.1",
            "locale": "zh-CN",
            "project": _project_overview(store, summary, user_id=user_id, expanded=True),
        }


def _require_user(auth: RuntimeAuthStore, request: Request) -> str:
    if not auth.enabled():
        raise HTTPException(status_code=403, detail="产品工作空间需要登录后访问。")
    user_id = str(auth.require_user(request).get("user_id") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录。")
    return user_id


def _require_project_owner(
    store: RuntimeStore,
    auth: RuntimeAuthStore,
    request: Request,
    project_id: str,
) -> str:
    user_id = _require_user(auth, request)
    if (
        not project_id
        or store.is_project_deleted(project_id)
        or not store.project_manifest_path(project_id).is_file()
        or not auth.user_can_access_project(user_id, project_id)
    ):
        raise HTTPException(status_code=403, detail="你没有访问该项目的权限。")
    return user_id


def _project_overview(
    store: RuntimeStore,
    summary: dict[str, Any],
    *,
    user_id: str,
    expanded: bool = False,
) -> dict[str, Any]:
    project_id = str(summary.get("project_id") or "")
    manifest = store.ensure_project_manifest(project_id)
    crew = _owned_crew(store, project_id, user_id)
    runs = [
        item for item in store.list_production_runs(project_id)
        if str(item.get("owner_user_id") or "") == user_id
    ]
    latest_run = max(runs, key=lambda item: str(item.get("updated_at") or ""), default={})
    studio_meta = _studio_meta(store, project_id)
    coverage = _canonical_coverage(latest_run)
    decisions = _decision_inbox(crew, latest_run)
    crew_summary = _crew_summary(crew)
    delivery = _delivery_summary(latest_run)
    jobs = _job_summary(store, project_id)
    stages = _stage_progress(manifest, crew, latest_run, coverage, decisions, delivery)
    completed = sum(item["state"] == "completed" for item in stages)
    progress = round((completed / len(stages)) * 100) if stages else 0
    result: dict[str, Any] = {
        "project_id": project_id,
        "name": str(studio_meta.get("projectName") or summary.get("goal") or "未命名项目"),
        "episode": _episode_label(latest_run),
        "status": _localized_project_status(str(summary.get("status") or ""), delivery),
        "updated_at": str(studio_meta.get("updated_at") or latest_run.get("updated_at") or ""),
        "progress_percent": progress,
        "current_stage": next((item["label"] for item in stages if item["state"] == "in_progress"), "待开始"),
        "next_action": _next_action(stages, decisions, crew_summary),
        "decision_inbox": decisions,
        "crew": crew_summary,
        "canonical_state": coverage,
        "delivery": delivery,
        "jobs": jobs,
    }
    if expanded:
        result["stages"] = stages
        result["recovery"] = {
            "reload_safe": True,
            "last_saved_at": str(studio_meta.get("saved_at") or latest_run.get("updated_at") or ""),
            "message": "项目状态来自已登录账户的持久化记录。",
        }
    return result


def _owned_crew(store: RuntimeStore, project_id: str, user_id: str) -> dict[str, Any]:
    try:
        crew = store.load_domain_crew(project_id)
    except KeyError:
        return {}
    if str(crew.get("owner_user_id") or "") != user_id:
        return {}
    return crew


def _studio_meta(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = store.projects_dir / project_id / "studio_state.json"
    if not path.is_file():
        return {}
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    return {
        "projectName": _safe_text(meta.get("projectName"), 100),
        "updated_at": _safe_text(meta.get("updated_at"), 80),
        "saved_at": _safe_text(payload.get("saved_at"), 80),
    }


def _decision_inbox(crew: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    conflicts = [item for item in crew.get("conflicts") or [] if isinstance(item, dict)]
    pending_conflicts = [item for item in conflicts if str(item.get("status") or "") not in {"resolved_by_creator", "closed"}]
    reconfirmations = [item for item in crew.get("propagation_reconfirmations") or [] if isinstance(item, dict)]
    pending_reconfirmations = [item for item in reconfirmations if item.get("reconfirmation_status") == "required_pending"]
    selected = run.get("selected_revision") if isinstance(run.get("selected_revision"), dict) else {}
    candidates = [item for item in run.get("candidates") or [] if isinstance(item, dict)]
    candidate_review_pending = bool(candidates and not selected)
    items = [
        {
            "kind": "creator_decision",
            "title": _safe_text(item.get("reason"), 120) or "创作冲突需要主创决定",
            "priority": "high",
            "action_label": "查看影响",
        }
        for item in pending_conflicts[:4]
    ]
    if candidate_review_pending:
        items.append({
            "kind": "candidate_review",
            "title": "候选版本等待主创审核",
            "priority": "normal",
            "action_label": "进入审核",
        })
    return {
        "pending_count": len(items),
        "reconfirmation_count": len(pending_reconfirmations),
        "items": items,
    }


def _crew_summary(crew: dict[str, Any]) -> dict[str, Any]:
    agents = [item for item in crew.get("agents") or [] if isinstance(item, dict)]
    tasks = [item for item in crew.get("tasks") or [] if isinstance(item, dict)]
    handoffs = [item for item in crew.get("handoffs") or [] if isinstance(item, dict)]
    blocked_states = {"blocked", "blocked_human", "revision_required", "reconfirmation_required"}
    blocked = [item for item in tasks if str(item.get("status") or "") in blocked_states]
    active = [item for item in tasks if str(item.get("status") or "") in {"ready", "claimed", "reconfirmation_required"}]
    role_by_agent = {str(item.get("agent_id") or ""): str(item.get("role") or "") for item in agents}
    activities = []
    for task in active[:6]:
        role = role_by_agent.get(str(task.get("assigned_agent_id") or ""), "")
        activities.append({
            "role": ROLE_LABELS.get(role, "数字剧组"),
            "responsibility": _safe_text(task.get("objective"), 140) or "等待下一步制作任务",
            "state": _localized_task_status(str(task.get("status") or "")),
        })
    return {
        "registered_role_count": len({item.get("role") for item in agents if item.get("role")}),
        "active_count": len(active),
        "blocked_count": len(blocked),
        "pending_handoff_count": sum(item.get("status") == "pending_receiver" for item in handoffs),
        "activities": activities,
    }


def _canonical_coverage(run: dict[str, Any]) -> dict[str, Any]:
    binding = run.get("representative_episode_binding") if isinstance(run.get("representative_episode_binding"), dict) else {}
    counts = binding.get("counts") if isinstance(binding.get("counts"), dict) else {}
    readiness = binding.get("asset_readiness") if isinstance(binding.get("asset_readiness"), dict) else {}
    return {
        "characters": int(counts.get("characters") or 0),
        "scenes": int(counts.get("scenes") or 0),
        "shots": int(counts.get("shots") or 0),
        "audio_items": int(counts.get("audio_items") or 0),
        "pending_media_count": int(readiness.get("pending_media_count") or 0),
        "all_assets_ready": readiness.get("all_assets_ready") is True,
        "propagation_complete": binding.get("propagation_complete") is True,
    }


def _delivery_summary(run: dict[str, Any]) -> dict[str, Any]:
    reviews = [item for item in run.get("quality_reviews") or [] if isinstance(item, dict)]
    exports = [item for item in run.get("exports") or [] if isinstance(item, dict)]
    selected = run.get("selected_revision") if isinstance(run.get("selected_revision"), dict) else {}
    approved = bool(reviews and str(reviews[-1].get("decision") or reviews[-1].get("status") or "") in {"approve", "approved", "passed"})
    return {
        "candidate_selected": bool(selected),
        "quality_reviewed": bool(reviews),
        "quality_approved": approved,
        "export_ready": bool(selected and approved),
        "delivered": bool(exports),
        "export_count": len(exports),
        "message": "已生成交付记录" if exports else "等待质量审核与主创批准" if selected else "等待选择候选版本",
    }


def _job_summary(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    jobs = store.list_project_jobs(project_id)
    running = sum(str(item.get("status") or "") in {"queued", "running", "polling"} for item in jobs)
    failed = sum(str(item.get("status") or "") in {"failed", "cancelled"} for item in jobs)
    return {
        "total_count": len(jobs),
        "running_count": running,
        "attention_count": failed,
        "cost_observability": "unavailable",
        "cost_message": "供应商成本以可核对账单为准。",
    }


def _stage_progress(
    manifest: dict[str, Any],
    crew: dict[str, Any],
    run: dict[str, Any],
    coverage: dict[str, Any],
    decisions: dict[str, Any],
    delivery: dict[str, Any],
) -> list[dict[str, str]]:
    tasks = [item for item in crew.get("tasks") or [] if isinstance(item, dict)]
    actions = {str(item.get("action") or ""): str(item.get("status") or "") for item in tasks}
    completed_actions = {key for key, status in actions.items() if status == "completed"}
    started_actions = set(actions)
    candidate_ready = bool(run.get("candidates"))
    completed = {
        "brief": bool(manifest.get("goal")),
        "script": "script.write" in completed_actions,
        "canon": bool(coverage["characters"] or coverage["scenes"]),
        "storyboard": "storyboard.compose" in completed_actions or coverage["shots"] > 0,
        "visual": candidate_ready,
        "av": "edit.assemble" in completed_actions,
        "decision": decisions["pending_count"] == 0 and delivery["candidate_selected"],
        "quality": delivery["quality_reviewed"],
        "delivery": delivery["delivered"],
    }
    started = {
        "script": "script.write" in started_actions,
        "canon": "art.create" in started_actions,
        "storyboard": "storyboard.compose" in started_actions,
        "visual": candidate_ready,
        "av": bool({"audio.produce", "edit.assemble"} & started_actions),
        "decision": decisions["pending_count"] > 0 or delivery["candidate_selected"],
        "quality": delivery["quality_reviewed"],
        "delivery": delivery["export_ready"],
    }
    first_open_seen = False
    result = []
    for key, label in STAGES:
        if completed.get(key):
            state = "completed"
        elif started.get(key) or not first_open_seen:
            state = "in_progress"
            first_open_seen = True
        else:
            state = "not_started"
        result.append({"key": key, "label": label, "state": state})
    return result


def _next_action(stages: list[dict[str, str]], decisions: dict[str, Any], crew: dict[str, Any]) -> str:
    if decisions["pending_count"]:
        return f"处理 {decisions['pending_count']} 项主创决策"
    if crew["blocked_count"]:
        return f"解除 {crew['blocked_count']} 项制作阻塞"
    current = next((item for item in stages if item["state"] == "in_progress"), None)
    return f"继续{current['label']}" if current else "检查交付准备度"


def _episode_label(run: dict[str, Any]) -> str:
    binding = run.get("representative_episode_binding") if isinstance(run.get("representative_episode_binding"), dict) else {}
    return _safe_text(binding.get("episode_title"), 100) or "第 01 集"


def _localized_project_status(status: str, delivery: dict[str, Any]) -> str:
    if delivery["delivered"]:
        return "已交付"
    return {
        "completed": "已完成",
        "in_progress": "制作中",
        "blocked": "有阻塞",
        "draft": "准备中",
    }.get(status, "制作中")


def _localized_task_status(status: str) -> str:
    return {
        "ready": "待开始",
        "claimed": "进行中",
        "completed": "已完成",
        "revision_required": "待修改",
        "reconfirmation_required": "待重新确认",
    }.get(status, "待处理")


def _safe_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


__all__ = ("register_runtime_product_read_model_routes",)
