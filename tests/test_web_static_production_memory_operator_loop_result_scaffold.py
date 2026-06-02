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


def test_web_static_operator_loop_renders_embedded_next_pass_result_scaffold(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T12:30:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(result, tmp_path)
    manifest_path = tmp_path / "production_memory_operator_loop_run.json"
    manifest_ref = json.dumps(str(manifest_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {manifest_ref};
const file = {{
  name: "production_memory_operator_loop_run.json",
  text: async () => await readFile(path, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  assetPaths: view.assets.map((item) => item.id),
  nextPassAction: view.next_pass.action,
  nextPassStatus: view.next_pass.status,
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  inspectorFacts: view.artifact_inspector.flatMap((item) => item.facts.map((fact) => `${{fact.label}}:${{fact.value}}`)),
}}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["state"] == "operator loop ready"
    assert "Next pass result" in payload["laneTitles"]
    assert any(
        card.startswith("Next pass result:scaffolded_for_operator_completion:1 scaffolded outputs")
        for card in payload["bundleCards"]
    )
    assert "next_pass_result" in payload["memoryIds"]
    assert "next_pass_result/next_pass_result.json" in payload["assetPaths"]
    assert "next_pass_result/next_pass_result.md" in payload["assetPaths"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "inspect_next_pass_result_scaffold_before_review"
    assert "next-pass result no-provider mode:review ready" in payload["protocolControls"]
    assert "next-pass result memory write disabled:review ready" in payload["protocolControls"]
    assert "next_pass_result_status:scaffolded_for_operator_completion" in payload["inspectorFacts"]
    assert "next_pass_result_output_artifacts:1" in payload["inspectorFacts"]


def test_web_static_operator_loop_result_scaffold_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/memory-workbench-production-operator-loop.js"),
        Path("apps/web/memory-workbench-production-inspector-facts.js"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in files)

    assert "lou" + "lan" not in combined
    for forbidden in [
        "fetch(",
        "xmlhttprequest",
        "websocket",
        "eventsource",
        "navigator.sendbeacon",
        "localstorage",
        "indexeddb",
        "document." + "co" + "okie",
        "showsavefilepicker",
        "createwritable",
        "filesystemwritablefilestream",
        "directory",
        "provider execution",
    ]:
        assert forbidden not in combined
