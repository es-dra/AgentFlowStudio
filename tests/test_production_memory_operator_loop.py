from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    OPERATOR_LOOP_KIND,
    build_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_operator_loop_run_manifest_covers_all_no_provider_nodes() -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)

    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T01:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    manifest = result["manifest"]
    node_ids = {node["node_id"] for node in manifest["operator_loop_nodes"]}
    controls = {control["control_id"]: control["status"] for control in manifest["controls"]}

    assert manifest["kind"] == OPERATOR_LOOP_KIND
    assert manifest["chain_status"] == "ready"
    assert manifest["provider_mode"] == "no-provider"
    assert manifest["provider_calls_started"] is False
    assert manifest["writes_long_term_memory"] is False
    assert manifest["writes_company_kb"] is False
    assert node_ids == {
        "project_input",
        "artifact_ledger",
        "feedback_events",
        "memory_candidates",
        "promotion_decisions",
        "context_bundle",
        "pass_readiness",
        "next_pass_bundle",
        "next_context_handoff",
        "next_task_packet",
        "session_report",
        "company_kb_feedback_candidate_packet",
    }
    assert controls["no_provider_mode"] == "passed"
    assert controls["company_kb_write_disabled"] == "passed"
    assert controls["company_feedback_candidate_only"] == "passed"
    assert manifest["context_summary"]["included_ref_count"] == 3
    assert manifest["context_summary"]["blocked_ref_count"] == 3
    assert manifest["next_context_handoff"]["handoff_status"] == "ready"
    assert manifest["next_context_handoff"]["next_context_ref_count"] == 3
    assert manifest["next_task_packet"]["packet_status"] == "ready"
    assert manifest["next_task_packet"]["allowed_ref_count"] == 3
    assert result["session_report"]["kind"] == "agentflow_production_memory_session_report"
    assert result["company_kb_feedback_candidate_packet"]["promotion_status"] == "candidate_only"
    assert result["next_task_packet"]["kind"] == "agentflow_production_memory_next_task_packet"


def test_operator_loop_cli_writes_auditable_artifact_chain(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-02T01:00:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in result.stdout
    assert "Provider calls: not started" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    assert (output_dir / "run" / "production_memory_loop_run.json").exists()
    assert (output_dir / "run" / "context_bundle.json").exists()
    assert (output_dir / "run" / "pass_readiness.json").exists()
    assert (output_dir / "run" / "next_pass_bundle.json").exists()
    assert (output_dir / "next_context_handoff" / "next_context_handoff.json").exists()
    assert (output_dir / "next_context_handoff" / "next_context_handoff.md").exists()
    assert (output_dir / "next_task_packet" / "next_task_packet.json").exists()
    assert (output_dir / "next_task_packet" / "next_task_packet.md").exists()
    assert (output_dir / "session_report" / "production_memory_session_report.json").exists()
    assert (output_dir / "company_kb_candidates" / "company_kb_feedback_candidate_packet.json").exists()

    manifest = json.loads((output_dir / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert manifest["kind"] == OPERATOR_LOOP_KIND
    assert manifest["chain_status"] == "ready"
    assert manifest["writes_company_kb"] is False
    assert "run/next_pass_bundle.json" in artifact_paths
    assert "next_context_handoff/next_context_handoff.json" in artifact_paths
    assert "next_context_handoff/next_context_handoff.md" in artifact_paths
    assert "next_task_packet/next_task_packet.json" in artifact_paths
    assert "next_task_packet/next_task_packet.md" in artifact_paths
    assert "session_report/production_memory_session_report.json" in artifact_paths
    assert "session_report/production_memory_session_report.md" in artifact_paths
    assert "company_kb_candidates/company_kb_feedback_candidate_packet.json" in artifact_paths
    assert "company_kb_candidates/company_kb_feedback_candidate_packet.md" in artifact_paths
    assert all(not Path(path).is_absolute() for path in artifact_paths)
