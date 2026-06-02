from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_feedback import build_production_memory_operator_feedback_event
from agentflow.memory.production_operator_feedback_candidate import build_operator_feedback_candidate_packet
from agentflow.memory.production_operator_loop import build_production_memory_operator_loop_run
from agentflow_studio.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _operator_feedback_candidate_packet() -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T08:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    event = build_production_memory_operator_feedback_event(
        result["manifest"],
        target_node_id="company_kb_feedback_candidate_packet",
        decision="accepted",
        summary="Operator reviewed the candidate packet shape for the next loop.",
        reviewer_role="operator",
        reviewed_at="2026-06-02T08:10:00+08:00",
    )
    return build_operator_feedback_candidate_packet(event, generated_at="2026-06-02T08:20:00+08:00")


def test_web_static_view_renders_operator_feedback_candidate_packet(tmp_path: Path) -> None:
    packet_path = write_json(tmp_path / "operator_feedback_candidate_packet.json", _operator_feedback_candidate_packet())
    packet_ref = json.dumps(str(packet_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "operator_feedback_candidate_packet.json",
  text: async () => await readFile({packet_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasOperatorFeedbackCandidate: Boolean(workspace.productionMemoryOperatorFeedbackCandidatePacket),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  memoryStatuses: view.memory_loaded.map((item) => item.status),
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

    assert payload["artifactType"] == "agentflow_production_memory_operator_feedback_candidate_packet"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory operator feedback candidate packet"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasOperatorFeedbackCandidate"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_operator_feedback_candidate_packet"
    assert payload["state"] == "candidate review"
    assert "Feedback candidate packet" in payload["laneTitles"]
    assert "Memory candidate" in payload["laneTitles"]
    assert "Promotion template" in payload["laneTitles"]
    assert any(card.startswith("Candidate packet:review ready:candidate_only") for card in payload["bundleCards"])
    assert any(card.startswith("Promotion decision:blocked:pending") for card in payload["bundleCards"])
    assert payload["memoryIds"][0].startswith("memory-candidate-operator-feedback")
    assert set(payload["memoryStatuses"]) == {"candidate"}
    assert payload["nextPassStatus"] == "blocked"
    assert payload["nextPassAction"] == "requires_explicit_promotion_decision_before_next_context"
    assert "candidate only:review ready" in payload["protocolControls"]
    assert "pending promotion template:blocked" in payload["protocolControls"]
    assert "feedback is not memory:review ready" in payload["protocolControls"]
    assert "candidate not promoted memory:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "human acceptance not claimed:blocked" in payload["protocolControls"]
    assert "agentflow_production_memory_operator_feedback_candidate_packet" in payload["inspectorTypes"]
    assert "candidate_generation_status:candidate_only" in payload["inspectorFacts"]
    assert "memory_candidate_status:candidate" in payload["inspectorFacts"]
    assert "promotion_decision:pending" in payload["inspectorFacts"]
    assert "candidate_is_promoted_memory:false" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_operator_feedback_candidate_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-operator-feedback-candidate.js"),
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
        "provider execution",
    ]:
        assert forbidden not in combined
