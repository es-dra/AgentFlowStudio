from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import build_production_memory_operator_loop_run, write_production_memory_operator_loop_run
from agentflow.memory.production_operator_manifest_check import (
    OPERATOR_MANIFEST_CHECK_KIND,
    check_operator_manifest,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _write_operator_loop(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T15:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(result, tmp_path)
    return tmp_path / "production_memory_operator_loop_run.json"


def test_operator_manifest_check_passes_complete_artifact_chain(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)

    check = check_operator_manifest(manifest_path)

    assert check["kind"] == OPERATOR_MANIFEST_CHECK_KIND
    assert check["check_status"] == "passed"
    assert check["provider_calls_started"] is False
    assert check["writes_long_term_memory"] is False
    assert check["writes_company_kb"] is False
    assert check["missing_refs"] == []
    assert check["mismatched_refs"] == []
    assert check["failed_controls"] == []
    assert check["checked_ref_count"] == len(check["checked_refs"])
    assert "next_pass_result/next_pass_result.json" in {ref["path"] for ref in check["checked_refs"]}


def test_operator_manifest_check_reports_missing_required_ref(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)
    (tmp_path / "next_context_handoff" / "next_context_handoff.json").unlink()

    check = check_operator_manifest(manifest_path)

    assert check["check_status"] == "failed"
    assert check["missing_refs"] == ["next_context_handoff/next_context_handoff.json"]
    assert check["ready_for_next_pass"] is False


def test_operator_manifest_check_reports_artifact_type_mismatch(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)
    context_path = tmp_path / "run" / "context_bundle.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    context["kind"] = "wrong_kind"
    context_path.write_text(json.dumps(context), encoding="utf-8")

    check = check_operator_manifest(manifest_path)

    assert check["check_status"] == "failed"
    assert check["mismatched_refs"] == [
        {
            "path": "run/context_bundle.json",
            "expected_artifact_type": "agentflow_production_memory_context_bundle",
            "actual_artifact_type": "wrong_kind",
        }
    ]
    assert check["ready_for_next_pass"] is False


def test_operator_manifest_check_reports_failed_operator_node(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["operator_loop_nodes"][0]["status"] = "blocked"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    check = check_operator_manifest(manifest_path)

    assert check["check_status"] == "failed"
    assert check["failed_nodes"] == [{"node_id": "project_input", "status": "blocked"}]
    assert check["ready_for_next_pass"] is False


def test_operator_manifest_check_cli_writes_report_and_fails_on_missing_ref(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)
    report_path = tmp_path / "operator_manifest_check.json"

    success = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-check-operator-manifest",
            str(manifest_path),
            "--output",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Operator manifest check: passed" in success.stdout
    assert "Failed nodes: 0" in success.stdout
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["kind"] == OPERATOR_MANIFEST_CHECK_KIND
    assert report["check_status"] == "passed"

    (tmp_path / "run" / "next_pass_bundle.json").unlink()
    failure = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-check-operator-manifest",
            str(manifest_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert failure.returncode == 1
    assert "Operator manifest check: failed" in failure.stdout
    assert "Missing refs: 1" in failure.stdout
