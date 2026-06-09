from __future__ import annotations

from typing import Any

from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_workbench_support import artifact, artifact_id, jobs_by_action, latest, list_value, payload, status, summary


def build_review_room(store: RuntimeStore, manifest: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = _review_decisions(store, manifest)
    candidates = [
        *_planned_candidates(manifest),
        *_runtime_candidates(store, jobs),
    ]
    return {
        "status": "ready" if candidates else "not_started",
        "title": "审片室",
        "summary": _summary(candidates, decisions),
        "candidates": [_with_decision(candidate, decisions) for candidate in candidates],
        "decision_counts": _decision_counts(decisions),
        "latest_decisions": decisions[-5:],
        "non_claims": ["not human acceptance", "not durable memory", "not business validation"],
    }


def _planned_candidates(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for index, item in enumerate(list_value(manifest.get("content_cards")), start=1):
        if not isinstance(item, dict):
            continue
        card_id = str(item.get("card_id") or f"scene-{index}")
        candidates.append(
            {
                "candidate_id": f"{card_id}:planned",
                "card_id": card_id,
                "stage": "planned_scene",
                "label": "规划",
                "title": str(item.get("title") or f"场景 {index}"),
                "status": str(item.get("status") or "ready_not_run"),
                "summary": str(item.get("summary") or "场景卡片已可审片。"),
                "artifact_id": "",
                "artifact_type": str(item.get("card_type") or "scene"),
                "compare_points": [
                    f"目标：{_target_platform(item.get('target_platform'))}",
                    "生成前可通过场景检查器继续编辑。",
                ],
            }
        )
    return candidates


def _runtime_candidates(store: RuntimeStore, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = jobs_by_action(jobs)
    round_1 = _candidate_from_job(
        store,
        latest(grouped, "asset_test_run"),
        role="real_asset_test_report",
        stage="first_generation_check",
        label="首轮",
        title="首轮检查",
    )
    round_2 = _candidate_from_job(
        store,
        latest(grouped, "two_round_validate"),
        role="two_round_context_runtime_report",
        stage="next_round",
        label="第二轮",
        title="下一轮",
    )
    return [candidate for candidate in (round_1, round_2) if candidate]


def _candidate_from_job(
    store: RuntimeStore,
    job: dict[str, Any] | None,
    *,
    role: str,
    stage: str,
    label: str,
    title: str,
) -> dict[str, Any] | None:
    if not job:
        return None
    ref = artifact(job, role)
    artifact_payload = payload(store, ref)
    blockers = artifact_payload.get("blocks") or artifact_payload.get("blocked_refs") or []
    return {
        "candidate_id": f"{job.get('job_id')}:{stage}",
        "card_id": str(stage),
        "stage": stage,
        "label": label,
        "title": title,
        "status": status(job),
        "summary": summary(artifact_payload, f"{title}已有运行证据。"),
        "artifact_id": artifact_id(ref) or "",
        "artifact_type": str((ref or {}).get("artifact_type") or role),
        "compare_points": _compare_points(stage, artifact_payload, blockers),
    }


def _compare_points(stage: str, artifact_payload: dict[str, Any], blockers: Any) -> list[str]:
    points = []
    if stage == "first_generation_check":
        provider_state = "未启动" if artifact_payload.get("provider_calls_started") is not True else "已启动"
        points.append(f"Provider 调用：{provider_state}")
    if stage == "next_round":
        points.append(f"验证：{artifact_payload.get('runtime_verification_status') or '未知'}")
        points.append(f"评估：{artifact_payload.get('improvement_assessment') or '未知'}")
    blocker_count = len(blockers) if isinstance(blockers, list) else 0
    points.append(f"阻塞项：{blocker_count}")
    return points


def _target_platform(value: Any) -> str:
    labels = {"short_video": "短视频", "product_launch": "产品发布"}
    text = str(value or "short_video")
    return labels.get(text, text)


def _review_decisions(store: RuntimeStore, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for ref in list_value(manifest.get("feedback_refs")):
        if not isinstance(ref, dict) or not ref.get("artifact_id"):
            continue
        try:
            artifact_payload = store.read_artifact(str(ref["artifact_id"])).get("payload", {})
        except (KeyError, ValueError):
            continue
        if not isinstance(artifact_payload, dict) or artifact_payload.get("artifact_type") != "agentflow_runtime_review_decision":
            continue
        decisions.append(
            {
                "review_id": str(artifact_payload.get("review_id") or ref.get("feedback_id") or ""),
                "card_id": str(artifact_payload.get("card_id") or ""),
                "candidate_id": str(artifact_payload.get("candidate_id") or ""),
                "artifact_id": str(artifact_payload.get("artifact_id") or ref.get("artifact_id") or ""),
                "decision": str(artifact_payload.get("decision") or ""),
                "note": str(artifact_payload.get("note") or ""),
                "generated_at": str(artifact_payload.get("generated_at") or ""),
            }
        )
    return decisions


def _with_decision(candidate: dict[str, Any], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_id = candidate["candidate_id"]
    card_id = candidate["card_id"]
    matches = [item for item in decisions if item.get("candidate_id") == candidate_id or item.get("card_id") == card_id]
    if not matches:
        return {**candidate, "latest_decision": ""}
    return {**candidate, "latest_decision": matches[-1]["decision"], "latest_decision_note": matches[-1]["note"]}


def _decision_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"keep": 0, "revise": 0, "reject": 0}
    for item in decisions:
        decision = item.get("decision")
        if decision in counts:
            counts[decision] += 1
    return counts


def _summary(candidates: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> str:
    if not candidates:
        return "先添加场景卡片并运行检查，再进入审片。"
    if decisions:
        return f"{len(candidates)} 个候选结果，已记录 {len(decisions)} 条审片决定。"
    return f"{len(candidates)} 个候选结果可审片。"


__all__ = ("build_review_room",)
