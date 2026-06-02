from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import build_acceptance_feedback_candidate_packet
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    build_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_action_result_acceptance_feedback import (
    build_production_memory_action_result_acceptance_feedback_event,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from narratocut.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _promotion_decision_path(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T02:20:00+08:00",
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
        reviewed_at="2026-06-03T02:25:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T02:30:00+08:00")
    decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable acceptance feedback selected for the next context overlay.",
        reviewer_role="operator",
        decided_at="2026-06-03T02:35:00+08:00",
    )
    return write_json(tmp_path / "acceptance_feedback_candidate_promotion_decision.json", decision)


def test_web_static_view_renders_acceptance_feedback_candidate_promotion_decision(tmp_path: Path) -> None:
    decision_path = _promotion_decision_path(tmp_path)
    decision_ref = json.dumps(str(decision_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "acceptance_feedback_candidate_promotion_decision.json",
  text: async () => await readFile({decision_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasDecision: Boolean(workspace.productionMemoryAcceptanceFeedbackCandidatePromotionDecision),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  protocolBoundaries: view.protocol_summary.boundaries.map((item) => `${{item.label}}:${{item.status}}:${{item.detail}}`),
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

    assert payload["artifactType"] == "agentflow_production_memory_acceptance_feedback_candidate_promotion_decision"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory acceptance feedback candidate promotion decision"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasDecision"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_acceptance_feedback_candidate_promotion_decision"
    assert payload["state"] == "acceptance candidate promotion decided"
    assert "Acceptance candidate promotion" in payload["laneTitles"]
    assert "Decision effect" in payload["laneTitles"]
    assert "Source acceptance" in payload["laneTitles"]
    assert any(card.startswith("Explicit decision:review ready:promoted") for card in payload["bundleCards"])
    assert any(card.startswith("Decision effect:review ready:eligible_for_next_context_overlay") for card in payload["bundleCards"])
    assert any(card.startswith("Candidate reuse:review ready:allowed") for card in payload["bundleCards"])
    assert any(memory_id.startswith("memory-candidate-acceptance-feedback") for memory_id in payload["memoryIds"])
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "build_next_context_overlay_from_acceptance_feedback_decision"
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "long term memory write disabled:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "business validation not claimed:blocked" in payload["protocolControls"]
    assert "decision is not business validation:blocked:non-claim boundary" in payload["protocolBoundaries"]
    assert "agentflow_production_memory_acceptance_feedback_candidate_promotion_decision" in payload["inspectorTypes"]
    assert "decision:promoted" in payload["inspectorFacts"]
    assert "decision_effect:eligible_for_next_context_overlay" in payload["inspectorFacts"]
    assert "source_acceptance_decision:accepted" in payload["inspectorFacts"]
    assert "candidate_reuse_allowed:true" in payload["inspectorFacts"]
    assert "candidate_is_durable_memory:false" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_promotion_view_renders_action_result_source(tmp_path: Path) -> None:
    decision_path = _action_result_promotion_decision_path(tmp_path)
    decision_ref = json.dumps(str(decision_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "acceptance_feedback_candidate_promotion_decision.json",
  text: async () => await readFile({decision_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryRefs: view.memory_loaded.flatMap((item) => item.source_evidence_refs),
  inspectorFacts: view.artifact_inspector.flatMap((item) => item.facts.map((fact) => `${{fact.label}}:${{fact.value}}`)),
  timelineLabels: view.timeline.map((item) => item.label),
  nextPassAction: view.next_pass.action,
}}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert "Source action result" in payload["laneTitles"]
    assert any(card.startswith("Source artifact:review ready:agentflow_production_memory_next_operator_action_result") for card in payload["bundleCards"])
    assert "next_operator_action_result/next_operator_action_result.json" in payload["memoryRefs"]
    assert "source_artifact_type:agentflow_production_memory_next_operator_action_result" in payload["inspectorFacts"]
    assert "source_artifact_status:action_completed" in payload["inspectorFacts"]
    assert "Source action result" in payload["timelineLabels"]
    assert payload["nextPassAction"] == "build_next_context_overlay_from_acceptance_feedback_decision"


def test_web_static_acceptance_feedback_candidate_promotion_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-acceptance-feedback-candidate-promotion.js"),
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


def _action_result_promotion_decision_path(tmp_path: Path) -> Path:
    action_result = _next_operator_action_result(tmp_path)
    event = build_production_memory_action_result_acceptance_feedback_event(
        action_result,
        decision="accepted",
        summary="Human operator accepted the completed action result for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T12:05:00+08:00",
        action_result_path="next_operator_action_result/next_operator_action_result.json",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T12:10:00+08:00")
    decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable action-result acceptance feedback selected for the next context overlay.",
        reviewer_role="operator",
        decided_at="2026-06-03T12:15:00+08:00",
    )
    return write_json(tmp_path / "action_result_acceptance_feedback_candidate_promotion_decision.json", decision)


def _next_operator_action_result(tmp_path: Path) -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T12:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path / "operator_loop_with_action_result",
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
        write_next_operator_start_event=True,
        next_operator_start_event_decision="started",
        next_operator_start_event_summary="Next operator started from the checked no-provider package.",
        write_next_operator_action_result=True,
        next_operator_action_result_decision="completed",
        next_operator_action_result_summary="Next operator completed the recorded no-provider action.",
        next_operator_action_result_refs=["next_pass_result/next_pass_result.json"],
    )
    action_result_path = (
        tmp_path
        / "operator_loop_with_action_result"
        / "next_operator_action_result"
        / "next_operator_action_result.json"
    )
    return json.loads(action_result_path.read_text(encoding="utf-8"))
