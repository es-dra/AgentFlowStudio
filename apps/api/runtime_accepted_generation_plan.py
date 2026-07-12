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
from apps.api.runtime_artifacts import feedback_ref
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload, safe_id
from apps.api.runtime_tracing import artifact_refs, write_run_trace


class AcceptedGenerationPlanPreviewRequest(BaseModel):
    fixture_mode: Literal["default_unconfirmed", "confirmed_local_fixture"] = DEFAULT_FIXTURE_MODE
    source_artifact_id: str = Field(default="", max_length=220)
    source_human_gate_id: str = Field(default="", max_length=220)
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
            report, packet, source_evidence = _load_plan_source(store, project_id, request)
            operator_evidence = _operator_evidence(report, packet, request.fixture_mode, source_evidence)
            preview = _preview_artifact(
                project_id=project_id,
                generated_at=request.generated_at,
                fixture_mode=request.fixture_mode,
                source_evidence=source_evidence,
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
                status=_workflow_status(operator_evidence),
                input_refs=_input_refs(request, source_evidence) + [
                    {"role": "fixture_mode", "ref": request.fixture_mode},
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
                    _workflow_status(operator_evidence),
                    artifacts=artifacts,
                )
            )
            store.update_project_manifest(
                project_id,
                {"accepted_generation_plan_refs": [_accepted_plan_ref(artifact, job_id, operator_evidence)]},
                status="in_progress" if operator_evidence["state"]["accepted"] else "blocked",
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
            "preview_status": _workflow_status(operator_evidence),
            "artifact": artifact,
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
        }


def _load_plan_source(
    store: RuntimeStore,
    project_id: str,
    request: AcceptedGenerationPlanPreviewRequest,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if request.source_artifact_id:
        source_artifact = _project_source_artifact(store, project_id, request.source_artifact_id)
        payload = source_artifact.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("accepted generation plan source artifact must be JSON")
        reject_unsafe_payload(payload)
        packet = _packet_from_source_payload(payload)
        if packet.get("accepted") is True:
            gate = _accepted_plan_gate_decision(store, project_id, request.source_human_gate_id, request.source_artifact_id)
            packet["source_human_gate_id"] = gate["human_gate_id"]
            packet["source_decision_ref"] = gate["human_gate_id"]
        elif request.source_human_gate_id:
            _accepted_plan_gate_decision(store, project_id, request.source_human_gate_id, request.source_artifact_id)
        report = _project_source_report(project_id, payload, packet, source_artifact)
        return report, packet, {
            "source_mode": "project_artifact",
            "source_artifact_id": request.source_artifact_id,
            "source_human_gate_id": request.source_human_gate_id,
            "fixture_demo": False,
        }

    report = validated_generation_plan_report(DEFAULT_FIXTURE_MODE)
    packet = dict(report["accepted_generation_plan_packet"])
    # Bundled fixtures are demo/preflight evidence only. They must never return
    # an accepted state because no project-scoped operator decision is attached.
    packet["accepted"] = False
    if request.fixture_mode == "confirmed_local_fixture":
        packet["packet_state"] = "fixture_demo_non_acceptance"
        packet["blocked_reasons"] = ["fixture_demo_requires_project_human_gate_decision"]
        packet["residual_closure_refs"] = []
    return report, packet, {
        "source_mode": "fixture_demo",
        "source_artifact_id": "",
        "source_human_gate_id": "",
        "fixture_demo": True,
    }


def _operator_evidence(
    report: dict[str, Any],
    packet: dict[str, Any],
    fixture_mode: str,
    source_evidence: dict[str, Any],
) -> dict[str, Any]:
    fixed_asset_evidence = report["fixed_asset_confirmation_evidence"]
    request_plan = packet["generation_request_plan"]
    accepted = bool(packet["accepted"])
    return {
        "state": {
            "packet_state": packet["packet_state"],
            "workflow_status": "accepted" if accepted else "blocked",
            "accepted": accepted,
            "request_state": request_plan["request_state"],
            "provider_gate": request_plan["provider_gate"],
            "provider_calls_started": False,
            "generated_media": False,
            "product_readiness": False,
        },
        "provenance": {
            "fixture_mode": fixture_mode,
            "source_mode": source_evidence["source_mode"],
            "source_artifact_id": source_evidence["source_artifact_id"],
            "source_human_gate_id": source_evidence["source_human_gate_id"],
            "fixture_demo_non_acceptance": bool(source_evidence["fixture_demo"]),
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
                "fixture_demo_not_acceptance" if source_evidence["fixture_demo"] else "project_step_gate_not_creative_acceptance",
            ],
        },
    }


def _preview_artifact(
    *,
    project_id: str,
    generated_at: str,
    fixture_mode: str,
    source_evidence: dict[str, Any],
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
        "source_mode": source_evidence["source_mode"],
        "source_artifact_id": source_evidence["source_artifact_id"],
        "source_human_gate_id": source_evidence["source_human_gate_id"],
        "workflow_status": _workflow_status(operator_evidence),
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


def _project_source_artifact(store: RuntimeStore, project_id: str, source_artifact_id: str) -> dict[str, Any]:
    try:
        artifact = store.read_artifact(source_artifact_id)
    except KeyError as exc:
        raise ValueError("accepted generation plan source artifact was not found") from exc
    prefix = f"runs-{safe_id(project_id)}-"
    project_prefix = f"projects-{safe_id(project_id)}-"
    if not (source_artifact_id.startswith(prefix) or source_artifact_id.startswith(project_prefix)):
        raise ValueError("accepted generation plan source artifact is not scoped to this project")
    return artifact


def _packet_from_source_payload(payload: dict[str, Any]) -> dict[str, Any]:
    packet = payload.get("accepted_generation_plan_packet") or payload.get("packet")
    if not isinstance(packet, dict):
        raise ValueError("accepted generation plan source artifact requires packet")
    packet = dict(packet)
    required = (
        "packet_state",
        "accepted",
        "generation_request_plan",
        "evidence_origin",
        "claim_level",
        "blocked_reasons",
        "residual_closure_refs",
        "close_condition_refs",
        "non_claim_boundary",
    )
    missing = [field for field in required if field not in packet]
    if missing:
        raise ValueError(f"accepted generation plan packet missing fields: {', '.join(missing)}")
    if packet.get("accepted") is True and packet.get("evidence_origin") == "repo_local_fixture":
        raise ValueError("repo local fixture cannot be accepted generation plan evidence")
    return packet


def _project_source_report(
    project_id: str,
    payload: dict[str, Any],
    packet: dict[str, Any],
    source_artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "fixture_id": "project_scoped_accepted_generation_plan_source",
        "package_id": str(payload.get("package_id") or packet.get("package_id") or source_artifact["artifact_id"]),
        "package_stage": str(payload.get("package_stage") or packet.get("packet_state") or "project_plan_review"),
        "review_status": {
            "unresolved_open_question_refs": list(payload.get("unresolved_open_question_refs") or []),
        },
        "fixed_asset_confirmation_evidence": {
            "pending_branch_asset_refs": list(payload.get("pending_branch_asset_refs") or []),
        },
        "source_boundary_refs": list(payload.get("source_boundary_refs") or []),
    }


def _accepted_plan_gate_decision(
    store: RuntimeStore,
    project_id: str,
    source_human_gate_id: str,
    source_artifact_id: str,
) -> dict[str, Any]:
    if not source_human_gate_id:
        raise ValueError("accepted generation plan source requires source_human_gate_id")
    manifest = store.ensure_project_manifest(project_id)
    for ref in manifest.get("feedback_refs", []):
        if not isinstance(ref, dict) or ref.get("feedback_id") != source_human_gate_id:
            continue
        event = store.read_artifact(str(ref.get("artifact_id") or "")).get("payload") or {}
        decision = event.get("decision") if isinstance(event, dict) else {}
        if (
            isinstance(decision, dict)
            and decision.get("target_type") == "accepted_generation_plan_packet"
            and decision.get("target_id") == safe_id(source_artifact_id)
            and decision.get("decision") == "accepted_for_next_step"
            and decision.get("human_acceptance_scope") == "local_step_gate_only"
            and decision.get("provider_calls_started") is False
        ):
            return {"human_gate_id": source_human_gate_id, "decision": decision}
    raise ValueError("accepted generation plan source has no matching local human gate decision")


def _workflow_status(operator_evidence: dict[str, Any]) -> str:
    return "succeeded" if operator_evidence["state"]["accepted"] else "blocked"


def _input_refs(request: AcceptedGenerationPlanPreviewRequest, source_evidence: dict[str, Any]) -> list[dict[str, str]]:
    if source_evidence["source_mode"] == "project_artifact":
        refs = [{"role": "accepted_generation_plan_source_artifact", "ref": request.source_artifact_id}]
        if request.source_human_gate_id:
            refs.append({"role": "accepted_generation_plan_source_human_gate", "ref": request.source_human_gate_id})
        return refs
    return [{"role": "branch_workflow_package_fixture", "ref": BRANCH_WORKFLOW_FIXTURE_REF}]


def _accepted_plan_ref(artifact: dict[str, Any], job_id: str, operator_evidence: dict[str, Any]) -> dict[str, Any]:
    provenance = operator_evidence["provenance"]
    state = operator_evidence["state"]
    return {
        **feedback_ref(artifact, job_id),
        "plan_preview_id": job_id,
        "workflow_status": state["workflow_status"],
        "packet_state": state["packet_state"],
        "accepted": state["accepted"],
        "source_mode": provenance["source_mode"],
        "source_artifact_id": provenance["source_artifact_id"],
        "source_human_gate_id": provenance["source_human_gate_id"],
        "provider_calls_started": False,
        "human_creative_acceptance_claimed": False,
        "business_validation_claimed": False,
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
