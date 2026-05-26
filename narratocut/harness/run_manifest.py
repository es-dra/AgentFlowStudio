from __future__ import annotations

from typing import TYPE_CHECKING, Any

from narratocut.schemas import WorkflowRun
from narratocut.utils import write_json

if TYPE_CHECKING:
    from narratocut.workflow_engine.context import WorkflowContext


PROJECT_NAME = "NarratoCut"
NARRATOSTUDIO_PROFILE = "narratostudio_production_handoff"
POSTERFLOW_PROFILE = "posterflow_memory_demo"
NARRATOSTUDIO_ARTIFACT_DEFAULTS = {
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


def write_run_manifest(run: WorkflowRun, context: WorkflowContext) -> dict[str, Any]:
    manifest = build_run_manifest(run, context)
    write_json(context.output_path("run_manifest.json"), manifest)
    return manifest


def build_run_manifest(run: WorkflowRun, context: WorkflowContext) -> dict[str, Any]:
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
    if context.quality_profile == NARRATOSTUDIO_PROFILE:
        manifest["module"] = "NarratoStudio"
    if context.quality_profile == POSTERFLOW_PROFILE:
        manifest["project"] = "AgentFlow Studio"
        manifest["module"] = "PosterFlow"
    return manifest


def _contract_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    if "input_text_file" not in inputs:
        return {key: _normalize_value(value) for key, value in inputs.items()}

    normalized = {"text": _normalize_value(inputs["input_text_file"])}
    for key, value in inputs.items():
        if key != "input_text_file":
            normalized[key] = _normalize_value(value)
    return normalized


def _contract_artifacts(artifacts: dict[str, str], context: WorkflowContext) -> dict[str, str]:
    normalized = dict(artifacts)
    normalized["manifest"] = "manifest.json"
    if context.quality_profile == NARRATOSTUDIO_PROFILE:
        for name, (path, _required) in NARRATOSTUDIO_ARTIFACT_DEFAULTS.items():
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


def _is_product_package_context(context: WorkflowContext) -> bool:
    return (
        context.quality_profile == "finished_package"
        or "finished_package_manifest" in context.artifacts
        or "package_report" in context.artifacts
    )


def _artifact_index(artifacts: dict[str, str], context: WorkflowContext) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for name, ref in artifacts.items():
        if not isinstance(ref, str) or not ref:
            continue
        required = _artifact_required(name, context)
        index[name] = {
            "path": _display_ref(ref),
            "required": required,
            "exists": _artifact_exists(context, ref),
        }
    return index


def _artifact_required(name: str, context: WorkflowContext) -> bool:
    if name == "manifest":
        return True
    if context.quality_profile == NARRATOSTUDIO_PROFILE and name in NARRATOSTUDIO_ARTIFACT_DEFAULTS:
        return NARRATOSTUDIO_ARTIFACT_DEFAULTS[name][1]
    if context.quality_profile == POSTERFLOW_PROFILE and name in POSTERFLOW_ARTIFACT_DEFAULTS:
        return POSTERFLOW_ARTIFACT_DEFAULTS[name][1]
    if name == "clips_dir" and "clips" in context.artifacts:
        return True
    if name in context.artifacts:
        return True
    return False


def _artifact_exists(context: WorkflowContext, ref: str) -> bool:
    path = context.output_path(ref.rstrip("/"))
    return path.is_dir() if ref.endswith("/") else path.exists()


def _as_directory_ref(path: str) -> str:
    return path if path.endswith("/") else f"{path}/"


def _display_ref(path: str) -> str:
    return path.replace("\\", "/")


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _display_ref(value)
    return value


def _project_name(context: WorkflowContext) -> str:
    if context.quality_profile == NARRATOSTUDIO_PROFILE:
        return "AgentFlow Studio"
    if context.quality_profile == POSTERFLOW_PROFILE:
        return "AgentFlow Studio"
    return PROJECT_NAME
