from __future__ import annotations

from datetime import datetime
from typing import Any

from agentflow_studio.schemas import StepResult, WorkflowRun
from agentflow_studio.utils import write_json


PROJECT_NAME = "AgentFlow Studio"
AGENTFLOW_PRODUCTION_PROFILE = "agentflow_production_handoff"
POSTERFLOW_PROFILE = "posterflow_memory_demo"
AGENTFLOW_PRODUCTION_ARTIFACT_DEFAULTS = {
    "creative_brief": ("creative_brief.json", True),
    "story_bible": ("story_bible.json", True),
    "episode_outline": ("episode_outline.json", True),
    "scene_plan": ("scene_plan.json", True),
    "shot_plan": ("shot_plan.json", True),
    "prompt_pack": ("prompt_pack.json", True),
    "production_handoff": ("production_handoff.json", True),
    "production_report": ("production_report.md", True),
    "memory_candidates": ("memory_candidates.json", True),
    "cost_quality_trace": ("cost_quality_trace.json", True),
    "feedback_signal_log": ("feedback_signal_log.json", True),
    "execution_trace": ("execution_trace.json", True),
}
POSTERFLOW_ARTIFACT_DEFAULTS = {
    "poster_brief": ("poster_brief.json", True),
    "poster_plan": ("poster_plan.json", True),
    "poster_prompt_pack": ("poster_prompt_pack.json", True),
    "poster_model_invocations": ("poster_model_invocations.json", True),
    "poster_candidates_manifest": ("poster_candidates_manifest.json", True),
    "poster_feedback": ("poster_feedback.jsonl", True),
    "poster_feedback_signal_log": ("poster_feedback_signal_log.json", True),
    "poster_memory_candidates_jsonl": ("poster_memory_candidates.jsonl", True),
    "poster_memory_candidates": ("poster_memory_candidates.json", True),
    "poster_memory_decisions": ("poster_memory_decisions.json", True),
    "poster_memory_review": ("poster_memory_review.jsonl", True),
    "poster_preference_profile": ("poster_preference_profile.json", True),
    "project_prefix": ("project_prefix.md", True),
    "context_bundle": ("context_bundle.json", True),
    "context_assembly_trace": ("context_assembly_trace.json", True),
    "next_round_prompt": ("next_round_prompt.json", True),
    "round_2_prompt_pack": ("round_2/poster_prompt_pack.json", True),
    "round_2_model_invocations": ("round_2/poster_model_invocations.json", True),
    "round_2_candidates_manifest": ("round_2/poster_candidates_manifest.json", True),
    "round_2_image_candidates": ("round_2/image_candidates/", True),
    "poster_round_comparison": ("poster_round_comparison.json", True),
    "poster_two_round_report": ("poster_two_round_report.md", True),
    "poster_report": ("poster_report.md", True),
    "poster_preview": ("poster_preview.html", True),
    "image_candidates": ("image_candidates/", True),
}
PRODUCT_ARTIFACT_DEFAULTS = {
    "transcript": ("transcript.json", False),
    "candidate_windows": ("candidate_windows.json", False),
    "highlight_score_report": ("highlight_score_report.json", False),
    "selection_diagnostics": ("selection_diagnostics.json", False),
    "highlight_plan": ("highlight_plan.json", False),
    "clip_plan": ("clip_plan.json", False),
    "real_slice_manifest": ("real_slice_manifest.json", False),
    "final_video_manifest": ("final_video_manifest.json", False),
    "finished_package_manifest": ("finished_package_manifest.json", False),
    "package_report": ("package_report.md", False),
    "quality_report": ("quality_report.json", False),
    "review_report": ("review_report.json", False),
}


def write_trace(definition: Any, run: WorkflowRun, context: Any) -> dict[str, Any]:
    trace = build_trace(definition, run, context)
    write_json(context.output_path("trace.json"), trace)
    if context.quality_profile == AGENTFLOW_PRODUCTION_PROFILE:
        write_json(context.output_path("execution_trace.json"), build_execution_trace(definition, run, context))
    return trace


def build_trace(definition: Any, run: WorkflowRun, context: Any) -> dict[str, Any]:
    step_definitions = {step.id: step for step in definition.steps}
    return {
        "workflow": _display_ref(context.workflow_path or run.workflow_name),
        "run_id": run.run_id,
        "steps": [
            _trace_step(result, step_definitions.get(result.step_id), context)
            for result in run.steps
        ],
    }


def build_execution_trace(definition: Any, run: WorkflowRun, context: Any) -> dict[str, Any]:
    step_definitions = {step.id: step for step in definition.steps}
    return {
        "schema_version": "0.1.0",
        "artifact_type": "execution_trace",
        "run_id": run.run_id,
        "workflow_name": definition.name,
        "workflow": _display_ref(context.workflow_path or run.workflow_name),
        "steps": [
            _execution_trace_step(result, step_definitions.get(result.step_id), context)
            for result in run.steps
        ],
    }


def write_run_manifest(run: WorkflowRun, context: Any) -> dict[str, Any]:
    manifest = build_run_manifest(run, context)
    write_json(context.output_path("run_manifest.json"), manifest)
    return manifest


def build_run_manifest(run: WorkflowRun, context: Any) -> dict[str, Any]:
    artifacts = _contract_artifacts(context.artifacts, context)
    manifest = {
        "project": _project_name(context),
        "run_id": run.run_id,
        "workflow": _display_ref(context.workflow_path or run.workflow_name),
        "mode": context.mode,
        "workflow_mode": context.mode,
        "quality_profile": context.quality_profile,
        "created_at": run.started_at.isoformat(),
        "status": run.status,
        "inputs": _contract_inputs(context.inputs),
        "artifacts": artifacts,
        "artifact_index": _artifact_index(artifacts, context),
        "environment": {
            "ffmpeg_required": context.ffmpeg_required,
            "network_required": context.network_required,
        },
    }
    if context.quality_profile == AGENTFLOW_PRODUCTION_PROFILE:
        manifest["module"] = "AgentFlow Production"
    if context.quality_profile == POSTERFLOW_PROFILE:
        manifest["project"] = "AgentFlow Studio"
        manifest["module"] = "PosterFlow"
    return manifest


def _execution_trace_step(result: StepResult, definition: Any | None, context: Any) -> dict[str, Any]:
    return {
        "step_id": result.step_id,
        "status": result.status,
        "started_at": _format_datetime(result.started_at),
        "ended_at": _format_datetime(result.ended_at),
        "inputs": _trace_inputs(definition, context),
        "outputs": result.artifacts,
        "error": result.error,
    }


def _trace_step(result: StepResult, definition: Any | None, context: Any) -> dict[str, Any]:
    return {
        "step_id": result.step_id,
        "status": result.status,
        "started_at": _format_datetime(result.started_at),
        "ended_at": _format_datetime(result.ended_at),
        "duration_ms": _duration_ms(result.started_at, result.ended_at),
        "inputs": _trace_inputs(definition, context),
        "outputs": result.artifacts,
        "warnings": [],
        "errors": [result.error] if result.error else [],
    }


def _trace_inputs(definition: Any | None, context: Any) -> list[str]:
    if definition is None:
        return []
    return [_resolve_trace_ref(value, context) for value in definition.inputs.values()]


def _resolve_trace_ref(value: object, context: Any) -> str:
    ref = str(value)
    if ref in context.inputs:
        return _display_ref(str(context.inputs[ref]))
    if ref in context.artifacts:
        return _display_ref(context.artifacts[ref])
    return _display_ref(ref)


def _contract_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    if "input_text_file" not in inputs:
        return {key: _normalize_value(value) for key, value in inputs.items()}
    normalized = {"text": _normalize_value(inputs["input_text_file"])}
    for key, value in inputs.items():
        if key != "input_text_file":
            normalized[key] = _normalize_value(value)
    return normalized


def _contract_artifacts(artifacts: dict[str, str], context: Any) -> dict[str, str]:
    normalized = dict(artifacts)
    normalized["manifest"] = "manifest.json"
    if context.quality_profile == AGENTFLOW_PRODUCTION_PROFILE:
        for name, (path, _required) in AGENTFLOW_PRODUCTION_ARTIFACT_DEFAULTS.items():
            normalized.setdefault(name, path)
    if context.quality_profile == POSTERFLOW_PROFILE:
        for name, (path, _required) in POSTERFLOW_ARTIFACT_DEFAULTS.items():
            normalized.setdefault(name, path)
    if _is_product_package_context(context):
        for name, (path, _required) in PRODUCT_ARTIFACT_DEFAULTS.items():
            normalized.setdefault(name, path)
    if "clips" in normalized:
        normalized["clips_dir"] = _as_directory_ref(normalized["clips"])
    return normalized


def _is_product_package_context(context: Any) -> bool:
    return (
        context.quality_profile == "finished_package"
        or "finished_package_manifest" in context.artifacts
        or "package_report" in context.artifacts
    )


def _artifact_index(artifacts: dict[str, str], context: Any) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for name, ref in artifacts.items():
        if not isinstance(ref, str) or not ref:
            continue
        index[name] = {
            "path": _display_ref(ref),
            "required": _artifact_required(name, context),
            "exists": _artifact_exists(context, ref),
        }
    return index


def _artifact_required(name: str, context: Any) -> bool:
    if name == "manifest":
        return True
    if context.quality_profile == AGENTFLOW_PRODUCTION_PROFILE and name in AGENTFLOW_PRODUCTION_ARTIFACT_DEFAULTS:
        return AGENTFLOW_PRODUCTION_ARTIFACT_DEFAULTS[name][1]
    if context.quality_profile == POSTERFLOW_PROFILE and name in POSTERFLOW_ARTIFACT_DEFAULTS:
        return POSTERFLOW_ARTIFACT_DEFAULTS[name][1]
    if name == "clips_dir" and "clips" in context.artifacts:
        return True
    if name in context.artifacts:
        return True
    return False


def _artifact_exists(context: Any, ref: str) -> bool:
    path = context.output_path(ref.rstrip("/"))
    return path.is_dir() if ref.endswith("/") else path.exists()


def _duration_ms(started_at: datetime | None, ended_at: datetime | None) -> int:
    if started_at is None or ended_at is None:
        return 0
    return max(0, round((ended_at - started_at).total_seconds() * 1000))


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _as_directory_ref(path: str) -> str:
    return path if path.endswith("/") else f"{path}/"


def _display_ref(path: str) -> str:
    return path.replace("\\", "/")


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _display_ref(value)
    return value


def _project_name(context: Any) -> str:
    if context.quality_profile == AGENTFLOW_PRODUCTION_PROFILE:
        return "AgentFlow Studio"
    if context.quality_profile == POSTERFLOW_PROFILE:
        return "AgentFlow Studio"
    return PROJECT_NAME
