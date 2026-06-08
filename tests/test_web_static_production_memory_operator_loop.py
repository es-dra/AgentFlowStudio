from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_next_pass_promotion import build_next_pass_promotion_decision
from agentflow.memory.production_next_pass_review import NEXT_PASS_RESULT_KIND
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _next_pass_result_for(packet: dict) -> dict:
    used_refs = [ref["ref_id"] for ref in packet["allowed_context_refs"][:2]]
    return {
        "kind": NEXT_PASS_RESULT_KIND,
        "artifact_type": NEXT_PASS_RESULT_KIND,
        "schema_version": packet["schema_version"],
        "task_packet_id": packet["task_packet_id"],
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "output_artifacts": [
            {
                "ref_id": "next-pass:artifact:draft-001",
                "title": "Second pass draft",
                "status": "draft",
                "used_context_refs": used_refs,
            }
        ],
        "feedback_events": [
            {
                "feedback_id": "feedback:next-pass-001",
                "target_ref": "next-pass:artifact:draft-001",
                "decision": "needs_revision",
                "summary": "Second pass needs operator review before memory promotion.",
            }
        ],
    }


def test_web_static_view_renders_production_memory_operator_loop_run(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T01:20:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    write_production_memory_operator_loop_run(result, tmp_path)
    manifest_path = tmp_path / "production_memory_operator_loop_run.json"
    manifest_ref = json.dumps(str(manifest_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {manifest_ref};
const file = {{
  name: "production_memory_operator_loop_run.json",
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
  hasOperatorLoopRun: Boolean(workspace.productionMemoryOperatorLoopRun),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleTitles: view.bundle_summary.map((item) => item.title),
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

    assert payload["artifactType"] == "agentflow_production_memory_operator_loop_run"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory operator loop run"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasOperatorLoopRun"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_operator_loop_run"
    assert payload["state"] == "operator loop ready"
    assert "Operator loop" in payload["laneTitles"]
    assert "Generated artifacts" in payload["laneTitles"]
    assert "Company KB feedback" in payload["laneTitles"]
    assert "Operator nodes" in payload["bundleTitles"]
    assert "Output artifacts" in payload["bundleTitles"]
    assert "Company KB feedback" in payload["bundleTitles"]
    assert "context_bundle" in payload["memoryIds"]
    assert "next_context_handoff" in payload["memoryIds"]
    assert "next_task_packet" in payload["memoryIds"]
    assert "company_kb_feedback_candidate_packet" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "inspect_generated_artifacts_before_next_pass"
    assert "no-provider mode:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "durable memory write disabled:review ready" in payload["protocolControls"]
    assert "agentflow_production_memory_operator_loop_run" in payload["inspectorTypes"]
    assert "chain_status:ready" in payload["inspectorFacts"]
    assert "operator_nodes:12" in payload["inspectorFacts"]
    assert "output_artifacts:13" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_operator_loop_renders_embedded_next_pass_promotion(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    seed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T06:30:00+08:00",
        source_kb_status="restructuring_or_unknown",
    )
    next_pass_result = _next_pass_result_for(seed["next_task_packet"])
    reviewed = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T06:30:00+08:00",
        source_kb_status="restructuring_or_unknown",
        next_pass_result=next_pass_result,
    )
    decision = build_next_pass_promotion_decision(
        reviewed["next_pass_review"],
        candidate_id=reviewed["next_pass_review"]["feedback_candidates"][0]["candidate_id"],
        decision="promoted",
        rationale="Traceable next-pass feedback selected by the operator.",
        reviewer_role="operator",
        decided_at="2026-06-02T06:40:00+08:00",
    )
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T06:30:00+08:00",
        source_kb_status="restructuring_or_unknown",
        next_pass_result=next_pass_result,
        next_pass_promotion_decision=decision,
    )
    write_production_memory_operator_loop_run(result, tmp_path)
    manifest_path = tmp_path / "production_memory_operator_loop_run.json"
    manifest_ref = json.dumps(str(manifest_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {manifest_ref};
const file = {{
  name: "production_memory_operator_loop_run.json",
  text: async () => await readFile(path, "utf8"),
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
    assert "Next pass promotion" in payload["laneTitles"]
    assert any(card.startswith("Next pass promotion:promoted:included_in_context") for card in payload["bundleCards"])
    assert "next_pass_promotion_decision" in payload["memoryIds"]
    assert "next_pass_promotion_overlay" in payload["memoryIds"]
    assert "next_pass_promotion_decision/next_pass_promotion_decision.json" in payload["assetPaths"]
    assert "next_pass_reviewed_feedback/next_pass_promotion_overlay.json" in payload["assetPaths"]
    assert "next_pass_reviewed_feedback/context_bundle.json" in payload["assetPaths"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "inspect_next_pass_promotion_overlay_before_followup_context"
    assert "next-pass promotion no-provider mode:review ready" in payload["protocolControls"]
    assert "next-pass promotion memory write disabled:review ready" in payload["protocolControls"]
    assert "next_pass_promotion_decision:promoted" in payload["inspectorFacts"]
    assert "next_pass_promotion_effect:included_in_context" in payload["inspectorFacts"]


def test_web_static_operator_loop_renders_post_check_next_operator_start_packet(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path,
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
    )
    manifest_path = tmp_path / "production_memory_operator_loop_run.json"
    manifest_ref = json.dumps(str(manifest_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {manifest_ref};
const file = {{
  name: "production_memory_operator_loop_run.json",
  text: async () => await readFile(path, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  state: view.state,
  actionIds: view.workflow_actions.map((item) => item.id),
  actionStatuses: view.workflow_actions.map((item) => `${{item.id}}:${{item.status}}`),
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleCards: view.bundle_summary.map((item) => `${{item.title}}:${{item.status}}:${{item.detail}}`),
  assetPaths: view.assets.map((item) => item.id),
  assetStatuses: view.assets.map((item) => `${{item.id}}:${{item.status}}`),
  memoryIds: view.memory_loaded.map((item) => item.id),
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  nextPassAction: view.next_pass.action,
  nextOperatorBrief: view.next_operator_brief,
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

    assert payload["state"] == "operator loop ready"
    assert "inspect_next_operator_start_packet" in payload["actionIds"]
    assert "inspect_next_operator_start_packet:review ready" in payload["actionStatuses"]
    assert "Next operator start packet" in payload["laneTitles"]
    assert "Post-check artifacts" in payload["laneTitles"]
    assert any(card.startswith("Next operator start packet:ready:ready") for card in payload["bundleCards"])
    assert any(card.startswith("Post-check artifacts:review ready:2 post-check refs") for card in payload["bundleCards"])
    assert "next_operator_start_packet/next_operator_start_packet.json" in payload["assetPaths"]
    assert "next_operator_start_packet/next_operator_start_packet.md" in payload["assetPaths"]
    assert "next_operator_start_packet/next_operator_start_packet.json:post-check" in payload["assetStatuses"]
    assert "next_operator_start_packet" in payload["memoryIds"]
    assert "next operator start packet ready:review ready" in payload["protocolControls"]
    assert payload["nextPassAction"] == "start_next_operator_action"
    assert payload["nextOperatorBrief"]["status"] == "review ready"
    assert payload["nextOperatorBrief"]["action"] == "review_or_complete_next_pass_result"
    assert payload["nextOperatorBrief"]["prompt_excerpt"].startswith("Use the generated next_task_packet")
    assert "Do not call remote providers" in payload["nextOperatorBrief"]["prompt_excerpt"]
    assert "Do not write Company KB or durable memory from this start packet." in payload["nextOperatorBrief"]["requirements"]
    assert "Next operator start packet" in payload["timelineLabels"]


def test_web_static_operator_loop_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-operator-loop.js"),
        Path("apps/web/memory-workbench-production-operator-loop-utils.js"),
        Path("apps/web/memory-workbench-production-next-operator-brief.js"),
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
