from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from agentflow.memory.production_operator_start_packet import (
    build_next_operator_start_packet_from_check_path,
    write_next_operator_start_packet_report,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_view_renders_production_memory_next_operator_start_packet(tmp_path: Path) -> None:
    packet_path = _write_next_operator_start_packet(tmp_path)
    packet_ref = json.dumps(str(packet_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {packet_ref};
const file = {{
  name: "next_operator_start_packet.json",
  text: async () => await readFile(path, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasStartPacket: Boolean(workspace.productionMemoryNextOperatorStartPacket),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  inspectorTypes: view.artifact_inspector.map((item) => item.artifact_type),
  inspectorFacts: view.artifact_inspector.flatMap((item) => item.facts.map((fact) => `${{fact.label}}:${{fact.value}}`)),
  sourceLabel: view.source_status.label,
}}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["artifactType"] == "agentflow_production_memory_next_operator_start_packet"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory next operator start packet"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasStartPacket"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_next_operator_start_packet"
    assert payload["state"] == "next operator start packet ready"
    assert "Start packet" in payload["laneTitles"]
    assert "Checked package items" in payload["laneTitles"]
    assert "Next operator" in payload["laneTitles"]
    assert "Boundaries" in payload["laneTitles"]
    assert "Start packet:review ready:ready" in payload["bundleCards"]
    assert "Checked package items:review ready:18 items checked" in payload["bundleCards"]
    assert "Blocked items:review ready:0 start blockers" in payload["bundleCards"]
    assert "next_operator_start_packet" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "review_or_complete_next_pass_result"
    assert "no-provider mode:review ready" in payload["protocolControls"]
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "durable memory write disabled:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "ready for next operator:review ready" in payload["protocolControls"]
    assert "agentflow_production_memory_next_operator_start_packet" in payload["inspectorTypes"]
    assert "start_packet_status:ready" in payload["inspectorFacts"]
    assert "ready_for_next_operator:true" in payload["inspectorFacts"]
    assert "checked_package_items:18" in payload["inspectorFacts"]
    assert "next_operator_action:review_or_complete_next_pass_result" in payload["inspectorFacts"]
    assert "package_check_status:passed" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_next_operator_start_packet_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-inspector-facts.js"),
        Path("apps/web/memory-workbench-production-next-operator-start.js"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in files if path.exists())

    assert "lou" + "lan" not in combined
    for forbidden in [
        "fet" + "ch(",
        "xmlhttp" + "request",
        "web" + "socket",
        "eventsource",
        "navigator.sendbeacon",
        "local" + "storage",
        "indexed" + "db",
        "document." + "coo" + "kie",
        "show" + "savefilepicker",
        "create" + "writable",
        "filesystemwritablefilestream",
        "dire" + "ctory",
        "provider " + "execution",
    ]:
        assert forbidden not in combined


def _write_next_operator_start_packet(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T09:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    output_root = tmp_path / "operator_loop"
    write_production_memory_operator_loop_run(
        result,
        output_root,
        write_run_package=True,
        write_run_package_check=True,
    )
    packet = build_next_operator_start_packet_from_check_path(
        output_root / "operator_run_package_check" / "operator_run_package_check.json",
        generated_at="2026-06-03T09:30:00+08:00",
    )
    write_next_operator_start_packet_report(packet, tmp_path / "start_packet")
    return tmp_path / "start_packet" / "next_operator_start_packet.json"
