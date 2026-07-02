from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from agentflow.harness.json_io import write_json
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_generation_preflight import (
    keyframe_generation_preflight,
    preflight_token_matches,
    provider_submit_preflight_requirement,
)
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
    @app.post("/projects/{project_id}/generation-comparisons/preflight")
    def generation_comparison_preflight(project_id: str, request: GenerationComparisonRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            return build_generation_comparison_preflight(store, project_id, request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_generation_comparison")) from exc

    @app.post("/projects/{project_id}/generation-comparisons")
    def generation_comparison(project_id: str, request: GenerationComparisonRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        preflight_requirement = generation_comparison_submit_preflight_requirement(request)
        if preflight_requirement["required"] and not request.preflight_token:
            raise HTTPException(
                status_code=428,
                detail=safe_error_detail(
                    "missing_preflight",
                    detail_code="preflight_required",
                    project_id=project_id,
                    node_id=request.node_id,
                    action="generation_comparison",
                    stage="preflight_required",
                    status="blocked",
                    retryable=True,
                    details={
                        "provider_calls_started": False,
                        "required_gate": preflight_requirement["required_gate"],
                        "required_gates": preflight_requirement["required_gates"],
                    },
                ),
            )
        if request.preflight_token:
            try:
                expected_preflight = build_generation_comparison_preflight(store, project_id, request)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=safe_error_detail("invalid_generation_comparison")) from exc
            if not preflight_token_matches(expected_preflight, request.preflight_token):
                raise HTTPException(
                    status_code=409,
                    detail=safe_error_detail(
                        "stale_preflight",
                        project_id=project_id,
                        node_id=request.node_id,
                        action="generation_comparison",
                        stage="preflight_token",
                        retryable=True,
                        details={"provider_calls_started": False},
                    ),
                )
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


def build_generation_comparison_preflight(
    store: RuntimeStore,
    project_id: str,
    request: GenerationComparisonRequest,
) -> dict[str, Any]:
    arm_preflights = []
    for arm in _arms(request):
        preflight = keyframe_generation_preflight(
            store,
            project_id,
            arm["request"],
            include_fixed_assets=arm["include_fixed_assets"],
        )
        arm_preflights.append(_arm_preflight_report(arm, preflight))
    requirement = generation_comparison_submit_preflight_requirement(request)
    payload = {
        "schema_version": "afs_generation_comparison_preflight.v0.1",
        "generation_kind": "generation_comparison",
        "project_id": project_id,
        "provider_calls_started": False,
        "requires_provider_gate": False,
        "provider_submit_preflight": requirement,
        "arms": arm_preflights,
        "preflight_token": _comparison_preflight_token(request, arm_preflights, requirement),
        "non_claims": [
            "preflight_only",
            "no_provider_submit",
            "not_human_acceptance",
            "not_business_validation",
            *COMPARISON_NON_CLAIMS,
        ],
    }
    reject_unsafe_payload(payload)
    return payload


def generation_comparison_submit_preflight_requirement(request: GenerationComparisonRequest) -> dict[str, Any]:
    arm_requirements = []
    for arm in _arms(request):
        requirement = provider_submit_preflight_requirement("keyframe", arm["request"])
        arm_requirements.append(
            {
                "arm_id": arm["arm_id"],
                "required": bool(requirement["required"]),
                "required_gate": str(requirement["required_gate"]),
                "provider_calls_started": False,
            }
        )
    required_gates = sorted(
        {
            item["required_gate"]
            for item in arm_requirements
            if item["required"]
        }
    )
    return {
        "required": bool(required_gates),
        "required_gate": required_gates[0] if required_gates else (arm_requirements[0]["required_gate"] if arm_requirements else ""),
        "required_gates": required_gates,
        "arm_requirements": arm_requirements,
        "provider_calls_started": False,
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


def _arm_preflight_report(arm: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "arm_id": arm["arm_id"],
        "include_fixed_assets": bool(arm["include_fixed_assets"]),
        "provider_calls_started": False,
        "provider_submit_preflight": preflight.get("provider_submit_preflight") or {},
        "preflight_token": preflight["preflight_token"],
        "included_asset_count": len(preflight.get("included_assets") or []),
        "included_asset_source_evidence_count": int(preflight.get("included_asset_source_evidence_count") or 0),
        "reference_image_count": len(preflight.get("reference_image_channel") or []),
        "subject_reference_asset_id": preflight.get("subject_reference_asset_id"),
    }


def _comparison_preflight_token(
    request: GenerationComparisonRequest,
    arm_preflights: list[dict[str, Any]],
    requirement: dict[str, Any],
) -> str:
    request_payload = request.model_dump(mode="json", by_alias=True)
    request_payload.pop("generated_at", None)
    request_payload.pop("preflight_token", None)
    digest = {
        "kind": "generation_comparison",
        "request": request_payload,
        "provider_submit_preflight": requirement,
        "arms": [
            {
                "arm_id": item["arm_id"],
                "include_fixed_assets": item["include_fixed_assets"],
                "preflight_token": item["preflight_token"],
            }
            for item in arm_preflights
        ],
    }
    data = json.dumps(digest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:32]


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
    safe_manifest = result.get("safe_manifest") if isinstance(result.get("safe_manifest"), dict) else {}
    return {
        "arm_id": arm["arm_id"],
        "status": result["status"],
        "provider_gate": result["provider_gate"],
        "provider_calls_started": result["provider_calls_started"],
        "retry_count": int(safe_manifest.get("retry_count") or 0),
        "blocks": safe_manifest.get("blocks") or [],
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


__all__ = (
    "build_generation_comparison_preflight",
    "build_generation_comparison_report",
    "generation_comparison_submit_preflight_requirement",
    "register_runtime_generation_comparison_routes",
)
