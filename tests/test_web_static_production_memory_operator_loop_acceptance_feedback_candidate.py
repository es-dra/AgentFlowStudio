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


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_operator_loop_renders_embedded_acceptance_feedback_candidate_promotion(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T04:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        seed,
        tmp_path / "operator_loop_seed",
        write_run_package=True,
        write_run_package_check=True,
    )
    check_path = tmp_path / "operator_loop_seed" / "operator_run_package_check" / "operator_run_package_check.json"
    package_check = json.loads(check_path.read_text(encoding="utf-8"))
    event = build_production_memory_acceptance_feedback_event(
        package_check,
        decision="accepted",
        summary="Human operator accepted the package for the next production-memory iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T04:05:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T04:10:00+08:00")
    decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable acceptance feedback candidate selected for reviewed context assembly.",
        reviewer_role="operator",
        decided_at="2026-06-03T04:15:00+08:00",
    )
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T04:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=decision,
    )
    write_production_memory_operator_loop_run(result, tmp_path)
    manifest_ref = json.dumps(str(tmp_path / "production_memory_operator_loop_run.json"))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "production_memory_operator_loop_run.json",
  text: async () => await readFile({manifest_ref}, "utf8"),
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
    assert "Acceptance feedback candidate promotion" in payload["laneTitles"]
    assert any(
        card.startswith("Acceptance feedback candidate promotion:promoted:included_in_context")
        for card in payload["bundleCards"]
    )
    assert "acceptance_feedback_candidate_promotion_decision" in payload["memoryIds"]
    assert "acceptance_feedback_candidate_promotion_overlay" in payload["memoryIds"]
    assert (
        "acceptance_feedback_candidate_promotion_decision/acceptance_feedback_candidate_promotion_decision.json"
        in payload["assetPaths"]
    )
    assert (
        "acceptance_feedback_candidate_reviewed_feedback/acceptance_feedback_candidate_promotion_overlay.json"
        in payload["assetPaths"]
    )
    assert "acceptance_feedback_candidate_reviewed_feedback/context_bundle.json" in payload["assetPaths"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "inspect_acceptance_feedback_candidate_overlay_before_next_pass"
    assert "acceptance feedback candidate promotion no-provider mode:review ready" in payload["protocolControls"]
    assert "acceptance feedback candidate promotion memory write disabled:review ready" in payload["protocolControls"]
    assert "acceptance_feedback_candidate_promotion_decision:promoted" in payload["inspectorFacts"]
    assert "acceptance_feedback_candidate_promotion_effect:included_in_context" in payload["inspectorFacts"]


def test_web_static_operator_loop_renders_action_result_acceptance_overlay_source(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
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
        rationale="Traceable action-result acceptance feedback selected for reviewed context assembly.",
        reviewer_role="operator",
        decided_at="2026-06-03T12:15:00+08:00",
    )
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T12:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=decision,
    )
    write_production_memory_operator_loop_run(result, tmp_path / "operator_loop")
    manifest_ref = json.dumps(str(tmp_path / "operator_loop" / "production_memory_operator_loop_run.json"))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "production_memory_operator_loop_run.json",
  text: async () => await readFile({manifest_ref}, "utf8"),
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
    assert any(card.startswith("Source action result:review ready:action_completed") for card in payload["bundleCards"])
    assert "next_operator_action_result/next_operator_action_result.json" in payload["memoryRefs"]
    assert "acceptance_feedback_source_artifact_type:agentflow_production_memory_next_operator_action_result" in payload["inspectorFacts"]
    assert "acceptance_feedback_source_artifact_status:action_completed" in payload["inspectorFacts"]
    assert "Source action result" in payload["timelineLabels"]


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
    return json.loads(
        (
            tmp_path
            / "operator_loop_with_action_result"
            / "next_operator_action_result"
            / "next_operator_action_result.json"
        ).read_text(encoding="utf-8")
    )
