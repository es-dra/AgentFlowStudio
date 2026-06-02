from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_acceptance_feedback import write_production_memory_acceptance_feedback_event
from agentflow.memory.production_action_result_acceptance_feedback import (
    build_production_memory_action_result_acceptance_feedback_event,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_acceptance_feedback_renders_action_result_source(tmp_path: Path) -> None:
    feedback_path = _action_result_acceptance_feedback_path(tmp_path)
    feedback_ref = json.dumps(str(feedback_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "acceptance_feedback_event.json",
  text: async () => await readFile({feedback_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryRefs: view.memory_loaded.flatMap((item) => item.source_evidence_refs),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
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

    assert payload["state"] == "acceptance feedback recorded"
    assert "Source action result" in payload["laneTitles"]
    assert any(card.startswith("Source action result:review ready:action_completed") for card in payload["bundleCards"])
    assert "next_operator_action_result/next_operator_action_result.json" in payload["memoryRefs"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "draft_acceptance_feedback_candidate_from_action_result"
    assert "feedback_scope:next_operator_action_result" in payload["inspectorFacts"]
    assert "source_artifact_status:action_completed" in payload["inspectorFacts"]
    assert "source_action_result_status:action_completed" in payload["inspectorFacts"]
    assert "source_action_decision:completed" in payload["inspectorFacts"]
    assert "source_result_refs:1" in payload["inspectorFacts"]
    assert "Source action result" in payload["timelineLabels"]


def _action_result_acceptance_feedback_path(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T12:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path / "operator_loop",
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
    action_result = json.loads(
        (
            tmp_path
            / "operator_loop"
            / "next_operator_action_result"
            / "next_operator_action_result.json"
        ).read_text(encoding="utf-8")
    )
    event = build_production_memory_action_result_acceptance_feedback_event(
        action_result,
        decision="accepted",
        summary="Human operator accepted the completed action result for the next local iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T12:05:00+08:00",
        action_result_path="next_operator_action_result/next_operator_action_result.json",
    )
    write_production_memory_acceptance_feedback_event(event, tmp_path / "action_result_acceptance_feedback")
    return tmp_path / "action_result_acceptance_feedback" / "acceptance_feedback_event.json"
