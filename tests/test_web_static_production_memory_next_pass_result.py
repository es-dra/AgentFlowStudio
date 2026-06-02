from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import build_production_memory_loop_run, load_production_memory_loop
from agentflow.memory.production_next_context import build_next_context_handoff
from agentflow.memory.production_next_pass_result import (
    NEXT_PASS_RESULT_KIND,
    build_next_pass_result_scaffold,
    write_next_pass_result_scaffold,
)
from agentflow.memory.production_next_task import build_next_task_packet


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _next_pass_result() -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at="2026-06-02T11:05:00+08:00")
    packet = build_next_task_packet(handoff, generated_at="2026-06-02T11:10:00+08:00")
    used_refs = [ref["ref_id"] for ref in packet["allowed_context_refs"][:2]]
    return build_next_pass_result_scaffold(
        packet,
        generated_at="2026-06-02T11:15:00+08:00",
        output_ref="next-pass:artifact:operator-draft-001",
        title="Second pass operator draft",
        summary="Operator-supplied scaffold for the second pass.",
        used_context_refs=used_refs,
    )


def test_web_static_view_renders_production_memory_next_pass_result(tmp_path: Path) -> None:
    result = _next_pass_result()
    write_next_pass_result_scaffold(result, tmp_path)
    result_path = tmp_path / "next_pass_result.json"
    result_ref = json.dumps(str(result_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {result_ref};
const file = {{
  name: "next_pass_result.json",
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
  hasNextPassResult: Boolean(workspace.productionMemoryNextPassResult),
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

    assert payload["artifactType"] == NEXT_PASS_RESULT_KIND
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory next pass result"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasNextPassResult"] is True
    assert payload["projectFormat"] == NEXT_PASS_RESULT_KIND
    assert payload["state"] == "next pass result scaffold ready"
    assert "Next pass result" in payload["laneTitles"]
    assert "Output artifacts" in payload["laneTitles"]
    assert "Used context refs" in payload["laneTitles"]
    assert "Feedback events" in payload["laneTitles"]
    assert any(card.startswith("Output artifacts:review ready:1 scaffolded outputs") for card in payload["bundleCards"])
    assert any(card.startswith("Used context refs:review ready:2 allowed refs used") for card in payload["bundleCards"])
    assert any(card.startswith("Feedback events:missing:0 explicit feedback events") for card in payload["bundleCards"])
    assert "next-pass:artifact:operator-draft-001" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "review_next_pass_result_against_task_packet"
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "feedback not auto created:review ready" in payload["protocolControls"]
    assert NEXT_PASS_RESULT_KIND in payload["inspectorTypes"]
    assert "result_status:scaffolded_for_operator_completion" in payload["inspectorFacts"]
    assert "output_artifacts:1" in payload["inspectorFacts"]
    assert "used_context_refs:2" in payload["inspectorFacts"]
    assert "feedback_events:0" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_next_pass_result_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-next-pass-result.js"),
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
        "document." + "co" + "okie",
        "showsavefilepicker",
        "createwritable",
        "filesystemwritablefilestream",
        "directory",
        "provider execution",
    ]:
        assert forbidden not in combined
