from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.memory.agentflow_production_assets import validate_agentflow_production_asset_feedback_sources
from agentflow_studio.workflow_engine import WorkflowContext, WorkflowRunner, default_node_registry, load_workflow


def test_agentflow_production_asset_feedback_source_validator_accepts_current_workflow_outputs(tmp_path: Path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    sources = _source_payloads(output_dir)
    original_sources = copy.deepcopy(sources)

    validation = validate_agentflow_production_asset_feedback_sources(**sources)

    assert validation["schema_version"] == "0.1.0"
    assert validation["artifact_type"] == "agentflow_production_asset_feedback_source_validation"
    assert validation["validation_scope"] == "agentflow_production_asset_feedback_sources"
    assert validation["runtime_status"] == "not_implemented"
    assert validation["does_not_execute"] is True
    assert validation["writes_long_term_memory"] is False
    assert validation["overall_status"] == "passed"
    assert sources == original_sources
    assert all(check["status"] == "passed" for check in validation["checks"])


def test_agentflow_production_asset_feedback_source_validator_rejects_primary_feedback_store(tmp_path: Path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    sources = _source_payloads(output_dir)
    sources["feedback_signal_log"]["is_primary_feedback_store"] = True

    validation = validate_agentflow_production_asset_feedback_sources(**sources)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"feedback_signal_log_is_derived"}


def test_agentflow_production_asset_feedback_source_validator_rejects_malformed_candidate_store(
    tmp_path: Path,
) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    sources = _source_payloads(output_dir)
    sources["memory_candidates"]["candidates"] = None

    validation = validate_agentflow_production_asset_feedback_sources(**sources)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"memory_candidates_candidate_only"}


def test_agentflow_production_asset_feedback_source_validator_requires_candidate_identity(
    tmp_path: Path,
) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    sources = _source_payloads(output_dir)
    sources["memory_candidates"]["candidates"][0].pop("id")

    validation = validate_agentflow_production_asset_feedback_sources(**sources)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"memory_candidates_have_mapping_fields"}


def test_agentflow_production_asset_feedback_source_validator_rejects_non_local_cost_trace(tmp_path: Path) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    sources = _source_payloads(output_dir)
    sources["cost_quality_trace"]["provider"] = "remote_model"

    validation = validate_agentflow_production_asset_feedback_sources(**sources)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"cost_quality_trace_local_deterministic"}


def test_agentflow_production_asset_feedback_source_validator_rejects_handoff_without_prompt_pack_ref(
    tmp_path: Path,
) -> None:
    output_dir = _run_agentflow_production_workflow(tmp_path)
    sources = _source_payloads(output_dir)
    sources["production_handoff"]["artifact_refs"].pop("prompt_pack")

    validation = validate_agentflow_production_asset_feedback_sources(**sources)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"production_handoff_has_prompt_pack_ref"}


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
