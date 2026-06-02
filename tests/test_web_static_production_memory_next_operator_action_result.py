from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_next_operator_action_result import (
    build_next_operator_action_result,
    write_next_operator_action_result_report,
)
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_view_renders_production_memory_next_operator_action_result(tmp_path: Path) -> None:
    result_path = _write_action_result(tmp_path)
    result_ref = json.dumps(str(result_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {result_ref};
const file = {{
  name: "next_operator_action_result.json",
  text: async () => await readFile(path, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  hasActionResult: Boolean(workspace.productionMemoryNextOperatorActionResult),
  projectFormat: view.project.format,
  state: view.state,
  actionIds: view.workflow_actions.map((item) => item.id),
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  nextPassAction: view.next_pass.action,
  nextPassStatus: view.next_pass.status,
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
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

    assert payload["artifactType"] == "agentflow_production_memory_next_operator_action_result"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory next operator action result"
    assert payload["hasActionResult"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_next_operator_action_result"
    assert payload["state"] == "next operator action result recorded"
    assert "inspect_action_result" in payload["actionIds"]
    assert "review_result_refs" in payload["actionIds"]
    assert "inspect_action_result_boundaries" in payload["actionIds"]
    assert "Action result" in payload["laneTitles"]
    assert "Source start event" in payload["laneTitles"]
    assert "Boundaries" in payload["laneTitles"]
    assert any(card.startswith("Action result:review ready:action_completed") for card in payload["bundleCards"])
    assert any(card.startswith("Execution boundary:blocked:not_claimed") for card in payload["bundleCards"])
    assert "next_operator_action_result" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "review_recorded_action_result_refs"
    assert "action result not acceptance:review ready" in payload["protocolControls"]
    assert "action result not execution:review ready" in payload["protocolControls"]
    assert "action result not memory:review ready" in payload["protocolControls"]
    assert "result_status:action_completed" in payload["inspectorFacts"]
    assert "action_decision:completed" in payload["inspectorFacts"]
    assert "result_refs:1" in payload["inspectorFacts"]
    assert "action_result_execution:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_next_operator_action_result_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-next-operator-action-result.js"),
        Path("apps/web/memory-workbench-production-inspector-facts.js"),
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


def _write_action_result(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    operator_dir = tmp_path / "operator_loop"
    write_production_memory_operator_loop_run(
        result,
        operator_dir,
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
        write_next_operator_start_event=True,
        next_operator_start_event_decision="started",
        next_operator_start_event_summary="Next operator received the checked no-provider start packet.",
    )
    start_event = json.loads(
        (operator_dir / "next_operator_start_event" / "next_operator_start_event.json").read_text(encoding="utf-8")
    )
    action_result = build_next_operator_action_result(
        start_event,
        decision="completed",
        summary="Next operator completed the recorded action and produced a local result ref.",
        result_refs=["next_pass_result/next_pass_result.json"],
        operator_role="next_operator",
        recorded_at="2026-06-03T10:30:00+08:00",
        start_event_path="next_operator_start_event/next_operator_start_event.json",
    )
    write_next_operator_action_result_report(action_result, tmp_path / "action_result")
    return tmp_path / "action_result" / "next_operator_action_result.json"
