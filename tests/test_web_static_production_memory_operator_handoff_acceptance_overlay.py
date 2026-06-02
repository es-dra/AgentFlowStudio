from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_acceptance_feedback import build_production_memory_acceptance_feedback_event
from agentflow.memory.production_acceptance_feedback_candidate import build_acceptance_feedback_candidate_packet
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    build_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_handoff_view_surfaces_acceptance_feedback_candidate_promotion(tmp_path: Path) -> None:
    output_root = _operator_loop_with_acceptance_feedback_overlay(tmp_path)
    payload = _web_view_payload(output_root / "operator_handoff" / "operator_handoff_packet.json")

    assert payload["artifactType"] == "agentflow_production_memory_operator_handoff_packet"
    assert payload["state"] == "operator handoff ready"
    assert payload["nextPassAction"] == "run_next_ai_task_with_acceptance_feedback_context"
    assert "Acceptance feedback candidate" in payload["laneTitles"]
    assert any(
        card.startswith("Acceptance feedback candidate:review ready:included_in_context")
        for card in payload["bundleCards"]
    )
    assert "acceptance_feedback_candidate_promotion" in payload["memoryIds"]
    assert "acceptance feedback candidate included:review ready" in payload["protocolControls"]
    assert "acceptance_feedback_candidate_promotion_decision:promoted" in payload["inspectorFacts"]
    assert "acceptance_feedback_candidate_promotion_effect:included_in_context" in payload["inspectorFacts"]
    assert "acceptance_feedback_candidate_included:true" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]


def test_web_static_run_package_view_surfaces_acceptance_feedback_candidate_promotion(tmp_path: Path) -> None:
    output_root = _operator_loop_with_acceptance_feedback_overlay(tmp_path)
    payload = _web_view_payload(output_root / "operator_run_package" / "operator_run_package.json")

    assert payload["artifactType"] == "agentflow_production_memory_operator_run_package"
    assert payload["state"] == "operator run package ready"
    assert payload["nextPassAction"] == "run_next_ai_task_with_acceptance_feedback_context"
    assert "Acceptance feedback candidate" in payload["laneTitles"]
    assert any(
        card.startswith("Acceptance feedback candidate:review ready:included_in_context")
        for card in payload["bundleCards"]
    )
    assert "acceptance_feedback_candidate_promotion" in payload["memoryIds"]
    assert "acceptance feedback candidate included:review ready" in payload["protocolControls"]
    assert "acceptance_feedback_candidate_promotion_decision:promoted" in payload["inspectorFacts"]
    assert "acceptance_feedback_candidate_promotion_effect:included_in_context" in payload["inspectorFacts"]
    assert "acceptance_feedback_candidate_included:true" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]


def test_web_static_handoff_acceptance_overlay_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/memory-workbench-production-acceptance-feedback-handoff.js"),
        Path("apps/web/memory-workbench-production-operator-handoff.js"),
        Path("apps/web/memory-workbench-production-operator-run-package.js"),
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
        "document." + "coo" + "kie",
        "showsavefilepicker",
        "createwritable",
        "filesystemwritablefilestream",
        "directory",
        "provider execution",
    ]:
        assert forbidden not in combined


def _operator_loop_with_acceptance_feedback_overlay(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed_result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T06:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        seed_result,
        tmp_path / "operator_loop_seed",
        write_run_package=True,
        write_run_package_check=True,
    )
    package_check = _read_json(
        tmp_path / "operator_loop_seed" / "operator_run_package_check" / "operator_run_package_check.json"
    )
    event = build_production_memory_acceptance_feedback_event(
        package_check,
        decision="accepted",
        summary="Human operator accepted the package for the next production-memory iteration.",
        reviewer_role="operator",
        reviewed_at="2026-06-03T06:05:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T06:10:00+08:00")
    decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable acceptance feedback candidate selected for Web handoff visibility.",
        reviewer_role="operator",
        decided_at="2026-06-03T06:15:00+08:00",
    )
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T06:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=decision,
    )
    output_root = tmp_path / "operator_loop_with_acceptance_handoff"
    write_production_memory_operator_loop_run(
        result,
        output_root,
        write_run_package=True,
        write_run_package_check=True,
    )
    return output_root


def _web_view_payload(path: Path) -> dict:
    path_ref = json.dumps(str(path))
    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: {json.dumps(path.name)},
  text: async () => await readFile({path_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  nextPassAction: view.next_pass.action,
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
    return json.loads(completed.stdout)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
