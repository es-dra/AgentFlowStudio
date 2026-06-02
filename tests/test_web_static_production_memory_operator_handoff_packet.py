from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_handoff import (
    build_operator_handoff_packet,
    write_operator_handoff_packet,
)
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_view_renders_production_memory_operator_handoff_packet(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T17:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    write_production_memory_operator_loop_run(result, tmp_path / "source", write_manifest_check=True)
    manifest = json.loads((tmp_path / "source" / "production_memory_operator_loop_run.json").read_text(encoding="utf-8"))
    check = json.loads((tmp_path / "source" / "operator_manifest_check" / "operator_manifest_check.json").read_text(encoding="utf-8"))
    packet = build_operator_handoff_packet(
        manifest,
        manifest_check=check,
        generated_at="2026-06-02T17:25:00+08:00",
    )
    write_operator_handoff_packet(packet, tmp_path / "handoff")
    packet_path = tmp_path / "handoff" / "operator_handoff_packet.json"
    packet_ref = json.dumps(str(packet_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "operator_handoff_packet.json",
  text: async () => await readFile({packet_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasOperatorHandoff: Boolean(workspace.productionMemoryOperatorHandoffPacket),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  protocolBoundaries: view.protocol_summary.boundaries.map((item) => `${{item.label}}:${{item.status}}:${{item.detail}}`),
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

    assert payload["artifactType"] == "agentflow_production_memory_operator_handoff_packet"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory operator handoff packet"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasOperatorHandoff"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_operator_handoff_packet"
    assert payload["state"] == "operator handoff ready"
    assert "Operator handoff" in payload["laneTitles"]
    assert "Artifact refs" in payload["laneTitles"]
    assert "Blocked items" in payload["laneTitles"]
    assert any(card.startswith("Handoff status:review ready:ready") for card in payload["bundleCards"])
    assert any(card.startswith("Artifact refs:review ready:") for card in payload["bundleCards"])
    assert any(card.startswith("Blocked items:review ready:0 blockers") for card in payload["bundleCards"])
    assert "operator_handoff_packet" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "run_next_ai_task_from_next_task_packet"
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "durable memory write disabled:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "human acceptance:blocked:not_reviewed" in payload["protocolBoundaries"]
    assert "business validation:blocked:not_validated" in payload["protocolBoundaries"]
    assert "agentflow_production_memory_operator_handoff_packet" in payload["inspectorTypes"]
    assert "handoff_status:ready" in payload["inspectorFacts"]
    assert "manifest_check_status:passed" in payload["inspectorFacts"]
    assert "blocked_items:0" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_operator_handoff_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-operator-handoff.js"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in files if path.exists())

    assert "lou" + "lan" not in combined
    for forbidden in [
        "fetch(",
        "xmlhttprequest",
        "websocket",
        "eventsource",
        "navigator.sendbeacon",
        "localstorage",
        "indexeddb",
        "document.cookie",
        "showsavefilepicker",
        "createwritable",
        "filesystemwritablefilestream",
        "directory",
        "provider execution",
    ]:
        assert forbidden not in combined
