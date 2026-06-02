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
from agentflow.memory.production_operator_run_package_check import (
    check_operator_run_package,
    write_operator_run_package_check,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_view_renders_production_memory_operator_run_package_check(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T21:10:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(result, tmp_path, write_run_package=True)
    package_path = tmp_path / "operator_run_package" / "operator_run_package.json"
    check = check_operator_run_package(package_path)
    write_operator_run_package_check(check, tmp_path / "operator_run_package_check" / "operator_run_package_check.json")
    check_path = tmp_path / "operator_run_package_check" / "operator_run_package_check.json"
    payload = _web_view_payload(check_path)

    assert payload["artifactType"] == "agentflow_production_memory_operator_run_package_check"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory operator run package check"
    assert payload["memoryBundleCount"] == 1
    assert payload["projectFormat"] == "agentflow_production_memory_operator_run_package_check"
    assert payload["state"] == "operator run package check passed"
    assert "Run package check" in payload["laneTitles"]
    assert "Checked items" in payload["laneTitles"]
    assert "Missing items" in payload["laneTitles"]
    assert any(card.startswith("Package check:review ready:passed") for card in payload["bundleCards"])
    assert any(card.startswith("Checked items:review ready:18 items checked") for card in payload["bundleCards"])
    assert any(card.startswith("Missing items:review ready:0 items missing") for card in payload["bundleCards"])
    assert "operator_run_package_check" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "handoff_to_next_operator"
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "durable memory write disabled:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "human acceptance:blocked:not_claimed" in payload["protocolBoundaries"]
    assert "business validation:blocked:not_claimed" in payload["protocolBoundaries"]
    assert "agentflow_production_memory_operator_run_package_check" in payload["inspectorTypes"]
    assert "check_status:passed" in payload["inspectorFacts"]
    assert "ready_for_handoff:true" in payload["inspectorFacts"]
    assert "checked_items:18" in payload["inspectorFacts"]
    assert "missing_refs:0" in payload["inspectorFacts"]
    assert "failed_controls:0" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_run_package_check_surfaces_acceptance_feedback_candidate_promotion_check(
    tmp_path: Path,
) -> None:
    output_root = _operator_loop_with_acceptance_feedback_overlay(tmp_path)
    payload = _web_view_payload(output_root / "operator_run_package_check" / "operator_run_package_check.json")

    assert payload["artifactType"] == "agentflow_production_memory_operator_run_package_check"
    assert payload["state"] == "operator run package check passed"
    assert "Acceptance promotion check" in payload["laneTitles"]
    assert any(
        card.startswith("Acceptance promotion check:review ready:included_in_context")
        for card in payload["bundleCards"]
    )
    assert "acceptance feedback candidate promotion included:review ready" in payload["protocolControls"]
    assert "acceptance_feedback_candidate_promotion_check:passed" in payload["inspectorFacts"]
    assert "acceptance_feedback_candidate_promotion_effect:included_in_context" in payload["inspectorFacts"]
    assert "acceptance_feedback_candidate_included:true" in payload["inspectorFacts"]
    assert "acceptance_feedback_candidate_handoff_matches_package:true" in payload["inspectorFacts"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "handoff_to_next_operator"


def test_web_static_operator_run_package_check_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-inspector-facts.js"),
        Path("apps/web/memory-workbench-production-operator-run-package-check.js"),
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


def _operator_loop_with_acceptance_feedback_overlay(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed_result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T08:00:00+08:00",
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
        reviewed_at="2026-06-03T08:05:00+08:00",
    )
    packet = build_acceptance_feedback_candidate_packet(event, generated_at="2026-06-03T08:10:00+08:00")
    decision = build_acceptance_feedback_candidate_promotion_decision(
        packet,
        decision="promoted",
        rationale="Traceable acceptance feedback candidate selected for Web package-check visibility.",
        reviewer_role="operator",
        decided_at="2026-06-03T08:15:00+08:00",
    )
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T08:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
        acceptance_feedback_candidate_packet=packet,
        acceptance_feedback_candidate_promotion_decision=decision,
    )
    output_root = tmp_path / "operator_loop_with_acceptance_check"
    write_production_memory_operator_loop_run(
        result,
        output_root,
        write_run_package=True,
        write_run_package_check=True,
    )
    return output_root


def _web_view_payload(path: Path) -> dict:
    check_ref = json.dumps(str(path))
    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: "operator_run_package_check.json",
  text: async () => await readFile({check_ref}, "utf8"),
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
    return json.loads(completed.stdout)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
