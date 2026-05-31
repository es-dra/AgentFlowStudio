from __future__ import annotations

import json
import subprocess


def test_web_memory_workbench_summarizes_explicitly_selected_bundle_artifacts() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { memoryWorkbenchFixture } from "./apps/web/memory-workbench-fixture.js";
import { buildMemoryWorkbenchPackageView } from "./apps/web/memory-workbench-package.js";
import { readFile } from "node:fs/promises";

const selectedFiles = await Promise.all([
  ["memory_video_pipeline_package.example.json", "examples/agentflow/memory_video_pipeline_package.example.json"],
  ["memory_video_pipeline_review.example.json", "examples/agentflow/memory_video_pipeline_review.example.json"],
  ["memory_video_pipeline_human_observation.example.json", "examples/agentflow/memory_video_pipeline_human_observation.example.json"],
  ["memory_video_pipeline_presentation_package.example.json", "examples/agentflow/memory_video_pipeline_presentation_package.example.json"],
].map(async ([name, path]) => ({
  name,
  text: async () => await readFile(path, "utf8"),
})));

selectedFiles.push({
  name: "memory_video_pipeline_feedback_event_draft.json",
  text: async () => JSON.stringify({
    schema_version: "0.1.0",
    artifact_type: "agentflow_feedback_event",
    feedback_id: "memory_video_pipeline_neon_rain_turnback_v1_feedback_draft",
    decision: "note",
    draft_status: "draft_not_persisted",
    reason_tags: ["baseline_more_variable", "memory_backed_more_stable", "not_human_acceptance"],
    user_note: "Bounded visual observation: memory-backed repeat runs were more stable.",
    writes_long_term_memory: false,
  }),
});

const workspace = normalizeWorkspace(await parseFiles(selectedFiles));
const view = buildMemoryWorkbenchPackageView(workspace, memoryWorkbenchFixture);
console.log(JSON.stringify({
  bundleTypes: workspace.memoryBundle.map((artifact) => artifact.artifactType),
  reviewOutput: view.lanes[0].output,
  memoryOutput: view.lanes[1].output,
  reviewDetail: view.review.storyboard_adherence,
  visualDetail: view.review.visual_consistency,
  feedbackSummary: view.feedback.summary,
  nextAction: view.next_pass.action,
  bundleSummary: view.bundle_summary.map((item) => `${item.id}:${item.status}:${item.detail}`),
  provenance: view.memory_loaded.map((item) => `${item.id}:${item.request_projection}`),
  protocol: {
    title: view.protocol_summary.title,
    controls: view.protocol_summary.controls.map((item) => `${item.label}:${item.status}:${item.detail}`),
    boundaries: view.protocol_summary.boundaries.map((item) => `${item.label}:${item.status}:${item.detail}`),
  },
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["bundleTypes"] == [
        "agentflow_memory_video_pipeline_package",
        "agentflow_memory_video_pipeline_review",
        "agentflow_memory_video_pipeline_human_observation",
        "agentflow_memory_video_pipeline_presentation_package",
        "agentflow_feedback_event",
    ]
    assert "baseline: 2 runs" in payload["reviewOutput"]
    assert "memory_backed: 2 runs" in payload["memoryOutput"]
    assert "5 checkpoints" in payload["reviewDetail"]
    assert "memory_backed_stronger: 4" in payload["visualDetail"]
    assert "draft_not_persisted" in payload["feedbackSummary"]
    assert "not durable memory" in payload["nextAction"]
    assert any("review_ref:review ready" in item and "selected explicitly" in item for item in payload["bundleSummary"])
    assert any("feedback_event_draft_ref:feedback captured" in item for item in payload["bundleSummary"])
    assert any("observation_summary" in item for item in payload["provenance"])
    assert payload["protocol"]["title"] == "Baseline parity protocol"
    assert any("only memory context differs:review ready" in item for item in payload["protocol"]["controls"])
    assert any("same provider route:review ready" in item for item in payload["protocol"]["controls"])
    assert any("human acceptance:blocked:not_acceptance" in item for item in payload["protocol"]["boundaries"])
    assert any("durable memory runtime:blocked:not_implemented" in item for item in payload["protocol"]["boundaries"])

def test_web_memory_artifact_inspector_summarizes_selected_memory_json_only() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryArtifactInspector } from "./apps/web/memory-workbench-inspector.js";
import { readFile } from "node:fs/promises";

const selectedFiles = await Promise.all([
  ["memory_video_pipeline_protocol.example.json", "examples/agentflow/memory_video_pipeline_protocol.example.json"],
  ["memory_video_pipeline_package.example.json", "examples/agentflow/memory_video_pipeline_package.example.json"],
  ["memory_video_pipeline_review.example.json", "examples/agentflow/memory_video_pipeline_review.example.json"],
  ["memory_video_pipeline_human_observation.example.json", "examples/agentflow/memory_video_pipeline_human_observation.example.json"],
  ["memory_video_pipeline_presentation_package.example.json", "examples/agentflow/memory_video_pipeline_presentation_package.example.json"],
].map(async ([name, path]) => ({
  name,
  text: async () => await readFile(path, "utf8"),
})));

selectedFiles.push({
  name: "memory_video_pipeline_feedback_event_draft.json",
  text: async () => JSON.stringify({
    schema_version: "0.1.0",
    artifact_type: "agentflow_feedback_event",
    feedback_id: "memory_video_pipeline_neon_rain_turnback_v1_feedback_draft",
    decision: "note",
    draft_status: "draft_not_persisted",
    reason_tags: ["baseline_more_variable", "memory_backed_more_stable"],
    writes_long_term_memory: false,
  }),
});
selectedFiles.push({
  name: "unknown.json",
  text: async () => JSON.stringify({ hello: "world" }),
});

const workspace = normalizeWorkspace(await parseFiles(selectedFiles));
const cards = buildMemoryArtifactInspector(workspace);
console.log(JSON.stringify({
  bundleTypes: workspace.memoryBundle.map((artifact) => artifact.artifactType),
  titles: cards.map((card) => card.title),
  facts: cards.flatMap((card) => card.facts.map((fact) => `${fact.label}:${fact.value}`)),
  focusTargets: cards.flatMap((card) => card.focus_targets),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["bundleTypes"] == [
        "agentflow_memory_video_pipeline_protocol",
        "agentflow_memory_video_pipeline_package",
        "agentflow_memory_video_pipeline_review",
        "agentflow_memory_video_pipeline_human_observation",
        "agentflow_memory_video_pipeline_presentation_package",
        "agentflow_feedback_event",
    ]
    assert "Pipeline protocol" in payload["titles"]
    assert "Pipeline package" in payload["titles"]
    assert "Human observation" in payload["titles"]
    assert "unknown.json" not in " ".join(payload["titles"])
    assert "memory_cards:3" in payload["facts"]
    assert "video_artifacts:4" in payload["facts"]
    assert "observations:6" in payload["facts"]
    assert any("takeaway:" in item for item in payload["facts"])
    assert "draft_status:draft_not_persisted" in payload["facts"]
    assert "review" in payload["focusTargets"]
    assert "feedback" in payload["focusTargets"]
