from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from agentflow.algorithms.asset_card_drafting import draft_asset_card, draft_id_from_refs
from agentflow.algorithms.fixed_asset_memory import build_video_asset_record, public_video_asset
from agentflow.algorithms.provider_gate_manifest import blocked_manifest, provider_gate_status
from agentflow.harness.json_io import write_json
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_image_assets import image_asset_metadata
from apps.api.runtime_jobs import runtime_job
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
            _validate_asset_card_draft_request(store, project_id, request)
            gate = provider_gate_status("vision")
            if gate.status != "open":
                safe_manifest = blocked_manifest(
                    action="asset_card_draft",
                    capability="vision",
                    required_gate=gate.required_gate,
                    failure_class="remote_vision_gate_closed",
                    provider_service_id=request.provider_service_id,
                )
                artifacts = _write_asset_card_artifacts(store, output_dir, safe_manifest=safe_manifest, draft=None)
                trace_path = write_run_trace(
                    output_dir,
                    project_id=project_id,
                    job_id=job_id,
                    action="asset_card_draft",
                    status="blocked",
                    input_refs=_draft_input_refs(request),
                    generated_artifact_refs=artifact_refs(artifacts),
                    blocked_refs=blocked_refs_from_blocks(safe_manifest.get("blocks") or []),
                    tester_feedback={"status": "vision_gate_closed"},
                    tool_gate_state=_vision_gate_state("blocked_by_default"),
                )
                artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
                job = runtime_job(job_id, project_id, "asset_card_draft", "blocked", artifacts=artifacts)
                public_job = store.write_job(job)
                return {
                    "job": public_job,
                    "provider_gate": gate.public(),
                    "provider_calls_started": False,
                    "safe_manifest": safe_manifest,
                    "draft": None,
                    "artifacts": artifacts,
                    "flow": build_flow_summary(store, project_id),
                }

            refs_for_id = [*request.source_image_asset_refs, *request.sampled_image_asset_refs]
            if request.source_video_artifact_id:
                refs_for_id.append(request.source_video_artifact_id)
            draft = draft_asset_card(
                asset_type=request.asset_type,
                project_id=project_id,
                draft_id=draft_id_from_refs(project_id, request.generated_at, refs_for_id),
                source_image_asset_refs=request.source_image_asset_refs,
                sampled_image_asset_refs=request.sampled_image_asset_refs,
                source_video_artifact_id=request.source_video_artifact_id,
                prompt_text=request.prompt_text,
                provider_service_id=request.provider_service_id,
            )
            reject_unsafe_payload(draft)
            safe_manifest = dict(draft["safe_manifest"])
            artifacts = _write_asset_card_artifacts(store, output_dir, safe_manifest=safe_manifest, draft=draft)
            trace_path = write_run_trace(
                output_dir,
                project_id=project_id,
                job_id=job_id,
                action="asset_card_draft",
                status="succeeded",
                input_refs=_draft_input_refs(request),
                generated_artifact_refs=artifact_refs(artifacts),
                tester_feedback={"status": "draft_recorded_not_fixed_asset"},
                tool_gate_state=_vision_gate_state("allowed"),
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
    if request.asset_type in {"character", "scene"} and not request.source_image_asset_refs:
        raise ValueError("source_image_asset_refs is required")
    if request.asset_type == "video" and not request.source_video_artifact_id:
        raise ValueError("source_video_artifact_id is required")
    for image_ref in image_refs:
        image_asset_metadata(store, project_id, image_ref)
    if request.source_video_artifact_id and safe_id(request.source_video_artifact_id) != request.source_video_artifact_id:
        raise ValueError("source_video_artifact_id must be a safe artifact id")


def _write_asset_card_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    *,
    safe_manifest: dict[str, Any],
    draft: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    reject_unsafe_payload(safe_manifest)
    write_json(output_dir / "asset_card_draft_safe_manifest.json", safe_manifest)
    artifacts = {
        "asset_card_draft_safe_manifest": store.register_artifact(
            output_dir / "asset_card_draft_safe_manifest.json",
            role="asset_card_draft_safe_manifest",
        )
    }
    if draft is not None:
        reject_unsafe_payload(draft)
        write_json(output_dir / "asset_card_draft.json", draft)
        artifacts["asset_card_draft"] = store.register_artifact(output_dir / "asset_card_draft.json", role="asset_card_draft")
    return artifacts


def _draft_input_refs(request: AssetCardDraftRequest) -> list[dict[str, str]]:
    refs = [
        {"role": "asset_type", "ref": request.asset_type},
        {"role": "node_id", "ref": request.node_id or "not_provided"},
        {"role": "provider_service_id", "ref": request.provider_service_id},
    ]
    refs.extend({"role": "source_image_asset_ref", "ref": item} for item in request.source_image_asset_refs)
    refs.extend({"role": "sampled_image_asset_ref", "ref": item} for item in request.sampled_image_asset_refs)
    if request.source_video_artifact_id:
        refs.append({"role": "source_video_artifact_id", "ref": request.source_video_artifact_id})
    return refs


def _vision_gate_state(value: str) -> dict[str, str]:
    return {
        "remote_llm": "blocked_by_default",
        "remote_asr": "blocked_by_default",
        "remote_image": "blocked_by_default",
        "remote_video": "blocked_by_default",
        "remote_vision": value,
    }


def _server_now() -> str:
    return datetime.now(UTC).isoformat()


def _video_asset_path(store: RuntimeStore, project_id: str, asset_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "video_assets" / safe_id(asset_id) / "video_asset.json"


__all__ = ("register_runtime_asset_card_routes",)
