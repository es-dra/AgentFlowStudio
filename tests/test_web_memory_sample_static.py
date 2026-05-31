from __future__ import annotations

import json
import subprocess


def test_web_memory_sample_bundle_button_loads_demo_artifacts_and_switches_mode() -> None:
    script = """
const listeners = {};

function element(id = "") {
  return {
    id,
    className: "",
    hidden: false,
    value: "",
    disabled: false,
    dataset: {},
    children: [],
    options: [],
    _text: "",
    _html: "",
    get classList() {
      const owner = this;
      return {
        toggle(name, force) {
          const classes = new Set(owner.className.split(/\\s+/).filter(Boolean));
          if (force) classes.add(name);
          else classes.delete(name);
          owner.className = [...classes].join(" ");
        },
        add(name) {
          owner.className = `${owner.className} ${name}`.trim();
        },
        remove(name) {
          owner.className = owner.className.split(/\\s+/).filter((item) => item && item !== name).join(" ");
        },
        contains(name) {
          return owner.className.split(/\\s+/).includes(name);
        },
      };
    },
    set textContent(value) {
      this._text = String(value);
    },
    get textContent() {
      return [this._text, ...this.children.map((child) => child.textContent || "")].join("");
    },
    set innerHTML(value) {
      this._html = String(value);
    },
    get innerHTML() {
      return this._html;
    },
    append(...children) {
      this.children.push(...children);
      if (this.id?.includes("select") || this.id?.includes("artifact")) this.options.push(...children);
    },
    replaceChildren(...children) {
      this.children = children;
      this.options = children;
    },
    setAttribute(name, value) {
      this[name] = String(value);
    },
    getAttribute(name) {
      return this[name];
    },
    addEventListener(name, handler) {
      listeners[`${this.id}:${name}`] = handler;
    },
    querySelectorAll() {
      return [];
    },
    querySelector() {
      return null;
    },
    focus() {},
    select() {},
  };
}

const byId = new Map();
const ids = [
  "app-root",
  "artifact-files", "language-toggle", "artifact-count", "inventory-list", "summary-content",
  "inspector-content", "evidence-map-content", "risk-ledger-content", "asset-ledger-content",
  "video-preview-content", "report-content", "report-tabs", "overall-status", "overall-status-label",
  "overall-status-value", "stat-artifacts", "stat-known", "stat-warnings", "stat-errors",
  "feedback-artifact", "feedback-decision", "feedback-risk", "feedback-time", "feedback-note",
  "feedback-output", "feedback-status", "feedback-copy", "mode-review", "mode-production",
  "mode-memory", "review-workbench", "production-workbench", "memory-workbench",
  "memory-sample-bundle", "memory-source-status", "memory-project-summary", "memory-bundle-summary",
      "memory-artifact-inspector", "memory-feedback-preview", "memory-feedback-copy",
      "memory-feedback-output", "memory-feedback-status", "memory-action-strip", "memory-asset-summary",
      "memory-state-strip", "memory-canvas-stage", "memory-demo-summary", "memory-demo-checklist", "memory-protocol-summary", "memory-lane-grid", "memory-run-timeline",
  "memory-provenance-panel", "bridge-health", "workflow-select", "workflow-input-path",
  "workflow-output-dir", "workflow-profile", "quick-demo-button", "product-workflow-button",
  "create-plan-button", "run-workflow-button", "refresh-review-button", "production-overview",
  "readiness-checklist", "production-next-action", "acceptance-path-detail", "operator-loop-status",
  "step-timeline", "production-artifacts", "production-video-preview", "production-asset-match",
  "supervision-panel", "supervision-actions", "production-log", "run-feedback-decision",
  "run-feedback-risk", "run-feedback-time", "run-feedback-note", "run-feedback-copy",
  "run-feedback-output", "run-feedback-status",
];
for (const id of ids) byId.set(id, element(id));
byId.get("feedback-decision").value = "approved";
byId.get("feedback-risk").value = "general_review";
byId.get("run-feedback-decision").value = "approved";
byId.get("run-feedback-risk").value = "production_readiness";

globalThis.document = {
  documentElement: element("html"),
  createElement: (tagName) => element(tagName),
  querySelector(selector) {
    if (selector.startsWith("#")) return byId.get(selector.slice(1));
    return element(selector);
  },
  querySelectorAll(selector) {
    if (selector === "#production-path li") return [element("li"), element("li"), element("li"), element("li"), element("li"), element("li")];
    return [];
  },
};
globalThis.window = { addEventListener() {} };
globalThis.URL = { createObjectURL: () => "blob:local", revokeObjectURL() {} };
globalThis.fetch = async () => { throw new Error("fetch should not be called"); };

await import("./apps/web/app.js");
await listeners["memory-sample-bundle:click"]();

console.log(JSON.stringify({
  reviewHidden: byId.get("review-workbench").hidden,
  memoryHidden: byId.get("memory-workbench").hidden,
  artifactCount: byId.get("stat-artifacts").textContent,
  knownCount: byId.get("stat-known").textContent,
  projectText: byId.get("memory-project-summary").textContent,
  sourceText: byId.get("memory-source-status").textContent,
  bundleText: byId.get("memory-bundle-summary").textContent,
  demoText: byId.get("memory-demo-summary").textContent,
  checklistText: byId.get("memory-demo-checklist").textContent,
  protocolText: byId.get("memory-protocol-summary").textContent,
  feedbackText: byId.get("memory-feedback-output").value,
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

    assert payload["reviewHidden"] is True
    assert payload["memoryHidden"] is False
    assert payload["artifactCount"].startswith("5")
    assert payload["knownCount"].startswith("5")
    assert "Sample bundle" in payload["sourceText"]
    assert "5 embedded sanitized memory artifacts" in payload["sourceText"]
    assert "Selected local memory video pipeline package" in payload["projectText"]
    assert "selected explicitly" in payload["bundleText"]
    assert "Demo Evidence Summary" in payload["demoText"]
    assert "Same task, assets, route, duration, and storyboard are held constant." in payload["demoText"]
    assert "Memory-backed" in payload["demoText"]
    assert "Demo-ready checklist" in payload["checklistText"]
    assert "review evidence" in payload["checklistText"]
    assert "feedback draft" in payload["checklistText"]
    assert "Baseline parity protocol" in payload["protocolText"]
    assert "only memory context differs" in payload["protocolText"]
    assert "human acceptance" in payload["protocolText"]
    assert '"artifact_type": "agentflow_feedback_event"' in payload["feedbackText"]
    assert '"writes_long_term_memory": false' in payload["feedbackText"]

def test_web_memory_source_status_distinguishes_fixture_sample_and_selected_files() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { memoryWorkbenchFixture } from "./apps/web/memory-workbench-fixture.js";
import { buildMemoryWorkbenchPackageView } from "./apps/web/memory-workbench-package.js";
import { renderMemoryWorkbench } from "./apps/web/memory-workbench-render.js";
import { memoryWorkbenchSampleFiles } from "./apps/web/memory-workbench-sample.js";
import { readFile } from "node:fs/promises";

function sourceStatus(source, workspace) {
  const bundleCount = Array.isArray(workspace?.memoryBundle) ? workspace.memoryBundle.length : 0;
  if (source === "sample_bundle") return { label: "Sample bundle", detail: `${bundleCount} embedded sanitized memory artifacts loaded in browser memory.`, status: "review ready" };
  if (source === "selected_files" && bundleCount) return { label: "Selected files", detail: `${bundleCount} explicit local memory artifacts selected by the operator.`, status: "review ready" };
  return { label: "Fixture", detail: "Built-in static fixture only; select files or load the sample bundle for evidence-backed inspection.", status: "planned" };
}

function element(tagName) {
  return {
    tagName,
    className: "",
    children: [],
    dataset: {},
    _text: "",
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
    memorySourceStatus: element("div"),
    memoryProjectSummary: element("div"),
    memoryAssetSummary: element("div"),
    memoryBundleSummary: element("div"),
    memoryArtifactInspector: element("div"),
    memoryFeedbackPreview: element("div"),
    memoryFeedbackOutput: element("textarea"),
    memoryFeedbackStatus: element("p"),
    memoryFeedbackCopy: element("button"),
    memoryActionStrip: element("div"),
    memoryStateStrip: element("div"),
    memoryCanvasStage: element("div"),
    memoryLaneGrid: element("div"),
    memoryRunTimeline: element("div"),
    memoryProvenancePanel: element("div"),
  };
}

const copy = { statusLabels: {}, noDetails: "" };
const fixtureElements = elements();
renderMemoryWorkbench(fixtureElements, { ...memoryWorkbenchFixture, source_status: sourceStatus("fixture", normalizeWorkspace([])) }, copy);

const sampleWorkspace = normalizeWorkspace(await parseFiles(memoryWorkbenchSampleFiles()));
const sampleView = buildMemoryWorkbenchPackageView(sampleWorkspace, memoryWorkbenchFixture);
sampleView.source_status = sourceStatus("sample_bundle", sampleWorkspace);
const sampleElements = elements();
renderMemoryWorkbench(sampleElements, sampleView, copy);

const packageText = await readFile("examples/agentflow/memory_video_pipeline_package.example.json", "utf8");
const selectedWorkspace = normalizeWorkspace(await parseFiles([{ name: "memory_video_pipeline_package.example.json", text: async () => packageText }]));
const selectedView = buildMemoryWorkbenchPackageView(selectedWorkspace, memoryWorkbenchFixture);
selectedView.source_status = sourceStatus("selected_files", selectedWorkspace);
const selectedElements = elements();
renderMemoryWorkbench(selectedElements, selectedView, copy);

console.log(JSON.stringify({
  fixture: fixtureElements.memorySourceStatus.textContent,
  sample: sampleElements.memorySourceStatus.textContent,
  selected: selectedElements.memorySourceStatus.textContent,
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

    assert "Fixture" in payload["fixture"]
    assert "Built-in static fixture only" in payload["fixture"]
    assert "Sample bundle" in payload["sample"]
    assert "5 embedded sanitized memory artifacts" in payload["sample"]
    assert "Selected files" in payload["selected"]
    assert "1 explicit local memory artifacts" in payload["selected"]
