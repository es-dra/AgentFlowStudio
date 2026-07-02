from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agentflow.algorithms.branch_workflow_package import PROTECTED_NON_CLAIMS
from agentflow.harness.json_io import write_json
from apps.api.runtime_accepted_generation_plan_fixture import (
    BRANCH_WORKFLOW_FIXTURE_REF,
    DEFAULT_FIXTURE_MODE,
    validated_generation_plan_report,
)
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job, safe_job_id
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload, safe_id
from apps.api.runtime_tracing import artifact_refs, write_run_trace


class AcceptedGenerationPlanPreviewRequest(BaseModel):
    fixture_mode: Literal["default_unconfirmed", "confirmed_local_fixture"] = DEFAULT_FIXTURE_MODE
    generated_at: str = Field(default="", max_length=80)


def register_runtime_accepted_generation_plan_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/accepted-generation-plan-packets/preview")
    def preview_accepted_generation_plan_packet(
        project_id: str,
        request: AcceptedGenerationPlanPreviewRequest,
    ) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        request_payload = request.model_dump(mode="json")
        try:
            reject_unsafe_payload(request_payload)
            report = validated_generation_plan_report(request.fixture_mode)
            packet = dict(report["accepted_generation_plan_packet"])
            operator_evidence = _operator_evidence(report, packet, request.fixture_mode)
            preview = _preview_artifact(
                project_id=project_id,
                generated_at=request.generated_at,
                fixture_mode=request.fixture_mode,
                report=report,
                packet=packet,
                operator_evidence=operator_evidence,
            )
            reject_unsafe_payload(preview)

            job_id = store.new_job_id("accepted_generation_plan_packet_preview", project_id)
            output_dir = store.run_dir(project_id, job_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            preview_path = write_json(output_dir / "accepted_generation_plan_packet_preview.json", preview)
            artifact = store.register_artifact(preview_path, role="accepted_generation_plan_packet_preview")
            artifacts = {"accepted_generation_plan_packet_preview": artifact}
            trace_path = write_run_trace(
                output_dir,
                project_id=project_id,
                job_id=job_id,
                action="accepted_generation_plan_packet_preview",
                status="succeeded",
                input_refs=[
                    {"role": "fixture_mode", "ref": request.fixture_mode},
                    {"role": "branch_workflow_package_fixture", "ref": BRANCH_WORKFLOW_FIXTURE_REF},
                ],
                generated_artifact_refs=artifact_refs(artifacts),
                blocked_refs=_blocked_refs(operator_evidence),
                tester_feedback={"status": "provider_closed_plan_review_preview"},
            )
            artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
            public_job = store.write_job(
                runtime_job(
                    job_id,
                    project_id,
                    "accepted_generation_plan_packet_preview",
                    "succeeded",
                    artifacts=artifacts,
                )
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=safe_error_detail(
                    "invalid_accepted_generation_plan_packet_preview",
                    message=str(exc),
                    project_id=project_id,
                    action="accepted_generation_plan_packet_preview",
                    stage="plan_preview",
                ),
            ) from exc

        return {
            "job": public_job,
            "packet": packet,
            "operator_evidence": operator_evidence,
            "artifact": artifact,
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
        }


def _operator_evidence(report: dict[str, Any], packet: dict[str, Any], fixture_mode: str) -> dict[str, Any]:
    fixed_asset_evidence = report["fixed_asset_confirmation_evidence"]
    request_plan = packet["generation_request_plan"]
    return {
        "state": {
            "packet_state": packet["packet_state"],
            "accepted": bool(packet["accepted"]),
            "request_state": request_plan["request_state"],
            "provider_gate": request_plan["provider_gate"],
            "provider_calls_started": False,
            "generated_media": False,
            "product_readiness": False,
        },
        "provenance": {
            "fixture_mode": fixture_mode,
            "evidence_origin": packet["evidence_origin"],
            "fixture_id": report["fixture_id"],
            "package_id": report["package_id"],
            "package_stage": report["package_stage"],
            "claim_level": packet["claim_level"],
            "source_fixture_ref": BRANCH_WORKFLOW_FIXTURE_REF,
            "generation_planning_candidate_ref": packet["generation_planning_candidate_ref"],
            "fixed_asset_confirmation_evidence_ref": packet["fixed_asset_confirmation_evidence_ref"],
            "source_boundary_refs": list(report.get("source_boundary_refs") or []),
        },
        "residual_blockers": {
            "blocked_reasons": list(packet["blocked_reasons"]),
            "unresolved_open_question_refs": list(report["review_status"]["unresolved_open_question_refs"]),
            "pending_branch_asset_refs": list(fixed_asset_evidence["pending_branch_asset_refs"]),
            "residual_closure_refs": list(packet["residual_closure_refs"]),
            "close_condition_refs": list(packet["close_condition_refs"]),
        },
        "non_claim_boundaries": {
            "provider_calls_started": False,
            "provider_gate": "closed",
            "generated_media": False,
            "generated_media_quality": False,
            "provider_smoke": False,
            "human_creative_acceptance": False,
            "business_validation": False,
            "product_readiness": False,
            "deploy_runtime_health": False,
            "companyos_projection": False,
            "cos_active_rule_promotion": False,
            "protected_non_claim_refs": sorted(PROTECTED_NON_CLAIMS),
            "packet_non_claim_boundary": dict(packet["non_claim_boundary"]),
            "explicit_non_claims": [
                "not_provider_smoke",
                "not_generated_media_qa",
                "not_product_readiness",
                "not_human_creative_acceptance",
                "not_business_validation",
                "not_deploy_runtime_health",
            ],
        },
    }


def _preview_artifact(
    *,
    project_id: str,
    generated_at: str,
    fixture_mode: str,
    report: dict[str, Any],
    packet: dict[str, Any],
    operator_evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "afs_accepted_generation_plan_packet_preview",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "fixture_mode": fixture_mode,
        "package_id": report["package_id"],
        "packet": packet,
        "operator_evidence": operator_evidence,
        "provider_calls_started": False,
        "generated_media": False,
        "generated_media_quality_claimed": False,
        "provider_smoke_claimed": False,
        "product_readiness": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "does_not_store_secrets": True,
        "does_not_store_private_asset_bytes": True,
    }


def _blocked_refs(operator_evidence: dict[str, Any]) -> list[dict[str, str]]:
    blockers = operator_evidence["residual_blockers"]
    refs: list[dict[str, str]] = []
    for reason in blockers["blocked_reasons"]:
        refs.append({"ref": safe_id(reason), "reason": str(reason)})
    for ref in blockers["pending_branch_asset_refs"]:
        refs.append({"ref": str(ref), "reason": "pending_branch_asset_confirmation"})
    for ref in blockers["unresolved_open_question_refs"]:
        refs.append({"ref": str(ref), "reason": "unresolved_open_question"})
    return refs


__all__ = ("register_runtime_accepted_generation_plan_routes",)
