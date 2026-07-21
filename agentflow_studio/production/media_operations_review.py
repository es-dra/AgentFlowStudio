from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from agentflow_studio.production.adaptive_canvas_v2 import load_adaptive_workspace


MEDIA_OPERATIONS_SCHEMA_VERSION = "afs.media_operations_review.v0.1"
COMMAND_PREVIEW_SCHEMA_VERSION = "afs.media_operations_command_preview.v0.1"
SAFE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")
PUBLIC_IMAGE_PRICE_USD = 0.0377
CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC = 0.25
DEFAULT_MEDIA_NEGATIVE_LOCKS = (
    "不出现烟雾、血腥、武器或明确伤害",
    "不出现品牌标识、可读文字或版权角色风格",
    "不使用名人脸或可识别真实人物肖像",
    "不改变已确认人物服装色块、空间布局、道具归属和灯光方向",
)
MEDIA_TYPES = {
    "reference-sheet": (("reference_sheet.png",), "image/png"),
    "keyframe": (("keyframes", "{media_id}.png"), "image/png"),
    "shot-video": (("shot_composes", "{media_id}.mp4"), "video/mp4"),
    "final-video": (("final", "adaptive_canvas_v2_final.mp4"), "video/mp4"),
    "contact-sheet": (("qa", "contact_sheet_1fps.jpg"), "image/jpeg"),
}


def load_media_operations_review(
    store: Any,
    *,
    project_id: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    workspace = load_adaptive_workspace(store, project_id=project_id, run_id=run_id)
    resolved_run_id = str(workspace["run_id"])
    run_root = adaptive_run_root(store, project_id=project_id, run_id=resolved_run_id)
    script_truth = _read_optional_json(run_root / "script_truth.json")
    delivery = _read_optional_json(run_root / "delivery_manifest.json")
    qa = _read_optional_json(run_root / "qa" / "technical_qa.json")
    ledger = _read_optional_json(run_root / "charge_ledger.json")
    run_state = _read_optional_json(run_root / "run_state.json")

    shots = _shots(workspace, script_truth, project_id=project_id, run_id=resolved_run_id, ledger=ledger)
    scenes = _scenes(workspace, shots)
    assets = _assets(workspace, project_id=project_id, run_id=resolved_run_id)
    quality = _quality(qa)
    cost = _cost(workspace, ledger)
    recovery = _recovery(ledger, run_state)
    graph_digest = _digest(
        {
            "script": workspace.get("script"),
            "assets": workspace.get("assets"),
            "shots": [
                {
                    "shot_id": shot.get("shot_id"),
                    "reference_sha256": shot.get("reference_sha256"),
                    "keyframe_sha256": shot.get("keyframe_sha256"),
                    "video_sha256": shot.get("video_sha256"),
                }
                for shot in shots
            ],
            "final_demo": workspace.get("final_demo"),
        }
    )
    selected_redo = _redo_preview(shots[0] if shots else None, shots, cost)
    classification = _classification(project_id, ledger)
    return _assert_safe_projection(
        {
            "schema_version": MEDIA_OPERATIONS_SCHEMA_VERSION,
            "project_id": project_id,
            "run_id": resolved_run_id,
            "source_schema_version": workspace.get("schema_version"),
            "status": "ready_for_owner_review" if workspace.get("qa", {}).get("status") == "pass" else "needs_attention",
            "classification": classification,
            "stage": {
                "label": "审片与交付候选",
                "next_action": _next_action(classification, recovery),
                "blocking_reason": recovery["blocking_reason"],
                "provider_closed_in_production": True,
            },
            "journey": _journey(workspace, cost, recovery),
            "script": {
                "title": _text(workspace.get("script", {}).get("title"), "未命名短片"),
                "logline": _text(workspace.get("script", {}).get("logline"), ""),
                "source_revision": _text(script_truth.get("provenance", {}).get("source_revision_id"), ""),
                "source_digest": _text(script_truth.get("provenance", {}).get("source_candidate_digest"), ""),
                "owner_acceptance": False,
            },
            "summary": {
                "scene_count": len(scenes),
                "shot_count": len(shots),
                "ready_shot_count": len([shot for shot in shots if shot.get("status") == "ready"]),
                "asset_count": len(assets["characters"]) + len(assets["scenes"]) + len(assets["props"]),
                "duration_sec": round(float(workspace.get("timeline", {}).get("duration_sec") or 0.0), 3),
                "graph_digest": graph_digest,
            },
            "assets": assets,
            "scenes": scenes,
            "shots": shots,
            "final_review": {
                "status_label": "可审片" if quality["status"] == "pass" else "需处理",
                "video_url": _media_url(project_id, resolved_run_id, "final-video", "primary"),
                "contact_sheet_url": _media_url(project_id, resolved_run_id, "contact-sheet", "primary"),
                "duration_sec": float(workspace.get("final_demo", {}).get("duration_sec") or 0.0),
                "sha256": _short_hash(workspace.get("final_demo", {}).get("sha256")),
                "audio": "无音频轨，当前只验证画面交付候选",
                "readiness": _readiness(quality, recovery),
                "provenance": {
                    "final_artifact_id": _text(delivery.get("final_artifact_id") or workspace.get("final_demo", {}).get("artifact_id"), ""),
                    "delivery_manifest_artifact_id": _text(workspace.get("qa", {}).get("delivery_manifest_artifact_id"), ""),
                    "graph_digest": graph_digest,
                },
            },
            "cost": cost,
            "recovery": recovery,
            "localized_redo": selected_redo,
            "commands": _commands(shots, selected_redo),
            "advanced_evidence": {
                "visible_only_when_expanded": True,
                "graph_digest": graph_digest,
                "provider_dispatch_count": int(workspace.get("provider_dispatch_count") or 0),
                "ledger_status_counts": _status_counts(ledger),
                "final_sha256": _short_hash(workspace.get("final_demo", {}).get("sha256")),
                "contact_sheet_sha256": _short_hash(qa.get("contact_sheet_sha256")),
                "qa_boundary": _text(qa.get("visual_qa_boundary"), "自动技术 QA；不是人工审片或商业验证"),
                "non_claims": list(workspace.get("non_claims") or []),
            },
            "provider_boundary": {
                "browser_dispatch_count": 0,
                "incremental_cost_usd": 0.0,
                "uses_existing_paid_evidence": True,
                "production_provider_gates_expected_closed": True,
            },
        }
    )


def build_media_operations_command_preview(
    store: Any,
    *,
    project_id: str,
    run_id: str | None,
    action: str,
    shot_id: str | None = None,
) -> dict[str, Any]:
    review = load_media_operations_review(store, project_id=project_id, run_id=run_id)
    action_id = _safe_action(action)
    shots = review["shots"]
    shot = _find_shot(shots, shot_id) if shot_id else (shots[0] if shots else None)
    if action_id in {"local_redo_preview", "retry_failed_shot", "resume_failed_shot"} and not shot:
        raise ValueError("shot_id is required for this command preview")
    estimated = _redo_estimate(shot, review["cost"]) if shot else 0.0
    payload = {
        "schema_version": COMMAND_PREVIEW_SCHEMA_VERSION,
        "project_id": project_id,
        "run_id": review["run_id"],
        "action": action_id,
        "shot_id": shot.get("shot_id") if shot else "",
        "status": "preview_ready",
        "will_mutate_now": False,
        "will_dispatch_provider_now": False,
        "requires_explicit_charge_confirmation": action_id in {"local_redo_preview", "retry_failed_shot", "resume_failed_shot"},
        "estimated_incremental_usd": estimated,
        "idempotency_key": _idempotency_key(project_id, review["run_id"], action_id, shot.get("shot_id") if shot else "final", review["summary"]["graph_digest"]),
        "unaffected_shot_digests_preserved": [
            item["digest"]
            for item in shots
            if not shot or item.get("shot_id") != shot.get("shot_id")
        ],
        "human_message": _command_message(action_id, shot, estimated),
        "provider_boundary": "预览只读；确认前不会提交付费生成或写入第二事实。",
    }
    return _assert_safe_projection(payload)


def media_file_path(
    store: Any,
    *,
    project_id: str,
    run_id: str | None,
    media_kind: str,
    media_id: str,
) -> tuple[Path, str]:
    workspace = load_adaptive_workspace(store, project_id=project_id, run_id=run_id)
    resolved_run_id = str(workspace["run_id"])
    kind = str(media_kind or "").strip()
    if kind not in MEDIA_TYPES:
        raise KeyError(media_kind)
    if kind in {"keyframe", "shot-video"}:
        allowed = {str(shot.get("shot_id") or "") for shot in workspace.get("shots") or []}
        if str(media_id or "") not in allowed:
            raise KeyError(media_id)
    segments, media_type = MEDIA_TYPES[kind]
    run_root = adaptive_run_root(store, project_id=project_id, run_id=resolved_run_id)
    resolved_segments = [part.format(media_id=_safe_id(str(media_id or ""))) for part in segments]
    path = run_root.joinpath(*resolved_segments).resolve()
    _assert_within(path, run_root)
    if not path.is_file():
        raise KeyError(media_id)
    return path, media_type


def adaptive_run_root(store: Any, *, project_id: str, run_id: str) -> Path:
    root = (store.projects_dir / _safe_id(project_id) / "adaptive_canvas_v2" / _safe_id(run_id)).resolve()
    _assert_within(root, store.root.resolve())
    return root


def _shots(
    workspace: dict[str, Any],
    script_truth: dict[str, Any],
    *,
    project_id: str,
    run_id: str,
    ledger: dict[str, Any],
) -> list[dict[str, Any]]:
    script_shots = {
        str(shot.get("shot_id") or ""): shot
        for shot in script_truth.get("shots") or []
        if isinstance(shot, dict)
    }
    video_hashes = _shot_video_hashes(ledger)
    shots: list[dict[str, Any]] = []
    for raw in workspace.get("shots") or []:
        if not isinstance(raw, dict):
            continue
        shot_id = _text(raw.get("shot_id"), "")
        script_shot = script_shots.get(shot_id, {})
        camera_parts = _parts(script_shot.get("camera"))
        action_parts = _parts(raw.get("action"))
        reference_sha = raw.get("reference_binding", {}).get("reference_sha256")
        keyframe_sha = raw.get("selected_keyframe", {}).get("keyframe_sha256")
        video_sha = video_hashes.get(shot_id, "")
        shot = {
            "shot_id": shot_id,
            "order": int(raw.get("order") or len(shots) + 1),
            "title": _text(raw.get("summary"), f"镜头 {len(shots) + 1}"),
            "scene_id": _text(raw.get("scene_id"), ""),
            "location": _text(raw.get("location"), ""),
            "characters": [_text(item, "") for item in raw.get("characters") or [] if _text(item, "")],
            "duration_sec": float(raw.get("target_duration_sec") or 0.0),
            "timeline_in_sec": float(raw.get("timeline_in_sec") or 0.0),
            "timeline_out_sec": float(raw.get("timeline_out_sec") or 0.0),
            "purpose": _text(action_parts[1] if len(action_parts) > 1 else raw.get("summary"), ""),
            "staging": _text(action_parts[0] if action_parts else raw.get("action"), ""),
            "shot_size": _text(camera_parts[0] if camera_parts else "按确认关键帧执行", ""),
            "camera_position": _text(camera_parts[1] if len(camera_parts) > 1 else "机位沿用已确认分镜", ""),
            "movement": _text(camera_parts[2] if len(camera_parts) > 2 else "运动沿用已确认视频生成计划", ""),
            "sound": _text(action_parts[2] if len(action_parts) > 2 else "当前候选无音频轨，仅保留声音设计意图", ""),
            "transition": _text(raw.get("continuity_out"), ""),
            "continuity_in": _text(raw.get("continuity_in"), ""),
            "continuity_out": _text(raw.get("continuity_out"), ""),
            "status": "ready" if raw.get("status") == "selected_and_composed" else "needs_attention",
            "keyframe_url": _media_url(project_id, run_id, "keyframe", shot_id),
            "video_url": _media_url(project_id, run_id, "shot-video", shot_id),
            "reference_sha256": _short_hash(reference_sha),
            "keyframe_sha256": _short_hash(keyframe_sha),
            "video_sha256": _short_hash(video_sha),
            "digest": _digest({"shot": shot_id, "reference": reference_sha, "keyframe": keyframe_sha, "video": video_sha}),
            "negative_locks": list(DEFAULT_MEDIA_NEGATIVE_LOCKS),
        }
        shots.append(shot)
    return shots


def _scenes(workspace: dict[str, Any], shots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scenes = []
    for index, raw in enumerate(workspace.get("assets", {}).get("scenes") or [], start=1):
        if not isinstance(raw, dict):
            continue
        scene_shots = [shot for shot in shots if shot.get("scene_id") == raw.get("scene_id")]
        scenes.append(
            {
                "scene_id": _text(raw.get("scene_id"), f"scene-{index}"),
                "order": index,
                "name": _text(raw.get("name"), f"场景 {index}"),
                "visual_mood": _text(raw.get("visual_mood"), ""),
                "story_function": _text(raw.get("story_function"), ""),
                "shot_count": len(scene_shots),
                "duration_sec": round(sum(float(shot.get("duration_sec") or 0.0) for shot in scene_shots), 3),
                "status": "ready" if scene_shots else "needs_attention",
            }
        )
    return scenes


def _assets(workspace: dict[str, Any], *, project_id: str, run_id: str) -> dict[str, Any]:
    assets = workspace.get("assets") if isinstance(workspace.get("assets"), dict) else {}
    characters = []
    for raw in assets.get("characters") or []:
        if not isinstance(raw, dict):
            continue
        characters.append(
            {
                "asset_id": _text(raw.get("character_id"), ""),
                "name": _text(raw.get("name"), "角色"),
                "role": _text(raw.get("role"), ""),
                "appearance": _text(raw.get("appearance"), ""),
                "wardrobe": _text(raw.get("wardrobe"), ""),
                "continuity": _text(raw.get("continuity"), ""),
                "status": "confirmed_reused",
            }
        )
    scenes = []
    for raw in assets.get("scenes") or []:
        if not isinstance(raw, dict):
            continue
        scenes.append(
            {
                "asset_id": _text(raw.get("scene_id"), ""),
                "name": _text(raw.get("name"), "场景"),
                "space_light": _text(raw.get("visual_mood"), ""),
                "continuity": _text(raw.get("story_function"), ""),
                "status": "confirmed_reused",
            }
        )
    return {
        "characters": characters,
        "scenes": scenes,
        "props": _prop_locks(workspace),
        "reference_set": {
            "status": "confirmed_reused",
            "reference_sheet_url": _media_url(project_id, run_id, "reference-sheet", "primary"),
            "negative_locks": list(DEFAULT_MEDIA_NEGATIVE_LOCKS),
            "style": _text(assets.get("style_bible"), ""),
        },
        "continuity_warning": "改动角色服装、空间光线、核心道具或 ReferenceSet 前需先预览影响；未确认不会写入制作图。",
    }


def _prop_locks(workspace: dict[str, Any]) -> list[dict[str, str]]:
    text = " ".join(
        [
            *(str(item.get("continuity") or "") for item in workspace.get("assets", {}).get("characters") or [] if isinstance(item, dict)),
            *(str(shot.get("action") or "") for shot in workspace.get("shots") or [] if isinstance(shot, dict)),
        ]
    )
    labels = []
    for token in ("旧镜头", "场记板", "硬盘", "蓝色雨披", "担架", "裂纹平板", "红色束带", "编号七"):
        if token in text:
            labels.append({"name": token, "continuity": "保持归属、出现顺序和画面可读性", "status": "locked"})
    return labels[:8]


def _quality(qa: dict[str, Any]) -> dict[str, Any]:
    metrics = qa.get("media_metrics") if isinstance(qa.get("media_metrics"), dict) else {}
    return {
        "status": _text(qa.get("status"), ""),
        "duration_sec": float(qa.get("final_duration_sec") or metrics.get("duration_sec") or 0.0),
        "frame_count": int(metrics.get("frame_count") or 0),
        "fps": float(metrics.get("fps") or 0.0),
        "width": int(metrics.get("width") or 0),
        "height": int(metrics.get("height") or 0),
        "black_segment_count": int(metrics.get("black_segment_count") or 0),
        "freeze_event_count": int(metrics.get("freeze_event_count") or 0),
        "repeat_or_freeze_event_count": int(metrics.get("repeat_or_freeze_event_count") or 0),
        "findings": [str(item)[:160] for item in qa.get("findings") or []],
    }


def _cost(workspace: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    attempts = [item for item in ledger.get("attempts") or [] if isinstance(item, dict)]
    image_attempts = [item for item in attempts if item.get("capability") == "image" and item.get("provider_calls_started")]
    video_attempts = [item for item in attempts if item.get("capability") == "video" and item.get("provider_calls_started")]
    video_seconds = float(workspace.get("timeline", {}).get("duration_sec") or 0.0)
    estimated_usd = round(len(image_attempts) * PUBLIC_IMAGE_PRICE_USD + video_seconds * CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC, 4)
    shot_count = len(workspace.get("shots") or [])
    return {
        "actual_receipt_status": "Provider 未返回逐项账单；当前使用 M6.2 保守单价估算。",
        "image_attempt_count": len(image_attempts),
        "video_attempt_count": len(video_attempts),
        "estimated_video_seconds": round(video_seconds, 3),
        "conservative_estimated_usd": estimated_usd,
        "avoided_dispatches_from_reference_reuse": max(0, shot_count - 1),
        "idempotency_replay_extra_dispatch_count": 0,
        "unit": {
            "image_usd": PUBLIC_IMAGE_PRICE_USD,
            "video_usd_per_sec": CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC,
        },
    }


def _recovery(ledger: dict[str, Any], run_state: dict[str, Any]) -> dict[str, Any]:
    attempts = [item for item in ledger.get("attempts") or [] if isinstance(item, dict)]
    failed = [item for item in attempts if item.get("status") != "succeeded"]
    nonterminal_video = [item for item in failed if item.get("stage") == "video_chunk"]
    resolved = []
    for item in failed[:6]:
        resolved.append(
            {
                "stage": _stage_label(item.get("stage")),
                "shot_id": _text(item.get("shot_id"), ""),
                "status": "已恢复" if ledger.get("paid_attempt_count") else "需处理",
                "safe_error": _safe_error(item.get("safe_error")),
            }
        )
    return {
        "state": "recovered_with_attention" if nonterminal_video else ("recovered" if failed else "clean"),
        "blocking_reason": "" if not nonterminal_video else "曾发生视频分段恢复问题；当前最终片已可播放，但此案只作为恢复证据。",
        "failed_attempt_count": len(failed),
        "video_recovery_attempt_count": len(nonterminal_video),
        "run_state": _text(run_state.get("status"), ""),
        "resolved_items": resolved,
        "fail_closed": True,
        "no_duplicate_charge_on_resume": len({item.get("attempt_id") for item in attempts}) == len(attempts),
    }


def _redo_preview(shot: dict[str, Any] | None, shots: list[dict[str, Any]], cost: dict[str, Any]) -> dict[str, Any]:
    if not shot:
        return {}
    estimate = _redo_estimate(shot, cost)
    return {
        "status": "preview_only",
        "selected_shot_id": shot["shot_id"],
        "selected_shot_title": shot["title"],
        "old_version_digest": shot["digest"],
        "new_version_digest": _digest({"redo": shot["digest"], "scope": "local_preview"}),
        "unaffected_shot_digests": [item["digest"] for item in shots if item["shot_id"] != shot["shot_id"]],
        "estimated_incremental_usd": estimate,
        "charge_confirmation_required": True,
        "provider_dispatch_now": False,
    }


def _commands(shots: list[dict[str, Any]], redo: dict[str, Any]) -> list[dict[str, Any]]:
    selected = redo.get("selected_shot_id") or (shots[0]["shot_id"] if shots else "")
    return [
        {
            "action": "local_redo_preview",
            "label": "预览局部重做",
            "shot_id": selected,
            "requires_confirmation": True,
            "paid_until_confirmed": False,
        },
        {
            "action": "resume_failed_shot",
            "label": "恢复中断镜头",
            "shot_id": selected,
            "requires_confirmation": True,
            "paid_until_confirmed": False,
        },
        {
            "action": "promote_version",
            "label": "提升当前版本",
            "shot_id": selected,
            "requires_confirmation": True,
            "paid_until_confirmed": False,
        },
    ]


def _journey(workspace: dict[str, Any], cost: dict[str, Any], recovery: dict[str, Any]) -> list[dict[str, str]]:
    shot_count = len(workspace.get("shots") or [])
    return [
        {"label": "剧本与修订", "state": "completed", "detail": "已读取 M6.1 revision2 的真实剧本与谱系"},
        {"label": "结构与拆镜", "state": "completed", "detail": f"内容驱动 {shot_count} 个镜头；不是固定模板"},
        {"label": "资产 Bible", "state": "completed", "detail": "角色、场景、ReferenceSet 与禁止变化项已确认"},
        {"label": "生成与复用", "state": "completed", "detail": f"复用参考避免 {cost['avoided_dispatches_from_reference_reuse']} 次重复生成"},
        {"label": "QA 与恢复", "state": "warning" if recovery["state"] == "recovered_with_attention" else "completed", "detail": _next_action(_classification("", {}), recovery)},
        {"label": "交付候选", "state": "in_progress", "detail": "可审片；仍需 Owner 人工判断"},
    ]


def _readiness(quality: dict[str, Any], recovery: dict[str, Any]) -> list[dict[str, str]]:
    items = [
        {"label": "可播放", "state": "pass" if quality["status"] == "pass" else "fail"},
        {"label": "黑帧/冻结", "state": "pass" if quality["black_segment_count"] == 0 and quality["freeze_event_count"] == 0 else "fail"},
        {"label": "成本可追踪", "state": "pass"},
        {"label": "恢复", "state": "warning" if recovery["state"] == "recovered_with_attention" else "pass"},
        {"label": "人工验收", "state": "not_claimed"},
    ]
    return items


def _classification(project_id: str, ledger: dict[str, Any]) -> str:
    attempts = [item for item in ledger.get("attempts") or [] if isinstance(item, dict)]
    video_failures = [item for item in attempts if item.get("stage") == "video_chunk" and item.get("status") != "succeeded"]
    if video_failures or "sci_fi_chamber" in project_id:
        return "RECOVERY_EVIDENCE_NOT_COUNTED"
    return "CLEAN_FULL_CASE"


def _next_action(classification: str, recovery: dict[str, Any]) -> str:
    if recovery.get("state") == "recovered_with_attention" or classification == "RECOVERY_EVIDENCE_NOT_COUNTED":
        return "查看恢复记录，确认不会重复扣费后再决定是否局部重做。"
    return "从故事板选择镜头，审看片段、资产锁和增量成本。"


def _safe_action(value: str) -> str:
    action = str(value or "").strip()
    if action not in {"local_redo_preview", "retry_failed_shot", "resume_failed_shot", "promote_version", "keep_version"}:
        raise ValueError("unsupported media operation action")
    return action


def _command_message(action: str, shot: dict[str, Any] | None, estimated: float) -> str:
    title = shot.get("title") if shot else "当前版本"
    if action == "promote_version":
        return f"{title} 的提升命令只会在确认后写入 ProductionGraph；本次预览不付费。"
    if action == "keep_version":
        return f"{title} 将保留当前版本；不会产生新媒体。"
    return f"{title} 的局部操作预计增量 ${estimated:.2f}，确认前不会发起生成或产生费用。"


def _redo_estimate(shot: dict[str, Any] | None, cost: dict[str, Any]) -> float:
    if not shot:
        return 0.0
    return round(float(cost["unit"]["image_usd"]) + float(shot.get("duration_sec") or 0.0) * float(cost["unit"]["video_usd_per_sec"]), 4)


def _find_shot(shots: list[dict[str, Any]], shot_id: str | None) -> dict[str, Any]:
    for shot in shots:
        if shot.get("shot_id") == shot_id:
            return shot
    raise ValueError("shot_id is not part of this production graph")


def _shot_video_hashes(ledger: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in ledger.get("attempts") or []:
        if not isinstance(item, dict):
            continue
        if item.get("stage") == "video_chunk" and item.get("status") == "succeeded" and item.get("shot_id"):
            values[str(item["shot_id"])] = _text(item.get("artifact_sha256"), "")
    return values


def _status_counts(ledger: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in ledger.get("attempts") or []:
        if isinstance(item, dict):
            key = _text(item.get("status"), "unknown")
            counts[key] = counts.get(key, 0) + 1
    return counts


def _idempotency_key(project_id: str, run_id: str, action: str, shot_id: str, digest: str) -> str:
    return "m6-3-" + _digest({"project_id": project_id, "run_id": run_id, "action": action, "shot_id": shot_id, "digest": digest})[:24]


def _media_url(project_id: str, run_id: str, kind: str, media_id: str) -> str:
    return (
        f"/projects/{quote(project_id, safe='')}/adaptive-canvas-v2/media/"
        f"{quote(kind, safe='')}/{quote(media_id, safe='')}?run_id={quote(run_id, safe='')}"
    )


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = _read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{Path(path).name} must be a JSON object")
    return payload


def _safe_id(value: str, *, max_length: int = 120) -> str:
    cleaned = SAFE_ID_PATTERN.sub("-", str(value).strip()).strip("-._")
    if not cleaned:
        cleaned = "item"
    if len(cleaned) <= max_length:
        return cleaned
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]
    prefix = cleaned[: max(1, max_length - len(digest) - 1)].rstrip("-._") or "item"
    return f"{prefix}-{digest}"


def _parts(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def _text(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else fallback).strip()
    text = " ".join(text.split())
    return text[:480]


def _safe_error(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        "type": _text(value.get("type"), "ProviderError")[:80],
        "message": _text(value.get("message") or value.get("safe_message"), "已安全失败并等待恢复")[:180],
    }


def _stage_label(value: Any) -> str:
    return {
        "reference_sheet": "参考图",
        "keyframe": "关键帧",
        "video_chunk": "视频分段",
        "final_compose": "最终合成",
    }.get(str(value or ""), _text(value, "制作步骤"))


def _short_hash(value: Any) -> str:
    text = _text(value, "")
    if not text:
        return ""
    return text[:12]


def _digest(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _assert_within(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("media path escapes runtime root") from exc


def _assert_safe_projection(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden = ("/home/", "/tmp/", "/var/", "api_key", "authorization", "bearer", "secret", "signed_url")
    leaked = [token for token in forbidden if token.lower() in text.lower()]
    if leaked:
        raise ValueError(f"unsafe media operations projection leaked private data: {leaked}")
    return payload


__all__ = (
    "COMMAND_PREVIEW_SCHEMA_VERSION",
    "MEDIA_OPERATIONS_SCHEMA_VERSION",
    "build_media_operations_command_preview",
    "load_media_operations_review",
    "media_file_path",
)
