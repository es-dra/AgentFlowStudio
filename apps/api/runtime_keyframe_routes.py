from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from apps.api.runtime_artifacts import keyframe_generation_artifacts
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_generated_image_assets import register_generated_image_asset
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_keyframes import KEYFRAME_NON_CLAIMS, build_keyframe_generation
from apps.api.runtime_models import KeyframeGenerationRequest
from apps.api.runtime_store import safe_id
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_tracing import artifact_refs, blocked_refs_from_blocks, write_run_trace


SAFE_CANDIDATE_ID = re.compile(r"^candidate_\d{3}$")
IMAGE_SUFFIX_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


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
                    {"role": "seed", "ref": str(request.seed) if request.seed is not None else "not_provided"},
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
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_keyframe_generation")) from exc
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
        candidate_previews = _candidate_previews(
            project_id,
            job_id,
            result.get("provider_outputs") or [],
        )
        reusable_image_assets = _reusable_image_assets(
            store,
            project_id,
            source_node_id=request.node_id,
            job_id=job_id,
            output_dir=output_dir,
            outputs=result.get("provider_outputs") or [],
        )
        return {
            "job": public_job,
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": safe_manifest,
            "context_bundle": result.get("context_bundle"),
            "artifacts": artifacts,
            "candidate_previews": candidate_previews,
            "reusable_image_assets": reusable_image_assets,
            "flow": build_flow_summary(store, project_id),
            "non_claims": KEYFRAME_NON_CLAIMS,
        }

    @app.get("/projects/{project_id}/keyframe-generations/{job_id}/candidates/{candidate_id}/preview")
    def keyframe_candidate_preview(project_id: str, job_id: str, candidate_id: str) -> FileResponse:
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if job.get("project_id") != project_id or job.get("action") != "keyframe_generation":
            raise HTTPException(status_code=404, detail="candidate not found")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            raise HTTPException(status_code=404, detail="candidate not found")
        path = _candidate_file(store.run_dir(project_id, job_id), candidate_id)
        if path is None:
            raise HTTPException(status_code=404, detail="candidate not found")
        return FileResponse(
            path,
            media_type=IMAGE_SUFFIX_TYPES[path.suffix.lower()],
            headers={"Cache-Control": "no-store"},
        )


def _candidate_previews(project_id: str, job_id: str, outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for item in outputs:
        candidate_id = str(item.get("candidate_id") or "")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            continue
        previews.append(
            {
                "candidate_id": candidate_id,
                "preview_url": (
                    f"/projects/{safe_id(project_id)}/keyframe-generations/"
                    f"{safe_id(job_id)}/candidates/{candidate_id}/preview"
                ),
                "byte_count": item.get("byte_count"),
                "sha256": item.get("sha256"),
                "width": item.get("width"),
                "height": item.get("height"),
                "aspect_ratio": item.get("aspect_ratio"),
            }
        )
    return previews


def _reusable_image_assets(
    store: RuntimeStore,
    project_id: str,
    *,
    source_node_id: str | None,
    job_id: str,
    output_dir: Path,
    outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for item in outputs:
        candidate_id = str(item.get("candidate_id") or "")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            continue
        path = _candidate_file(output_dir, candidate_id)
        if path is None:
            continue
        try:
            registered = register_generated_image_asset(
                store,
                project_id,
                source_node_id=source_node_id,
                source_job_id=job_id,
                source_candidate_id=candidate_id,
                image_path=path,
            )
        except ValueError:
            continue
        assets.append(registered["asset"])
    return assets


def _candidate_file(output_dir: Path, candidate_id: str) -> Path | None:
    image_dir = (output_dir / "image_candidates").resolve()
    root = output_dir.resolve()
    try:
        image_dir.relative_to(root)
    except ValueError:
        return None
    for suffix in IMAGE_SUFFIX_TYPES:
        path = (image_dir / f"{candidate_id}{suffix}").resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.exists() and path.is_file():
            return path
    return None


__all__ = ("register_runtime_keyframe_routes",)
