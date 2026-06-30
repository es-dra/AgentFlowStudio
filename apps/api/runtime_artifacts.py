from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.api.runtime_store import RuntimeStore


def script_provider_artifacts(store: RuntimeStore, output_dir: Path) -> dict[str, Any]:
    return {
        "llm_script_request_plan": store.register_artifact(
            output_dir / "llm_script_request_plan.json",
            role="llm_script_request_plan",
        ),
        "script_storyboard_safe_artifact": store.register_artifact(
            output_dir / "script_storyboard_safe_artifact.json",
            role="script_storyboard_safe_artifact",
        ),
        "script_provider_safe_manifest": store.register_artifact(
            output_dir / "script_provider_safe_manifest.json",
            role="script_provider_safe_manifest",
        ),
    }


def prompt_memory_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    *,
    include_script_plan: bool = False,
) -> dict[str, Any]:
    artifacts = {
        "model_call_context": store.register_artifact(
            output_dir / "model_call_context.json",
            role="model_call_context",
        ),
        "creative_brief": store.register_artifact(
            output_dir / "creative_brief.json",
            role="creative_brief",
        ),
        "prompt_assembly_trace": store.register_artifact(
            output_dir / "prompt_assembly_trace.json",
            role="prompt_assembly_trace",
        ),
        "prompt_optimization_safe_manifest": store.register_artifact(
            output_dir / "prompt_optimization_safe_manifest.json",
            role="prompt_optimization_safe_manifest",
        ),
    }
    if include_script_plan:
        artifacts["script_plan"] = store.register_artifact(
            output_dir / "script_plan.json",
            role="script_plan",
        )
    return artifacts


def keyframe_generation_artifacts(store: RuntimeStore, output_dir: Path) -> dict[str, Any]:
    artifacts = {
        "model_call_context": store.register_artifact(
            output_dir / "model_call_context.json",
            role="model_call_context",
        ),
        "model_request_plan": store.register_artifact(
            output_dir / "model_request_plan.json",
            role="model_request_plan",
        ),
        "keyframe_request_plan": store.register_artifact(
            output_dir / "keyframe_request_plan.json",
            role="keyframe_request_plan",
        ),
        "keyframe_candidates_summary": store.register_artifact(
            output_dir / "keyframe_candidates_summary.json",
            role="keyframe_candidates_summary",
        ),
        "keyframe_generation_safe_manifest": store.register_artifact(
            output_dir / "keyframe_generation_safe_manifest.json",
            role="keyframe_generation_safe_manifest",
        ),
    }
    bridge_path = output_dir / "keyframe_generation_bridge.json"
    if bridge_path.is_file():
        artifacts["keyframe_generation_bridge"] = store.register_artifact(
            bridge_path,
            role="keyframe_generation_bridge",
        )
    return artifacts


def feedback_ref(artifact: dict[str, Any], feedback_id: str) -> dict[str, Any]:
    return {**_artifact_list_ref(artifact), "feedback_id": str(feedback_id)}


def _artifact_list_ref(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": artifact["artifact_id"],
        "artifact_type": artifact["artifact_type"],
        "filename": artifact["filename"],
    }


__all__ = (
    "feedback_ref",
    "keyframe_generation_artifacts",
    "prompt_memory_artifacts",
    "script_provider_artifacts",
)
