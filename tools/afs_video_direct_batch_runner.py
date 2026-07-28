from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from agentflow.harness.json_io import exclusive_file_lock, write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_models import VideoGenerationRequest
from apps.api.runtime_production_graph import ProductionGraphStore
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id
from apps.api.runtime_video_admission import (
    FIRST_FRAME,
    MODEL_ID,
    REFERENCE_CONDITIONED,
    SERVICE_ID,
    _canonical_video_shot_grounding,
    _confirm_video_admission_command,
    _source_contract,
    load_video_admission_manifest,
    preview_video_admission_command,
    video_admission_generation_request,
)
from apps.api.runtime_video_candidates import candidate_file
from apps.api.runtime_video_dispatch import poll_video_generation, submit_video_generation
from apps.api.runtime_video_manifest import video_response, write_video_job


PROJECT_ID = "studio-1785154250742-86s0uf"
POST_ONLY_SHOTS = {31, 33, 34}
TERMINAL_JOB_STATES = {
    "succeeded",
    "failed",
    "blocked",
    "cancelled",
    "needs_attention",
    "reconcile_required",
    "poll_failed",
}


@dataclass(frozen=True)
class BatchTarget:
    shot_id: str
    shot_number: int
    shot_label: str
    generation_mode: str
    reference_count: int
    skip_reason: str = ""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def default_runtime_root() -> Path:
    return Path(os.environ.get("AFS_RUNTIME_ROOT") or os.environ.get("AFS_RUNTIME_SERVICE_ROOT") or "/var/lib/afs-runtime")


def batch_root(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "video_direct_batch"


def batch_path(store: RuntimeStore, project_id: str, run_id: str) -> Path:
    return batch_root(store, project_id) / safe_id(run_id) / "batch_run.json"


def load_batch_ledger(store: RuntimeStore, project_id: str, run_id: str) -> dict[str, Any]:
    path = batch_path(store, project_id, run_id)
    if not path.is_file():
        return {
            "schema_version": "afs.video_direct_batch_run.v0.1",
            "project_id": project_id,
            "run_id": run_id,
            "status": "created",
            "targets": [],
            "events": [],
            "provider_dispatch_count": 0,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
    value = read_json(path)
    reject_unsafe_payload(value)
    if value.get("project_id") != project_id or value.get("run_id") != run_id:
        raise ValueError("video batch ledger scope mismatch")
    return value


def save_batch_ledger(store: RuntimeStore, project_id: str, ledger: Mapping[str, Any]) -> None:
    path = batch_path(store, project_id, str(ledger["run_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(ledger)
    payload["updated_at"] = utc_now()
    reject_unsafe_payload(payload)
    with exclusive_file_lock(path.with_suffix(".lock")):
        write_json(path, payload)


def record_event(store: RuntimeStore, project_id: str, ledger: dict[str, Any], event: str, **fields: Any) -> None:
    safe = {
        "event": event,
        "recorded_at": utc_now(),
        **{
            key: value
            for key, value in fields.items()
            if value not in (None, "")
        },
    }
    ledger.setdefault("events", []).append(safe)
    save_batch_ledger(store, project_id, ledger)


def provider_pool_summary() -> dict[str, Any]:
    try:
        registry = load_provider_registry()
        descriptor = registry.descriptor(SERVICE_ID)
        pool_id = str(getattr(descriptor, "account_pool_id", "") or "")
        pool = registry.store.account_pools.get(pool_id, {}) if pool_id else {}
        entries = [
            item
            for item in pool.get("accounts", [])
            if isinstance(item, dict)
            and item.get("enabled", True) is True
            and (not item.get("service_id") or item.get("service_id") == SERVICE_ID)
            and (
                not item.get("enabled_capabilities")
                or "video" in list(item.get("enabled_capabilities") or [])
            )
        ]
        return {
            "dispatch_ready": True,
            "service_id": SERVICE_ID,
            "model": MODEL_ID,
            "account_pool_id": pool_id,
            "enabled_video_accounts": len(entries) if entries else 1,
            "concurrency_capacity": sum(int(item.get("concurrency_limit") or 1) for item in entries) if entries else 1,
        }
    except (KeyError, ValueError, OSError, ModelGatewayError) as exc:
        return {
            "dispatch_ready": False,
            "service_id": SERVICE_ID,
            "model": MODEL_ID,
            "reason": str(exc),
            "enabled_video_accounts": 0,
            "concurrency_capacity": 0,
        }


def target_concurrency(requested: int | None = None) -> int:
    if requested and requested > 0:
        return max(1, min(12, requested))
    summary = provider_pool_summary()
    capacity = int(summary.get("concurrency_capacity") or summary.get("enabled_video_accounts") or 4)
    return max(1, min(12, capacity))


def canonical_video_shots(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), Mapping) else {}
    active = {
        str(node_id): node
        for node_id, node in nodes.items()
        if isinstance(node, Mapping) and node.get("state", "active") == "active"
    }
    scene_ids = {
        str(relation.get("from_id") or "")
        for relation in graph.get("relations", [])
        if relation.get("relation_type") == "contains"
        and (active.get(str(relation.get("from_id") or "")) or {}).get("category") == "location"
        and (active.get(str(relation.get("to_id") or "")) or {}).get("category") == "unit"
    }
    shot_ids: list[str] = []
    seen: set[str] = set()
    for relation in graph.get("relations", []):
        if relation.get("relation_type") != "contains":
            continue
        scene_id = str(relation.get("from_id") or "")
        shot_id = str(relation.get("to_id") or "")
        if shot_id in seen or scene_id not in scene_ids:
            continue
        if (active.get(shot_id) or {}).get("category") != "unit":
            continue
        seen.add(shot_id)
        shot_ids.append(shot_id)
    shots = [_canonical_video_shot_grounding(graph, shot_id=shot_id) for shot_id in shot_ids]
    return sorted(shots, key=lambda item: (int(item.get("number") or 0), str(item.get("shot_id") or "")))


def build_targets(store: RuntimeStore, project_id: str) -> list[BatchTarget]:
    graph = ProductionGraphStore(store).load(project_id)
    targets: list[BatchTarget] = []
    for shot in canonical_video_shots(graph):
        shot_id = str(shot["shot_id"])
        number = int(shot.get("number") or 0)
        label = str(shot.get("title") or f"镜头 {number:02d}")
        if number in POST_ONLY_SHOTS:
            targets.append(BatchTarget(shot_id, number, label, REFERENCE_CONDITIONED, 0, "post_only"))
            continue
        try:
            source = _source_contract(
                store,
                project_id,
                shot_id=shot_id,
                allow_partial_references=True,
                partial_reference_reason=(
                    "Direct batch production may proceed with approved identity/prop references "
                    "and textual scene grounding when a non-primary scene reference is not yet approved."
                ),
            )
        except (KeyError, ValueError) as exc:
            targets.append(BatchTarget(shot_id, number, label, REFERENCE_CONDITIONED, 0, f"source_blocked:{exc}"))
            continue
        if number == 35 and not source.get("keyframe"):
            targets.append(BatchTarget(shot_id, number, label, FIRST_FRAME, len(source.get("references") or []), "requires_approved_first_frame"))
            continue
        mode = FIRST_FRAME if number == 35 else REFERENCE_CONDITIONED
        targets.append(BatchTarget(shot_id, number, label, mode, len(source.get("references") or [])))
    return targets


def temporal_staging_for_target(store: RuntimeStore, project_id: str, target: BatchTarget) -> dict[str, str]:
    source = _source_contract(
        store,
        project_id,
        shot_id=target.shot_id,
        allow_partial_references=True,
        partial_reference_reason=(
            "Direct batch production may proceed with approved identity/prop references "
            "and textual scene grounding when a non-primary scene reference is not yet approved."
        ),
    )
    shot = source["shot_semantics"]
    refs = "、".join(str(ref.get("label") or ref.get("target_asset_id") or "") for ref in source.get("references", []))
    if target.shot_number == 1:
        return {
            "subject_action_arc": "成年女性在清澈蓝色水下平静漂浮，完整日常服装随水流轻轻摆动。",
            "spatial_displacement": "她从柔和光束下方缓慢向画面深处移动，姿态自然舒展，人物轮廓始终清楚。",
            "interaction_object": "水流、气泡、发丝和衣料形成轻柔运动，参考角色脸型与象征性深海色彩保持连续。",
            "camera_movement": "水下缓慢跟拍并轻微推进，从大全景靠近到中近景，保持安静电影感。",
            "environment_dynamics": "清澈蓝色水体、柔和光束和细小气泡持续流动，背景简洁梦境化。",
            "pacing": "固定6秒慢节奏连续镜头，动作平稳、柔和、克制。",
            "start_state": "成年女性完整着装，平静漂浮在清澈蓝色水下空间中。",
            "end_state": "她仍在柔和光束与气泡中缓慢移动，画面安静收束。",
            "narrative_purpose": "用梦境般水下影像建立重生前奏和人物内心氛围，保持安静、完整着装、电影化表达。",
        }
    if target.shot_number == 3:
        return {
            "subject_action_arc": "抽象光影记忆碎片在画面中交错闪现，人物轮廓只作为远景剪影或反射出现。",
            "spatial_displacement": "冷色光带和室内影子从画面两侧缓慢掠过，形成片段式空间转换。",
            "interaction_object": "光影、门缝、窗帘和远处车辆反光作为视觉线索，不出现具体事件细节。",
            "camera_movement": "镜头以慢速滑移和轻微失焦转换串联碎片，保持抽象电影感。",
            "environment_dynamics": "灰蓝低饱和空间、弱光反射和轻微颗粒营造记忆感，不加入新人物或文字。",
            "pacing": "固定6秒，前半段碎片闪回，后半段归于安静的冷色空间。",
            "start_state": "画面从柔和冷光和模糊室内线条开始。",
            "end_state": "抽象光影逐渐退暗，留下安静悬念。",
            "narrative_purpose": "用抽象光影表现前情记忆和情绪铺垫，避免具象敏感事件表达。",
        }
    return {
        "subject_action_arc": str(shot.get("action") or f"{target.shot_label} 的主体动作在一个连续镜头内完成。"),
        "spatial_displacement": "保持前景、中景、背景空间关系清楚，主体在已确认场景内完成可读位移。",
        "interaction_object": refs or "与已确认场景、道具和环境关系保持连续。",
        "camera_movement": str(shot.get("movement") or "稳定电影镜头，按叙事重点缓慢推进或跟随。"),
        "environment_dynamics": "环境动态服务表演和调度，不加入未确认人物、地点、道具或文字。",
        "pacing": "固定6秒单段视频，动作起承转合清楚，节奏符合当前镜头叙事。",
        "start_state": f"{target.shot_label} 从当前剧本设定的镜头起点自然开始。",
        "end_state": f"{target.shot_label} 在可衔接下一镜头的状态结束。",
        "narrative_purpose": str(shot.get("purpose") or shot.get("emotion") or "服务当前镜头叙事和连续性。"),
    }


def admission_command(
    store: RuntimeStore,
    project_id: str,
    shot_id: str,
    command: dict[str, Any],
    *,
    confirm: bool = True,
) -> dict[str, Any]:
    graph_store = ProductionGraphStore(store)
    body = {"command": command, "requested_at": utc_now()}
    preview = preview_video_admission_command(store, project_id, body, lane_shot_id=shot_id)
    if not confirm:
        return preview
    return _confirm_video_admission_command(
        store,
        graph_store,
        project_id,
        {**body, "preview_digest": preview["preview_digest"]},
        lane_shot_id=shot_id,
    )


def ensure_manifest(store: RuntimeStore, project_id: str, run_id: str, target: BatchTarget) -> dict[str, Any]:
    existing = load_video_admission_manifest(store, project_id, shot_id=target.shot_id)
    state = str((existing.get("item") or {}).get("state") or "")
    command_type = "compile"
    if existing and state == "reconcile_required":
        command_type = "create_new_round"
    elif existing and state in {"planned", "reserved", "dispatch_prepared", "processing", "candidate", "approved"}:
        return existing
    elif existing:
        raise ValueError(f"existing video lane is terminal and not recoverable: {state}")
    command = {
        "type": command_type,
        "shot_id": target.shot_id,
        "generation_mode": target.generation_mode,
        "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。" if target.generation_mode == REFERENCE_CONDITIONED else "仅在镜头明确要求从已批准首帧开始时使用。",
        "temporal_staging": temporal_staging_for_target(store, project_id, target),
        "allow_partial_references": True,
        "partial_reference_reason": (
            "Direct batch production may proceed with approved identity/prop references "
            "and textual scene grounding when a non-primary scene reference is not yet approved."
        ),
        "idempotency_key": f"video-direct-{command_type}-{run_id}-{target.shot_id}",
    }
    response = admission_command(store, project_id, target.shot_id, command)
    return response["result"]["manifest"]


def reserve_manifest(store: RuntimeStore, project_id: str, run_id: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    item = manifest.get("item") or {}
    if item.get("state") != "planned":
        return dict(manifest)
    shot_id = str((manifest.get("source", {}).get("shot") or {}).get("shot_id") or "")
    response = admission_command(
        store,
        project_id,
        shot_id,
        {
            "type": "reserve_dispatch",
            "idempotency_key": f"video-direct-reserve-{run_id}-{shot_id}-{manifest.get('manifest_hash')}",
        },
    )
    return response["result"]["manifest"]


def dispatch_once(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    manifest: Mapping[str, Any],
    *,
    job_id: str | None = None,
) -> dict[str, Any]:
    request = VideoGenerationRequest(
        **{
            **video_admission_generation_request(manifest, generated_at=utc_now()),
            "quota_override_confirmed": True,
        }
    )
    job_id = job_id or store.new_job_id("video_generation", project_id)
    output_dir = store.run_dir(project_id, job_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        store.load_job(job_id)
    except KeyError:
        store.write_job(runtime_job(job_id, project_id, "video_generation", "dispatch_prepared"))
    result = submit_video_generation(
        store,
        project_id,
        job_id,
        request,
        output_dir,
        load_registry=load_provider_registry,
        request_id=f"direct-video-{run_id}-{safe_id(request.node_id or '')}",
        client_request_id=f"direct-video-{run_id}-{safe_id(request.node_id or '')}",
    )
    job = write_video_job(store, project_id, job_id, result)
    return video_response(store, project_id, job, result)


def poll_existing_job(
    store: RuntimeStore,
    project_id: str,
    *,
    job_id: str,
    poll_interval_sec: float,
    max_poll_sec: int,
) -> dict[str, Any]:
    result = poll_video_generation(
        store,
        project_id,
        store.run_dir(project_id, job_id),
        load_registry=load_provider_registry,
        request_id=f"direct-poll-{job_id}",
        client_request_id=f"direct-poll-{job_id}",
    )
    job = write_video_job(store, project_id, job_id, result)
    return poll_until_terminal(
        store,
        project_id,
        video_response(store, project_id, job, result),
        poll_interval_sec=poll_interval_sec,
        max_poll_sec=max_poll_sec,
    )


def poll_until_terminal(
    store: RuntimeStore,
    project_id: str,
    response: Mapping[str, Any],
    *,
    poll_interval_sec: float,
    max_poll_sec: int,
) -> dict[str, Any]:
    job = response.get("job") or {}
    job_id = str(job.get("job_id") or "")
    deadline = time.monotonic() + max_poll_sec
    current = dict(response)
    while job_id and time.monotonic() < deadline:
        status = str((current.get("job") or {}).get("status") or current.get("status") or "")
        if current.get("candidate_previews") or status in TERMINAL_JOB_STATES:
            return current
        time.sleep(poll_interval_sec)
        result = poll_video_generation(
            store,
            project_id,
            store.run_dir(project_id, job_id),
            load_registry=load_provider_registry,
            request_id=f"direct-poll-{job_id}",
            client_request_id=f"direct-poll-{job_id}",
        )
        job = write_video_job(store, project_id, job_id, result)
        current = video_response(store, project_id, job, result)
    return current


def record_candidate(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    shot_id: str,
    response: Mapping[str, Any],
) -> dict[str, Any]:
    previews = response.get("candidate_previews") or []
    if not previews:
        return {}
    candidate = dict(previews[0])
    job_id = str((response.get("job") or {}).get("job_id") or "")
    safe = response.get("safe_manifest") if isinstance(response.get("safe_manifest"), Mapping) else {}
    usage = safe.get("usage_evidence") if isinstance(safe.get("usage_evidence"), Mapping) else {}
    candidate["job_id"] = job_id
    candidate["usage_evidence"] = {
        "provider_reported_usage": bool(usage.get("provider_reported_usage")),
        "provider_reported_cost": False,
        "actual_charge_verification": "unverified",
        **({"output_tokens": int(usage.get("output_tokens"))} if str(usage.get("output_tokens") or "").isdigit() else {}),
    }
    command = {
        "type": "record_candidate",
        "candidate": candidate,
        "idempotency_key": f"video-direct-candidate-{run_id}-{shot_id}-{job_id}",
    }
    result = admission_command(store, project_id, shot_id, command)
    return result["result"]["manifest"]


def record_failure(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    shot_id: str,
    *,
    status: str,
) -> dict[str, Any]:
    response = admission_command(
        store,
        project_id,
        shot_id,
        {
            "type": "record_failure",
            "error_category": status or "video_generation_failed",
            "idempotency_key": f"video-direct-failure-{run_id}-{shot_id}-{status or 'unknown'}",
        },
    )
    return response["result"]["manifest"]


def promote_candidate(store: RuntimeStore, project_id: str, run_id: str, shot_id: str) -> dict[str, Any]:
    response = admission_command(
        store,
        project_id,
        shot_id,
        {
            "type": "approve",
            "idempotency_key": f"video-direct-promote-{run_id}-{shot_id}",
        },
    )
    return response["result"]["manifest"]


def candidate_technical_summary(store: RuntimeStore, project_id: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    candidate = (manifest.get("item") or {}).get("candidate") or {}
    job_id = str(candidate.get("job_id") or "")
    candidate_id = str(candidate.get("candidate_id") or "")
    path = candidate_file(store.run_dir(project_id, job_id), candidate_id) if job_id and candidate_id else None
    digest = ""
    if path and path.is_file():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "preview_url": str(candidate.get("preview_url") or ""),
        "sha256": digest or str(candidate.get("sha256") or ""),
        "byte_count": int(candidate.get("byte_count") or 0),
        "technical_qa": candidate.get("technical_qa") or {},
    }


def execute_target(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    target: BatchTarget,
    *,
    poll_interval_sec: float,
    max_poll_sec: int,
    promote: bool,
) -> dict[str, Any]:
    if target.skip_reason:
        return {"shot_id": target.shot_id, "shot_number": target.shot_number, "status": "skipped", "reason": target.skip_reason}
    manifest = ensure_manifest(store, project_id, run_id, target)
    manifest = reserve_manifest(store, project_id, run_id, manifest)
    item_state = str((manifest.get("item") or {}).get("state") or "")
    if item_state == "candidate":
        recorded = manifest
    elif item_state == "approved":
        return {"shot_id": target.shot_id, "shot_number": target.shot_number, "status": "already_approved"}
    elif item_state == "dispatch_prepared":
        job_id = str((manifest.get("item") or {}).get("provider_job_id") or "")
        if not job_id:
            return {"shot_id": target.shot_id, "shot_number": target.shot_number, "status": "dispatch_prepared_without_job"}
        response = poll_until_terminal(
            store,
            project_id,
            dispatch_once(store, project_id, run_id, manifest, job_id=job_id),
            poll_interval_sec=poll_interval_sec,
            max_poll_sec=max_poll_sec,
        )
        if response.get("candidate_previews"):
            recorded = record_candidate(store, project_id, run_id, target.shot_id, response)
        else:
            status = str((response.get("job") or {}).get("status") or response.get("status") or "unknown")
            return _terminal_non_candidate_result(
                store,
                project_id,
                run_id,
                target,
                status=status,
                job_id=str((response.get("job") or {}).get("job_id") or job_id),
                response=response,
            )
    elif item_state == "processing":
        job_id = str((manifest.get("item") or {}).get("provider_job_id") or "")
        if not job_id:
            return {"shot_id": target.shot_id, "shot_number": target.shot_number, "status": "processing_without_job"}
        response = poll_existing_job(
            store,
            project_id,
            job_id=job_id,
            poll_interval_sec=poll_interval_sec,
            max_poll_sec=max_poll_sec,
        )
        if response.get("candidate_previews"):
            recorded = record_candidate(store, project_id, run_id, target.shot_id, response)
        else:
            status = str((response.get("job") or {}).get("status") or response.get("status") or "unknown")
            return _terminal_non_candidate_result(
                store,
                project_id,
                run_id,
                target,
                status=status,
                job_id=job_id,
                response=response,
            )
    elif item_state != "reserved":
        return {"shot_id": target.shot_id, "shot_number": target.shot_number, "status": item_state or "blocked"}
    else:
        response = poll_until_terminal(
            store,
            project_id,
            dispatch_once(store, project_id, run_id, manifest),
            poll_interval_sec=poll_interval_sec,
            max_poll_sec=max_poll_sec,
        )
        if response.get("candidate_previews"):
            recorded = record_candidate(store, project_id, run_id, target.shot_id, response)
        else:
            status = str((response.get("job") or {}).get("status") or response.get("status") or "unknown")
            return _terminal_non_candidate_result(
                store,
                project_id,
                run_id,
                target,
                status=status,
                job_id=str((response.get("job") or {}).get("job_id") or ""),
                response=response,
            )
    summary = candidate_technical_summary(store, project_id, recorded)
    if promote:
        promoted = promote_candidate(store, project_id, run_id, target.shot_id)
        return {
            "shot_id": target.shot_id,
            "shot_number": target.shot_number,
            "status": "promoted",
            "manifest_id": str(promoted.get("manifest_id") or ""),
            **summary,
        }
    return {
        "shot_id": target.shot_id,
        "shot_number": target.shot_number,
        "status": "candidate_recorded",
        "manifest_id": str(recorded.get("manifest_id") or ""),
        **summary,
    }


def _terminal_non_candidate_result(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    target: BatchTarget,
    *,
    status: str,
    job_id: str,
    response: Mapping[str, Any],
) -> dict[str, Any]:
    manifest_state = str(
        (
            load_video_admission_manifest(
                store,
                project_id,
                shot_id=target.shot_id,
            ).get("item")
            or {}
        ).get("state")
        or ""
    )
    failure_recorded = False
    if manifest_state in {"reserved", "processing"} and status in TERMINAL_JOB_STATES:
        try:
            record_failure(
                store,
                project_id,
                run_id,
                target.shot_id,
                status=status,
            )
            failure_recorded = True
        except (KeyError, ValueError):
            failure_recorded = False
    return {
        "shot_id": target.shot_id,
        "shot_number": target.shot_number,
        "status": status,
        "job_id": job_id,
        "provider_calls_started": bool(response.get("provider_calls_started")),
        "block_count": len((response.get("safe_manifest") or {}).get("blocks") or []),
        "failure_recorded": failure_recorded,
        "manifest_state": manifest_state,
    }


def dry_run(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    targets = build_targets(store, project_id)
    compiled: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for target in targets:
        if target.skip_reason:
            skipped.append(target.__dict__)
            continue
        existing = load_video_admission_manifest(store, project_id, shot_id=target.shot_id)
        existing_state = str((existing.get("item") or {}).get("state") or "")
        if existing and existing_state != "reconcile_required":
            prompt = str((existing.get("source", {}).get("prompt_contract") or {}).get("provider_prompt") or "")
            compiled.append({
                "shot_id": target.shot_id,
                "shot_number": target.shot_number,
                "shot_label": target.shot_label,
                "generation_mode": target.generation_mode,
                "reference_count": target.reference_count,
                "manifest_id": existing["manifest_id"],
                "existing_state": existing_state,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest() if prompt else "",
                "shot1_policy_safe": (
                    target.shot_number != 1
                    or all(term not in prompt for term in ("坠落", "濒死", "恐惧", "创伤", "死亡", "伤害", "无伤害"))
                ),
            })
            continue
        preview = admission_command(
            store,
            project_id,
            target.shot_id,
            {
                "type": "create_new_round" if existing_state == "reconcile_required" else "compile",
                "shot_id": target.shot_id,
                "generation_mode": target.generation_mode,
                "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。" if target.generation_mode == REFERENCE_CONDITIONED else "仅在镜头明确要求从已批准首帧开始时使用。",
                "temporal_staging": temporal_staging_for_target(store, project_id, target),
                "allow_partial_references": True,
                "partial_reference_reason": (
                    "Direct batch production may proceed with approved identity/prop references "
                    "and textual scene grounding when a non-primary scene reference is not yet approved."
                ),
                "idempotency_key": f"video-direct-dry-{target.shot_id}",
            },
            confirm=False,
        )
        manifest = preview["result"]["manifest"]
        prompt = str((manifest.get("source", {}).get("prompt_contract") or {}).get("provider_prompt") or "")
        compiled.append({
            "shot_id": target.shot_id,
            "shot_number": target.shot_number,
            "shot_label": target.shot_label,
            "generation_mode": target.generation_mode,
            "reference_count": target.reference_count,
            "manifest_id": manifest["manifest_id"],
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "shot1_policy_safe": (
                target.shot_number != 1
                or all(term not in prompt for term in ("坠落", "濒死", "恐惧", "创伤", "死亡", "伤害", "无伤害"))
            ),
        })
    return {
        "project_id": project_id,
        "eligible": len(compiled),
        "skipped": len(skipped),
        "compiled": compiled,
        "skipped_items": skipped,
        "provider_pool": provider_pool_summary(),
        "target_concurrency": target_concurrency(),
        "provider_dispatch_count": 0,
    }


def execute_batch(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    *,
    concurrency: int,
    poll_interval_sec: float,
    max_poll_sec: int,
    promote: bool,
) -> dict[str, Any]:
    ledger = load_batch_ledger(store, project_id, run_id)
    targets = build_targets(store, project_id)
    ledger["targets"] = [target.__dict__ for target in targets]
    ledger["status"] = "running"
    save_batch_ledger(store, project_id, ledger)
    record_event(store, project_id, ledger, "batch_started", concurrency=concurrency, promote=promote)
    results: list[dict[str, Any]] = []
    queue = [target for target in targets if not target.skip_reason]
    queue.sort(
        key=lambda target: (
            _resume_priority(store, project_id, target),
            _defer_existing_safety_block(store, project_id, target),
            target.shot_number,
        )
    )
    skipped = [target for target in targets if target.skip_reason]
    for target in skipped:
        result = {"shot_id": target.shot_id, "shot_number": target.shot_number, "status": "skipped", "reason": target.skip_reason}
        results.append(result)
        record_event(store, project_id, ledger, "shot_skipped", **result)
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        pending = {}
        while queue or pending:
            while queue and len(pending) < concurrency:
                target = queue.pop(0)
                future = executor.submit(
                    execute_target,
                    store,
                    project_id,
                    run_id,
                    target,
                    poll_interval_sec=poll_interval_sec,
                    max_poll_sec=max_poll_sec,
                    promote=promote,
                )
                pending[future] = target
                record_event(store, project_id, ledger, "shot_started", shot_id=target.shot_id, shot_number=target.shot_number)
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                target = pending.pop(future)
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001 - every item must be isolated and recorded.
                    result = {
                        "shot_id": target.shot_id,
                        "shot_number": target.shot_number,
                        "status": "runner_error",
                        "error_type": type(exc).__name__,
                        "message": str(exc)[:240],
                    }
                results.append(result)
                record_event(store, project_id, ledger, "shot_finished", **result)
    ledger["status"] = "completed"
    ledger["results"] = results
    ledger["provider_dispatch_count"] = sum(1 for item in results if item.get("job_id") or item.get("candidate_id"))
    save_batch_ledger(store, project_id, ledger)
    return {
        "project_id": project_id,
        "run_id": run_id,
        "status": "completed",
        "concurrency": concurrency,
        "results": results,
        "counts": count_results(results),
        "ledger_path": str(batch_path(store, project_id, run_id)),
    }


def _defer_existing_safety_block(
    store: RuntimeStore,
    project_id: str,
    target: BatchTarget,
) -> int:
    manifest = load_video_admission_manifest(store, project_id, shot_id=target.shot_id)
    item = manifest.get("item") or {}
    if item.get("state") != "reconcile_required" or item.get("candidate") is not None:
        return 0
    if str(item.get("provider_task_fingerprint") or ""):
        return 0
    job_id = str(item.get("provider_job_id") or "")
    if not job_id:
        return 0
    safe_path = store.run_dir(project_id, job_id) / "video_generation_safe_manifest.json"
    if not safe_path.is_file():
        return 0
    safe_manifest = read_json(safe_path)
    blocks = [
        block for block in safe_manifest.get("blocks", [])
        if isinstance(block, Mapping)
    ]
    safety_blocked = any(
        int(block.get("provider_http_status") or 0) == 400
        and (
            str(block.get("provider_error_code") or "") == "sensitive_words_detected"
            or "content safety" in str(block.get("reason") or "").lower()
            or "sensitive" in str(block.get("reason") or "").lower()
        )
        for block in blocks
    )
    if (
        safety_blocked
        and safe_manifest.get("outputs") in (None, [])
        and not str(safe_manifest.get("provider_task_fingerprint") or "")
        and not str(safe_manifest.get("provider_task_id") or "")
        and not str(safe_manifest.get("task_id") or "")
    ):
        return 1
    return 0


def _resume_priority(
    store: RuntimeStore,
    project_id: str,
    target: BatchTarget,
) -> int:
    manifest = load_video_admission_manifest(store, project_id, shot_id=target.shot_id)
    state = str((manifest.get("item") or {}).get("state") or "")
    if state in {"reserved", "dispatch_prepared", "processing"}:
        return -1
    return 0


def count_results(results: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in results:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="AFS direct ProductionGraph video batch runner")
    parser.add_argument("--project-id", default=PROJECT_ID)
    parser.add_argument("--runtime-root", type=Path, default=default_runtime_root())
    parser.add_argument("--run-id", default=f"video-direct-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--concurrency", type=int, default=0)
    parser.add_argument("--poll-interval-sec", type=float, default=20.0)
    parser.add_argument("--max-poll-sec", type=int, default=1200)
    parser.add_argument("--promote-technical-pass", action="store_true")
    args = parser.parse_args()
    if args.dry_run == args.execute:
        raise SystemExit("choose exactly one of --dry-run or --execute")
    store = RuntimeStore(args.runtime_root)
    store.ensure_project_manifest(args.project_id)
    if args.dry_run:
        print(json.dumps(dry_run(store, args.project_id), ensure_ascii=False, indent=2))
        return
    concurrency = target_concurrency(args.concurrency or None)
    print(json.dumps({
        "event": "video_direct_batch_execute_start",
        "project_id": args.project_id,
        "run_id": args.run_id,
        "concurrency": concurrency,
        "provider_pool": provider_pool_summary(),
        "promote_technical_pass": bool(args.promote_technical_pass),
    }, ensure_ascii=False))
    result = execute_batch(
        store,
        args.project_id,
        args.run_id,
        concurrency=concurrency,
        poll_interval_sec=args.poll_interval_sec,
        max_poll_sec=args.max_poll_sec,
        promote=args.promote_technical_pass,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
