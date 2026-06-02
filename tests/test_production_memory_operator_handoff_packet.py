from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_handoff import (
    OPERATOR_HANDOFF_PACKET_KIND,
    build_operator_handoff_packet,
    render_operator_handoff_packet_markdown,
    write_operator_handoff_packet,
)
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _operator_loop_with_check(tmp_path: Path, *, generated_at: str = "2026-06-02T17:20:00+08:00") -> tuple[dict, dict]:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at=generated_at,
        source_kb_status="restructuring_or_unknown",
    )
    write_production_memory_operator_loop_run(result, tmp_path, write_manifest_check=True)
    manifest = json.loads((tmp_path / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    check = json.loads((tmp_path / "operator_manifest_check" / "operator_manifest_check.json").read_text(encoding="utf-8"))
    return manifest, check


def test_operator_handoff_packet_summarizes_ready_manifest_and_check(tmp_path: Path) -> None:
    manifest, check = _operator_loop_with_check(tmp_path)

    packet = build_operator_handoff_packet(
        manifest,
        manifest_check=check,
        generated_at="2026-06-02T17:25:00+08:00",
    )

    assert packet["kind"] == OPERATOR_HANDOFF_PACKET_KIND
    assert packet["handoff_status"] == "ready"
    assert packet["project_id"] == manifest["project_id"]
    assert packet["manifest_check_status"] == "passed"
    assert packet["checked_ref_count"] == check["checked_ref_count"]
    assert packet["output_artifact_count"] == len(manifest["output_artifacts"])
    assert packet["next_operator_action"]["action"] == "run_next_ai_task_from_next_task_packet"
    assert packet["context_summary"]["included_ref_count"] == 3
    assert packet["context_summary"]["blocked_ref_count"] == 3
    assert packet["provider_calls_started"] is False
    assert packet["writes_long_term_memory"] is False
    assert packet["writes_company_kb"] is False
    assert packet["blocked_items"] == []
    assert "Use the generated next_task_packet" in packet["handoff_prompt"]
    assert "Do not use blocked refs" in packet["handoff_prompt"]
    assert "Do not call remote providers" in packet["handoff_prompt"]
    assert "not human acceptance" in packet["non_claims"]
    controls = {control["control_id"]: control["status"] for control in packet["controls"]}
    assert controls["manifest_chain_ready"] == "passed"
    assert controls["operator_manifest_check_passed"] == "passed"
    assert controls["provider_calls_not_started"] == "passed"
    assert controls["company_kb_write_disabled"] == "passed"


def test_operator_handoff_packet_blocks_failed_manifest_check(tmp_path: Path) -> None:
    manifest, check = _operator_loop_with_check(tmp_path)
    check["check_status"] = "failed"
    check["missing_refs"] = ["run/context_bundle.json"]

    packet = build_operator_handoff_packet(
        manifest,
        manifest_check=check,
        generated_at="2026-06-02T17:25:00+08:00",
    )

    assert packet["handoff_status"] == "blocked"
    assert packet["next_operator_action"]["action"] == "resolve_operator_manifest_check_blockers"
    assert "run/context_bundle.json" in {item["ref"] for item in packet["blocked_items"]}
    controls = {control["control_id"]: control["status"] for control in packet["controls"]}
    assert controls["operator_manifest_check_passed"] == "failed"


def test_operator_handoff_packet_blocks_missing_manifest_check(tmp_path: Path) -> None:
    manifest, _check = _operator_loop_with_check(tmp_path)

    packet = build_operator_handoff_packet(
        manifest,
        generated_at="2026-06-02T17:25:00+08:00",
    )

    assert packet["handoff_status"] == "blocked"
    assert packet["manifest_check_status"] == "not_supplied"
    assert packet["next_operator_action"]["action"] == "run_operator_manifest_check"
    assert any(item["reason"] == "operator manifest check is required before handoff readiness" for item in packet["blocked_items"])


def test_operator_handoff_packet_reports_source_provider_and_write_blockers(tmp_path: Path) -> None:
    manifest, check = _operator_loop_with_check(tmp_path)
    manifest["provider_calls_started"] = True
    manifest["writes_long_term_memory"] = True
    manifest["writes_company_kb"] = True

    packet = build_operator_handoff_packet(
        manifest,
        manifest_check=check,
        generated_at="2026-06-02T17:25:00+08:00",
    )

    assert packet["handoff_status"] == "blocked"
    assert packet["provider_calls_started"] is True
    assert packet["writes_long_term_memory"] is True
    assert packet["writes_company_kb"] is True
    blocked = {item["ref"]: item["reason"] for item in packet["blocked_items"]}
    assert blocked["provider_calls"] == "provider calls started before no-provider handoff"
    assert blocked["long_term_memory"] == "handoff source writes durable memory"
    assert blocked["company_kb"] == "handoff source writes Company KB"
    controls = {control["control_id"]: control["status"] for control in packet["controls"]}
    assert controls["provider_calls_not_started"] == "failed"
    assert controls["long_term_memory_write_disabled"] == "failed"
    assert controls["company_kb_write_disabled"] == "failed"
    markdown = render_operator_handoff_packet_markdown(packet)
    assert "Provider calls: started" in markdown
    assert "Durable memory write: enabled" in markdown
    assert "Company KB write: enabled" in markdown


def test_operator_handoff_packet_writes_json_and_markdown(tmp_path: Path) -> None:
    manifest, check = _operator_loop_with_check(tmp_path / "source")
    packet = build_operator_handoff_packet(
        manifest,
        manifest_check=check,
        generated_at="2026-06-02T17:25:00+08:00",
    )

    written = write_operator_handoff_packet(packet, tmp_path / "handoff")

    assert tmp_path / "handoff" / "operator_handoff_packet.json" in written
    assert tmp_path / "handoff" / "operator_handoff_packet.md" in written
    markdown = (tmp_path / "handoff" / "operator_handoff_packet.md").read_text(encoding="utf-8")
    assert "Production Memory Operator Handoff Packet" in markdown
    assert "Status: ready" in markdown
    assert "Manifest check: passed" in markdown
    assert "Provider calls: not started" in markdown
    assert "Company KB write: disabled" in markdown


def test_operator_handoff_packet_cli_writes_ready_packet(tmp_path: Path) -> None:
    source_dir = tmp_path / "operator_loop"
    output_dir = tmp_path / "handoff"
    _operator_loop_with_check(source_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-operator-handoff-packet",
            str(source_dir / "production_memory_operator_loop_run.json"),
            "--manifest-check",
            str(source_dir / "operator_manifest_check" / "operator_manifest_check.json"),
            "--generated-at",
            "2026-06-02T17:25:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory operator handoff: ready" in result.stdout
    assert "Manifest check: passed" in result.stdout
    assert "Next operator action: run_next_ai_task_from_next_task_packet" in result.stdout
    packet = json.loads((output_dir / "operator_handoff_packet.json").read_text(encoding="utf-8"))
    assert packet["kind"] == OPERATOR_HANDOFF_PACKET_KIND
    assert (output_dir / "operator_handoff_packet.md").exists()


def test_operator_handoff_packet_cli_reports_blocked_provider_state(tmp_path: Path) -> None:
    source_dir = tmp_path / "operator_loop"
    output_dir = tmp_path / "handoff"
    manifest, _check = _operator_loop_with_check(source_dir)
    manifest["provider_calls_started"] = True
    (source_dir / "production_memory_operator_loop_run.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-operator-handoff-packet",
            str(source_dir / "production_memory_operator_loop_run.json"),
            "--manifest-check",
            str(source_dir / "operator_manifest_check" / "operator_manifest_check.json"),
            "--generated-at",
            "2026-06-02T17:25:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Production memory operator handoff: blocked" in result.stdout
    assert "Provider calls: true" in result.stdout
    packet = json.loads((output_dir / "operator_handoff_packet.json").read_text(encoding="utf-8"))
    assert packet["handoff_status"] == "blocked"
    assert packet["provider_calls_started"] is True
