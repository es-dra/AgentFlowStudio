from __future__ import annotations

from pathlib import Path

from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.workflow_engine.registry import NodeRegistry
from narratostudio.posterflow.provider import OpenAICompatibleImageProvider
from narratostudio.posterflow.report import render_poster_preview, render_poster_report
from narratostudio.posterflow.sop import (
    accept_memory_candidates,
    build_feedback_signal_log,
    build_next_round_prompt,
    build_poster_plan,
    build_poster_prompt_pack,
    build_preference_profile,
    build_project_prefix,
    extract_memory_candidates,
    load_poster_brief,
)


def register_posterflow_nodes(registry: NodeRegistry) -> None:
    registry.register("posterflow_load_brief", load_poster_brief_node)
    registry.register("posterflow_build_plan", build_poster_plan_node)
    registry.register("posterflow_build_prompt_pack", build_poster_prompt_pack_node)
    registry.register("posterflow_generate_candidates", generate_poster_candidates_node)
    registry.register("posterflow_apply_demo_feedback", apply_demo_feedback_node)
    registry.register("posterflow_extract_memory", extract_poster_memory_node)
    registry.register("posterflow_build_profile", build_poster_profile_node)
    registry.register("posterflow_build_next_prompt", build_next_prompt_node)
    registry.register("posterflow_write_report", write_poster_report_node)


def load_poster_brief_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    brief_ref = _require_input(step, "poster_brief")
    if str(brief_ref) == "poster_brief" and context.inputs.get("artifact_type") == "poster_brief":
        from narratostudio.posterflow.schemas import PosterBrief

        brief = PosterBrief.model_validate(context.inputs)
    else:
        brief = load_poster_brief(Path(str(context.resolve_input(str(brief_ref)))))
    output_ref = _require_output(step, "poster_brief")
    write_json(context.output_path(output_ref), brief)
    context.state["poster_brief"] = brief
    context.artifacts["poster_brief"] = output_ref
    return [output_ref]


def build_poster_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    brief = context.state["poster_brief"]
    plan = build_poster_plan(brief, context.run_id)
    output_ref = _require_output(step, "poster_plan")
    write_json(context.output_path(output_ref), plan)
    context.state["poster_plan"] = plan
    context.artifacts["poster_plan"] = output_ref
    return [output_ref]


def build_poster_prompt_pack_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    prompt_pack = build_poster_prompt_pack(context.state["poster_plan"])
    output_ref = _require_output(step, "poster_prompt_pack")
    write_json(context.output_path(output_ref), prompt_pack)
    context.state["poster_prompt_pack"] = prompt_pack
    context.artifacts["poster_prompt_pack"] = output_ref
    return [output_ref]


def generate_poster_candidates_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    candidate_count = int(step.inputs.get("candidate_count", 3))
    provider = OpenAICompatibleImageProvider.from_env()
    manifest, invocations = provider.generate(
        context.state["poster_prompt_pack"],
        context.output_dir,
        candidate_count=candidate_count,
    )
    candidates_ref = _require_output(step, "poster_candidates_manifest")
    invocations_ref = _require_output(step, "poster_model_invocations")
    write_json(context.output_path(candidates_ref), manifest)
    write_json(context.output_path(invocations_ref), invocations)
    context.state["poster_candidates_manifest"] = manifest
    context.state["poster_model_invocations"] = invocations
    context.artifacts["poster_candidates_manifest"] = candidates_ref
    context.artifacts["poster_model_invocations"] = invocations_ref
    context.artifacts["image_candidates"] = "image_candidates/"
    return [candidates_ref, invocations_ref, "image_candidates/"]


def apply_demo_feedback_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    feedback_ref = _require_input(step, "poster_feedback")
    feedback = build_feedback_signal_log(
        context.resolve_input(str(feedback_ref)),
        project_id=context.state["poster_brief"].project_id,
        run_id=context.run_id,
    )
    output_ref = _require_output(step, "poster_feedback_signal_log")
    write_json(context.output_path(output_ref), feedback)
    context.state["poster_feedback_signal_log"] = feedback
    context.artifacts["poster_feedback_signal_log"] = output_ref
    return [output_ref]


def extract_poster_memory_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    memory = extract_memory_candidates(context.state["poster_feedback_signal_log"])
    decisions = accept_memory_candidates(memory)
    memory_ref = _require_output(step, "poster_memory_candidates")
    decisions_ref = _require_output(step, "poster_memory_decisions")
    write_json(context.output_path(memory_ref), memory)
    write_json(context.output_path(decisions_ref), decisions)
    context.state["poster_memory_candidates"] = memory
    context.state["poster_memory_decisions"] = decisions
    context.artifacts["poster_memory_candidates"] = memory_ref
    context.artifacts["poster_memory_decisions"] = decisions_ref
    return [memory_ref, decisions_ref]


def build_poster_profile_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    profile = build_preference_profile(
        context.state["poster_memory_candidates"],
        context.state["poster_memory_decisions"],
    )
    prefix = build_project_prefix(profile)
    profile_ref = _require_output(step, "poster_preference_profile")
    prefix_ref = _require_output(step, "project_prefix")
    write_json(context.output_path(profile_ref), profile)
    context.output_path(prefix_ref).write_text(prefix, encoding="utf-8")
    context.state["poster_preference_profile"] = profile
    context.artifacts["poster_preference_profile"] = profile_ref
    context.artifacts["project_prefix"] = prefix_ref
    return [profile_ref, prefix_ref]


def build_next_prompt_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    next_prompt = build_next_round_prompt(
        context.state["poster_prompt_pack"],
        context.state["poster_preference_profile"],
    )
    output_ref = _require_output(step, "next_round_prompt")
    write_json(context.output_path(output_ref), next_prompt)
    context.state["next_round_prompt"] = next_prompt
    context.artifacts["next_round_prompt"] = output_ref
    return [output_ref]


def write_poster_report_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    report_ref = _require_output(step, "poster_report")
    preview_ref = _require_output(step, "poster_preview")
    context.output_path(report_ref).write_text(
        render_poster_report(
            context.state["poster_brief"],
            context.state["poster_candidates_manifest"],
            context.state["poster_feedback_signal_log"],
            context.state["poster_memory_candidates"],
            context.state["poster_preference_profile"],
            context.state["next_round_prompt"],
        ),
        encoding="utf-8",
    )
    context.output_path(preview_ref).write_text(
        render_poster_preview(
            context.state["poster_brief"],
            context.state["poster_plan"],
            context.state["poster_candidates_manifest"],
            context.state["poster_feedback_signal_log"],
            context.state["poster_memory_candidates"],
            context.state["poster_preference_profile"],
            context.state["next_round_prompt"],
        ),
        encoding="utf-8",
    )
    context.artifacts["poster_report"] = report_ref
    context.artifacts["poster_preview"] = preview_ref
    return [report_ref, preview_ref]


def _require_input(step: WorkflowStepDefinition, name: str) -> object:
    if name not in step.inputs:
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return step.inputs[name]


def _require_output(step: WorkflowStepDefinition, name: str) -> str:
    if name not in step.outputs:
        raise ValueError(f"Step {step.id} missing required output: {name}")
    return step.outputs[name]
