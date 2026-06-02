from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_next_pass_result import NEXT_PASS_RESULT_KIND
from agentflow.memory.production_operator_loop import (
    OPERATOR_LOOP_KIND,
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _next_pass_result_for(packet: dict) -> dict:
    used_refs = [ref["ref_id"] for ref in packet["allowed_context_refs"][:2]]
    return {
        "kind": NEXT_PASS_RESULT_KIND,
        "artifact_type": NEXT_PASS_RESULT_KIND,
        "schema_version": packet["schema_version"],
        "task_packet_id": packet["task_packet_id"],
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "output_artifacts": [
            {
                "ref_id": "next-pass:artifact:draft-001",
                "title": "Second pass draft",
                "status": "draft",
                "used_context_refs": used_refs,
            }
        ],
        "feedback_events": [
            {
                "feedback_id": "feedback:next-pass-001",
                "target_ref": "next-pass:artifact:draft-001",
                "decision": "needs_revision",
                "summary": "Second pass needs operator review before memory promotion.",
            }
        ],
    }


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


def test_operator_loop_can_draft_next_pass_result_scaffold_without_review() -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)

    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T12:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    manifest = result["manifest"]
    node_ids = {node["node_id"] for node in manifest["operator_loop_nodes"]}
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    scaffold = result["next_pass_result"]
    assert manifest["chain_status"] == "ready"
    assert scaffold["kind"] == NEXT_PASS_RESULT_KIND
    assert scaffold["result_status"] == "scaffolded_for_operator_completion"
    assert scaffold["provider_calls_started"] is False
    assert scaffold["writes_long_term_memory"] is False
    assert scaffold["writes_company_kb"] is False
    assert scaffold["feedback_events"] == []
    assert "next_pass_result" in node_ids
    assert "next_pass_review" not in node_ids
    assert "next_pass_review" not in result
    assert manifest["next_pass_result"]["result_status"] == "scaffolded_for_operator_completion"
    assert manifest["next_pass_result"]["output_artifact_count"] == 1
    assert "next_pass_result/next_pass_result.json" in artifact_paths
    assert "next_pass_result/next_pass_result.md" in artifact_paths


def test_operator_loop_cli_writes_optional_next_pass_result_scaffold(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-02T12:00:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--draft-next-pass-result",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in result.stdout
    assert "Next pass result scaffold: scaffolded_for_operator_completion" in result.stdout
    assert (output_dir / "next_pass_result" / "next_pass_result.json").exists()
    assert (output_dir / "next_pass_result" / "next_pass_result.md").exists()
    assert not (output_dir / "next_pass_review" / "next_pass_review.json").exists()
    manifest = json.loads((output_dir / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    artifact_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    assert manifest["next_pass_result"]["result_status"] == "scaffolded_for_operator_completion"
    assert "next_pass_result/next_pass_result.json" in artifact_paths
    assert "next_pass_result/next_pass_result.md" in artifact_paths
    assert "next_pass_review/next_pass_review.json" not in artifact_paths


def test_operator_loop_manifest_embeds_next_operator_start_brief_summary(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    write_production_memory_operator_loop_run(
        result,
        tmp_path,
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
    )

    manifest = json.loads((tmp_path / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    start_packet = manifest["next_operator_start_packet"]
    assert start_packet["next_operator_action"] == "review_or_complete_next_pass_result"
    assert start_packet["operator_prompt_excerpt"].startswith("Use the generated next_task_packet")
    assert "Do not call remote providers" in start_packet["operator_prompt_excerpt"]
    assert start_packet["start_requirements"] == [
        "Execute next operator action: review_or_complete_next_pass_result",
        "Use only checked package items and the embedded operator prompt.",
        "Do not use blocked refs, unpromoted candidates, or feedback events as memory.",
        "Do not call remote providers without an explicit provider gate.",
        "Do not write Company KB or durable memory from this start packet.",
    ]


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
        next_pass_result=_next_pass_result_for(seed["next_task_packet"]),
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
            next_pass_result=_next_pass_result_for(seed["next_task_packet"]),
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
    result_path.write_text(json.dumps(_next_pass_result_for(seed["next_task_packet"]), indent=2), encoding="utf-8")

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
