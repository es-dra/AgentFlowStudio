from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from agentflow.harness.json_io import write_json
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_keyframes import KEYFRAME_NON_CLAIMS, build_keyframe_generation
from apps.api.runtime_models import GenerationComparisonRequest, KeyframeGenerationRequest
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload
from apps.api.runtime_tracing import artifact_refs, write_run_trace


COMPARISON_NON_CLAIMS = [
    "comparison report is runtime evidence only",
    "not human acceptance",
    "not business validation",
    "not durable memory",
]


def register_runtime_generation_comparison_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/generation-comparisons")
    def generation_comparison(project_id: str, request: GenerationComparisonRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("generation_comparison", project_id)
        output_dir = store.run_dir(project_id, job_id)
        try:
            report = build_generation_comparison_report(store, project_id, request, output_dir)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_generation_comparison")) from exc
        artifact = store.register_artifact(output_dir / "generation_comparison_report.json", role="generation_comparison_report")
        artifacts = {"generation_comparison_report": artifact}
        status = str(report["status"])
        trace_path = write_run_trace(
            output_dir,
            project_id=project_id,
            job_id=job_id,
            action="generation_comparison",
            status=status,
            input_refs=[
                {"role": "prompt_text", "ref": "request_body.prompt_text"},
                {"role": "context_subgraph", "ref": "request_body.context_subgraph" if request.context_subgraph else "not_provided"},
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            tester_feedback={"status": "generation_comparison_report_created"},
            tool_gate_state=report["tool_gate_state"],
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        public_job = store.write_job(runtime_job(job_id, project_id, "generation_comparison", status, artifacts=artifacts))
        return {
            "job": public_job,
            "report": report,
            "artifacts": artifacts,
            "provider_calls_started": report["provider_calls_started"],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "flow": build_flow_summary(store, project_id),
            "non_claims": COMPARISON_NON_CLAIMS,
        }


def build_generation_comparison_report(
    store: RuntimeStore,
    project_id: str,
    request: GenerationComparisonRequest,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    arm_results = []
    for arm in _arms(request):
        arm_dir = output_dir / arm["arm_id"]
        result = build_keyframe_generation(
            store,
            project_id,
            arm["request"],
            arm_dir,
            include_fixed_assets=arm["include_fixed_assets"],
        )
        plan = read_json(arm_dir / "keyframe_request_plan.json")
        arm_results.append(_arm_report(arm, result, plan))
    status = "blocked" if any(item["status"] == "blocked" for item in arm_results) else "succeeded"
    report = {
        "artifact_type": "generation_comparison_report",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "status": status,
        "arms": arm_results,
        "manual_scores": request.manual_scores,
        "provider_calls_started": any(item["provider_calls_started"] for item in arm_results),
        "provider_gate": arm_results[0]["provider_gate"] if arm_results else {},
        "tool_gate_state": _tool_gate_state(arm_results),
        "arm_definitions": {
            "A": "original prompt, no asset_refs, no reference image, legacy provider path",
            "B": "new resolver generate mode with fixed asset injection disabled",
            "C": "new resolver generate mode with fixed asset feature and lock injection enabled",
        },
        "non_claims": [*COMPARISON_NON_CLAIMS, *KEYFRAME_NON_CLAIMS],
    }
    reject_unsafe_payload(report)
    write_json(output_dir / "generation_comparison_report.json", report)
    return report


def _arms(request: GenerationComparisonRequest) -> list[dict[str, Any]]:
    return [
        {"arm_id": "A", "include_fixed_assets": False, "request": _keyframe_request(request, optimized_prompt=request.prompt_text, context_subgraph=None)},
        {"arm_id": "B", "include_fixed_assets": False, "request": _keyframe_request(request, optimized_prompt=request.optimized_prompt or request.prompt_text, context_subgraph=request.context_subgraph)},
        {"arm_id": "C", "include_fixed_assets": True, "request": _keyframe_request(request, optimized_prompt=request.optimized_prompt or request.prompt_text, context_subgraph=request.context_subgraph)},
    ]


def _keyframe_request(
    request: GenerationComparisonRequest,
    *,
    optimized_prompt: str,
    context_subgraph: Any,
) -> KeyframeGenerationRequest:
    return KeyframeGenerationRequest(
        node_id=request.node_id,
        prompt_text=request.prompt_text,
        optimized_prompt=optimized_prompt,
        target_platform=request.target_platform,
        style=request.style,
        aspect_ratio=request.aspect_ratio,
        candidate_count=request.candidate_count,
        seed=request.seed,
        provider_service_id=request.provider_service_id,
        asset_refs=[],
        context_subgraph=context_subgraph,
        generated_at=request.generated_at,
    )


def _arm_report(arm: dict[str, Any], result: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "arm_id": arm["arm_id"],
        "status": result["status"],
        "provider_gate": result["provider_gate"],
        "provider_calls_started": result["provider_calls_started"],
        "fixed_asset_injection": bool(arm["include_fixed_assets"]),
        "context_path": plan.get("context_path"),
        "provider_prompt": plan.get("provider_prompt"),
        "subject_reference_asset_id": plan.get("subject_reference_asset_id"),
        "reference_images": plan.get("reference_images") or [],
        "context_bundle": plan.get("context_bundle"),
        "result_refs": [
            {"candidate_id": item.get("candidate_id"), "image_ref": item.get("image_ref")}
            for item in result.get("provider_outputs", [])
        ],
    }


def _tool_gate_state(arms: list[dict[str, Any]]) -> dict[str, str]:
    image_state = "not_requested"
    for arm in arms:
        image_state = str(arm.get("provider_gate", {}).get("status") or image_state)
    return {
        "remote_llm": "not_requested",
        "remote_asr": "blocked_by_default",
        "remote_image": image_state,
        "remote_video": "blocked_by_default",
    }


__all__ = ("build_generation_comparison_report", "register_runtime_generation_comparison_routes")
