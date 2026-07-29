from __future__ import annotations

from typing import Any, Mapping

from apps.api.runtime_production_graph import ProductionGraphError, impacted_descendants
from apps.api.runtime_studio_safety import safe_identifier, safe_text


def allowed_actions(
    surface: str,
    *,
    entities: list[Mapping[str, Any]],
    reviews: list[Mapping[str, Any]],
    artifacts: list[Mapping[str, Any]],
    rework_preview: Mapping[str, Any],
    delivery: Mapping[str, Any],
) -> list[dict[str, Any]]:
    focused_entity_id = safe_identifier(
        entities[0].get("entity_id") if entities else ""
    )
    actions = [
        _action(
            "inspect_entity",
            enabled=bool(focused_entity_id),
            target_entity_id=focused_entity_id,
            reason=(
                "查看当前对象的安全摘要。"
                if focused_entity_id
                else "当前工作面没有可检查对象。"
            ),
        ),
        _action(
            "open_agent_context",
            enabled=True,
            target_entity_id=focused_entity_id,
            reason="打开与当前项目版本绑定的创作助手上下文。",
        ),
    ]
    if surface == "canvas":
        actions.append(
            _action(
                "inspect_lineage",
                enabled=bool(focused_entity_id),
                target_entity_id=focused_entity_id,
                reason=(
                    "查看 ProductionGraph 来源与影响关系。"
                    if focused_entity_id
                    else "当前没有可追溯对象。"
                ),
            )
        )
    if surface == "script":
        storyboard_target = _first_entity_id(entities, ("unit", "location", "collection"))
        actions.append(
            _action(
                "continue_to_storyboard",
                enabled=bool(storyboard_target),
                target_entity_id=storyboard_target,
                reason=(
                    "沿当前剧本拆解进入分镜排布。"
                    if storyboard_target
                    else "当前项目尚未形成可进入分镜的剧本拆解。"
                ),
            )
        )
    if surface == "storyboard":
        asset_target = _first_entity_id(entities, ("entity", "resource", "location"))
        actions.append(
            _action(
                "continue_to_asset_bible",
                enabled=bool(asset_target),
                target_entity_id=asset_target,
                reason=(
                    "检查当前镜头依赖的角色、场景和道具设定。"
                    if asset_target
                    else "当前分镜还没有绑定可检查的资产设定。"
                ),
            )
        )
    if surface == "asset-bible":
        canvas_target = _first_entity_id(entities, ("unit", "location", "entity", "resource"))
        actions.append(
            _action(
                "return_to_canvas",
                enabled=bool(canvas_target),
                target_entity_id=canvas_target,
                reason=(
                    "带着当前资产上下文回到制作画布。"
                    if canvas_target
                    else "当前资产设定还没有可回到制作画布的对象。"
                ),
            )
        )
    if surface == "review":
        review_target = safe_identifier(
            reviews[0].get("target_entity_id") if reviews else ""
        )
        actions.extend(
            [
                _action(
                    "inspect_candidate",
                    enabled=bool(review_target and artifacts),
                    target_entity_id=review_target,
                    reason=(
                        "检查候选及其审核证据。"
                        if review_target and artifacts
                        else "尚无同时具备审核目标和候选证据的对象。"
                    ),
                ),
                _action(
                    "preview_rework",
                    enabled=bool(rework_preview.get("available")),
                    requires_preview=True,
                    target_entity_id=safe_identifier(
                        rework_preview.get("target_entity_id")
                    ),
                    reason=safe_text(rework_preview.get("reason"), 240),
                ),
            ]
        )
    if surface == "delivery":
        delivery_version_id = safe_identifier(delivery.get("delivery_version_id"))
        actions.append(
            _action(
                "inspect_delivery_version",
                enabled=bool(delivery_version_id),
                target_entity_id=delivery_version_id,
                reason=(
                    "检查当前交付事实与阻塞项。"
                    if delivery_version_id
                    else "尚未形成交付版本。"
                ),
            )
        )
    return actions


def _first_entity_id(
    entities: list[Mapping[str, Any]],
    entity_types: tuple[str, ...],
) -> str:
    for entity_type in entity_types:
        target = next(
            (
                safe_identifier(item.get("entity_id"))
                for item in entities
                if str(item.get("entity_type") or "") == entity_type
            ),
            "",
        )
        if target:
            return target
    return ""


def surface_summary(
    *,
    surface: str,
    entities: list[Mapping[str, Any]],
    reviews: list[Mapping[str, Any]],
    tasks: list[Mapping[str, Any]],
    delivery: Mapping[str, Any],
) -> dict[str, Any]:
    pending_reviews = [
        item
        for item in reviews
        if str(item.get("state") or "") in {"pending", "rejected"}
    ]
    attention_tasks = [
        item
        for item in tasks
        if str(item.get("state") or "")
        in {"dispatched", "submission_unknown", "reconcile_required"}
    ]
    attention_count = len(pending_reviews) + len(attention_tasks)
    if surface == "delivery" and int(delivery.get("blocker_count") or 0) > 0:
        state = "blocked"
        headline = f"{int(delivery.get('blocker_count') or 0)} 项阻塞待处理"
    elif attention_tasks:
        state = "attention"
        headline = "存在远端任务需要安全对账"
    elif pending_reviews:
        state = "attention"
        headline = f"{len(pending_reviews)} 项内容等待审核"
    elif entities:
        state = "ready"
        headline = "当前工作面已从 ProductionGraph 投影"
    else:
        state = "empty"
        headline = "当前工作面尚无可显示对象"
    return {
        "state": state,
        "headline": headline,
        "entity_count": len(entities),
        "attention_count": attention_count,
    }


def resume_target(
    *,
    surface: str,
    entities: list[Mapping[str, Any]],
    reviews: list[Mapping[str, Any]],
    recovery: Mapping[str, Any],
) -> dict[str, Any]:
    if recovery.get("attention_required"):
        return {
            "available": True,
            "surface": "delivery",
            "entity_id": "",
            "reason": safe_text(recovery.get("message"), 240),
        }
    pending_review = next(
        (
            item
            for item in reviews
            if str(item.get("state") or "") in {"pending", "rejected"}
        ),
        None,
    )
    if pending_review:
        return {
            "available": True,
            "surface": "review",
            "entity_id": safe_identifier(pending_review.get("target_entity_id")),
            "reason": "继续处理当前最优先的审核决定。",
        }
    if entities:
        return {
            "available": True,
            "surface": surface,
            "entity_id": safe_identifier(entities[0].get("entity_id")),
            "reason": "继续查看当前工作面的第一个制作对象。",
        }
    return {
        "available": False,
        "surface": surface,
        "entity_id": "",
        "reason": "当前没有可恢复的制作位置。",
    }


def focused_entity(
    entities: list[dict[str, Any]],
    resume: Mapping[str, Any],
) -> dict[str, Any] | None:
    resume_id = str(resume.get("entity_id") or "")
    if resume_id:
        for entity in entities:
            if str(entity.get("entity_id") or "") == resume_id:
                return entity
    return entities[0] if entities else None


def agent_summary(
    project_version: int,
    resume: Mapping[str, Any],
    recovery: Mapping[str, Any],
) -> dict[str, Any]:
    if recovery.get("attention_required"):
        state = "attention_required"
        headline = "有任务需要对账；不会自动重复派发。"
    elif resume.get("available"):
        state = "suggestion_available"
        headline = safe_text(resume.get("reason"), 240)
    else:
        state = "collapsed"
        headline = "创作助手已收起。"
    return {
        "state": state,
        "based_on_project_version": max(0, project_version),
        "entity_id": safe_identifier(resume.get("entity_id")),
        "headline": headline,
    }


def rework_preview(
    surface: str,
    reviews: list[Mapping[str, Any]],
    graph: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    target_id = ""
    if surface == "review" and graph is not None:
        target_id = next(
            (
                safe_identifier(relation.get("from_id"))
                for relation in graph.get("relations", [])
                if isinstance(relation, Mapping)
                and str(relation.get("relation_type") or "")
                == "pending_video_candidate"
                and _is_reworkable_unit(graph, relation.get("from_id"))
            ),
            "",
        )
    if surface == "review" and not target_id and graph is not None:
        pending_review = next(
            (
                item
                for item in reviews
                if str(item.get("state") or "") in {"pending", "rejected"}
            ),
            None,
        )
        if pending_review and _is_reworkable_unit(
            graph,
            pending_review.get("target_entity_id"),
        ):
            target_id = safe_identifier(pending_review.get("target_entity_id"))
    impact_refs: list[str] = []
    keep_refs: list[str] = []
    if target_id and graph is not None:
        if _has_planned_rework(graph, target_id):
            return {
                "available": False,
                "target_entity_id": target_id,
                "impact_refs": [],
                "keep_refs": [],
                "cost_available": False,
                "reason": "该镜头已有待执行的局部返工任务。",
            }
        try:
            impact = impacted_descendants(graph, [target_id])
        except ProductionGraphError:
            target_id = ""
        else:
            impact_refs = [
                safe_ref
                for value in impact.get("invalidated_node_ids", [])
                if (safe_ref := safe_identifier(value))
            ]
            keep_refs = [
                safe_ref
                for value in impact.get("preserved_node_ids", [])
                if (safe_ref := safe_identifier(value))
            ]
    return {
        "available": bool(target_id),
        "target_entity_id": target_id,
        "impact_refs": impact_refs,
        "keep_refs": keep_refs,
        "cost_available": False,
        "reason": (
            "可以生成绑定当前项目版本的局部返工影响预览；费用尚未接入。"
            if target_id
            else "当前没有可预览局部返工的审核目标。"
        ),
    }


def _is_reworkable_unit(
    graph: Mapping[str, Any],
    entity_id: Any,
) -> bool:
    node = graph.get("nodes", {}).get(str(entity_id or ""))
    return bool(
        isinstance(node, Mapping)
        and node.get("category") == "unit"
        and node.get("state") != "invalidated"
    )


def _has_planned_rework(
    graph: Mapping[str, Any],
    target_entity_id: str,
) -> bool:
    prefix = f"rework-{target_entity_id}-v"
    return any(
        str(work_id).startswith(prefix)
        and isinstance(work, Mapping)
        and str(work.get("state") or "") == "planned"
        for work_id, work in graph.get("work", {}).items()
    )


def delivery_summary(
    graph: Mapping[str, Any] | None,
    reviews: list[Mapping[str, Any]],
    tasks: list[Mapping[str, Any]],
) -> dict[str, Any]:
    deliveries = (
        graph.get("deliveries")
        if graph is not None and isinstance(graph.get("deliveries"), Mapping)
        else {}
    )
    delivery_id, delivery_record = next(iter(deliveries.items()), ("", {}))
    delivery_state = (
        safe_identifier(delivery_record.get("state"), 80)
        if isinstance(delivery_record, Mapping)
        else ""
    )
    blocking_reviews = [
        item
        for item in reviews
        if str(item.get("state") or "") in {"pending", "rejected"}
    ]
    blocking_tasks = [
        item
        for item in tasks
        if str(item.get("state") or "")
        not in {"succeeded", "complete", "completed", "adopted"}
    ]
    blocker_count = len(blocking_reviews) + len(blocking_tasks)
    if not delivery_id:
        state = "empty"
    elif blocker_count:
        state = "blocked"
    elif delivery_state in {"delivered", "published"}:
        state = "delivered"
    elif delivery_state in {"ready", "approved"}:
        state = "ready"
    else:
        state = "review_ready"
    approved_video_count = 0
    if graph is not None:
        approved_video_count = sum(
            1
            for relation in graph.get("relations", [])
            if isinstance(relation, Mapping)
            and str(relation.get("relation_type") or "") == "approved_video"
        )
    return {
        "state": state,
        "blocker_count": blocker_count,
        "delivery_version_id": safe_identifier(delivery_id),
        "playable": bool(
            approved_video_count
            and state in {"review_ready", "ready", "delivered"}
        ),
    }


def _action(
    action: str,
    *,
    enabled: bool,
    target_entity_id: str = "",
    reason: str,
    requires_preview: bool = False,
) -> dict[str, Any]:
    return {
        "action": action,
        "enabled": enabled,
        "requires_preview": requires_preview,
        "target_entity_id": safe_identifier(target_entity_id),
        "reason": safe_text(reason, 240),
    }


__all__ = (
    "agent_summary",
    "allowed_actions",
    "delivery_summary",
    "focused_entity",
    "resume_target",
    "rework_preview",
    "surface_summary",
)
