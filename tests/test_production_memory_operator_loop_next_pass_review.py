from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import build_production_memory_operator_loop_run
from tests.fixtures.production_memory_operator_loop import EXAMPLE_PATH, next_pass_result_for


def test_operator_loop_can_include_explicit_next_pass_review() -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T04:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )

    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T04:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        next_pass_result=next_pass_result_for(seed["next_task_packet"]),
    )

    manifest = result["manifest"]
    node_ids = {node["node_id"] for node in manifest["operator_loop_nodes"]}
    artifact_types = {artifact["artifact_type"] for artifact in manifest["output_artifacts"]}
    assert manifest["chain_status"] == "ready"
    assert "next_pass_review" in node_ids
    assert manifest["next_pass_review"]["review_status"] == "ready_for_operator_review"
    assert manifest["next_pass_review"]["feedback_candidate_count"] == 1
    assert result["next_pass_review"]["kind"] == "agentflow_production_memory_next_pass_review"
    assert "agentflow_production_memory_next_pass_review" in artifact_types
    assert manifest["writes_company_kb"] is False
    assert manifest["provider_calls_started"] is False


def test_operator_loop_rejects_draft_result_scaffold_with_explicit_next_pass_result() -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T12:40:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )

    try:
        build_production_memory_operator_loop_run(
            loop,
            generated_at="2026-06-02T12:40:00+08:00",
            source_kb_status="restructuring_or_unknown",
            draft_next_pass_result=True,
            next_pass_result=next_pass_result_for(seed["next_task_packet"]),
        )
    except ValueError as exc:
        assert "draft_next_pass_result cannot be combined with next_pass_result" in str(exc)
    else:
        raise AssertionError("draft scaffold was accepted with an explicit next-pass result")


def test_operator_loop_cli_writes_optional_next_pass_review_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"
    result_path = tmp_path / "next_pass_result.json"
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T04:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    result_path.write_text(json.dumps(next_pass_result_for(seed["next_task_packet"]), indent=2), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-02T04:00:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--next-pass-result",
            str(result_path),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in result.stdout
    assert "Next pass review: ready_for_operator_review" in result.stdout
    assert (output_dir / "next_pass_review" / "next_pass_review.json").exists()
    assert (output_dir / "next_pass_review" / "next_pass_review.md").exists()
    manifest = json.loads((output_dir / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert "next_pass_review/next_pass_review.json" in artifact_paths
    assert "next_pass_review/next_pass_review.md" in artifact_paths
    assert manifest["next_pass_review"]["review_status"] == "ready_for_operator_review"
