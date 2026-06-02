from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_view_renders_production_memory_operator_manifest_check(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T16:30:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(result, tmp_path, write_manifest_check=True)
    check_path = tmp_path / "operator_manifest_check" / "operator_manifest_check.json"
    check_ref = json.dumps(str(check_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "operator_manifest_check.json",
  text: async () => await readFile({check_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasManifestCheck: Boolean(workspace.productionMemoryOperatorManifestCheck),
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

    assert payload["artifactType"] == "agentflow_production_memory_operator_manifest_check"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory operator manifest check"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasManifestCheck"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_operator_manifest_check"
    assert payload["state"] == "operator manifest check passed"
    assert "Manifest check" in payload["laneTitles"]
    assert "Checked refs" in payload["laneTitles"]
    assert "Failed nodes" in payload["laneTitles"]
    assert any(card.startswith("Checked refs:review ready:15 refs checked") for card in payload["bundleCards"])
    assert any(card.startswith("Missing refs:review ready:0 refs missing") for card in payload["bundleCards"])
    assert any(card.startswith("Failed controls:review ready:0 controls failed") for card in payload["bundleCards"])
    assert "operator_manifest_check" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "inspect_operator_manifest_check_before_next_pass"
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "durable memory write disabled:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "agentflow_production_memory_operator_manifest_check" in payload["inspectorTypes"]
    assert "check_status:passed" in payload["inspectorFacts"]
    assert "checked_refs:15" in payload["inspectorFacts"]
    assert "missing_refs:0" in payload["inspectorFacts"]
    assert "mismatched_refs:0" in payload["inspectorFacts"]
    assert "failed_nodes:0" in payload["inspectorFacts"]
    assert "failed_controls:0" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_operator_manifest_check_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-operator-manifest-check.js"),
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
