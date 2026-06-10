from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from apps.api.runtime_artifacts import script_provider_artifacts
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_models import ProviderScriptDraftPlanRequest
from apps.api.runtime_provider_script import LLM_SCRIPT_NON_CLAIMS, build_llm_script_draft_plan
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_tracing import artifact_refs, blocked_refs_from_blocks, write_run_trace


def register_runtime_provider_script_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/provider/script-draft-plan")
    def provider_script_draft_plan(request: ProviderScriptDraftPlanRequest) -> dict[str, Any]:
        store.ensure_project_manifest(request.project_id)
        job_id = store.new_job_id("llm_script_draft_plan", request.project_id)
        output_dir = store.run_dir(request.project_id, job_id)
        try:
            review_note = _review_note_from_artifact(store, request.review_feedback_artifact_id)
            plan = build_llm_script_draft_plan(request, output_dir, review_note=review_note)
            artifacts = script_provider_artifacts(store, output_dir)
            safe_manifest = dict(plan["safe_manifest"])
            status = str(plan["job_status"])
            trace_path = write_run_trace(
                output_dir,
                project_id=request.project_id,
                job_id=job_id,
                action="llm_script_draft_plan",
                status=status,
                input_refs=[
                    {"role": "goal", "ref": "request_body"},
                    {"role": "target_platform", "ref": request.target_platform},
                    {"role": "style", "ref": request.style},
                    {
                        "role": "review_feedback_artifact_id",
                        "ref": request.review_feedback_artifact_id or "not_provided",
                    },
                    {
                        "role": "previous_script_artifact_id",
                        "ref": request.previous_script_artifact_id or "not_provided",
                    },
                ],
                generated_artifact_refs=artifact_refs(artifacts),
                blocked_refs=blocked_refs_from_blocks(safe_manifest.get("blocks", [])),
                tester_feedback={
                    "status": "llm_script_plan_created",
                    "feedback_reuse_policy": "candidate_constraints_only",
                },
                tool_gate_state=dict(plan["tool_gate_state"]),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, request.project_id, "llm_script_draft_plan", status, artifacts=artifacts)
        job["ui_summary"] = {
            "provider_gate": {
                "status": safe_manifest.get("status", status),
                "provider_calls_started": False,
                "blockers": safe_manifest.get("blockers") or safe_manifest.get("blocks") or [],
            }
        }
        public_job = store.write_job(job)
        return {
            "job": public_job,
            "provider_gate": plan["provider_gate"],
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": safe_manifest,
            "artifacts": artifacts,
            "flow": build_flow_summary(store, request.project_id),
            "non_claims": LLM_SCRIPT_NON_CLAIMS,
        }


def _review_note_from_artifact(store: RuntimeStore, artifact_id: str | None) -> str | None:
    if not artifact_id:
        return None
    try:
        payload = dict(store.read_artifact(artifact_id).get("payload") or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="review feedback artifact not found") from exc
    note = payload.get("note")
    if isinstance(note, str) and note.strip():
        return note.strip()
    feedback = payload.get("feedback")
    if isinstance(feedback, dict):
        feedback_note = feedback.get("note") or feedback.get("summary")
        if isinstance(feedback_note, str) and feedback_note.strip():
            return feedback_note.strip()
    return None


__all__ = ("register_runtime_provider_script_routes",)
