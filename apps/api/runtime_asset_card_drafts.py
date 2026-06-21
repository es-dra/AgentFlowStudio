from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from agentflow.algorithms.asset_card_drafting import draft_asset_card, draft_id_from_refs
from agentflow.algorithms.fixed_asset_memory import build_video_asset_record, public_video_asset
from agentflow.algorithms.provider_gate_manifest import blocked_manifest, provider_gate_status
from agentflow.algorithms.request_projection import build_request_plan
from agentflow.algorithms.visual_understanding import normalize_visual_observation
from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from apps.api.runtime_asset_card_artifacts import draft_input_refs, vision_gate_state, write_asset_card_artifacts
from apps.api.runtime_asset_card_observation import (
    dispatch_visual_inspection,
    draft_prompt_from_observation,
    normalize_asset_card_provider_service,
    provider_observation_for_asset_card,
    vision_provider_constraints,
)
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_image_assets import image_asset_metadata
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_model_call_context import visual_inspect_model_call_context
from apps.api.runtime_models import AssetCardDraftRequest, VideoAssetPromoteRequest
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload, safe_id
from apps.api.runtime_tracing import artifact_refs, blocked_refs_from_blocks, write_run_trace


def register_runtime_asset_card_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/asset-card-drafts")
    def create_asset_card_draft(project_id: str, request: AssetCardDraftRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("asset_card_draft", project_id)
        output_dir = store.run_dir(project_id, job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            normalize_asset_card_provider_service(request)
            _validate_asset_card_draft_request(store, project_id, request)
            gate = provider_gate_status("vision")
            model_call_context = visual_inspect_model_call_context(
                project_id=project_id,
                request=request,
                provider_constraints=vision_provider_constraints(request, gate.public()),
            )
            model_request_plan = build_request_plan(
                model_call_context=model_call_context,
                canonical_brief={"canonical_prompt": request.prompt_text},
                provider_service_id=request.provider_service_id,
            )
            if gate.status != "open":
                return _blocked_asset_card_response(
                    store,
                    project_id=project_id,
                    job_id=job_id,
                    output_dir=output_dir,
                    request=request,
                    gate=gate.public(),
                    model_call_context=model_call_context,
                    model_request_plan=model_request_plan,
                    failure_class="remote_vision_gate_closed",
                    reason="remote provider gate is closed",
                    tester_status="vision_gate_closed",
                )

            refs_for_id = [*request.source_image_asset_refs, *request.sampled_image_asset_refs]
            if request.source_video_artifact_id:
                refs_for_id.append(request.source_video_artifact_id)
            try:
                provider_result = dispatch_visual_inspection(store, project_id, request, output_dir)
            except ModelGatewayError as exc:
                return _blocked_asset_card_response(
                    store,
                    project_id=project_id,
                    job_id=job_id,
                    output_dir=output_dir,
                    request=request,
                    gate=gate.public(),
                    model_call_context=model_call_context,
                    model_request_plan=model_request_plan,
                    failure_class="remote_vision_provider_not_ready",
                    reason=_safe_provider_reason(str(exc)),
                    tester_status="vision_provider_not_ready",
                )
            provider_observation = provider_observation_for_asset_card(request, provider_result)
            visual_observation = normalize_visual_observation(
                project_id=project_id,
                observation_id=f"vu_{job_id}",
                source_refs={
                    "image_asset_refs": [*request.source_image_asset_refs, *request.sampled_image_asset_refs],
                    "video_artifact_id": request.source_video_artifact_id,
                },
                provider_observation=provider_observation,
                project_need={
                    "asset_types": [request.asset_type],
                    "focus": "draft_asset_card",
                },
            )
            draft_prompt = draft_prompt_from_observation(request, provider_observation)
            draft = draft_asset_card(
                asset_type=request.asset_type,
                project_id=project_id,
                draft_id=draft_id_from_refs(project_id, request.generated_at, refs_for_id),
                source_image_asset_refs=request.source_image_asset_refs,
                sampled_image_asset_refs=request.sampled_image_asset_refs,
                source_video_artifact_id=request.source_video_artifact_id,
                prompt_text=draft_prompt,
                provider_service_id=request.provider_service_id,
            )
            draft["visual_observation_ref"] = "visual_understanding_observation.json"
            reject_unsafe_payload(draft)
            safe_manifest = dict(draft["safe_manifest"])
            safe_manifest["model_call_context_id"] = model_call_context["context_id"]
            safe_manifest["model_request_plan_ref"] = "model_request_plan.json"
            safe_manifest["visual_understanding_observation_ref"] = "visual_understanding_observation.json"
            artifacts = write_asset_card_artifacts(
                store,
                output_dir,
                safe_manifest=safe_manifest,
                draft=draft,
                model_call_context=model_call_context,
                model_request_plan=model_request_plan,
                visual_observation=visual_observation,
            )
            trace_path = write_run_trace(
                output_dir,
                project_id=project_id,
                job_id=job_id,
                action="asset_card_draft",
                status="succeeded",
                input_refs=draft_input_refs(request),
                generated_artifact_refs=artifact_refs(artifacts),
                tester_feedback={"status": "draft_recorded_not_fixed_asset"},
                tool_gate_state=vision_gate_state("allowed"),
            )
            artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_asset_card_draft")) from exc
        job = runtime_job(job_id, project_id, "asset_card_draft", "succeeded", artifacts=artifacts)
        public_job = store.write_job(job)
        return {
            "job": public_job,
            "provider_gate": provider_gate_status("vision", enabled=True).public(),
            "provider_calls_started": True,
            "safe_manifest": safe_manifest,
            "draft": draft,
            "artifacts": artifacts,
            "model_call_context_id": model_call_context["context_id"],
            "flow": build_flow_summary(store, project_id),
        }

    @app.post("/projects/{project_id}/video-assets/promote")
    def promote_video_asset(project_id: str, request: VideoAssetPromoteRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            if not request.summary.strip():
                raise ValueError("summary is required")
            record = build_video_asset_record(
                project_id=project_id,
                asset_id=f"vasset_{uuid4().hex[:12]}",
                request=request,
                created_at=_server_now(),
                server_recorded_at=_server_now(),
            )
            reject_unsafe_payload(record)
            path = _video_asset_path(store, project_id, str(record["asset_id"]))
            path.parent.mkdir(parents=True, exist_ok=True)
            write_json(path, record)
            artifact = store.register_artifact(path, role="video_asset")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_asset")) from exc
        return {"asset": public_video_asset(record), "artifact": artifact, "flow": build_flow_summary(store, project_id)}


def _validate_asset_card_draft_request(store: RuntimeStore, project_id: str, request: AssetCardDraftRequest) -> None:
    image_refs = [*request.source_image_asset_refs, *request.sampled_image_asset_refs]
    if request.asset_type in {"character", "scene", "prop"} and not request.source_image_asset_refs:
        raise ValueError("source_image_asset_refs is required")
    if request.asset_type == "video" and not request.source_video_artifact_id:
        raise ValueError("source_video_artifact_id is required")
    for image_ref in image_refs:
        image_asset_metadata(store, project_id, image_ref)
    if request.source_video_artifact_id and safe_id(request.source_video_artifact_id) != request.source_video_artifact_id:
        raise ValueError("source_video_artifact_id must be a safe artifact id")


def _blocked_asset_card_response(
    store: RuntimeStore,
    *,
    project_id: str,
    job_id: str,
    output_dir: Path,
    request: AssetCardDraftRequest,
    gate: dict[str, str],
    model_call_context: dict[str, Any],
    model_request_plan: dict[str, Any],
    failure_class: str,
    reason: str,
    tester_status: str,
) -> dict[str, Any]:
    safe_manifest = blocked_manifest(
        action="asset_card_draft",
        capability="vision",
        required_gate=gate.get("required_gate") or "AFS_ALLOW_REMOTE_VISION",
        failure_class=failure_class,
        provider_service_id=request.provider_service_id,
    )
    safe_manifest["blocks"][0]["reason"] = reason
    safe_manifest["model_call_context_id"] = model_call_context["context_id"]
    safe_manifest["model_request_plan_ref"] = "model_request_plan.json"
    artifacts = write_asset_card_artifacts(
        store,
        output_dir,
        safe_manifest=safe_manifest,
        draft=None,
        model_call_context=model_call_context,
        model_request_plan=model_request_plan,
        visual_observation=None,
    )
    trace_path = write_run_trace(
        output_dir,
        project_id=project_id,
        job_id=job_id,
        action="asset_card_draft",
        status="blocked",
        input_refs=draft_input_refs(request),
        generated_artifact_refs=artifact_refs(artifacts),
        blocked_refs=blocked_refs_from_blocks(safe_manifest.get("blocks") or []),
        tester_feedback={"status": tester_status},
        tool_gate_state=vision_gate_state("blocked_by_default" if failure_class == "remote_vision_gate_closed" else "provider_not_ready"),
    )
    artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
    job = runtime_job(job_id, project_id, "asset_card_draft", "blocked", artifacts=artifacts)
    return {
        "job": store.write_job(job),
        "provider_gate": gate,
        "provider_calls_started": False,
        "safe_manifest": safe_manifest,
        "draft": None,
        "artifacts": artifacts,
        "model_call_context_id": model_call_context["context_id"],
        "flow": build_flow_summary(store, project_id),
    }


def _safe_provider_reason(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "vision provider configuration is not ready"
    return " ".join(value.split())[:160] or "vision provider is not ready"


def _server_now() -> str:
    return datetime.now(UTC).isoformat()


def _video_asset_path(store: RuntimeStore, project_id: str, asset_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "video_assets" / safe_id(asset_id) / "video_asset.json"


__all__ = ("register_runtime_asset_card_routes",)
