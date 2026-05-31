from __future__ import annotations

import json
import subprocess


def test_web_memory_studio_status_renders_readiness_summary_without_execution() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { memoryWorkbenchFixture } from "./apps/web/memory-workbench-fixture.js";
import { buildMemoryWorkbenchView } from "./apps/web/memory-workbench-controller.js";
import { renderMemoryWorkbench } from "./apps/web/memory-workbench-render.js";
import { readFile } from "node:fs/promises";

function element(tagName) {
  return {
    tagName,
    className: "",
    children: [],
    dataset: {},
    _text: "",
    style: { setProperty() {} },
    get classList() {
      return { toggle() {} };
    },
    set textContent(value) {
      this._text = String(value);
    },
    get textContent() {
      return [this._text, ...this.children.map((child) => child.textContent || "")].join("");
    },
    append(...children) {
      this.children.push(...children);
    },
    replaceChildren(...children) {
      this.children = children;
    },
    setAttribute() {},
    addEventListener() {},
    querySelectorAll() {
      return [];
    },
  };
}

globalThis.document = { createElement: element };

function elements() {
  return {
    memoryWorkbench: element("section"),
    memoryStudioStatus: element("div"),
    memorySourceStatus: element("div"),
    memoryProjectSummary: element("div"),
    memoryAssetSummary: element("div"),
    memoryBundleSummary: element("div"),
    memoryArtifactInspector: element("div"),
    memoryFeedbackPreview: element("div"),
    memoryFeedbackOutput: element("textarea"),
    memoryFeedbackStatus: element("p"),
    memoryFeedbackCopy: element("button"),
    memoryFocusSummary: element("div"),
    memoryDemoSummary: element("div"),
    memoryDemoChecklist: element("div"),
    memoryActionStrip: element("div"),
    memoryStateStrip: element("div"),
    memoryCanvasStage: element("div"),
    memoryProtocolSummary: element("div"),
    memoryLaneGrid: element("div"),
    memoryRunTimeline: element("div"),
    memoryProvenancePanel: element("div"),
  };
}

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
const view = buildMemoryWorkbenchView(workspace, "selected_files");
const fixtureElements = elements();
renderMemoryWorkbench(fixtureElements, view, { statusLabels: {}, noDetails: "" });

console.log(JSON.stringify({
  studioStatus: fixtureElements.memoryStudioStatus.textContent,
  checklist: fixtureElements.memoryDemoChecklist.textContent,
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

    assert "Can present" in payload["studioStatus"]
    assert "6/6" in payload["studioStatus"]
    assert "Evidence gaps" in payload["studioStatus"]
    assert "0" in payload["studioStatus"]
    assert "Do not claim" in payload["studioStatus"]
    assert "4 boundaries" in payload["studioStatus"]
    assert "可讲内容" in payload["checklist"]
    assert "待补缺口" in payload["checklist"]
    assert "禁止宣称" in payload["checklist"]

def test_web_memory_workbench_builds_view_from_selected_package_artifact() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { memoryWorkbenchFixture } from "./apps/web/memory-workbench-fixture.js";
import { buildMemoryWorkbenchPackageView } from "./apps/web/memory-workbench-package.js";
import { readFile } from "node:fs/promises";

const packageText = await readFile("examples/agentflow/memory_video_pipeline_package.example.json", "utf8");
const artifacts = await parseFiles([
  { name: "memory_video_pipeline_package.example.json", text: async () => packageText },
]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchPackageView(workspace, memoryWorkbenchFixture);
console.log(JSON.stringify({
  artifactType: workspace.memoryPackage?.artifactType,
  title: view.project.title,
  state: view.state,
  sourceRole: workspace.memoryPackage?.sourceRole,
  provenanceIds: view.memory_loaded.map((item) => item.id),
  bundleSummary: view.bundle_summary.map((item) => `${item.id}:${item.status}:${item.detail}`),
  timelineLabels: view.timeline.map((item) => item.label),
  claimBoundary: view.review.boundary,
  route: view.project.route,
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

    assert payload["artifactType"] == "agentflow_memory_video_pipeline_package"
    assert payload["sourceRole"] == "memory video pipeline package"
    assert payload["title"] == "memory_video_pipeline_neon_rain_turnback_v1"
    assert payload["state"] == "feedback captured"
    assert "plan_ref" in payload["provenanceIds"]
    assert "feedback_event_draft_ref" in payload["provenanceIds"]
    assert any("review_ref:missing" in item for item in payload["bundleSummary"])
    assert any("referenced but not selected" in item for item in payload["bundleSummary"])
    assert payload["timelineLabels"] == [
        "Project",
        "Assets",
        "Memory Loaded",
        "Baseline Run",
        "Memory-backed Run",
        "Review",
        "Feedback",
        "Next Pass",
    ]
    assert payload["claimBoundary"] == "not_acceptance / not_validated / not_implemented"
    assert payload["route"] == "selected local JSON package; no bridge or provider call"
