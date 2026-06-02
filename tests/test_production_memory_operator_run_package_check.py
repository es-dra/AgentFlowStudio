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
from agentflow.memory.production_operator_run_package_check import (
    OPERATOR_RUN_PACKAGE_CHECK_KIND,
    check_operator_run_package,
    render_operator_run_package_check_markdown,
    write_operator_run_package_check_report,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _write_operator_run_package(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T20:30:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(result, tmp_path, write_run_package=True)
    return tmp_path / "operator_run_package" / "operator_run_package.json"


def test_operator_run_package_check_passes_complete_package(tmp_path: Path) -> None:
    package_path = _write_operator_run_package(tmp_path)

    check = check_operator_run_package(package_path)

    assert check["kind"] == OPERATOR_RUN_PACKAGE_CHECK_KIND
    assert check["check_status"] == "passed"
    assert check["package_status"] == "ready"
    assert check["ready_for_handoff"] is True
    assert check["provider_calls_started"] is False
    assert check["writes_long_term_memory"] is False
    assert check["writes_company_kb"] is False
    assert check["missing_refs"] == []
    assert check["mismatched_refs"] == []
    assert check["unsafe_refs"] == []
    assert check["failed_controls"] == []
    assert check["checked_item_count"] == len(check["checked_items"])
    assert "operator_handoff/operator_handoff_packet.json" in {item["path"] for item in check["checked_items"]}


def test_operator_loop_writer_can_emit_run_package_check_after_run_package(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T22:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )

    written_paths = write_production_memory_operator_loop_run(
        result,
        tmp_path,
        write_run_package=True,
        write_run_package_check=True,
    )

    check_path = tmp_path / "operator_run_package_check" / "operator_run_package_check.json"
    markdown_path = tmp_path / "operator_run_package_check" / "operator_run_package_check.md"
    assert check_path in written_paths
    assert markdown_path in written_paths
    assert check_path.exists()
    assert markdown_path.exists()
    check = json.loads(check_path.read_text(encoding="utf-8"))
    assert check["kind"] == OPERATOR_RUN_PACKAGE_CHECK_KIND
    assert check["check_status"] == "passed"
    assert check["ready_for_handoff"] is True
    assert check["checked_item_count"] == 18
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Status: passed" in markdown
    assert "Provider calls: not started" in markdown
    assert "Company KB write: disabled" in markdown
    assert result["operator_run_package_check"]["check_status"] == "passed"


def test_operator_run_package_check_markdown_report_preserves_boundaries(tmp_path: Path) -> None:
    package_path = _write_operator_run_package(tmp_path)
    check = check_operator_run_package(package_path)

    markdown = render_operator_run_package_check_markdown(check)

    assert "# Production Memory Operator Run Package Check" in markdown
    assert "Status: passed" in markdown
    assert "Ready for handoff: true" in markdown
    assert "Checked items: 18" in markdown
    assert "Missing refs: 0" in markdown
    assert "Failed controls: 0" in markdown
    assert "Provider calls: not started" in markdown
    assert "Durable memory write: disabled" in markdown
    assert "Company KB write: disabled" in markdown
    assert "- not human acceptance" in markdown
    assert "- not business validation" in markdown
    assert "- not durable memory" in markdown
    assert "- not provider success" in markdown


def test_operator_run_package_check_report_writer_preserves_json_contract(tmp_path: Path) -> None:
    package_path = _write_operator_run_package(tmp_path)
    check = check_operator_run_package(package_path)

    written_paths = write_operator_run_package_check_report(check, tmp_path / "check_report")

    json_path = tmp_path / "check_report" / "operator_run_package_check.json"
    markdown_path = tmp_path / "check_report" / "operator_run_package_check.md"
    assert written_paths == [json_path, markdown_path]
    assert json_path.exists()
    assert markdown_path.exists()
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["kind"] == OPERATOR_RUN_PACKAGE_CHECK_KIND
    assert report["check_status"] == "passed"
    assert "Ready for handoff: true" in markdown_path.read_text(encoding="utf-8")


def test_operator_run_package_check_reports_missing_package_item(tmp_path: Path) -> None:
    package_path = _write_operator_run_package(tmp_path)
    (tmp_path / "operator_handoff" / "operator_handoff_packet.json").unlink()

    check = check_operator_run_package(package_path)

    assert check["check_status"] == "failed"
    assert check["ready_for_handoff"] is False
    assert check["missing_refs"] == ["operator_handoff/operator_handoff_packet.json"]


def test_operator_run_package_check_blocks_provider_and_write_boundaries(tmp_path: Path) -> None:
    package_path = _write_operator_run_package(tmp_path)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["provider_calls_started"] = True
    package["writes_company_kb"] = True
    package_path.write_text(json.dumps(package), encoding="utf-8")

    check = check_operator_run_package(package_path)

    assert check["check_status"] == "failed"
    assert check["ready_for_handoff"] is False
    assert check["provider_calls_started"] is True
    assert check["writes_company_kb"] is True
    failed_controls = {item["control_id"]: item["status"] for item in check["failed_controls"]}
    assert failed_controls["provider_calls_not_started"] == "failed"
    assert failed_controls["company_kb_write_disabled"] == "failed"


def test_operator_run_package_check_cli_writes_report_and_fails_on_missing_ref(tmp_path: Path) -> None:
    package_path = _write_operator_run_package(tmp_path)
    report_path = tmp_path / "operator_run_package_check.json"

    success = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-check-operator-run-package",
            str(package_path),
            "--output",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Operator run package check: passed" in success.stdout
    assert "Missing package items: 0" in success.stdout
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["kind"] == OPERATOR_RUN_PACKAGE_CHECK_KIND
    assert report["check_status"] == "passed"

    (tmp_path / "operator_manifest_check" / "operator_manifest_check.json").unlink()
    failure = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-check-operator-run-package",
            str(package_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert failure.returncode == 1
    assert "Operator run package check: failed" in failure.stdout
    assert "Missing package items: 1" in failure.stdout


def test_operator_loop_cli_can_write_run_package_check_with_run_package(tmp_path: Path) -> None:
    output_dir = tmp_path / "operator_loop"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-operator-no-provider",
            str(EXAMPLE_PATH),
            "--generated-at",
            "2026-06-02T22:05:00+08:00",
            "--source-kb-status",
            "restructuring_or_unknown",
            "--draft-next-pass-result",
            "--write-run-package",
            "--write-run-package-check",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    check_path = output_dir / "operator_run_package_check" / "operator_run_package_check.json"
    markdown_path = output_dir / "operator_run_package_check" / "operator_run_package_check.md"
    assert "Operator run package: ready" in result.stdout
    assert "Operator run package check: passed" in result.stdout
    assert check_path.exists()
    assert markdown_path.exists()
    check = json.loads(check_path.read_text(encoding="utf-8"))
    assert check["kind"] == OPERATOR_RUN_PACKAGE_CHECK_KIND
    assert check["check_status"] == "passed"
    assert check["ready_for_handoff"] is True
    assert "Failed controls: 0" in markdown_path.read_text(encoding="utf-8")
