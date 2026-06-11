from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from apps.api.runtime_artifacts import keyframe_generation_artifacts
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_keyframes import KEYFRAME_NON_CLAIMS, build_keyframe_generation
from apps.api.runtime_models import KeyframeGenerationRequest
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_tracing import artifact_refs, blocked_refs_from_blocks, write_run_trace


def register_runtime_keyframe_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/keyframe-generations")
    def keyframe_generation(project_id: str, request: KeyframeGenerationRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("keyframe_generation", project_id)
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = build_keyframe_generation(store, project_id, request, output_dir)
            artifacts = keyframe_generation_artifacts(store, output_dir)
            safe_manifest = dict(result["safe_manifest"])
            status = str(result["status"])
            trace_path = write_run_trace(
                output_dir,
                project_id=project_id,
                job_id=job_id,
                action="keyframe_generation",
                status=status,
                input_refs=[
                    {"role": "node_id", "ref": request.node_id or "not_provided"},
                    {"role": "prompt_text", "ref": "request_body.prompt_text"},
                    {"role": "target_platform", "ref": request.target_platform},
                    {"role": "aspect_ratio", "ref": request.aspect_ratio},
                    {"role": "candidate_count", "ref": str(request.candidate_count)},
                ],
                generated_artifact_refs=artifact_refs(artifacts),
                blocked_refs=blocked_refs_from_blocks(safe_manifest.get("blocks", [])),
                tester_feedback={
                    "status": "keyframe_request_created",
                    "provider_policy": "image_gate_required",
                },
                tool_gate_state=dict(result["tool_gate_state"]),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, project_id, "keyframe_generation", status, artifacts=artifacts)
        job["ui_summary"] = {
            "provider_gate": {
                "status": safe_manifest.get("status", status),
                "provider_calls_started": result["provider_calls_started"],
                "blockers": safe_manifest.get("blocks") or [],
            }
        }
        public_job = store.write_job(job)
        return {
            "job": public_job,
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": safe_manifest,
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
            "non_claims": KEYFRAME_NON_CLAIMS,
        }


__all__ = ("register_runtime_keyframe_routes",)
