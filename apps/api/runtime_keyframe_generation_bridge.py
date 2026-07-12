from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.algorithms.generation_bridge import build_keyframe_generation_bridge
from agentflow.harness.json_io import write_json
from apps.api.runtime_models import KeyframeGenerationRequest
from apps.api.runtime_store import reject_unsafe_payload


def write_keyframe_generation_bridge(
    output_dir: Path,
    *,
    project_id: str,
    request: KeyframeGenerationRequest,
    status: str,
    provider_gate: dict[str, str],
    provider_calls_started: bool,
    reference_image_count: int,
    blocks: list[dict[str, Any]],
    context_bundle: dict[str, Any] | None,
    model_call_context: dict[str, Any],
    model_request_plan: dict[str, Any],
    safe_manifest: dict[str, Any],
) -> dict[str, Any] | None:
    if provider_calls_started:
        return None
    safe_artifacts = safe_manifest.setdefault("safe_artifacts", [])
    if "keyframe_generation_bridge.json" not in safe_artifacts:
        safe_artifacts.append("keyframe_generation_bridge.json")
    safe_manifest["local_generation_bridge_ready"] = True
    bridge = build_keyframe_generation_bridge(
        project_id=project_id,
        node_id=request.node_id,
        status=status,
        provider_gate=provider_gate,
        provider_calls_started=provider_calls_started,
        requested_candidate_count=request.candidate_count,
        reference_image_count=reference_image_count,
        seed=request.seed,
        blocks=blocks,
        context_bundle=context_bundle,
        model_call_context=model_call_context,
        model_request_plan=model_request_plan,
    )
    reject_unsafe_payload(bridge)
    write_json(output_dir / "keyframe_generation_bridge.json", bridge)
    return bridge


__all__ = ("write_keyframe_generation_bridge",)
