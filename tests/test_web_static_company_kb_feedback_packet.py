from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_web_static_view_renders_company_kb_feedback_candidate_packet() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView } from "./apps/web/memory-workbench-controller.js";
import { readFile } from "node:fs/promises";

const path = "examples/agentflow/company_kb_feedback_candidate_packet.example.json";
const file = {
  name: "company_kb_feedback_candidate_packet.example.json",
  text: async () => await readFile(path, "utf8"),
};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasCompanyKbPacket: Boolean(workspace.companyKbFeedbackCandidatePacket),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleTitles: view.bundle_summary.map((item) => item.title),
  candidateIds: view.memory_loaded.map((item) => item.id),
  memoryStatuses: view.memory_loaded.map((item) => item.status),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
  protocolControls: view.protocol_summary.controls.map((item) => `${item.label}:${item.status}`),
  inspectorTypes: view.artifact_inspector.map((item) => item.artifact_type),
  inspectorFacts: view.artifact_inspector.flatMap((item) => item.facts.map((fact) => `${fact.label}:${fact.value}`)),
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

    assert payload["artifactType"] == "agentflow_company_kb_feedback_candidate_packet"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Company KB feedback candidate packet"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasCompanyKbPacket"] is True
    assert payload["projectFormat"] == "agentflow_company_kb_feedback_candidate_packet"
    assert payload["state"] == "candidate review"
    assert "Candidate packet" in payload["laneTitles"]
    assert "Candidate items" in payload["laneTitles"]
    assert "Explicit non-promotions" in payload["laneTitles"]
    assert "Candidate items" in payload["bundleTitles"]
    assert "Human review" in payload["bundleTitles"]
    assert "Company KB write" in payload["bundleTitles"]
    assert "company-kb:candidate:context-bundle-audit:v1" in payload["candidateIds"]
    assert set(payload["memoryStatuses"]) == {"candidate"}
    assert payload["nextPassStatus"] == "blocked"
    assert payload["nextPassAction"] == "human_review_required_before_company_memory_promotion"
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "Durable memory write disabled:review ready" in payload["protocolControls"]
    assert "Human review required:blocked" in payload["protocolControls"]
    assert "agentflow_company_kb_feedback_candidate_packet" in payload["inspectorTypes"]
    assert "promotion_status:candidate_only" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "requires_human_review:true" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_company_kb_feedback_slice_adds_no_project_specific_or_provider_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-company-kb-feedback.js"),
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
