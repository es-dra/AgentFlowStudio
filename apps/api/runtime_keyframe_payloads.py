from __future__ import annotations

import re
from typing import Any

from agentflow.algorithms.feedback_overlay_prompt_policy import feedback_overlay_prompt_policy
from apps.api.runtime_keyframe_plan import build_keyframe_plan
from apps.api.runtime_models import KeyframeGenerationRequest
from apps.api.runtime_recovery_contract import annotate_blocks, recovery_manifest_fields
from apps.api.runtime_store import safe_id


SAFE_REVIEW_CANDIDATE_ID = re.compile(r"^candidate_\d{3}$")


def keyframe_request_plan(
    request: KeyframeGenerationRequest,
    provider_prompt: str,
    provider_gate: dict[str, str],
    assembly: dict[str, Any],
    status: str,
    reference_images: list[dict[str, Any]],
    context_bundle: dict[str, Any] | None,
    non_claims: list[str],
) -> dict[str, Any]:
    public_refs = [item["public"] for item in reference_images]
    subject_reference_asset_id = (
        context_bundle.get("subject_reference_asset_id")
        if context_bundle
        else (public_refs[0]["asset_id"] if public_refs else None)
    )
    keyframe_plan = build_keyframe_plan(
        request,
        provider_prompt=provider_prompt,
        reference_images=reference_images,
        context_bundle=context_bundle,
    )
    payload = {
        "artifact_type": "agentflow_keyframe_request_plan",
        "schema_version": "0.1.0",
        "node_id": request.node_id,
        "requested_capability": "image_keyframe",
        "provider": request.provider_service_id,
        "provider_gate": provider_gate,
        "live_call_authorized": provider_gate["status"] != "blocked",
        "status": status,
        "target_platform": request.target_platform,
        "aspect_ratio": request.aspect_ratio,
        "candidate_count": request.candidate_count,
        "seed": request.seed,
        "prompt_source": "request.optimized_prompt" if request.optimized_prompt else "creative_intent_control_agent",
        "context_path": "context_subgraph_v0.1" if context_bundle else "legacy_asset_refs",
        "reference_image_count": len(public_refs),
        "reference_images": public_refs,
        "subject_reference_asset_id": subject_reference_asset_id,
        "keyframe_plan": keyframe_plan,
        "provider_prompt": provider_prompt,
        "creative_agent": assembly["creative_agent"],
        "claim_boundary": "gate_closed_request_plan_only" if provider_gate["status"] == "blocked" else "provider_smoke_request_plan",
        "artifact_policy": {
            "provider_config_path_persisted": False,
            "authorization_header_persisted": False,
            "secret_material_persisted": False,
            "raw_provider_response_persisted": False,
            "media_bytes_returned_by_api": False,
        },
        "non_claims": non_claims,
    }
    if context_bundle:
        payload["context_bundle"] = context_bundle
    return payload


def keyframe_candidate_summary(
    request: KeyframeGenerationRequest,
    provider_prompt: str,
    outputs: list[dict[str, Any]],
    non_claims: list[str],
    *,
    project_id: str = "",
    job_id: str = "",
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_keyframe_candidates_summary",
        "schema_version": "0.1.0",
        "node_id": request.node_id,
        "provider": request.provider_service_id,
        "candidate_count": len(outputs),
        "requested_candidate_count": request.candidate_count,
        "seed": request.seed,
        "provider_prompt": provider_prompt,
        "outputs": outputs,
        "review_preview_refs": keyframe_review_preview_refs(project_id, job_id, outputs),
        "media_bytes_in_payload": False,
        "provider_raw_response_stored": False,
        "non_claims": non_claims,
    }


def keyframe_safe_manifest(
    project_id: str,
    request: KeyframeGenerationRequest,
    *,
    status: str,
    provider_gate: dict[str, str],
    blocks: list[dict[str, str]],
    provider_calls_started: bool,
    output_count: int,
    reference_image_count: int,
    retry_count: int,
    context_bundle: dict[str, Any] | None,
    non_claims: list[str],
    job_id: str = "",
    review_preview_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    safe_blocks = annotate_blocks(blocks)
    payload = {
        "artifact_type": "agentflow_keyframe_generation_safe_manifest",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "job_id": safe_id(job_id) if job_id else "",
        "node_id": request.node_id,
        "status": status,
        "requested_capability": "image_keyframe",
        "provider_gate": provider_gate,
        "provider_calls_started": provider_calls_started,
        "raw_provider_response_stored": False,
        "generated_media_bytes_stored": False,
        "generated_media_bytes_returned": False,
        "generated_media_artifacts_registered": False,
        "output_count": output_count,
        "reference_image_count": reference_image_count,
        "retry_count": retry_count,
        "seed": request.seed,
        "blocks": safe_blocks,
        "review_preview_refs": list(review_preview_refs or []),
        "review_preview_ref_policy": "safe_route_and_metadata_only",
        "safe_artifacts": [
            "keyframe_request_plan.json",
            "keyframe_candidates_summary.json",
            "keyframe_generation_safe_manifest.json",
        ],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": non_claims,
    }
    payload.update(
        recovery_manifest_fields(
            status=status,
            requested_count=request.candidate_count,
            output_count=output_count,
            blocks=safe_blocks,
            provider_calls_started=provider_calls_started,
            retry_count=retry_count,
            stage="provider_gate" if status == "blocked" else "",
            capability="image_keyframe",
        )
    )
    if context_bundle:
        payload["context_bundle_mode"] = context_bundle.get("mode")
        payload["context_included_asset_count"] = len(context_bundle.get("included_assets", []))
        overlays = [item for item in context_bundle.get("feedback_context_overlays", []) if isinstance(item, dict)]
        payload["context_feedback_overlay_count"] = len(overlays)
        payload["context_feedback_overlay_ids"] = [
            str(item.get("overlay_id") or "")[:180]
            for item in overlays
            if item.get("overlay_id")
        ]
        payload["feedback_context_overlay_prompt_policy"] = feedback_overlay_prompt_policy(
            context_bundle=context_bundle,
            context_overlays=overlays,
        )
    else:
        payload["feedback_context_overlay_prompt_policy"] = feedback_overlay_prompt_policy(context_overlays=[])
    return payload


def keyframe_review_preview_refs(project_id: str, job_id: str, outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not project_id or not job_id:
        return []
    refs: list[dict[str, Any]] = []
    safe_project_id = safe_id(project_id)
    safe_job_id = safe_id(job_id)
    for item in outputs:
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("candidate_id") or "")
        if not SAFE_REVIEW_CANDIDATE_ID.match(candidate_id):
            continue
        refs.append(
            {
                "job_id": safe_job_id,
                "candidate_id": candidate_id,
                "safe_preview_ref": (
                    f"/projects/{safe_project_id}/keyframe-generations/"
                    f"{safe_job_id}/candidates/{candidate_id}/preview"
                ),
                "byte_count": item.get("byte_count"),
                "sha256": item.get("sha256"),
                "width": item.get("width"),
                "height": item.get("height"),
                "aspect_ratio": item.get("aspect_ratio"),
            }
        )
    return refs


__all__ = (
    "keyframe_candidate_summary",
    "keyframe_request_plan",
    "keyframe_review_preview_refs",
    "keyframe_safe_manifest",
)
