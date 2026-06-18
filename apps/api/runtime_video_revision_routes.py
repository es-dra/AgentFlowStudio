from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException

from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_models import VideoRevisionRequest
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload
from apps.api.runtime_video_revision_context import (
    build_video_revision_algorithm_bundle,
    write_video_revision_algorithm_artifacts,
)


REMOTE_VIDEO_ENV = "AFS_ALLOW_REMOTE_VIDEO"
EXPERIMENTAL_VIDEO_REVISION_ENV = "AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION"
TRUE_VALUES = {"1", "true", "yes", "on"}
VIDEO_REVISION_NON_CLAIMS = [
    "experimental_contract_only",
    "best_effort_preservation",
    "not_pixel_identical_guarantee",
    "not_human_acceptance",
    "not_business_validation",
    "no_provider_submit_in_flag_closed_mode",
]


def register_runtime_video_revision_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/video-revisions/preflight")
    def video_revision_preflight_route(project_id: str, request: VideoRevisionRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            return video_revision_preflight(request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_revision")) from exc

    @app.post("/projects/{project_id}/video-revisions")
    def video_revision(project_id: str, request: VideoRevisionRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        if request.preflight_token:
            expected_preflight = video_revision_preflight(request)
            if request.preflight_token != expected_preflight.get("preflight_token"):
                raise HTTPException(status_code=409, detail=safe_error_detail("stale_preflight"))
        if request.candidate_count != 1:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_revision"))
        job_id = store.new_job_id("video_revision", project_id)
        output_dir = store.run_dir(project_id, job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            feature_flag = _feature_flag()
            video_gate = _video_gate()
            algorithm_bundle = build_video_revision_algorithm_bundle(
                project_id=project_id,
                request=request,
                feature_flag=feature_flag,
                provider_gate=video_gate,
            )
            result = _blocked_revision_result(project_id, request, feature_flag=feature_flag, video_gate=video_gate)
            result["safe_manifest"]["model_call_context_id"] = algorithm_bundle["model_call_context"]["context_id"]
            result["safe_manifest"]["model_request_plan_ref"] = "model_request_plan.json"
            result["safe_manifest"]["revision_plan_ref"] = "revision_plan.json"
            result["artifacts"] = write_video_revision_algorithm_artifacts(
                store,
                output_dir,
                safe_manifest=result["safe_manifest"],
                bundle=algorithm_bundle,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_revision")) from exc
        job = _write_video_revision_job(store, project_id, job_id, result)
        return _video_revision_response(project_id, job, result)


def video_revision_preflight(request: VideoRevisionRequest) -> dict[str, Any]:
    payload = {
        "schema_version": "afs_video_revision_preflight.v0.1",
        "experimental": True,
        "provider_calls_started": False,
        "requires_provider_gate": False,
        "feature_flag": _feature_flag(),
        "provider_gate": _video_gate(),
        "provider_capability_mode": request.provider_capability_mode,
        "preserve_policy": _preserve_policy(request),
        "base_video_job_id": request.base_video_job_id,
        "base_video_artifact_id": request.base_video_artifact_id,
        "base_lineage_root_job_id": _base_lineage_root_job_id(request),
        "parent_revision_job_id": request.parent_revision_job_id,
        "preserve_change_taxonomy": _preserve_change_taxonomy(request),
        "candidate_count": request.candidate_count,
        "preflight_token": _preflight_token(request),
        "non_claims": VIDEO_REVISION_NON_CLAIMS,
    }
    reject_unsafe_payload(payload)
    return payload


def _blocked_revision_result(
    project_id: str,
    request: VideoRevisionRequest,
    *,
    feature_flag: dict[str, str] | None = None,
    video_gate: dict[str, str] | None = None,
) -> dict[str, Any]:
    feature_flag = feature_flag or _feature_flag()
    video_gate = video_gate or _video_gate()
    if feature_flag["status"] == "blocked":
        blocks = [_feature_disabled_block()]
    elif video_gate["status"] == "blocked":
        blocks = [_gate_closed_block()]
    else:
        blocks = [_provider_not_implemented_block()]
    manifest = _safe_manifest(
        project_id,
        request,
        status="blocked",
        provider_calls_started=False,
        feature_flag=feature_flag,
        provider_gate=video_gate,
        blocks=blocks,
    )
    return {"status": "blocked", "safe_manifest": manifest}


def _safe_manifest(
    project_id: str,
    request: VideoRevisionRequest,
    *,
    status: str,
    provider_calls_started: bool,
    feature_flag: dict[str, str],
    provider_gate: dict[str, str],
    blocks: list[dict[str, str]],
) -> dict[str, Any]:
    manifest = {
        "schema_version": "afs_video_revision_safe_manifest.v0.1",
        "experimental": True,
        "status": status,
        "project_id": project_id,
        "provider": "registry",
        "capability": "video_revision",
        "provider_capability_mode": request.provider_capability_mode,
        "feature_flag": feature_flag,
        "provider_gate": provider_gate,
        "provider_calls_started": provider_calls_started,
        "blocks": blocks,
        "base_video_job_id": request.base_video_job_id,
        "base_video_artifact_id_present": bool(request.base_video_artifact_id),
        "base_lineage_root_job_id": _base_lineage_root_job_id(request),
        "parent_revision_job_id": request.parent_revision_job_id,
        "preserve_policy": _preserve_policy(request),
        "editable_targets": _normalized_list(request.editable_targets),
        "locked_aspect_count": len(_normalized_list(request.locked_aspects)),
        "temporal_scope": _safe_temporal_scope(request.temporal_scope),
        "revision_intent_length": len(request.revision_intent),
        "first_frame_image_asset_id": request.first_frame_image_asset_id,
        "last_frame_image_asset_id_present": bool(request.last_frame_image_asset_id),
        "candidate_count": request.candidate_count,
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "provider_urls_persisted": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": VIDEO_REVISION_NON_CLAIMS,
    }
    reject_unsafe_payload(manifest)
    return manifest


def _video_revision_response(project_id: str, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "job": job,
        "provider_gate": (result.get("safe_manifest") or {}).get("provider_gate") or _video_gate(),
        "provider_calls_started": bool((result.get("safe_manifest") or {}).get("provider_calls_started")),
        "safe_manifest": result.get("safe_manifest"),
        "artifacts": result.get("artifacts") or {},
        "model_call_context_id": (result.get("safe_manifest") or {}).get("model_call_context_id"),
        "candidate_previews": [],
        "flow": {"project_id": project_id},
        "non_claims": VIDEO_REVISION_NON_CLAIMS,
    }


def _write_video_revision_job(store: RuntimeStore, project_id: str, job_id: str, result: dict[str, Any]) -> dict[str, Any]:
    job = runtime_job(job_id, project_id, "video_revision", str(result["status"]), artifacts=result.get("artifacts") or {})
    job["ui_summary"] = {
        "video_revision": {
            "status": result["status"],
            "experimental": True,
            "provider_calls_started": bool((result.get("safe_manifest") or {}).get("provider_calls_started")),
        }
    }
    return store.write_job(job)


def _preflight_token(request: VideoRevisionRequest) -> str:
    request_payload = request.model_dump(mode="json", by_alias=True)
    request_payload.pop("generated_at", None)
    request_payload.pop("preflight_token", None)
    digest = {
        "kind": "video_revision",
        "schema_version": "afs_video_revision_preflight.v0.1",
        "request": request_payload,
        "feature_flag": _feature_flag(),
        "provider_gate": _video_gate(),
    }
    data = json.dumps(digest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:32]


def _preserve_change_taxonomy(request: VideoRevisionRequest) -> dict[str, Any]:
    return {
        "editable_targets": _normalized_list(request.editable_targets),
        "locked_aspects": _normalized_list(request.locked_aspects),
        "temporal_scope": _safe_temporal_scope(request.temporal_scope),
        "preserve_policy": _preserve_policy(request),
        "stability_goal": "change_requested_effects_first_keep_unrelated_aspects_as_stable_as_possible",
    }


def _base_lineage_root_job_id(request: VideoRevisionRequest) -> str:
    return request.base_lineage_root_job_id or request.base_video_job_id


def _preserve_policy(request: VideoRevisionRequest) -> str:
    value = str(request.preserve_policy or "best_effort").strip().lower()
    return value if value in {"best_effort", "strict_prompt_preserve"} else "best_effort"


def _normalized_list(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values or []:
        item = str(value or "").strip()[:80]
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result[:12]


def _safe_temporal_scope(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed = {}
    for key in ("kind", "start_frame", "end_frame", "start_sec", "end_sec", "note"):
        if key not in value:
            continue
        current = value[key]
        if isinstance(current, (int, float, str, bool)) or current is None:
            allowed[key] = current
    return allowed


def _feature_flag() -> dict[str, str]:
    status = "enabled" if os.environ.get(EXPERIMENTAL_VIDEO_REVISION_ENV, "").strip().lower() in TRUE_VALUES else "blocked"
    return {"env": EXPERIMENTAL_VIDEO_REVISION_ENV, "status": status}


def _video_gate() -> dict[str, str]:
    status = "ready_not_run" if os.environ.get(REMOTE_VIDEO_ENV, "").strip().lower() in TRUE_VALUES else "blocked"
    return {"capability": "video", "env": REMOTE_VIDEO_ENV, "status": status}


def _feature_disabled_block() -> dict[str, str]:
    return {
        "block_id": "experimental_video_revision_disabled",
        "reason": f"Set {EXPERIMENTAL_VIDEO_REVISION_ENV}=true only for an explicit video revision drill.",
        "required_gate": EXPERIMENTAL_VIDEO_REVISION_ENV,
    }


def _gate_closed_block() -> dict[str, str]:
    return {
        "block_id": "remote_video_gate_closed",
        "reason": f"Set {REMOTE_VIDEO_ENV}=true only for an explicit video provider smoke.",
        "required_gate": REMOTE_VIDEO_ENV,
    }


def _provider_not_implemented_block() -> dict[str, str]:
    return {
        "block_id": "video_revision_provider_not_implemented",
        "reason": "Current provider path is I2V only; localized video revision is a best-effort experimental contract.",
        "required_gate": EXPERIMENTAL_VIDEO_REVISION_ENV,
    }


__all__ = ("EXPERIMENTAL_VIDEO_REVISION_ENV", "register_runtime_video_revision_routes", "video_revision_preflight")
