from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import build_production_memory_loop_run
from agentflow.memory.production_session import build_production_memory_session_report


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_view_renders_generic_production_memory_session_report(tmp_path: Path) -> None:
    loop = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    run = build_production_memory_loop_run(loop)
    report = build_production_memory_session_report(run, generated_at="2026-06-02T00:10:00+08:00")
    report_path = tmp_path / "production_memory_session_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    report_ref = json.dumps(str(report_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {report_ref};
const file = {{
  name: "production_memory_session_report.json",
  text: async () => await readFile(path, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  memoryBundleCount: workspace.memoryBundle.length,
  hasSessionReport: Boolean(workspace.productionMemorySessionReport),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleTitles: view.bundle_summary.map((item) => item.title),
  provenanceIds: view.memory_loaded.map((item) => item.id),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
  sourceLabel: view.source_status.label,
}}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["artifactType"] == "agentflow_production_memory_session_report"
    assert payload["artifactClass"] == "known_contract"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasSessionReport"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_session_report"
    assert payload["state"] == "pass ready"
    assert "Session report" in payload["laneTitles"]
    assert "Included refs" in payload["bundleTitles"]
    assert "Blocked refs" in payload["bundleTitles"]
    assert "memory:candidate:approved-style:v1" in payload["provenanceIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "prepare_next_pass"
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_session_report_adds_no_provider_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-session.js"),
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
