from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import build_production_memory_loop_run, load_production_memory_loop
from agentflow.memory.production_next_context import build_next_context_handoff
from agentflow.memory.production_next_task import build_next_task_packet, write_next_task_packet


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_view_renders_production_memory_next_task_packet(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at="2026-06-02T03:10:00+08:00")
    packet = build_next_task_packet(handoff, generated_at="2026-06-02T03:12:00+08:00")
    write_next_task_packet(packet, tmp_path)
    packet_path = tmp_path / "next_task_packet.json"
    packet_ref = json.dumps(str(packet_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {packet_ref};
const file = {{
  name: "next_task_packet.json",
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
  hasNextTaskPacket: Boolean(workspace.productionMemoryNextTaskPacket),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleTitles: view.bundle_summary.map((item) => item.title),
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

    assert payload["artifactType"] == "agentflow_production_memory_next_task_packet"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory next task packet"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasNextTaskPacket"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_next_task_packet"
    assert payload["state"] == "next task ready"
    assert "Next task packet" in payload["laneTitles"]
    assert "Allowed context refs" in payload["laneTitles"]
    assert "Blocked refs" in payload["laneTitles"]
    assert "Allowed context refs" in payload["bundleTitles"]
    assert "Blocked refs" in payload["bundleTitles"]
    assert "Non-claims" in payload["bundleTitles"]
    assert "artifact:brief:v1" in payload["memoryIds"]
    assert "memory:candidate:approved-style:v1" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "use_next_task_packet_for_next_ai_task"
    assert "no-provider mode:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "durable memory write disabled:review ready" in payload["protocolControls"]
    assert "blocked refs excluded:review ready" in payload["protocolControls"]
    assert "agentflow_production_memory_next_task_packet" in payload["inspectorTypes"]
    assert "packet_status:ready" in payload["inspectorFacts"]
    assert "allowed_context_refs:3" in payload["inspectorFacts"]
    assert "blocked_refs:3" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_next_task_packet_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-next-task.js"),
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
