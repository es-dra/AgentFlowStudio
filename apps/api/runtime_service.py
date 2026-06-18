from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from agentflow.algorithms.quality_feedback_scoring import sanitize_quality_feedback
from agentflow.harness.json_io import write_json
from apps.api.runtime_cors import configure_runtime_cors
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_info import runtime_capabilities_payload, runtime_health_payload
from apps.api.runtime_artifacts import feedback_ref
from apps.api.runtime_events import runtime_feedback_event
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import (
    public_job_from_store,
    runtime_job,
    safe_job_id,
)
from apps.api.runtime_models import (
    FeedbackRecordRequest,
    ProjectCreateRequest,
)
from apps.api.runtime_prompt_memory_routes import register_runtime_prompt_memory_routes
from apps.api.runtime_provider_script_routes import register_runtime_provider_script_routes
from apps.api.runtime_generation_comparisons import register_runtime_generation_comparison_routes
from apps.api.runtime_company_os import register_runtime_company_os_routes
from apps.api.runtime_keyframe_routes import register_runtime_keyframe_routes
from apps.api.runtime_image_assets import register_runtime_image_asset_routes
from apps.api.runtime_asset_card_drafts import register_runtime_asset_card_routes
from apps.api.runtime_studio_state import register_runtime_studio_state_routes
from apps.api.runtime_visual_assets import register_runtime_visual_asset_routes
from apps.api.runtime_video_revision_routes import register_runtime_video_revision_routes
from apps.api.runtime_video_routes import register_runtime_video_routes
from apps.api.runtime_tracing import artifact_refs, write_run_trace
from apps.api.runtime_store import RuntimeStore, read_json, safe_id
from apps.api.runtime_threadpool_compat import configure_runtime_threadpool_compat
from apps.api.runtime_auth import (
    RuntimeAuthStore,
    configure_runtime_auth_middleware,
    register_runtime_auth_routes,
)
from apps.api.runtime_v02 import register_runtime_v02_routes
from apps.api.runtime_studio_static import (
    DEFAULT_SITE_ROOT,
    DEFAULT_STUDIO_ROOT,
    configure_site_static,
    configure_studio_static,
    studio_static_status,
)


DEFAULT_RUNTIME_ROOT = Path("data/processed/runs/runtime_service")
LEGACY_RUNTIME_V02_ENV = "AFS_ENABLE_LEGACY_RUNTIME_V02"
TRUE_VALUES = {"1", "true", "yes", "on"}


def _project_summary_with_studio_meta(store: RuntimeStore, summary: dict[str, Any]) -> dict[str, Any]:
    project_id = str(summary.get("project_id") or "")
    path = store.projects_dir / safe_id(project_id) / "studio_state.json"
    meta: dict[str, Any] = {}
    if path.is_file():
        try:
            payload = read_json(path)
            state = payload.get("state")
            if isinstance(state, dict) and isinstance(state.get("meta"), dict):
                meta = {
                    "projectName": state["meta"].get("projectName", ""),
                    "canvasName": state["meta"].get("canvasName", ""),
                    "seq": state["meta"].get("seq", 1),
                    "updated_at": state["meta"].get("updated_at", ""),
                    "state_version": payload.get("state_version", ""),
                    "saved_at": payload.get("saved_at", ""),
                }
        except (ValueError, OSError):
            meta = {}
    return {**summary, "studio_state_meta": meta}


def create_runtime_app(
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    studio_root: Path = DEFAULT_STUDIO_ROOT,
    site_root: Path = DEFAULT_SITE_ROOT,
) -> FastAPI:
    configure_runtime_threadpool_compat()
    store = RuntimeStore(runtime_root)
    auth = RuntimeAuthStore(store)
    app = FastAPI(
        title="AgentFlow Runtime Service",
        version="0.2.0",
        summary="Local AFS API adapter for AFS Studio canvas integration.",
    )
    configure_runtime_cors(app)
    configure_runtime_auth_middleware(app, auth)
    register_runtime_auth_routes(app, auth)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return runtime_health_payload(
            runtime_root=runtime_root,
            studio_static=studio_static_status(studio_root),
        )

    @app.get("/capabilities")
    def capabilities() -> dict[str, Any]:
        return runtime_capabilities_payload()

    @app.get("/projects")
    def list_projects(request: Request) -> dict[str, Any]:
        summaries = [_project_summary_with_studio_meta(store, item) for item in store.list_project_summaries()]
        if auth.enabled():
            user = auth.require_user(request)
            summaries = auth.filter_project_summaries(str(user["user_id"]), summaries)
        return {"projects": summaries}

    @app.post("/projects")
    def create_project(request: Request, body: ProjectCreateRequest) -> dict[str, Any]:
        user = auth.require_user(request) if auth.enabled() else None
        if user:
            owner = auth.project_owner(body.project_id)
            if owner and owner != str(user["user_id"]):
                raise HTTPException(status_code=403, detail="project access denied")
        manifest = store.create_project_manifest(
            project_id=body.project_id,
            project_type=body.project_type,
            goal=body.goal,
            status=body.status,
        )
        if user:
            auth.register_project_owner(body.project_id, str(user["user_id"]))
        ref = store.register_artifact(store.project_manifest_path(body.project_id), role="project_manifest")
        return {"project_id": body.project_id, "manifest": manifest, "artifact": ref, "flow": build_flow_summary(store, body.project_id)}

    @app.get("/projects/{project_id}/manifest")
    def project_manifest(project_id: str) -> dict[str, Any]:
        try:
            manifest = store.ensure_project_manifest(project_id)
            ref = store.register_artifact(store.project_manifest_path(project_id), role="project_manifest")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_project_manifest")) from exc
        return {"project_id": project_id, "manifest": manifest, "artifact": ref}

    @app.get("/artifacts/{artifact_id}")
    def artifact(artifact_id: str, request: Request) -> dict[str, Any]:
        try:
            artifact_payload = store.read_artifact(artifact_id)
            _enforce_payload_project_access(auth, request, artifact_payload)
            return artifact_payload
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="artifact not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_artifact")) from exc

    @app.post("/runs/asset-test", include_in_schema=False)
    @app.post("/runs/two-round-validate", include_in_schema=False)
    @app.post("/provider/validation-plan", include_in_schema=False)
    def retired_production_memory_http_route() -> None:
        raise HTTPException(status_code=404, detail="route not found")

    @app.get("/runs/{job_id}")
    def run_job(job_id: str, request: Request) -> dict[str, Any]:
        try:
            job = public_job_from_store(store, job_id)
            _enforce_project_access(auth, request, str(job.get("project_id", "")))
            return {"job": job}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc

    @app.post("/feedback")
    def record_feedback(request: Request, body: FeedbackRecordRequest) -> dict[str, Any]:
        _enforce_project_access(auth, request, body.project_id)
        store.ensure_project_manifest(body.project_id)
        job_id = store.new_job_id("record_feedback", body.project_id)
        output_dir = store.feedback_dir / safe_job_id(body.project_id) / safe_job_id(job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        event = runtime_feedback_event(body.project_id, sanitize_runtime_feedback(body.feedback), body.generated_at)
        write_json(output_dir / "runtime_feedback_event.json", event)
        artifact_ref = store.register_artifact(output_dir / "runtime_feedback_event.json", role="runtime_feedback_event")
        artifacts = {"runtime_feedback_event": artifact_ref}
        trace_path = write_run_trace(
            output_dir,
            project_id=body.project_id,
            job_id=job_id,
            action="record_feedback",
            status="succeeded",
            input_refs=[{"role": "feedback", "ref": "request_body"}],
            generated_artifact_refs=artifact_refs(artifacts),
            tester_feedback={"status": "recorded_raw_evidence"},
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, body.project_id, "record_feedback", "succeeded", artifacts=artifacts)
        public_job = store.write_job(job)
        store.update_project_manifest(
            body.project_id,
            {"feedback_refs": [feedback_ref(artifact_ref, event.get("feedback_id", job_id))]},
            status="in_progress",
        )
        return {"job": public_job, "feedback_event": event, "artifact": artifact_ref, "flow": build_flow_summary(store, body.project_id)}

    if legacy_runtime_v02_enabled():
        register_runtime_v02_routes(app, store)
    register_runtime_company_os_routes(app)
    register_runtime_prompt_memory_routes(app, store)
    register_runtime_provider_script_routes(app, store)
    register_runtime_image_asset_routes(app, store)
    register_runtime_asset_card_routes(app, store)
    register_runtime_visual_asset_routes(app, store)
    register_runtime_keyframe_routes(app, store)
    register_runtime_video_routes(app, store)
    register_runtime_video_revision_routes(app, store)
    register_runtime_generation_comparison_routes(app, store)
    register_runtime_studio_state_routes(app, store)
    configure_site_static(app, site_root)
    configure_studio_static(app, studio_root)

    return app


def legacy_runtime_v02_enabled() -> bool:
    return os.environ.get(LEGACY_RUNTIME_V02_ENV, "").strip().lower() in TRUE_VALUES


def sanitize_runtime_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    return sanitize_quality_feedback(feedback)


def _enforce_project_access(auth: RuntimeAuthStore, request: Request, project_id: str) -> None:
    if not auth.enabled():
        return
    user = auth.require_user(request)
    if not project_id or not auth.user_can_access_project(str(user["user_id"]), project_id):
        raise HTTPException(status_code=403, detail="project access denied")


def _enforce_payload_project_access(auth: RuntimeAuthStore, request: Request, payload: dict[str, Any]) -> None:
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    project_id = str(body.get("project_id", "") if isinstance(body, dict) else "")
    if project_id:
        _enforce_project_access(auth, request, project_id)


__all__ = (
    "DEFAULT_RUNTIME_ROOT",
    "LEGACY_RUNTIME_V02_ENV",
    "create_runtime_app",
    "legacy_runtime_v02_enabled",
    "sanitize_runtime_feedback",
)
