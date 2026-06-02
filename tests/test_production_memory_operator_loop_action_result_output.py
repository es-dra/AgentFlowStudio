from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_next_operator_action_result import NEXT_OPERATOR_ACTION_RESULT_KIND
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_operator_loop_cli_writes_post_check_next_operator_action_result(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-03T11:00:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--draft-next-pass-result",
            "--write-run-package",
            "--write-run-package-check",
            "--write-next-operator-start-packet",
            "--write-next-operator-start-event",
            "--next-operator-start-decision",
            "started",
            "--next-operator-start-summary",
            "Next operator started from the checked no-provider package.",
            "--write-next-operator-action-result",
            "--next-operator-action-decision",
            "completed",
            "--next-operator-action-summary",
            "Next operator completed the recorded no-provider action and returned explicit result refs.",
            "--next-operator-action-result-ref",
            "next_pass_result/next_pass_result.json",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator loop: ready" in result.stdout
    assert "Next operator start event: operator_started" in result.stdout
    assert "Next operator action result: action_completed" in result.stdout
    action_result_path = output_dir / "next_operator_action_result" / "next_operator_action_result.json"
    markdown_path = output_dir / "next_operator_action_result" / "next_operator_action_result.md"
    assert action_result_path.exists()
    assert markdown_path.exists()

    action_result = _read_json(action_result_path)
    manifest = _read_json(output_dir / "production_memory_operator_loop_run.json")
    package_check = _read_json(output_dir / "operator_run_package_check" / "operator_run_package_check.json")
    output_paths = {artifact["path"] for artifact in manifest["output_artifacts"]}
    post_check_paths = {artifact["path"] for artifact in manifest["post_check_artifacts"]}
    checked_package_paths = {item["path"] for item in package_check["checked_items"]}

    assert action_result["kind"] == NEXT_OPERATOR_ACTION_RESULT_KIND
    assert action_result["result_status"] == "action_completed"
    assert action_result["action_decision"] == "completed"
    assert action_result["source_start_event_status"] == "operator_started"
    assert action_result["result_refs"] == ["next_pass_result/next_pass_result.json"]
    assert action_result["action_result_is_acceptance"] is False
    assert action_result["action_result_is_execution"] is False
    assert action_result["action_result_is_memory"] is False
    assert action_result["creates_memory_candidate"] is False
    assert action_result["creates_promotion_decision"] is False
    assert action_result["provider_calls_started"] is False
    assert action_result["writes_long_term_memory"] is False
    assert action_result["writes_company_kb"] is False
    assert manifest["next_operator_action_result"]["result_status"] == "action_completed"
    assert manifest["next_operator_action_result"]["result_ref_count"] == 1
    assert manifest["next_operator_action_result"]["action_result_is_execution"] is False
    assert "next_operator_action_result/next_operator_action_result.json" in post_check_paths
    assert "next_operator_action_result/next_operator_action_result.md" in post_check_paths
    assert "next_operator_action_result/next_operator_action_result.json" not in output_paths
    assert "next_operator_action_result/next_operator_action_result.json" not in checked_package_paths


def test_operator_loop_writer_requires_start_event_for_action_result(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T11:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    with pytest.raises(ValueError, match="write_next_operator_action_result requires write_next_operator_start_event"):
        write_production_memory_operator_loop_run(
            result,
            tmp_path / "operator_loop",
            write_run_package=True,
            write_run_package_check=True,
            write_next_operator_start_packet=True,
            write_next_operator_action_result=True,
            next_operator_action_result_decision="completed",
            next_operator_action_result_summary="Next operator completed the recorded action.",
            next_operator_action_result_refs=["next_pass_result/next_pass_result.json"],
        )


def test_operator_loop_writer_requires_completed_action_result_refs(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T11:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    with pytest.raises(ValueError, match="completed next_operator_action_result requires result refs"):
        write_production_memory_operator_loop_run(
            result,
            tmp_path / "operator_loop",
            write_run_package=True,
            write_run_package_check=True,
            write_next_operator_start_packet=True,
            write_next_operator_start_event=True,
            next_operator_start_event_decision="started",
            next_operator_start_event_summary="Next operator started from the checked no-provider package.",
            write_next_operator_action_result=True,
            next_operator_action_result_decision="completed",
            next_operator_action_result_summary="Next operator completed the recorded action.",
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
