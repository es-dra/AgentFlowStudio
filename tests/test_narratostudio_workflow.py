from __future__ import annotations

import json
from pathlib import Path

from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.workflow_engine import WorkflowContext, WorkflowRunner, default_node_registry, load_workflow
from narratostudio import (
    CostQualityTrace,
    EpisodeOutline,
    FeedbackSignalLog,
    MemoryCandidateStore,
    ProductionHandoff,
    PromptPack,
    ScenePlan,
    ShotPlan,
    StoryBible,
)


def test_narratostudio_workflow_generates_production_handoff_artifacts(tmp_path) -> None:
    output_dir = tmp_path / "narratostudio_run"
    workflow_path = "workflows/narratostudio_brief_to_production_handoff.yaml"
    workflow = load_workflow(workflow_path)
    context = WorkflowContext(
        run_id="narratostudio_run",
        workflow_name=workflow.name,
        workflow_path=workflow_path,
        mode=workflow.mode,
        quality_profile=workflow.quality_profile,
        output_dir=output_dir,
        inputs={"creative_brief": "examples/narratostudio/creative_brief.example.json"},
    )

    run = WorkflowRunner(default_node_registry()).run(workflow, context)

    assert run.status == "success"
    assert workflow.name == "narratostudio_brief_to_production_handoff_v0.1"
    assert workflow.quality_profile == "narratostudio_production_handoff"

    for filename in [
        "creative_brief.json",
        "story_bible.json",
        "episode_outline.json",
        "scene_plan.json",
        "shot_plan.json",
        "prompt_pack.json",
        "production_handoff.json",
        "production_report.md",
        "memory_candidates.json",
        "cost_quality_trace.json",
        "feedback_signal_log.json",
        "manifest.json",
        "run_manifest.json",
        "execution_trace.json",
    ]:
        assert (output_dir / filename).is_file(), filename

    StoryBible.model_validate(_read_json(output_dir / "story_bible.json"))
    EpisodeOutline.model_validate(_read_json(output_dir / "episode_outline.json"))
    scene_plan = ScenePlan.model_validate(_read_json(output_dir / "scene_plan.json"))
    shot_plan = ShotPlan.model_validate(_read_json(output_dir / "shot_plan.json"))
    prompt_pack = PromptPack.model_validate(_read_json(output_dir / "prompt_pack.json"))
    handoff = ProductionHandoff.model_validate(_read_json(output_dir / "production_handoff.json"))
    memory = MemoryCandidateStore.model_validate(_read_json(output_dir / "memory_candidates.json"))
    cost_trace = CostQualityTrace.model_validate(_read_json(output_dir / "cost_quality_trace.json"))
    feedback = FeedbackSignalLog.model_validate(_read_json(output_dir / "feedback_signal_log.json"))

    scene_ids = {scene.scene_id for scene in scene_plan.scenes}
    assert {shot.scene_id for shot in shot_plan.shots} <= scene_ids
    shot_ids = {shot.shot_id for shot in shot_plan.shots}
    assert {prompt.shot_id for prompt in prompt_pack.prompts} <= shot_ids
    assert handoff.prompt_pack_id == prompt_pack.prompt_pack_id
    assert {candidate.promotion_status for candidate in memory.candidates} == {"candidate"}
    assert cost_trace.provider == "local_deterministic"
    assert cost_trace.execution_mode == "local_deterministic"
    assert feedback.is_primary_feedback_store is False

    run_manifest = _read_json(output_dir / "run_manifest.json")
    assert run_manifest["project"] == "AgentFlow Studio"
    assert run_manifest["module"] == "NarratoStudio"
    assert run_manifest["artifact_index"]["production_handoff"]["path"] == "production_handoff.json"
    assert run_manifest["artifact_index"]["execution_trace"]["path"] == "execution_trace.json"
    assert run_manifest["artifact_index"]["execution_trace"]["exists"] is True

    execution_trace = _read_json(output_dir / "execution_trace.json")
    assert execution_trace["schema_version"] == "0.1.0"
    assert execution_trace["artifact_type"] == "execution_trace"
    assert execution_trace["workflow_name"] == workflow.name
    assert [step["step_id"] for step in execution_trace["steps"]] == [
        "load_creative_brief",
        "build_story_bible",
        "build_episode_outline",
        "build_scene_plan",
        "build_shot_plan",
        "build_prompt_pack",
        "build_production_handoff",
    ]


def test_narratostudio_workflow_accepts_creative_brief_json_as_cli_input(tmp_path) -> None:
    output_dir = tmp_path / "narratostudio_cli_run"

    status, manifest_path = run_workflow_from_cli(
        Path("workflows/narratostudio_brief_to_production_handoff.yaml"),
        Path("examples/narratostudio/creative_brief.example.json"),
        output_dir,
    )

    assert status == "success"
    assert manifest_path == output_dir / "manifest.json"
    assert (output_dir / "production_handoff.json").is_file()
    assert (output_dir / "production_report.md").is_file()


def test_narratostudio_inspect_and_review_pass_for_valid_run(tmp_path) -> None:
    output_dir = _run_narratostudio_workflow(tmp_path)

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)

    assert inspection["status"] == "pass"
    assert inspection["quality_report"]["summary"]["quality_profile"] == "narratostudio_production_handoff"
    assert review["status"] == "passed"
    assert "narratostudio_artifacts" in [section["name"] for section in review["sections"]]


def test_narratostudio_review_fails_on_prompt_shot_mismatch(tmp_path) -> None:
    output_dir = _run_narratostudio_workflow(tmp_path)
    prompt_pack = _read_json(output_dir / "prompt_pack.json")
    prompt_pack["prompts"][0]["shot_id"] = "missing_shot"
    (output_dir / "prompt_pack.json").write_text(json.dumps(prompt_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    inspect_run(output_dir)

    review = review_run(output_dir)

    failed_ids = {
        check["id"]
        for section in review["sections"]
        for check in section["checks"]
        if check["status"] == "failed"
    }
    assert review["status"] == "failed"
    assert "narratostudio_prompt_shots_exist" in failed_ids


def test_narratostudio_review_fails_on_artifact_schema_error(tmp_path) -> None:
    output_dir = _run_narratostudio_workflow(tmp_path)
    handoff = _read_json(output_dir / "production_handoff.json")
    handoff.pop("prompt_pack_id")
    (output_dir / "production_handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
    inspect_run(output_dir)

    review = review_run(output_dir)

    failed_ids = {
        check["id"]
        for section in review["sections"]
        for check in section["checks"]
        if check["status"] == "failed"
    }
    assert review["status"] == "failed"
    assert "narratostudio_production_handoff_schema_valid" in failed_ids


def test_narratostudio_review_fails_on_invalid_json(tmp_path) -> None:
    output_dir = _run_narratostudio_workflow(tmp_path)
    (output_dir / "prompt_pack.json").write_text("{not valid json", encoding="utf-8")
    inspect_run(output_dir)

    review = review_run(output_dir)

    failed_ids = {
        check["id"]
        for section in review["sections"]
        for check in section["checks"]
        if check["status"] == "failed"
    }
    assert review["status"] == "failed"
    assert "narratostudio_prompt_pack_json_valid" in failed_ids


def _run_narratostudio_workflow(tmp_path: Path) -> Path:
    output_dir = tmp_path / "narratostudio_run"
    workflow_path = "workflows/narratostudio_brief_to_production_handoff.yaml"
    workflow = load_workflow(workflow_path)
    context = WorkflowContext(
        run_id="narratostudio_run",
        workflow_name=workflow.name,
        workflow_path=workflow_path,
        mode=workflow.mode,
        quality_profile=workflow.quality_profile,
        output_dir=output_dir,
        inputs={"creative_brief": "examples/narratostudio/creative_brief.example.json"},
    )
    run = WorkflowRunner(default_node_registry()).run(workflow, context)
    assert run.status == "success"
    inspect_run(output_dir)
    return output_dir


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
