from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import build_production_memory_loop_run, load_production_memory_loop
from agentflow.memory.production_next_context import build_next_context_handoff
from agentflow.memory.production_next_pass_review import (
    NEXT_PASS_RESULT_KIND,
    build_next_pass_review,
    write_next_pass_review,
)
from agentflow.memory.production_next_task import build_next_task_packet


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def _next_pass_review() -> dict:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at="2026-06-02T03:10:00+08:00")
    packet = build_next_task_packet(handoff, generated_at="2026-06-02T03:12:00+08:00")
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
                "summary": "Second pass needs operator review before memory promotion.",
            }
        ],
    }
    return build_next_pass_review(packet, result, reviewed_at="2026-06-02T03:30:00+08:00")


def test_web_static_view_renders_production_memory_next_pass_review(tmp_path: Path) -> None:
    review = _next_pass_review()
    write_next_pass_review(review, tmp_path)
    review_path = tmp_path / "next_pass_review.json"
    review_ref = json.dumps(str(review_path))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const path = {review_ref};
const file = {{
  name: "next_pass_review.json",
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
  hasNextPassReview: Boolean(workspace.productionMemoryNextPassReview),
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

    assert payload["artifactType"] == "agentflow_production_memory_next_pass_review"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory next pass review"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasNextPassReview"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_next_pass_review"
    assert payload["state"] == "next pass review ready"
    assert "Next pass review" in payload["laneTitles"]
    assert "Used allowed refs" in payload["laneTitles"]
    assert "Blocked or unknown refs" in payload["laneTitles"]
    assert "Candidate feedback" in payload["laneTitles"]
    assert "Used allowed refs" in payload["bundleTitles"]
    assert "Blocked or unknown refs" in payload["bundleTitles"]
    assert "Feedback candidates" in payload["bundleTitles"]
    assert "Pending promotion templates" in payload["bundleTitles"]
    assert "memory-candidate-feedback-next-pass-001" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "review_candidate_feedback_for_explicit_promotion"
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "no blocked or unknown context refs used:review ready" in payload["protocolControls"]
    assert "feedback candidate only:review ready" in payload["protocolControls"]
    assert "agentflow_production_memory_next_pass_review" in payload["inspectorTypes"]
    assert "review_status:ready_for_operator_review" in payload["inspectorFacts"]
    assert "used_allowed_refs:2" in payload["inspectorFacts"]
    assert "blocked_or_unknown_refs:0" in payload["inspectorFacts"]
    assert "feedback_candidates:1" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]
    assert payload["sourceLabel"] == "Selected files"


def test_web_static_next_pass_review_slice_adds_no_provider_scan_or_project_specific_behavior() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-next-pass-review.js"),
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
