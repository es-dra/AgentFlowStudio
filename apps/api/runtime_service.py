from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from apps.api.runtime_cors import configure_runtime_cors
from apps.api.runtime_info import runtime_capabilities_payload, runtime_health_payload
from apps.api.runtime_artifacts import (
    asset_run_artifacts,
    feedback_ref,
    provider_artifacts,
    round_2_run_ref,
    two_round_artifacts,
    update_project_after_asset_run,
)
from apps.api.runtime_events import runtime_feedback_event
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import (
    load_round_1_job,
    optional_path,
    presence_ref,
    public_job_from_store,
    runtime_job,
    safe_job_id,
)
from apps.api.runtime_models import (
    AssetTestRunRequest,
    FeedbackRecordRequest,
    ProjectCreateRequest,
    ProviderValidationPlanRequest,
    TwoRoundValidateRequest,
)
from apps.api.runtime_prompt_memory_routes import register_runtime_prompt_memory_routes
from apps.api.runtime_provider_script_routes import register_runtime_provider_script_routes
from apps.api.runtime_keyframe_routes import register_runtime_keyframe_routes
from apps.api.runtime_tracing import (
    PROVIDER_PLAN_TOOL_GATE_STATE,
    artifact_refs,
    blocked_refs_from_blocks,
    safe_request_ref,
    write_run_trace,
)
from apps.api.runtime_store import RuntimeStore, read_json
from apps.api.runtime_v02 import register_runtime_v02_routes
from apps.api.runtime_studio_static import configure_studio_static
from agentflow.harness.json_io import write_json
from agentflow.memory.production_asset_provider_validation_gate import run_provider_validation_gate
from agentflow.memory.production_asset_test_run_harness import run_real_asset_test_harness
from agentflow.memory.production_asset_two_round_validation import run_two_round_context_runtime_validation


DEFAULT_RUNTIME_ROOT = Path("data/processed/runs/runtime_service")


def create_runtime_app(runtime_root: Path = DEFAULT_RUNTIME_ROOT) -> FastAPI:
    store = RuntimeStore(runtime_root)
    app = FastAPI(
        title="AgentFlow Runtime Service",
        version="0.2.0",
        summary="Local AFS API adapter for AFS Studio canvas integration.",
    )
    configure_runtime_cors(app)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return runtime_health_payload()

    @app.get("/capabilities")
    def capabilities() -> dict[str, Any]:
        return runtime_capabilities_payload()

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
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"project_id": project_id, "manifest": manifest, "artifact": ref}

    @app.get("/artifacts/{artifact_id}")
    def artifact(artifact_id: str) -> dict[str, Any]:
        try:
            return store.read_artifact(artifact_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="artifact not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/runs/{job_id}")
    def run_job(job_id: str) -> dict[str, Any]:
        try:
            return {"job": public_job_from_store(store, job_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc

    @app.post("/runs/asset-test")
    def asset_test_run(request: AssetTestRunRequest) -> dict[str, Any]:
        store.ensure_project_manifest(request.project_id)
        job_id = store.new_job_id("asset_test_run", request.project_id)
        output_dir = store.run_dir(request.project_id, job_id)
        try:
            report = run_real_asset_test_harness(
                loop_path=Path(request.loop),
                asset_profile_seed_path=Path(request.asset_profile_seed),
                feedback_json_path=Path(request.feedback_json),
                consistency_review_json_path=Path(request.consistency_review_json),
                output_dir=output_dir,
                promotion_decision=request.promotion_decision,
                promotion_rationale=request.promotion_rationale,
                generated_at=request.generated_at,
                decided_at=request.decided_at,
                reviewed_at=request.reviewed_at,
                project_materials_path=optional_path(request.project_materials),
                character_reference_image_path=optional_path(request.character_reference_image),
                reviewer_role=request.reviewer_role,
            )
        except Exception as exc:  # noqa: BLE001 - API returns structured local runtime failures.
            job = runtime_job(job_id, request.project_id, "asset_test_run", "failed", error=str(exc))
            store.write_job(job)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        artifacts = asset_run_artifacts(store, output_dir)
        status = "blocked" if report.get("blocks") else "succeeded"
        trace_path = write_run_trace(
            output_dir,
            project_id=request.project_id,
            job_id=job_id,
            action="asset_test_run",
            status=status,
            input_refs=[
                safe_request_ref("asset_profile_seed", request.asset_profile_seed),
                safe_request_ref("feedback_json", request.feedback_json),
                safe_request_ref("consistency_review_json", request.consistency_review_json),
                presence_ref("project_materials", request.project_materials),
                presence_ref("character_reference_image", request.character_reference_image),
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            blocked_refs=blocked_refs_from_blocks(report.get("blocks", [])),
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, request.project_id, "asset_test_run", status, artifacts=artifacts)
        job["_output_dir"] = output_dir.as_posix()
        public_job = store.write_job(job)
        update_project_after_asset_run(store, request.project_id, job_id, report, artifacts)
        return {"job": public_job, "report": report, "artifacts": artifacts, "flow": build_flow_summary(store, request.project_id)}

    @app.post("/runs/two-round-validate")
    def two_round_validate(request: TwoRoundValidateRequest) -> dict[str, Any]:
        round_1 = load_round_1_job(store, request.round_1_job_id)
        job_id = store.new_job_id("two_round_validate", request.project_id)
        output_dir = store.run_dir(request.project_id, job_id)
        try:
            report = run_two_round_context_runtime_validation(
                round_1_dir=Path(str(round_1["_output_dir"])),
                output_dir=output_dir,
                consistency_review_json_path=Path(request.consistency_review_json),
                generated_at=request.generated_at,
                reviewed_at=request.reviewed_at,
            )
        except Exception as exc:  # noqa: BLE001 - API returns structured local runtime failures.
            job = runtime_job(job_id, request.project_id, "two_round_validate", "failed", error=str(exc))
            store.write_job(job)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        artifacts = two_round_artifacts(store, output_dir)
        status = "succeeded" if report.get("runtime_verification_status") == "verified" else "blocked"
        trace_path = write_run_trace(
            output_dir,
            project_id=request.project_id,
            job_id=job_id,
            action="two_round_validate",
            status=status,
            input_refs=[
                {"role": "round_1_job_id", "ref": safe_job_id(request.round_1_job_id)},
                safe_request_ref("consistency_review_json", request.consistency_review_json),
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            blocked_refs=blocked_refs_from_blocks(report.get("blocked_refs", [])),
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, request.project_id, "two_round_validate", status, artifacts=artifacts)
        job["_output_dir"] = output_dir.as_posix()
        public_job = store.write_job(job)
        store.update_project_manifest(
            request.project_id,
            {"runs": [round_2_run_ref(job_id, status, artifacts["two_round_context_runtime_report"])]},
            status="ready_for_next_round" if status == "succeeded" else "blocked",
        )
        return {"job": public_job, "report": report, "artifacts": artifacts, "flow": build_flow_summary(store, request.project_id)}

    @app.post("/feedback")
    def record_feedback(request: FeedbackRecordRequest) -> dict[str, Any]:
        store.ensure_project_manifest(request.project_id)
        job_id = store.new_job_id("record_feedback", request.project_id)
        output_dir = store.feedback_dir / safe_job_id(request.project_id) / safe_job_id(job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        event = runtime_feedback_event(request.project_id, request.feedback, request.generated_at)
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

    @app.post("/provider/validation-plan")
    def provider_validation_plan(request: ProviderValidationPlanRequest) -> dict[str, Any]:
        store.ensure_project_manifest(request.project_id)
        job_id = store.new_job_id("provider_validation_plan", request.project_id)
        output_dir = store.run_dir(request.project_id, job_id)
        report = run_provider_validation_gate(
            asset_profile_seed_path=Path(request.asset_profile_seed),
            output_dir=output_dir,
            generated_at=request.generated_at,
            request_provider_validation=True,
            run_provider_validation=False,
            provider_config_path=optional_path(request.provider_config),
            project_materials_path=optional_path(request.project_materials),
            character_reference_image_path=optional_path(request.character_reference_image),
            image_service=request.image_service,
            video_service=request.video_service,
        )
        artifacts = provider_artifacts(store, output_dir)
        safe_manifest = read_json(output_dir / "provider_safe_manifest.json")
        status = "blocked" if safe_manifest.get("status") == "blocked" else "succeeded"
        trace_path = write_run_trace(
            output_dir,
            project_id=request.project_id,
            job_id=job_id,
            action="provider_validation_plan",
            status=status,
            input_refs=[
                safe_request_ref("asset_profile_seed", request.asset_profile_seed),
                presence_ref("provider_config", request.provider_config),
                presence_ref("project_materials", request.project_materials),
                presence_ref("character_reference_image", request.character_reference_image),
                {"role": "image_service", "ref": request.image_service},
                {"role": "video_service", "ref": request.video_service},
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            blocked_refs=blocked_refs_from_blocks(safe_manifest.get("blocks", [])),
            tool_gate_state=PROVIDER_PLAN_TOOL_GATE_STATE,
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, request.project_id, "provider_validation_plan", status, artifacts=artifacts)
        job["ui_summary"] = {
            "provider_gate": {
                "status": safe_manifest.get("status", status),
                "provider_calls_started": safe_manifest.get("provider_calls_started") is True,
                "blockers": safe_manifest.get("blockers") or safe_manifest.get("blocks") or [],
            }
        }
        public_job = store.write_job(job)
        return {"job": public_job, "report": report, "safe_manifest": safe_manifest, "artifacts": artifacts, "flow": build_flow_summary(store, request.project_id)}

    register_runtime_v02_routes(app, store)
    register_runtime_prompt_memory_routes(app, store)
    register_runtime_provider_script_routes(app, store)
    register_runtime_keyframe_routes(app, store)
    configure_studio_static(app)

    return app


__all__ = ("DEFAULT_RUNTIME_ROOT", "create_runtime_app")
