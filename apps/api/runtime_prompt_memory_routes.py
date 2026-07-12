from __future__ import annotations

from typing import Any

import time

from fastapi import FastAPI, HTTPException, Request

from apps.api.runtime_artifacts import prompt_memory_artifacts
from apps.api.runtime_errors import safe_exception_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_creative_runtime_contract import public_prompt_creative_runtime_contract_summary
from apps.api.runtime_logging import (
    client_request_id_from_request,
    log_business_event,
    request_id_from_request,
    studio_node_id_from_request,
    studio_node_type_from_request,
    user_action_from_request,
)
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_model_call_context import public_model_call_context_summary
from apps.api.runtime_prompt_memory import (
    PROMPT_MEMORY_NON_CLAIMS,
    PromptOptimizationUnavailable,
    build_prompt_optimization,
)
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_tracing import artifact_refs, write_run_trace


def register_runtime_prompt_memory_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/prompt-optimizations")
    def prompt_optimization(project_id: str, request: PromptOptimizationRequest, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        studio_node_id = studio_node_id_from_request(http_request) or request.node_id or ""
        studio_node_type = studio_node_type_from_request(http_request) or request.node_type
        user_action = user_action_from_request(http_request) or "click_optimize_prompt"
        log_business_event(
            "prompt_optimization_started",
            file_log_domain="prompt",
            file_log_event="optimize_start",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=studio_node_id,
            action="prompt_optimization",
            stage="start",
            user_action=user_action,
            studio_node_type=studio_node_type,
            generation_target=request.generation_target,
        )
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("prompt_optimization", project_id)
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = build_prompt_optimization(
                store,
                project_id,
                request,
                output_dir,
                request_id=request_id,
                client_request_id=client_request_id,
                user_action=user_action,
                studio_node_type=studio_node_type,
            )
            artifact_started = time.perf_counter()
            log_business_event(
                "prompt_optimization_artifact_collection_started",
                file_log_domain="prompt",
                file_log_event="artifact_collection_start",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=studio_node_id,
                action="prompt_optimization",
                stage="artifact_collection_start",
                user_action=user_action,
                studio_node_type=studio_node_type,
            )
            artifacts = prompt_memory_artifacts(
                store,
                output_dir,
                include_script_plan=bool(result.get("script_plan")),
            )
            log_business_event(
                "prompt_optimization_artifact_collection_completed",
                file_log_domain="prompt",
                file_log_event="artifact_collection_done",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=studio_node_id,
                action="prompt_optimization",
                stage="artifact_collection_done",
                artifact_count=len(artifacts),
                elapsed_ms=_elapsed_ms(artifact_started),
                user_action=user_action,
                studio_node_type=studio_node_type,
            )
            trace_started = time.perf_counter()
            log_business_event(
                "prompt_optimization_trace_write_started",
                file_log_domain="prompt",
                file_log_event="trace_write_start",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=studio_node_id,
                action="prompt_optimization",
                stage="trace_write_start",
                artifact_count=len(artifacts),
                user_action=user_action,
                studio_node_type=studio_node_type,
            )
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
            log_business_event(
                "prompt_optimization_trace_write_completed",
                file_log_domain="prompt",
                file_log_event="trace_write_done",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=studio_node_id,
                action="prompt_optimization",
                stage="trace_write_done",
                artifact_count=len(artifacts),
                elapsed_ms=_elapsed_ms(trace_started),
                user_action=user_action,
                studio_node_type=studio_node_type,
            )
        except ValueError as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            llm_enhancement = getattr(exc, "llm_enhancement", {}) if isinstance(exc, PromptOptimizationUnavailable) else {}
            timings = llm_enhancement.get("timings_ms") if isinstance(llm_enhancement, dict) else {}
            log_business_event(
                "prompt_optimization_failed",
                file_log_domain="prompt",
                file_log_event="optimize_failed",
                file_log_level="WARNING",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=studio_node_id,
                action="prompt_optimization",
                stage="failed",
                status_code=422,
                error="invalid_prompt_optimization",
                reason=safe_exception_detail(exc, "invalid_prompt_optimization"),
                provider=llm_enhancement.get("provider") if isinstance(llm_enhancement, dict) else "",
                optimization_mode=llm_enhancement.get("optimization_mode") if isinstance(llm_enhancement, dict) else "",
                provider_calls_started=llm_enhancement.get("provider_calls_started") if isinstance(llm_enhancement, dict) else "",
                llm_status=llm_enhancement.get("status") if isinstance(llm_enhancement, dict) else "",
                discard_reason=llm_enhancement.get("discard_reason") if isinstance(llm_enhancement, dict) else "",
                user_action=user_action,
                elapsed_ms=elapsed_ms,
                llm_elapsed_ms=timings.get("total") if isinstance(timings, dict) else "",
                provider_elapsed_ms=timings.get("provider_dispatch") if isinstance(timings, dict) else "",
                retry_or_salvage_ms=timings.get("retry_or_salvage") if isinstance(timings, dict) else "",
                provider_output_length=llm_enhancement.get("provider_output_length") if isinstance(llm_enhancement, dict) else "",
                provider_error_markers=llm_enhancement.get("provider_error_markers") if isinstance(llm_enhancement, dict) else "",
                missing_sections=llm_enhancement.get("missing_sections") if isinstance(llm_enhancement, dict) else "",
                provider_output_preview=llm_enhancement.get("provider_output_preview") if isinstance(llm_enhancement, dict) else "",
                retryable=True,
                studio_node_type=studio_node_type,
            )
            raise HTTPException(
                status_code=422,
                detail=safe_exception_detail(exc, "invalid_prompt_optimization"),
            ) from exc
        trace_register_started = time.perf_counter()
        log_business_event(
            "prompt_optimization_trace_register_started",
            file_log_domain="prompt",
            file_log_event="trace_register_start",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=studio_node_id,
            action="prompt_optimization",
            stage="trace_register_start",
            user_action=user_action,
            studio_node_type=studio_node_type,
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        log_business_event(
            "prompt_optimization_trace_register_completed",
            file_log_domain="prompt",
            file_log_event="trace_register_done",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=studio_node_id,
            action="prompt_optimization",
            stage="trace_register_done",
            artifact_count=len(artifacts),
            elapsed_ms=_elapsed_ms(trace_register_started),
            user_action=user_action,
            studio_node_type=studio_node_type,
        )
        job_write_started = time.perf_counter()
        log_business_event(
            "prompt_optimization_job_write_started",
            file_log_domain="prompt",
            file_log_event="job_write_start",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=studio_node_id,
            action="prompt_optimization",
            stage="job_write_start",
            artifact_count=len(artifacts),
            user_action=user_action,
            studio_node_type=studio_node_type,
        )
        public_job = store.write_job(runtime_job(job_id, project_id, "prompt_optimization", "succeeded", artifacts=artifacts))
        log_business_event(
            "prompt_optimization_job_write_completed",
            file_log_domain="prompt",
            file_log_event="job_write_done",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=studio_node_id,
            action="prompt_optimization",
            stage="job_write_done",
            artifact_count=len(artifacts),
            elapsed_ms=_elapsed_ms(job_write_started),
            user_action=user_action,
            studio_node_type=studio_node_type,
        )
        timings = result.get("llm_timings_ms") or {}
        log_business_event(
            "prompt_optimization_succeeded",
            file_log_domain="prompt",
            file_log_event="optimize_succeeded",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=studio_node_id,
            action="prompt_optimization",
            stage="complete",
            provider=result.get("llm_provider"),
            optimization_mode=result.get("optimization_mode"),
            provider_calls_started=result["provider_calls_started"],
            llm_status=result.get("llm_status"),
            fallback_used=result.get("llm_guardrail_fallback_used") or result.get("llm_format_salvage_used"),
            optimized_changed=result.get("optimized_changed"),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            llm_elapsed_ms=timings.get("total"),
            provider_elapsed_ms=timings.get("provider_dispatch"),
            retry_or_salvage_ms=timings.get("retry_or_salvage"),
            provider_output_length=result.get("provider_output_length"),
            missing_sections=result.get("missing_sections"),
            studio_node_type=studio_node_type,
        )
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
            "model_call_context_id": result["model_call_context"]["context_id"],
            "model_call_context_summary": public_model_call_context_summary(
                result["model_call_context"],
                artifact=artifacts.get("model_call_context"),
            ),
            "creative_runtime_contract_id": result["creative_runtime_contract"]["contract_id"],
            "creative_runtime_contract_summary": public_prompt_creative_runtime_contract_summary(
                result["creative_runtime_contract"],
                artifact=artifacts.get("creative_runtime_contract"),
            ),
            "script_plan": result.get("script_plan"),
            "script_generation_body": result.get("script_generation_body"),
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": result["safe_manifest"],
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
            "non_claims": PROMPT_MEMORY_NON_CLAIMS,
        }


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


__all__ = ("register_runtime_prompt_memory_routes",)
