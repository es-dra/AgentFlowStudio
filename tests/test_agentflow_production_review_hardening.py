from __future__ import annotations

import json
from pathlib import Path

from agentflow_studio.harness.inspection import inspect_run
from agentflow_studio.harness.reviewer import review_run
from agentflow_studio.workflow_engine import WorkflowContext, WorkflowRunner, default_node_registry, load_workflow


def test_agentflow_production_review_fails_when_scene_references_missing_beat(tmp_path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    scene_plan = _read_json(output_dir / "scene_plan.json")
    scene_plan["scenes"][0]["beat_id"] = "missing_beat"
    _write_json(output_dir / "scene_plan.json", scene_plan)

    failed_ids = _failed_review_check_ids(output_dir)

    assert "agentflow_production_scene_beats_exist" in failed_ids


def test_agentflow_production_review_fails_when_outline_beat_has_no_scene(tmp_path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    scene_plan = _read_json(output_dir / "scene_plan.json")
    scene_plan["scenes"] = [scene for scene in scene_plan["scenes"] if scene["beat_id"] != "beat_003"]
    _write_json(output_dir / "scene_plan.json", scene_plan)

    failed_ids = _failed_review_check_ids(output_dir)

    assert "agentflow_production_outline_beats_covered_by_scenes" in failed_ids


def test_agentflow_production_review_fails_when_scene_has_no_shot(tmp_path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    shot_plan = _read_json(output_dir / "shot_plan.json")
    shot_plan["shots"] = [shot for shot in shot_plan["shots"] if shot["scene_id"] != "scene_003"]
    _write_json(output_dir / "shot_plan.json", shot_plan)

    failed_ids = _failed_review_check_ids(output_dir)

    assert "agentflow_production_scenes_covered_by_shots" in failed_ids


def test_agentflow_production_review_fails_when_shot_has_no_prompt(tmp_path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    prompt_pack = _read_json(output_dir / "prompt_pack.json")
    prompt_pack["prompts"] = [
        prompt for prompt in prompt_pack["prompts"] if prompt["shot_id"] != "scene_003_shot_002"
    ]
    _write_json(output_dir / "prompt_pack.json", prompt_pack)

    failed_ids = _failed_review_check_ids(output_dir)

    assert "agentflow_production_shots_covered_by_prompts" in failed_ids


def test_agentflow_production_review_fails_when_handoff_core_reference_breaks(tmp_path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    handoff = _read_json(output_dir / "production_handoff.json")
    handoff["scene_plan_id"] = "wrong_scene_plan"
    _write_json(output_dir / "production_handoff.json", handoff)

    failed_ids = _failed_review_check_ids(output_dir)

    assert "agentflow_production_handoff_core_ids_match" in failed_ids


def test_agentflow_production_review_fails_when_handoff_artifact_ref_missing(tmp_path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    handoff = _read_json(output_dir / "production_handoff.json")
    handoff["artifact_refs"].pop("scene_plan")
    _write_json(output_dir / "production_handoff.json", handoff)

    failed_ids = _failed_review_check_ids(output_dir)

    assert "agentflow_production_handoff_artifact_refs_complete" in failed_ids


def test_agentflow_production_review_lightly_checks_production_report_identity(tmp_path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    (output_dir / "production_report.md").write_text("unrelated report\n", encoding="utf-8")

    failed_ids = _failed_review_check_ids(output_dir)

    assert "agentflow_production_production_report_identity" in failed_ids


def _run_agentflow_production_workflow(tmp_path: Path) -> Path:
    output_dir = tmp_path / "agentflow_production_run"
    workflow_path = "workflows/agentflow_production_handoff.yaml"
    workflow = load_workflow(workflow_path)
    context = WorkflowContext(
        run_id="agentflow_production_run",
        workflow_name=workflow.name,
        workflow_path=workflow_path,
        mode=workflow.mode,
        quality_profile=workflow.quality_profile,
        output_dir=output_dir,
        inputs={"creative_brief": "examples/agentflow_production/creative_brief.example.json"},
    )
    run = WorkflowRunner(default_node_registry()).run(workflow, context)
    assert run.status == "success"
    return output_dir


def _failed_review_check_ids(output_dir: Path) -> set[str]:
    inspect_run(output_dir)
    review = review_run(output_dir)
    return {
        check["id"]
        for section in review["sections"]
        for check in section["checks"]
        if check["status"] == "failed"
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
