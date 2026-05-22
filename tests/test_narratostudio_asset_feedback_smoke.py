from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agentflow.memory.assets import validate_asset_memory_contract_set
from agentflow.memory.narratostudio_assets import build_narratostudio_asset_memory_contract_set
from narratocut.workflow_engine import WorkflowContext, WorkflowRunner, default_node_registry, load_workflow


def test_narratostudio_workflow_outputs_build_asset_memory_contract_set(tmp_path: Path) -> None:
    output_dir = _run_narratostudio_workflow(tmp_path)
    source_payloads = _source_payloads(output_dir)
    original_payloads = copy.deepcopy(source_payloads)
    original_files = sorted(path.name for path in output_dir.iterdir())

    contracts = build_narratostudio_asset_memory_contract_set(**source_payloads)
    validation = validate_asset_memory_contract_set(**contracts)

    assert source_payloads == original_payloads
    assert sorted(path.name for path in output_dir.iterdir()) == original_files
    assert set(contracts) == {
        "intermediate_asset",
        "reusable_asset_profile",
        "asset_reuse_decision",
        "memory_candidate",
        "memory_promotion_decision",
    }
    assert validation["overall_status"] == "passed"
    assert validation["runtime_status"] == "not_implemented"
    assert validation["does_not_execute"] is True
    assert validation["writes_long_term_memory"] is False
    assert contracts["intermediate_asset"]["module_origin"] == "NarratoStudio"
    assert contracts["intermediate_asset"]["reuse_status"] == "candidate"
    assert contracts["memory_candidate"]["promotion_status"] == "candidate"
    assert contracts["memory_candidate"]["source_of_truth"] == "feedback.jsonl"
    assert contracts["memory_promotion_decision"]["promotion_mode"] == "human_reviewed"
    assert contracts["memory_promotion_decision"]["writes_long_term_memory"] is False
    assert contracts["reusable_asset_profile"]["reuse_policy"]["requires_human_review"] is True
    assert contracts["asset_reuse_decision"]["does_not_execute"] is True


def test_narratostudio_asset_memory_contract_set_requires_candidate_memory() -> None:
    payloads = {
        "production_handoff": {"handoff_id": "handoff_001", "content_mode": "episodic_story_production"},
        "memory_candidates": {"candidates": []},
        "feedback_signal_log": {"source_of_truth": "feedback.jsonl", "is_primary_feedback_store": False},
        "cost_quality_trace": {"provider": "local_deterministic", "execution_mode": "local_deterministic"},
    }

    with pytest.raises(ValueError, match="memory candidate"):
        build_narratostudio_asset_memory_contract_set(**payloads)


def test_narratostudio_asset_memory_contract_set_does_not_normalize_missing_feedback_source(
    tmp_path: Path,
) -> None:
    output_dir = _run_narratostudio_workflow(tmp_path)
    source_payloads = _source_payloads(output_dir)
    source_payloads["feedback_signal_log"].pop("source_of_truth")

    contracts = build_narratostudio_asset_memory_contract_set(**source_payloads)
    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"memory_candidate_uses_raw_feedback_source"}


def test_narratostudio_asset_memory_contract_set_does_not_normalize_missing_promotion_status(
    tmp_path: Path,
) -> None:
    output_dir = _run_narratostudio_workflow(tmp_path)
    source_payloads = _source_payloads(output_dir)
    source_payloads["memory_candidates"]["candidates"][0].pop("promotion_status")

    contracts = build_narratostudio_asset_memory_contract_set(**source_payloads)
    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"memory_candidate_candidate_only"}


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
