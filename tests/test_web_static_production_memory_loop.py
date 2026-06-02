from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_web_static_view_renders_generic_production_memory_loop() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView } from "./apps/web/memory-workbench-controller.js";
import { readFile } from "node:fs/promises";

const path = "examples/agentflow/production_memory_loop.example.json";
const file = {
  name: "production_memory_loop.example.json",
  text: async () => await readFile(path, "utf8"),
};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  memoryBundleCount: workspace.memoryBundle.length,
  hasProductionLoop: Boolean(workspace.productionMemoryLoop),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleTitles: view.bundle_summary.map((item) => item.title),
  provenanceIds: view.memory_loaded.map((item) => item.id),
  nextPassStatus: view.next_pass.status,
  sourceLabel: view.source_status.label,
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["artifactType"] == "agentflow_production_memory_loop"
    assert payload["artifactClass"] == "known_contract"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasProductionLoop"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_loop"
    assert payload["state"] == "pass ready"
    assert "Artifact ledger" in payload["laneTitles"]
    assert "Memory candidates" in payload["laneTitles"]
    assert "Included refs" in payload["bundleTitles"]
    assert "Blocked refs" in payload["bundleTitles"]
    assert "memory:candidate:approved-style:v1" in payload["provenanceIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_slice_adds_no_project_specific_inspector_or_provider_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-production-loop.js"),
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
    ]:
        assert forbidden not in combined
