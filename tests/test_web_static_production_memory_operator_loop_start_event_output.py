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


def test_web_static_operator_loop_renders_post_check_next_operator_start_event(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path,
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
        write_next_operator_start_event=True,
        next_operator_start_event_decision="started",
        next_operator_start_event_summary="Next operator received the checked no-provider start packet.",
    )
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
  actionIds: view.workflow_actions.map((item) => item.id),
  actionStatuses: view.workflow_actions.map((item) => `${{item.id}}:${{item.status}}`),
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  assetPaths: view.assets.map((item) => item.id),
  assetStatuses: view.assets.map((item) => `${{item.id}}:${{item.status}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  nextPassAction: view.next_pass.action,
  nextPassStatus: view.next_pass.status,
  inspectorFacts: view.artifact_inspector.flatMap((item) => item.facts.map((fact) => `${{fact.label}}:${{fact.value}}`)),
  timelineLabels: view.timeline.map((item) => item.label),
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
    assert "inspect_next_operator_start_event" in payload["actionIds"]
    assert "inspect_next_operator_start_event:review ready" in payload["actionStatuses"]
    assert "Next operator start event" in payload["laneTitles"]
    assert any(card.startswith("Next operator start event:operator_started:started") for card in payload["bundleCards"])
    assert "next_operator_start_event/next_operator_start_event.json" in payload["assetPaths"]
    assert "next_operator_start_event/next_operator_start_event.md" in payload["assetPaths"]
    assert "next_operator_start_event/next_operator_start_event.json:post-check" in payload["assetStatuses"]
    assert "next_operator_start_event" in payload["memoryIds"]
    assert "next operator start event not acceptance:review ready" in payload["protocolControls"]
    assert "next operator start event not execution:review ready" in payload["protocolControls"]
    assert "next operator start event not memory:review ready" in payload["protocolControls"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "continue_recorded_next_operator_action"
    assert "next_operator_start_event_status:operator_started" in payload["inspectorFacts"]
    assert "next_operator_start_decision:started" in payload["inspectorFacts"]
    assert "next_operator_start_event_acceptance:false" in payload["inspectorFacts"]
    assert "next_operator_start_event_execution:false" in payload["inspectorFacts"]
    assert "Next operator start event" in payload["timelineLabels"]
