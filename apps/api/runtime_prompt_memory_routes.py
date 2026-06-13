from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from apps.api.runtime_artifacts import prompt_memory_artifacts
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_memory import PROMPT_MEMORY_NON_CLAIMS, build_prompt_optimization
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_tracing import artifact_refs, write_run_trace


def register_runtime_prompt_memory_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/prompt-optimizations")
    def prompt_optimization(project_id: str, request: PromptOptimizationRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("prompt_optimization", project_id)
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = build_prompt_optimization(store, project_id, request, output_dir)
            artifacts = prompt_memory_artifacts(store, output_dir)
            trace_path = write_run_trace(
                output_dir,
                project_id=project_id,
                job_id=job_id,
                action="prompt_optimization",
                status="succeeded",
                input_refs=[
                    {"role": "node_id", "ref": request.node_id or "not_provided"},
                    {"role": "node_type", "ref": request.node_type},
                    {"role": "prompt_text", "ref": "request_body.prompt_text"},
                    {"role": "generation_target", "ref": request.generation_target},
                    {"role": "target_platform", "ref": request.target_platform},
                ],
                generated_artifact_refs=artifact_refs(artifacts),
                tester_feedback={
                    "status": "node_prompt_optimization_created",
                    "memory_policy": "background_context_internal_only",
                },
                tool_gate_state={
                    "remote_llm": str(result["provider_gate"].get("status") or "blocked"),
                    "remote_asr": "blocked_by_default",
                    "remote_image": "not_requested",
                    "remote_video": "not_requested",
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        public_job = store.write_job(runtime_job(job_id, project_id, "prompt_optimization", "succeeded", artifacts=artifacts))
        return {
            "job": public_job,
            "ui_surface": "node_prompt_optimizer",
            "original_prompt": result["original_prompt"],
            "optimized_prompt": result["optimized_prompt"],
            "optimization_mode": result.get("optimization_mode", "not_applicable"),
            "user_prompt": result["user_prompt"],
            "user_prompt_sections": result["user_prompt_sections"],
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "context_bundle": result.get("context_bundle"),
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": result["safe_manifest"],
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
            "non_claims": PROMPT_MEMORY_NON_CLAIMS,
        }


__all__ = ("register_runtime_prompt_memory_routes",)
