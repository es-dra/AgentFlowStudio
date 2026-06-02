from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from agentflow.memory.production_operator_run_package import (
    OPERATOR_RUN_PACKAGE_KIND,
    build_operator_run_package,
    write_operator_run_package,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _operator_chain(tmp_path: Path, *, draft_next_pass_result: bool = False) -> tuple[dict, dict, dict]:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T18:10:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=draft_next_pass_result,
    )
    write_production_memory_operator_loop_run(result, tmp_path, write_handoff_packet=True)
    manifest = json.loads((tmp_path / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    check = json.loads((tmp_path / "operator_manifest_check" / "operator_manifest_check.json").read_text(encoding="utf-8"))
    handoff = json.loads((tmp_path / "operator_handoff" / "operator_handoff_packet.json").read_text(encoding="utf-8"))
    return manifest, check, handoff


def test_operator_run_package_summarizes_ready_operator_chain(tmp_path: Path) -> None:
    manifest, check, handoff = _operator_chain(tmp_path / "source")

    package = build_operator_run_package(
        manifest,
        manifest_check=check,
        handoff_packet=handoff,
        generated_at="2026-06-02T18:15:00+08:00",
    )

    assert package["kind"] == OPERATOR_RUN_PACKAGE_KIND
    assert package["package_status"] == "ready"
    assert package["source_operator_loop_id"] == manifest["loop_id"]
    assert package["manifest_chain_status"] == "ready"
    assert package["manifest_check_status"] == "passed"
    assert package["handoff_status"] == "ready"
    assert package["provider_mode"] == "no-provider"
    assert package["provider_calls_started"] is False
    assert package["writes_long_term_memory"] is False
    assert package["writes_company_kb"] is False
    assert package["next_operator_action"] == handoff["next_operator_action"]
    assert "not human acceptance" in package["non_claims"]
    assert "not business validation" in package["non_claims"]
    assert "not provider success" in package["non_claims"]

    item_paths = {item["path"] for item in package["package_items"]}
    assert "production_memory_operator_loop_run.json" in item_paths
    assert "operator_manifest_check/operator_manifest_check.json" in item_paths
    assert "operator_handoff/operator_handoff_packet.json" in item_paths
    assert "operator_handoff/operator_handoff_packet.md" in item_paths

    controls = {control["control_id"]: control["status"] for control in package["controls"]}
    assert controls["manifest_chain_ready"] == "passed"
    assert controls["operator_manifest_check_passed"] == "passed"
    assert controls["operator_handoff_ready"] == "passed"
    assert controls["provider_calls_not_started"] == "passed"
    assert controls["company_kb_write_disabled"] == "passed"


def test_operator_run_package_blocks_failed_handoff_packet(tmp_path: Path) -> None:
    manifest, check, handoff = _operator_chain(tmp_path / "source")
    handoff["handoff_status"] = "blocked"
    handoff["blocked_items"] = [{"ref": "operator_manifest_check", "reason": "operator manifest check did not pass"}]

    package = build_operator_run_package(
        manifest,
        manifest_check=check,
        handoff_packet=handoff,
        generated_at="2026-06-02T18:15:00+08:00",
    )

    assert package["package_status"] == "blocked"
    blockers = {item["ref"]: item["reason"] for item in package["blocked_items"]}
    assert blockers["operator_handoff"] == "operator handoff packet is not ready"
    assert blockers["operator_manifest_check"] == "operator manifest check did not pass"
    controls = {control["control_id"]: control["status"] for control in package["controls"]}
    assert controls["operator_handoff_ready"] == "failed"


def test_operator_run_package_blocks_mismatched_handoff_source(tmp_path: Path) -> None:
    manifest, check, handoff = _operator_chain(tmp_path / "source")
    handoff["source_operator_loop_id"] = "operator-loop:other-run"

    package = build_operator_run_package(
        manifest,
        manifest_check=check,
        handoff_packet=handoff,
        generated_at="2026-06-02T18:15:00+08:00",
    )

    assert package["package_status"] == "blocked"
    blockers = {item["ref"]: item["reason"] for item in package["blocked_items"]}
    assert blockers["operator_handoff"] == "operator handoff source does not match manifest"
    controls = {control["control_id"]: control["status"] for control in package["controls"]}
    assert controls["operator_handoff_source_matches_manifest"] == "failed"


def test_operator_run_package_writes_json_and_markdown(tmp_path: Path) -> None:
    manifest, check, handoff = _operator_chain(tmp_path / "source")
    package = build_operator_run_package(
        manifest,
        manifest_check=check,
        handoff_packet=handoff,
        generated_at="2026-06-02T18:15:00+08:00",
    )

    written = write_operator_run_package(package, tmp_path / "operator_run_package")

    json_path = tmp_path / "operator_run_package" / "operator_run_package.json"
    markdown_path = tmp_path / "operator_run_package" / "operator_run_package.md"
    assert json_path in written
    assert markdown_path in written
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Production Memory Operator Run Package" in markdown
    assert "Status: ready" in markdown
    assert "Manifest check: passed" in markdown
    assert "Operator handoff: ready" in markdown
    assert "Company KB write: disabled" in markdown


def test_operator_loop_cli_can_write_run_package_with_handoff_packet(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-02T18:10:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--draft-next-pass-result",
            "--write-run-package",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    package_path = output_dir / "operator_run_package" / "operator_run_package.json"
    assert "Operator manifest check: passed" in result.stdout
    assert "Operator handoff packet: ready" in result.stdout
    assert "Operator run package: ready" in result.stdout
    assert package_path.exists()
    assert (output_dir / "operator_run_package" / "operator_run_package.md").exists()
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert package["kind"] == OPERATOR_RUN_PACKAGE_KIND
    assert package["package_status"] == "ready"
    assert package["next_operator_action"]["action"] == "review_or_complete_next_pass_result"
