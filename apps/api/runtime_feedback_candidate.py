from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from agentflow.algorithms.feedback_candidate_promotion import build_feedback_candidate_promotion_decision
from agentflow.harness.json_io import write_json
from apps.api.runtime_artifacts import feedback_ref
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job, safe_job_id
from apps.api.runtime_models import FeedbackCandidatePromotionRequest
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload
from apps.api.runtime_tracing import artifact_refs, write_run_trace


def register_runtime_feedback_candidate_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/feedback-candidate-promotions")
    def record_feedback_candidate_promotion(
        project_id: str,
        request: FeedbackCandidatePromotionRequest,
    ) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            reject_unsafe_payload(request.model_dump(mode="json"))
            source_artifact = store.read_artifact(request.feedback_artifact_id)
            feedback_event = source_artifact.get("payload")
            if not isinstance(feedback_event, dict):
                raise ValueError("source feedback artifact has no JSON payload")
            job_id = store.new_job_id("feedback_candidate_promotion", project_id)
            output_dir = store.feedback_dir / safe_job_id(project_id) / safe_job_id(job_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            decision = build_feedback_candidate_promotion_decision(
                project_id=project_id,
                feedback_artifact_id=request.feedback_artifact_id,
                feedback_event=feedback_event,
                candidate_id=request.candidate_id,
                decision=request.decision,
                rationale=request.rationale,
                reviewed_at=request.reviewed_at,
            )
            reject_unsafe_payload(decision)
            decision_path = write_json(
                output_dir / "runtime_feedback_candidate_promotion_decision.json",
                decision,
            )
            artifact = store.register_artifact(
                decision_path,
                role="runtime_feedback_candidate_promotion_decision",
            )
            artifacts = {"runtime_feedback_candidate_promotion_decision": artifact}
            trace_path = write_run_trace(
                output_dir,
                project_id=project_id,
                job_id=job_id,
                action="feedback_candidate_promotion",
                status="succeeded",
                input_refs=[
                    {"role": "feedback_candidate_promotion_request", "ref": "request_body"},
                    {"role": "source_feedback_event", "artifact_id": request.feedback_artifact_id},
                ],
                generated_artifact_refs=artifact_refs(artifacts),
                tester_feedback={"status": "feedback_candidate_promotion_recorded"},
            )
            artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
            job = runtime_job(job_id, project_id, "feedback_candidate_promotion", "succeeded", artifacts=artifacts)
            public_job = store.write_job(job)
            store.update_project_manifest(
                project_id,
                {"feedback_refs": [feedback_ref(artifact, decision["decision_id"])]},
                status="in_progress",
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail=safe_error_detail("invalid_feedback_candidate_promotion"),
            ) from exc
        return {
            "job": public_job,
            "feedback_candidate_promotion_decision": decision,
            "artifact": artifact,
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
        }


__all__ = ("register_runtime_feedback_candidate_routes",)
