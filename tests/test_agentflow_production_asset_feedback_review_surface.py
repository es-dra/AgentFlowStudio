from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.memory.agentflow_production_review import review_agentflow_production_asset_feedback_loop
from agentflow_studio.workflow_engine import WorkflowContext, WorkflowRunner, default_node_registry, load_workflow


def test_agentflow_production_asset_feedback_review_surface_accepts_current_workflow_outputs(
    tmp_path: Path,
) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    sources = _source_payloads(output_dir)
    original_sources = copy.deepcopy(sources)
    original_files = sorted(path.name for path in output_dir.iterdir())

    review = review_agentflow_production_asset_feedback_loop(**sources)

    assert review["schema_version"] == "0.1.0"
    assert review["artifact_type"] == "agentflow_production_asset_feedback_review"
    assert review["validation_scope"] == "agentflow_production_asset_feedback_loop"
    assert review["runtime_status"] == "not_implemented"
    assert review["does_not_execute"] is True
    assert review["writes_long_term_memory"] is False
    assert review["overall_status"] == "passed"
    assert review["source_validation"]["overall_status"] == "passed"
    assert review["asset_memory_validation"]["overall_status"] == "passed"
    assert review["asset_memory_step_status"] == "passed"
    assert set(review["contract_set_keys"]) == {
        "intermediate_asset",
        "reusable_asset_profile",
        "asset_reuse_decision",
        "memory_candidate",
        "memory_promotion_decision",
    }
    assert sources == original_sources
    assert sorted(path.name for path in output_dir.iterdir()) == original_files


def test_agentflow_production_asset_feedback_review_surface_does_not_build_when_sources_fail(
    tmp_path: Path,
) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    sources = _source_payloads(output_dir)
    sources["memory_candidates"]["candidates"] = None

    review = review_agentflow_production_asset_feedback_loop(**sources)

    assert review["overall_status"] == "failed"
    assert review["source_validation"]["overall_status"] == "failed"
    assert review["asset_memory_step_status"] == "not_run"
    assert review["asset_memory_validation"]["overall_status"] == "not_run"
    assert review["asset_memory_validation"]["skip_reason"] == "source_validation_failed"
    assert review["contract_set_keys"] == []
    assert _failed_check_ids(review["source_validation"]) >= {"memory_candidates_candidate_only"}


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


def _source_payloads(output_dir: Path) -> dict[str, dict]:
    return {
        "production_handoff": _read_json(output_dir / "production_handoff.json"),
        "memory_candidates": _read_json(output_dir / "memory_candidates.json"),
        "feedback_signal_log": _read_json(output_dir / "feedback_signal_log.json"),
        "cost_quality_trace": _read_json(output_dir / "cost_quality_trace.json"),
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _failed_check_ids(validation: dict) -> set[str]:
    return {check["check_id"] for check in validation["checks"] if check["status"] == "failed"}
