from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.algorithms.request_projection import build_request_plan
from agentflow.algorithms.revision_drift_control import revision_plan
from agentflow.harness.json_io import write_json
from apps.api.runtime_model_call_context import revision_model_call_context
from apps.api.runtime_models import VideoRevisionRequest
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


def build_video_revision_algorithm_bundle(
    *,
    project_id: str,
    request: VideoRevisionRequest,
    feature_flag: dict[str, str],
    provider_gate: dict[str, str],
) -> dict[str, dict[str, Any]]:
    revision_control = revision_plan(
        intent=request.revision_intent,
        preserve=request.locked_aspects,
        change=request.editable_targets,
        temporal_scope=request.temporal_scope,
    )
    model_call_context = revision_model_call_context(
        project_id=project_id,
        request=request,
        revision_control=revision_control,
        provider_constraints=_provider_constraints(request, feature_flag, provider_gate),
    )
    model_request_plan = build_request_plan(
        model_call_context=model_call_context,
        canonical_brief={"canonical_prompt": request.revision_intent},
        provider_service_id=request.provider_service_id,
    )
    return {
        "revision_plan": revision_control,
        "model_call_context": model_call_context,
        "model_request_plan": model_request_plan,
    }


def write_video_revision_algorithm_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    *,
    safe_manifest: dict[str, Any],
    bundle: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    payloads = {
        "video_revision_safe_manifest": safe_manifest,
        "revision_plan": bundle["revision_plan"],
        "model_call_context": bundle["model_call_context"],
        "model_request_plan": bundle["model_request_plan"],
    }
    artifacts: dict[str, dict[str, Any]] = {}
    for role, payload in payloads.items():
        reject_unsafe_payload(payload)
        path = output_dir / f"{role}.json"
        write_json(path, payload)
        artifacts[role] = store.register_artifact(path, role=role)
    return artifacts


def _provider_constraints(
    request: VideoRevisionRequest, feature_flag: dict[str, str], provider_gate: dict[str, str]
) -> dict[str, Any]:
    return {
        "capability": "video_revision",
        "provider_service_id": request.provider_service_id,
        "provider_capability_mode": request.provider_capability_mode,
        "feature_flag": feature_flag,
        "provider_gate": provider_gate,
        "mode": "revision",
    }


__all__ = (
    "build_video_revision_algorithm_bundle",
    "write_video_revision_algorithm_artifacts",
)
