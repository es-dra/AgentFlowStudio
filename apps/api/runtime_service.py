from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

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
from apps.api.runtime_keyframe_routes import register_runtime_keyframe_routes
from apps.api.runtime_image_assets import register_runtime_image_asset_routes
from apps.api.runtime_studio_state import register_runtime_studio_state_routes
from apps.api.runtime_visual_assets import register_runtime_visual_asset_routes
from apps.api.runtime_video_revision_routes import register_runtime_video_revision_routes
from apps.api.runtime_video_routes import register_runtime_video_routes
from apps.api.runtime_tracing import artifact_refs, write_run_trace
from apps.api.runtime_store import RuntimeStore, read_json, safe_id
from apps.api.runtime_v02 import register_runtime_v02_routes
from apps.api.runtime_studio_static import DEFAULT_STUDIO_ROOT, configure_studio_static, studio_static_status
from agentflow.harness.json_io import write_json


DEFAULT_RUNTIME_ROOT = Path("data/processed/runs/runtime_service")
LEGACY_RUNTIME_V02_ENV = "AFS_ENABLE_LEGACY_RUNTIME_V02"
TRUE_VALUES = {"1", "true", "yes", "on"}
QUALITY_FEEDBACK_METRICS = {
    "identity_similarity",
    "wardrobe_consistency",
    "scene_continuity",
    "text_or_watermark",
    "target_change_success",
}
SAFE_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")


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
                }
        except (ValueError, OSError):
            meta = {}
    return {**summary, "studio_state_meta": meta}


def create_runtime_app(runtime_root: Path = DEFAULT_RUNTIME_ROOT, studio_root: Path = DEFAULT_STUDIO_ROOT) -> FastAPI:
    store = RuntimeStore(runtime_root)
    app = FastAPI(
        title="AgentFlow Runtime Service",
        version="0.2.0",
        summary="Local AFS API adapter for AFS Studio canvas integration.",
    )
    configure_runtime_cors(app)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return runtime_health_payload(studio_static=studio_static_status(studio_root))

    @app.get("/capabilities")
    def capabilities() -> dict[str, Any]:
        return runtime_capabilities_payload()

    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        return {"projects": [_project_summary_with_studio_meta(store, item) for item in store.list_project_summaries()]}

    @app.post("/projects")
    def create_project(request: ProjectCreateRequest) -> dict[str, Any]:
        manifest = store.create_project_manifest(
            project_id=request.project_id,
            project_type=request.project_type,
            goal=request.goal,
            status=request.status,
        )
        ref = store.register_artifact(store.project_manifest_path(request.project_id), role="project_manifest")
        return {"project_id": request.project_id, "manifest": manifest, "artifact": ref, "flow": build_flow_summary(store, request.project_id)}

    @app.get("/projects/{project_id}/manifest")
    def project_manifest(project_id: str) -> dict[str, Any]:
        try:
            manifest = store.ensure_project_manifest(project_id)
            ref = store.register_artifact(store.project_manifest_path(project_id), role="project_manifest")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_project_manifest")) from exc
        return {"project_id": project_id, "manifest": manifest, "artifact": ref}

    @app.get("/artifacts/{artifact_id}")
    def artifact(artifact_id: str) -> dict[str, Any]:
        try:
            return store.read_artifact(artifact_id)
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
    def run_job(job_id: str) -> dict[str, Any]:
        try:
            return {"job": public_job_from_store(store, job_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc

    @app.post("/feedback")
    def record_feedback(request: FeedbackRecordRequest) -> dict[str, Any]:
        store.ensure_project_manifest(request.project_id)
        job_id = store.new_job_id("record_feedback", request.project_id)
        output_dir = store.feedback_dir / safe_job_id(request.project_id) / safe_job_id(job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        event = runtime_feedback_event(request.project_id, sanitize_runtime_feedback(request.feedback), request.generated_at)
        write_json(output_dir / "runtime_feedback_event.json", event)
        artifact_ref = store.register_artifact(output_dir / "runtime_feedback_event.json", role="runtime_feedback_event")
        artifacts = {"runtime_feedback_event": artifact_ref}
        trace_path = write_run_trace(
            output_dir,
            project_id=request.project_id,
            job_id=job_id,
            action="record_feedback",
            status="succeeded",
            input_refs=[{"role": "feedback", "ref": "request_body"}],
            generated_artifact_refs=artifact_refs(artifacts),
            tester_feedback={"status": "recorded_raw_evidence"},
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, request.project_id, "record_feedback", "succeeded", artifacts=artifacts)
        public_job = store.write_job(job)
        store.update_project_manifest(
            request.project_id,
            {"feedback_refs": [feedback_ref(artifact_ref, event.get("feedback_id", job_id))]},
            status="in_progress",
        )
        return {"job": public_job, "feedback_event": event, "artifact": artifact_ref, "flow": build_flow_summary(store, request.project_id)}

    if legacy_runtime_v02_enabled():
        register_runtime_v02_routes(app, store)
    register_runtime_prompt_memory_routes(app, store)
    register_runtime_provider_script_routes(app, store)
    register_runtime_image_asset_routes(app, store)
    register_runtime_visual_asset_routes(app, store)
    register_runtime_keyframe_routes(app, store)
    register_runtime_video_routes(app, store)
    register_runtime_video_revision_routes(app, store)
    register_runtime_generation_comparison_routes(app, store)
    register_runtime_studio_state_routes(app, store)
    configure_studio_static(app, studio_root)

    return app


def legacy_runtime_v02_enabled() -> bool:
    return os.environ.get(LEGACY_RUNTIME_V02_ENV, "").strip().lower() in TRUE_VALUES


def sanitize_runtime_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    if feedback.get("kind") == "studio_quality_feedback":
        ratings = {
            key: value
            for key, value in (feedback.get("ratings") or {}).items()
            if key in QUALITY_FEEDBACK_METRICS and _rating_or_none(value) is not None
        }
        return {
            "kind": "studio_quality_feedback",
            "node_id": _safe_token(feedback.get("node_id")),
            "node_type": _safe_token(feedback.get("node_type")),
            "video_job_id": _safe_token(feedback.get("video_job_id")),
            "video_revision_job_id": _safe_token(feedback.get("video_revision_job_id")),
            "artifact_ref": _safe_token(feedback.get("artifact_ref")),
            "safe_preview_ref": "runtime_preview_endpoint"
            if feedback.get("safe_preview_ref") == "runtime_preview_endpoint"
            else "none",
            "ratings": ratings,
            "target_change_success": _rating_or_none(feedback.get("target_change_success")),
            "drift_notes": _sanitize_feedback_text(feedback.get("drift_notes")),
            "prompt_char_count": _bounded_int(feedback.get("prompt_char_count")),
            "result_char_count": _bounded_int(feedback.get("result_char_count")),
            "raw_evidence_policy": "raw_evidence_not_memory",
            "feedback_is_memory": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safety_boundary": {
                "no_provider_raw": True,
                "no_signed_url": True,
                "no_local_path": True,
                "no_media_bytes": True,
            },
        }
    return {
        "kind": _safe_token(feedback.get("kind")) or "runtime_feedback",
        "note": _sanitize_feedback_text(feedback.get("note") or feedback.get("summary")),
        "raw_evidence_policy": "raw_evidence_not_memory",
        "feedback_is_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _safe_token(value: Any) -> str:
    return SAFE_TOKEN_RE.sub("_", str(value or "")).strip("_")[:120]


def _sanitize_feedback_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"Bearer\s+\S+", "Bearer <redacted>", text, flags=re.IGNORECASE)
    text = re.sub(r"[A-Za-z]:\\[^\s\"'<>]+", "<local-path-redacted>", text)
    text = re.sub(r"https?://[^\s\"'<>]+", "<url-redacted>", text)
    return text[:600]


def _rating_or_none(value: Any) -> int | None:
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None
    return rating if 1 <= rating <= 5 else None


def _bounded_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, 200_000))


__all__ = (
    "DEFAULT_RUNTIME_ROOT",
    "LEGACY_RUNTIME_V02_ENV",
    "create_runtime_app",
    "legacy_runtime_v02_enabled",
    "sanitize_runtime_feedback",
)
