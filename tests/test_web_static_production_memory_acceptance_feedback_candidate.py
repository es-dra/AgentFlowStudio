from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import (
    build_acceptance_feedback_candidate_packet,
    write_acceptance_feedback_candidate_packet,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _candidate_packet_path(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T01:30:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path / "operator_loop",
        write_run_package=True,
        write_run_package_check=True,
    )
    check_path = tmp_path / "operator_loop" / "operator_run_package_check" / "operator_run_package_check.json"
    check = json.loads(check_path.read_text(encoding="utf-8"))
    event = build_production_memory_acceptance_feedback_event(
        check,
        decision="accepted",
        summary="Human operator accepted the package for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T01:35:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T01:40:00+08:00")
    write_acceptance_feedback_candidate_packet(packet, tmp_path / "acceptance_feedback_candidate")
    return tmp_path / "acceptance_feedback_candidate" / "acceptance_feedback_candidate_packet.json"


def test_web_static_view_renders_production_memory_acceptance_feedback_candidate(tmp_path: Path) -> None:
    packet_path = _candidate_packet_path(tmp_path)
    packet_ref = json.dumps(str(packet_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "acceptance_feedback_candidate_packet.json",
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
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  protocolBoundaries: view.protocol_summary.boundaries.map((item) => `${{item.label}}:${{item.status}}:${{item.detail}}`),
  inspectorTypes: view.artifact_inspector.map((item) => item.artifact_type),
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

    assert payload["artifactType"] == "agentflow_production_memory_acceptance_feedback_candidate_packet"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory acceptance feedback candidate packet"
    assert payload["memoryBundleCount"] == 1
    assert payload["projectFormat"] == "agentflow_production_memory_acceptance_feedback_candidate_packet"
    assert payload["state"] == "acceptance candidate review"
    assert "Acceptance candidate packet" in payload["laneTitles"]
    assert "Memory candidate" in payload["laneTitles"]
    assert "Promotion template" in payload["laneTitles"]
    assert any(card.startswith("Candidate packet:review ready:candidate_only") for card in payload["bundleCards"])
    assert any(card.startswith("Source acceptance:review ready:accepted") for card in payload["bundleCards"])
    assert any(card.startswith("Promotion decision:blocked:pending") for card in payload["bundleCards"])
    assert payload["nextPassStatus"] == "blocked"
    assert payload["nextPassAction"] == "requires_explicit_promotion_decision_before_next_context"
    assert "candidate only:review ready" in payload["protocolControls"]
    assert "pending promotion template:blocked" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "not promoted memory:blocked:non-claim boundary" in payload["protocolBoundaries"]
    assert "agentflow_production_memory_acceptance_feedback_candidate_packet" in payload["inspectorTypes"]
    assert "candidate_generation_status:candidate_only" in payload["inspectorFacts"]
    assert "source_acceptance_decision:accepted" in payload["inspectorFacts"]
    assert "promotion_decision:pending" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]


def test_web_static_acceptance_feedback_candidate_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-acceptance-feedback-candidate.js"),
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
        "provider execution",
    ]:
        assert forbidden not in combined
