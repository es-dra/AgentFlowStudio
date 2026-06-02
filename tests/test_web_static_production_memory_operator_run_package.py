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


def test_web_static_view_renders_production_memory_operator_run_package(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T19:10:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(result, tmp_path, write_run_package=True)
    package_path = tmp_path / "operator_run_package" / "operator_run_package.json"
    package_ref = json.dumps(str(package_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "operator_run_package.json",
  text: async () => await readFile({package_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasRunPackage: Boolean(workspace.productionMemoryOperatorRunPackage),
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

    assert payload["artifactType"] == "agentflow_production_memory_operator_run_package"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory operator run package"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasRunPackage"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_operator_run_package"
    assert payload["state"] == "operator run package ready"
    assert "Operator run package" in payload["laneTitles"]
    assert "Package items" in payload["laneTitles"]
    assert "Blocked items" in payload["laneTitles"]
    assert any(card.startswith("Package status:review ready:ready") for card in payload["bundleCards"])
    assert any(card.startswith("Manifest check:review ready:passed") for card in payload["bundleCards"])
    assert any(card.startswith("Handoff packet:review ready:ready") for card in payload["bundleCards"])
    assert any(card.startswith("Blocked items:review ready:0 blockers") for card in payload["bundleCards"])
    assert "operator_run_package" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "review_or_complete_next_pass_result"
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "durable memory write disabled:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "human acceptance:blocked:not_reviewed" in payload["protocolBoundaries"]
    assert "business validation:blocked:not_validated" in payload["protocolBoundaries"]
    assert "agentflow_production_memory_operator_run_package" in payload["inspectorTypes"]
    assert "package_status:ready" in payload["inspectorFacts"]
    assert "manifest_check_status:passed" in payload["inspectorFacts"]
    assert "handoff_status:ready" in payload["inspectorFacts"]
    assert "package_items:18" in payload["inspectorFacts"]
    assert "blocked_items:0" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_operator_run_package_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-operator-run-package.js"),
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
        "document." + "coo" + "kie",
        "showsavefilepicker",
        "createwritable",
        "filesystemwritablefilestream",
        "directory",
        "provider execution",
    ]:
        assert forbidden not in combined
