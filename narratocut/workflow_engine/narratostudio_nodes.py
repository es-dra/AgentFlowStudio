from __future__ import annotations

from pathlib import Path

from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.workflow_engine.registry import NodeRegistry
from narratostudio.io import (
    load_creative_brief,
    load_episode_outline,
    load_prompt_pack,
    load_scene_plan,
    load_shot_plan,
    load_story_bible,
)
from narratostudio.report import render_production_report
from narratostudio.sop import (
    build_cost_quality_trace,
    build_episode_outline,
    build_feedback_signal_log,
    build_memory_candidates,
    build_production_handoff,
    build_prompt_pack,
    build_scene_plan,
    build_shot_plan,
    build_story_bible,
)


def load_creative_brief_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    brief = _resolve_creative_brief(step, context)
    output_ref = _require_output(step, "creative_brief")
    write_json(context.output_path(output_ref), brief)
    context.artifacts["creative_brief"] = output_ref
    context.state["creative_brief"] = brief
    return [output_ref]


def _resolve_creative_brief(step: WorkflowStepDefinition, context: WorkflowContext) -> object:
    brief_ref = _require_input(step, "creative_brief")
    if str(brief_ref) == "creative_brief" and context.inputs.get("artifact_type") == "creative_brief":
        from narratostudio.schemas import CreativeBrief

        return CreativeBrief.model_validate(context.inputs)
    return load_creative_brief(Path(str(context.resolve_input(str(brief_ref)))))


def register_narratostudio_nodes(registry: NodeRegistry) -> None:
    registry.register("narratostudio_load_creative_brief", load_creative_brief_node)
    registry.register("narratostudio_build_story_bible", build_story_bible_node)
    registry.register("narratostudio_build_episode_outline", build_episode_outline_node)
    registry.register("narratostudio_build_scene_plan", build_scene_plan_node)
    registry.register("narratostudio_build_shot_plan", build_shot_plan_node)
    registry.register("narratostudio_build_prompt_pack", build_prompt_pack_node)
    registry.register("narratostudio_build_production_handoff", build_production_handoff_node)


def build_story_bible_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    brief = context.state.get("creative_brief") or load_creative_brief(context.output_path(context.artifacts["creative_brief"]))
    bible = build_story_bible(brief)
    output_ref = _require_output(step, "story_bible")
    write_json(context.output_path(output_ref), bible)
    context.artifacts["story_bible"] = output_ref
    context.state["story_bible"] = bible
    return [output_ref]


def build_episode_outline_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    brief = context.state.get("creative_brief") or load_creative_brief(context.output_path(context.artifacts["creative_brief"]))
    bible = context.state.get("story_bible") or load_story_bible(context.output_path(context.artifacts["story_bible"]))
    outline = build_episode_outline(brief, bible)
    output_ref = _require_output(step, "episode_outline")
    write_json(context.output_path(output_ref), outline)
    context.artifacts["episode_outline"] = output_ref
    context.state["episode_outline"] = outline
    return [output_ref]


def build_scene_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    outline = context.state.get("episode_outline") or load_episode_outline(
        context.output_path(context.artifacts["episode_outline"])
    )
    scene_plan = build_scene_plan(outline)
    output_ref = _require_output(step, "scene_plan")
    write_json(context.output_path(output_ref), scene_plan)
    context.artifacts["scene_plan"] = output_ref
    context.state["scene_plan"] = scene_plan
    return [output_ref]


def build_shot_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    brief = context.state.get("creative_brief") or load_creative_brief(context.output_path(context.artifacts["creative_brief"]))
    scene_plan = context.state.get("scene_plan") or load_scene_plan(context.output_path(context.artifacts["scene_plan"]))
    shot_plan = build_shot_plan(scene_plan, brief)
    output_ref = _require_output(step, "shot_plan")
    write_json(context.output_path(output_ref), shot_plan)
    context.artifacts["shot_plan"] = output_ref
    context.state["shot_plan"] = shot_plan
    return [output_ref]


def build_prompt_pack_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    bible = context.state.get("story_bible") or load_story_bible(context.output_path(context.artifacts["story_bible"]))
    shot_plan = context.state.get("shot_plan") or load_shot_plan(context.output_path(context.artifacts["shot_plan"]))
    prompt_pack = build_prompt_pack(shot_plan, bible)
    output_ref = _require_output(step, "prompt_pack")
    write_json(context.output_path(output_ref), prompt_pack)
    context.artifacts["prompt_pack"] = output_ref
    context.state["prompt_pack"] = prompt_pack
    return [output_ref]


def build_production_handoff_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    brief = context.state.get("creative_brief") or load_creative_brief(context.output_path(context.artifacts["creative_brief"]))
    bible = context.state.get("story_bible") or load_story_bible(context.output_path(context.artifacts["story_bible"]))
    outline = context.state.get("episode_outline") or load_episode_outline(
        context.output_path(context.artifacts["episode_outline"])
    )
    scene_plan = context.state.get("scene_plan") or load_scene_plan(context.output_path(context.artifacts["scene_plan"]))
    shot_plan = context.state.get("shot_plan") or load_shot_plan(context.output_path(context.artifacts["shot_plan"]))
    prompt_pack = context.state.get("prompt_pack") or load_prompt_pack(context.output_path(context.artifacts["prompt_pack"]))
    handoff = build_production_handoff(brief, bible, outline, scene_plan, shot_plan, prompt_pack)

    handoff_ref = _require_output(step, "production_handoff")
    report_ref = _require_output(step, "production_report")
    write_json(context.output_path(handoff_ref), handoff)
    context.output_path(report_ref).write_text(
        render_production_report(brief, bible, scene_plan, shot_plan, prompt_pack, handoff),
        encoding="utf-8",
    )
    _write_auxiliary_artifacts(context, brief, bible)
    context.artifacts["production_handoff"] = handoff_ref
    context.artifacts["production_report"] = report_ref
    return [handoff_ref, report_ref, "memory_candidates.json", "cost_quality_trace.json", "feedback_signal_log.json"]


def _write_auxiliary_artifacts(context: WorkflowContext, brief: object, bible: object) -> None:
    write_json(context.output_path("memory_candidates.json"), build_memory_candidates(brief, bible, context.run_id))
    write_json(context.output_path("cost_quality_trace.json"), build_cost_quality_trace(context.run_id))
    write_json(context.output_path("feedback_signal_log.json"), build_feedback_signal_log(context.run_id))
    context.artifacts["memory_candidates"] = "memory_candidates.json"
    context.artifacts["cost_quality_trace"] = "cost_quality_trace.json"
    context.artifacts["feedback_signal_log"] = "feedback_signal_log.json"


def _require_input(step: WorkflowStepDefinition, name: str) -> object:
    if name not in step.inputs:
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return step.inputs[name]


def _require_output(step: WorkflowStepDefinition, name: str) -> str:
    if name not in step.outputs:
        raise ValueError(f"Step {step.id} missing required output: {name}")
    return step.outputs[name]
