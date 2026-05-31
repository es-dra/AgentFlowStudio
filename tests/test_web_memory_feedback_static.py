from __future__ import annotations

import json
import subprocess
from tests.web_static_helpers import read_web_file as _read_web_file


def test_web_memory_workbench_sample_bundle_is_sanitized_and_complete() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { memoryWorkbenchSampleFiles } from "./apps/web/memory-workbench-sample.js";

const workspace = normalizeWorkspace(await parseFiles(memoryWorkbenchSampleFiles()));
console.log(JSON.stringify({
  artifactCount: workspace.artifacts.length,
  bundleTypes: workspace.memoryBundle.map((artifact) => artifact.artifactType),
  packageId: workspace.memoryPackage?.payload?.protocol_id,
  rawText: workspace.artifacts.map((artifact) => artifact.rawText).join("\\n"),
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

    assert payload["artifactCount"] == 5
    assert payload["bundleTypes"] == [
        "agentflow_memory_video_pipeline_package",
        "agentflow_memory_video_pipeline_review",
        "agentflow_memory_video_pipeline_human_observation",
        "agentflow_memory_video_pipeline_presentation_package",
        "agentflow_feedback_event",
    ]
    assert payload["packageId"] == "memory_video_pipeline_neon_rain_turnback_v1"
    for forbidden in ["Authorization", "Bearer ", "api_key", "secret", "signed_url", "https://", "http://", "D:/", "D:\\\\"]:
        assert forbidden not in payload["rawText"]

def test_web_memory_workbench_builds_browser_local_feedback_draft_from_selected_bundle() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryFeedbackDraft } from "./apps/web/memory-workbench-feedback.js";
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

const workspace = normalizeWorkspace(await parseFiles(selectedFiles));
const preview = buildMemoryFeedbackDraft(workspace);
console.log(JSON.stringify({
  mode: preview.mode,
  status: preview.status,
  copyEnabled: preview.copy_enabled,
  draft: preview.draft,
  jsonText: preview.json_text,
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
    draft = payload["draft"]

    assert payload["mode"] == "draft"
    assert payload["status"] == "draft_not_persisted"
    assert payload["copyEnabled"] is True
    assert draft["artifact_type"] == "agentflow_feedback_event"
    assert draft["decision"] == "note"
    assert draft["writes_long_term_memory"] is False
    assert draft["provider_calls_started"] is False
    assert draft["browser_generated_only"] is True
    assert "baseline_more_variable" in draft["reason_tags"]
    assert "memory_backed_more_stable" in draft["reason_tags"]
    assert draft["refs"]["package"]["file_name"] == "memory_video_pipeline_package.example.json"
    assert draft["refs"]["review"]["artifact_type"] == "agentflow_memory_video_pipeline_review"
    assert "same keyframe" in draft["user_note"].lower()
    assert "5 storyboard checkpoints" in draft["next_pass_hint"]
    assert '"draft_status": "draft_not_persisted"' in payload["jsonText"]

def test_web_memory_workbench_selected_feedback_remains_read_only_and_not_persisted() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryFeedbackDraft } from "./apps/web/memory-workbench-feedback.js";

const workspace = normalizeWorkspace(await parseFiles([
  {
    name: "memory_video_pipeline_feedback_event_draft.json",
    text: async () => JSON.stringify({
      schema_version: "0.1.0",
      artifact_type: "agentflow_feedback_event",
      feedback_id: "selected_feedback",
      decision: "note",
      draft_status: "draft_not_persisted",
      reason_tags: ["selected"],
      writes_long_term_memory: true
    }),
  },
]));
const preview = buildMemoryFeedbackDraft(workspace);
console.log(JSON.stringify(preview));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    preview = json.loads(result.stdout)

    assert preview["mode"] == "selected"
    assert preview["copy_enabled"] is True
    assert preview["draft"]["feedback_id"] == "selected_feedback"
    assert preview["draft"]["writes_long_term_memory"] is False

def test_web_memory_demo_summary_builds_talk_track_from_package_view() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { memoryWorkbenchFixture } from "./apps/web/memory-workbench-fixture.js";
import { buildMemoryWorkbenchPackageView } from "./apps/web/memory-workbench-package.js";
import { buildDemoEvidenceSummary } from "./apps/web/memory-workbench-demo-summary.js";
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

const workspace = normalizeWorkspace(await parseFiles(selectedFiles));
const view = buildMemoryWorkbenchPackageView(workspace, memoryWorkbenchFixture);
const summary = buildDemoEvidenceSummary(view);
console.log(JSON.stringify(summary));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    summary = json.loads(result.stdout)

    assert summary["title"] == "Demo Evidence Summary"
    assert summary["status"] == "review ready"
    assert "Same task, assets, route, duration, and storyboard are held constant." in summary["talk_track"]
    assert any(card["label"] == "Experiment setup" and card["status"] == "review ready" for card in summary["evidence_cards"])
    assert any(card["label"] == "Baseline" for card in summary["comparison"])
    assert any(card["label"] == "Memory-backed" for card in summary["comparison"])
    assert any(card["label"] == "human acceptance" and card["status"] == "blocked" for card in summary["non_claims"])

def test_web_memory_demo_ready_checklist_tracks_loaded_evidence_without_execution() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { memoryWorkbenchFixture } from "./apps/web/memory-workbench-fixture.js";
import { buildMemoryWorkbenchPackageView } from "./apps/web/memory-workbench-package.js";
import { buildMemoryFeedbackDraft } from "./apps/web/memory-workbench-feedback.js";
import { buildDemoReadyChecklist } from "./apps/web/memory-workbench-demo-checklist.js";
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

const workspace = normalizeWorkspace(await parseFiles(selectedFiles));
const view = buildMemoryWorkbenchPackageView(workspace, memoryWorkbenchFixture);
view.source_status = { label: "Selected files", status: "review ready", detail: "4 explicit local memory artifacts selected by the operator." };
view.feedback_draft = buildMemoryFeedbackDraft(workspace);
const checklist = buildDemoReadyChecklist(view);
console.log(JSON.stringify(checklist));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    checklist = json.loads(result.stdout)
    items = {item["label"]: item for item in checklist["items"]}

    assert checklist["title"] == "Demo-ready checklist"
    assert checklist["status"] == "review ready"
    assert items["source loaded"]["status"] == "review ready"
    assert items["review evidence"]["status"] == "review ready"
    assert items["observation notes"]["status"] == "review ready"
    assert items["presentation summary"]["status"] == "review ready"
    assert items["lane parity"]["detail"] == "6/6 parity controls ready"
    assert items["feedback draft"]["status"] == "review ready"
    assert items["claim boundaries visible"]["detail"] == "4 boundaries shown"
    assert checklist["summary"]["ready_count"] == 6
    assert checklist["summary"]["total_count"] == 6
    assert checklist["summary"]["gap_count"] == 0
    assert checklist["summary"]["boundary_count"] == 4
    groups = {group["id"]: group for group in checklist["groups"]}
    assert groups["speakable"]["title"] == "可讲内容"
    assert groups["speakable"]["status"] == "review ready"
    assert [item["label"] for item in groups["speakable"]["items"]] == [
        "source loaded",
        "package selected",
        "lane parity",
        "feedback draft",
    ]
    assert groups["gaps"]["title"] == "待补缺口"
    assert groups["gaps"]["status"] == "review ready"
    assert groups["non-claims"]["title"] == "禁止宣称"
    assert groups["non-claims"]["status"] == "blocked"
    assert [item["label"] for item in groups["non-claims"]["items"]] == [
        "human acceptance",
        "business validation",
        "quality improvement claim",
        "durable memory runtime",
    ]
