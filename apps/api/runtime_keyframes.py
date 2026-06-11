from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.minimax_image_smoke import run_minimax_image_smoke
from apps.api.runtime_models import KeyframeGenerationRequest, PromptOptimizationRequest
from apps.api.runtime_prompt_memory_engine import assemble_prompt_context
from apps.api.runtime_prompt_memory_state import load_creative_memory_state
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


REMOTE_IMAGE_ENV = "AFS_ALLOW_REMOTE_IMAGE"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
KEYFRAME_NON_CLAIMS = [
    "runtime verification only",
    "not human acceptance",
    "not business validation",
    "not video provider smoke",
    "not durable memory",
]


def build_keyframe_generation(
    store: RuntimeStore,
    project_id: str,
    request: KeyframeGenerationRequest,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_request = _prompt_request(request)
    state = load_creative_memory_state(store, project_id)
    assembly = assemble_prompt_context(prompt_request, state)
    provider_prompt = request.optimized_prompt or assembly["creative_agent"]["provider_translation"]["prompt"]
    provider_gate = image_provider_gate()

    provider_outputs: list[dict[str, Any]] = []
    status = "blocked"
    blocks = []
    provider_calls_started = False
    if provider_gate["status"] == "blocked":
        blocks.append(_gate_closed_block())
    else:
        try:
            provider_calls_started = True
            manifest = run_minimax_image_smoke(
                load_company_provider_secrets(),
                service_id=request.provider_service_id,
                prompt=provider_prompt,
                output_dir=output_dir,
                aspect_ratio=request.aspect_ratio,
                candidate_count=request.candidate_count,
            )
            status = "succeeded"
            provider_outputs = _provider_outputs(manifest)
        except ModelGatewayError as exc:
            status = "blocked"
            provider_calls_started = False
            blocks.append(
                {
                    "block_id": "remote_image_provider_not_ready",
                    "reason": _safe_error(str(exc)),
                    "required_gate": REMOTE_IMAGE_ENV,
                }
            )

    request_plan = _request_plan(request, provider_prompt, provider_gate, assembly, status)
    candidates = _candidate_summary(request, provider_prompt, provider_outputs)
    safe_manifest = _safe_manifest(
        project_id,
        request,
        status=status,
        provider_gate=provider_gate,
        blocks=blocks,
        provider_calls_started=provider_calls_started,
        output_count=len(provider_outputs),
    )
    for payload in (request_plan, candidates, safe_manifest):
        reject_unsafe_payload(payload)
    write_json(output_dir / "keyframe_request_plan.json", request_plan)
    write_json(output_dir / "keyframe_candidates_summary.json", candidates)
    write_json(output_dir / "keyframe_generation_safe_manifest.json", safe_manifest)
    return {
        "status": status,
        "provider_gate": provider_gate,
        "provider_calls_started": provider_calls_started,
        "safe_manifest": safe_manifest,
        "tool_gate_state": {
            "remote_llm": "not_requested",
            "remote_asr": "blocked_by_default",
            "remote_image": provider_gate["status"],
            "remote_video": "blocked_by_default",
        },
    }


def image_provider_gate() -> dict[str, str]:
    status = "ready_not_run" if os.environ.get(REMOTE_IMAGE_ENV, "").strip().lower() in REMOTE_TRUE_VALUES else "blocked"
    return {"capability": "image", "env": REMOTE_IMAGE_ENV, "status": status}


def _prompt_request(request: KeyframeGenerationRequest) -> PromptOptimizationRequest:
    params = dict(request.node_parameters or {})
    params.setdefault("aspect_ratio", request.aspect_ratio)
    return PromptOptimizationRequest(
        node_id=request.node_id,
        node_type="image",
        prompt_text=request.prompt_text,
        generation_target="keyframe",
        target_platform=request.target_platform,
        style=request.style,
        asset_refs=list(request.asset_refs),
        director_setup=request.director_setup,
        node_parameters=params,
        generated_at=request.generated_at,
    )


def _request_plan(
    request: KeyframeGenerationRequest,
    provider_prompt: str,
    provider_gate: dict[str, str],
    assembly: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    return {
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
        "prompt_source": "request.optimized_prompt" if request.optimized_prompt else "creative_intent_control_agent",
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
        "non_claims": KEYFRAME_NON_CLAIMS,
    }


def _candidate_summary(
    request: KeyframeGenerationRequest,
    provider_prompt: str,
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_keyframe_candidates_summary",
        "schema_version": "0.1.0",
        "node_id": request.node_id,
        "provider": request.provider_service_id,
        "candidate_count": len(outputs),
        "requested_candidate_count": request.candidate_count,
        "provider_prompt": provider_prompt,
        "outputs": outputs,
        "media_bytes_in_payload": False,
        "provider_raw_response_stored": False,
        "non_claims": KEYFRAME_NON_CLAIMS,
    }


def _safe_manifest(
    project_id: str,
    request: KeyframeGenerationRequest,
    *,
    status: str,
    provider_gate: dict[str, str],
    blocks: list[dict[str, str]],
    provider_calls_started: bool,
    output_count: int,
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_keyframe_generation_safe_manifest",
        "schema_version": "0.1.0",
        "project_id": project_id,
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
        "blocks": blocks,
        "safe_artifacts": [
            "keyframe_request_plan.json",
            "keyframe_candidates_summary.json",
            "keyframe_generation_safe_manifest.json",
        ],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": KEYFRAME_NON_CLAIMS,
    }


def _provider_outputs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    for item in manifest.get("outputs", []):
        if not isinstance(item, dict):
            continue
        outputs.append(
            {
                "candidate_id": item.get("candidate_id"),
                "image_ref": item.get("image_path"),
                "byte_count": item.get("byte_count"),
                "sha256": item.get("sha256"),
                "provider_url_persisted": False,
            }
        )
    return outputs


def _gate_closed_block() -> dict[str, str]:
    return {
        "block_id": "remote_image_gate_closed",
        "reason": f"Set {REMOTE_IMAGE_ENV}=true only for an explicit image/keyframe provider smoke.",
        "required_gate": REMOTE_IMAGE_ENV,
    }


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "api" in lowered or "key" in lowered or "secret" in lowered:
        return "Image provider configuration is not ready."
    return value[:160]


__all__ = ("KEYFRAME_NON_CLAIMS", "REMOTE_IMAGE_ENV", "build_keyframe_generation", "image_provider_gate")
