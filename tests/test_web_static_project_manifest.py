from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_web_static_renders_agentflow_project_manifest_workbench() -> None:
    manifest_ref = json.dumps(str(Path("examples/agentflow/project_manifest.example.json")))

    payload = _build_web_view_payload("project_manifest.example.json", manifest_ref)

    assert payload["artifactType"] == "agentflow_project_manifest"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "AgentFlow project manifest"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasProjectManifest"] is True
    assert payload["projectFormat"] == "agentflow_project_manifest"
    assert payload["state"] == "project manifest ready"
    assert "Project runs" in payload["laneTitles"]
    assert "Packages" in payload["laneTitles"]
    assert "Feedback refs" in payload["laneTitles"]
    assert "Profile versions" in payload["laneTitles"]
    assert "Runs" in payload["bundleTitles"]
    assert "Packages" in payload["bundleTitles"]
    assert "Feedback refs" in payload["bundleTitles"]
    assert "Profile versions" in payload["bundleTitles"]
    assert "run:asset-loop-round-1" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "open_referenced_package_or_next_round"
    assert "no database:review ready" in payload["protocolControls"]
    assert "no account:review ready" in payload["protocolControls"]
    assert "no automatic sync:review ready" in payload["protocolControls"]
    assert "no private asset bytes:review ready" in payload["protocolControls"]
    assert "agentflow_project_manifest" in payload["inspectorTypes"]


def _build_web_view_payload(file_name: str, path_ref: str) -> dict:
    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: {json.dumps(file_name)},
  text: async () => await readFile({path_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasProjectManifest: Boolean(workspace.agentflowProjectManifest),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleTitles: view.bundle_summary.map((item) => item.title),
  memoryIds: view.memory_loaded.map((item) => item.id),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  inspectorTypes: view.artifact_inspector.map((item) => item.artifact_type),
}}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)
