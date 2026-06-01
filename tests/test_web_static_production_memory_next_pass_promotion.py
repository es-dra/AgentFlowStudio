from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import build_production_memory_loop_run, load_production_memory_loop
from agentflow.memory.production_next_context import build_next_context_handoff
from agentflow.memory.production_next_pass_promotion import (
    build_next_pass_promotion_decision,
    build_next_pass_reviewed_feedback_run,
)
from agentflow.memory.production_next_pass_review import NEXT_PASS_RESULT_KIND, build_next_pass_review
from agentflow.memory.production_next_task import build_next_task_packet
from narratocut.utils import write_json


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _promotion_artifacts() -> tuple[dict, dict]:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at="2026-06-02T06:00:00+08:00")
    packet = build_next_task_packet(handoff, generated_at="2026-06-02T06:02:00+08:00")
    used_refs = [ref["ref_id"] for ref in packet["allowed_context_refs"][:2]]
    result = {
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
                "summary": "Keep the next-pass feedback reusable only after explicit decision.",
            }
        ],
    }
    review = build_next_pass_review(packet, result, reviewed_at="2026-06-02T06:05:00+08:00")
    decision = build_next_pass_promotion_decision(
        review,
        candidate_id=review["feedback_candidates"][0]["candidate_id"],
        decision="promoted",
        rationale="Traceable next-pass feedback selected by the operator.",
        reviewer_role="operator",
        decided_at="2026-06-02T06:10:00+08:00",
    )
    _derived_loop, run, overlay = build_next_pass_reviewed_feedback_run(loop, review, decision)
    return decision, overlay


def test_web_static_view_renders_production_memory_next_pass_promotion(tmp_path: Path) -> None:
    decision, overlay = _promotion_artifacts()
    decision_path = write_json(tmp_path / "next_pass_promotion_decision.json", decision)
    overlay_path = write_json(tmp_path / "next_pass_promotion_overlay.json", overlay)
    decision_ref = json.dumps(str(decision_path))
    overlay_ref = json.dumps(str(overlay_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const files = [
  {{
    name: "next_pass_promotion_decision.json",
    text: async () => await readFile({decision_ref}, "utf8"),
  }},
  {{
    name: "next_pass_promotion_overlay.json",
    text: async () => await readFile({overlay_ref}, "utf8"),
  }},
];
const artifacts = await parseFiles(files);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactTypes: artifacts.map((artifact) => artifact.artifactType),
  artifactClasses: artifacts.map((artifact) => artifact.artifactClass),
  sourceRoles: artifacts.map((artifact) => artifact.sourceRole),
  memoryBundleCount: workspace.memoryBundle.length,
  hasDecision: Boolean(workspace.productionMemoryNextPassPromotionDecision),
  hasOverlay: Boolean(workspace.productionMemoryNextPassPromotionOverlay),
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

    assert payload["artifactTypes"] == [
        "agentflow_production_memory_next_pass_promotion_decision",
        "agentflow_production_memory_next_pass_promotion_overlay",
    ]
    assert payload["artifactClasses"] == ["known_contract", "known_contract"]
    assert payload["sourceRoles"] == [
        "production memory next pass promotion decision",
        "production memory next pass promotion overlay",
    ]
    assert payload["memoryBundleCount"] == 2
    assert payload["hasDecision"] is True
    assert payload["hasOverlay"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_next_pass_promotion_overlay"
    assert payload["state"] == "next pass promotion ready"
    assert "Next pass promotion" in payload["laneTitles"]
    assert "Decision effect" in payload["laneTitles"]
    assert "Follow-up context" in payload["laneTitles"]
    assert "Explicit decision" in payload["bundleTitles"]
    assert "Decision effect" in payload["bundleTitles"]
    assert "Context bundle" in payload["bundleTitles"]
    assert "memory-candidate-feedback-next-pass-001" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "build_followup_context_from_explicit_decision"
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "long term memory write disabled:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "agentflow_production_memory_next_pass_promotion_decision" in payload["inspectorTypes"]
    assert "agentflow_production_memory_next_pass_promotion_overlay" in payload["inspectorTypes"]
    assert "decision:promoted" in payload["inspectorFacts"]
    assert "decision_effect:included_in_context" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_next_pass_promotion_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-next-pass-promotion.js"),
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
