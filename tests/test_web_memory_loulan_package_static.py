from __future__ import annotations

import json
import subprocess


def test_web_memory_workbench_renders_selected_loulan_package() -> None:
    script = """
import { readFile } from "node:fs/promises";
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView } from "./apps/web/memory-workbench-controller.js";
import { renderMemoryWorkbench } from "./apps/web/memory-workbench-render.js";

function element(tagName) {
  return {
    tagName,
    className: "",
    children: [],
    dataset: {},
    style: { setProperty() {} },
    _text: "",
    _value: "",
    disabled: false,
    type: "",
    title: "",
    get classList() {
      return { toggle() {} };
    },
    set textContent(value) { this._text = String(value); },
    get textContent() { return [this._text, ...this.children.map((child) => child.textContent || "")].join(""); },
    set value(value) { this._value = String(value); },
    get value() { return this._value; },
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    setAttribute(name, value) { this[name] = String(value); },
    addEventListener() {},
    querySelectorAll() { return []; },
    querySelector() { return null; },
    focus() {},
    select() {},
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
    memoryDemoSummary: element("div"),
    memoryDemoChecklist: element("div"),
    memoryProtocolSummary: element("div"),
    memoryFocusSummary: element("div"),
    memoryOperatorDock: element("div"),
  };
}

const packageText = await readFile("examples/agentflow/loulan_memory_package.example.json", "utf8");
const workspace = normalizeWorkspace(await parseFiles([{ name: "loulan_memory_package.example.json", text: async () => packageText }]));
const view = buildMemoryWorkbenchView(workspace, "selected_files");
const nodes = elements();
renderMemoryWorkbench(nodes, view, { statusLabels: {}, noDetails: "" });

console.log(JSON.stringify({
  source: nodes.memorySourceStatus.textContent,
  project: nodes.memoryProjectSummary.textContent,
  assets: nodes.memoryAssetSummary.textContent,
  lanes: nodes.memoryLaneGrid.textContent,
  provenance: nodes.memoryProvenancePanel.textContent,
  feedback: nodes.memoryFeedbackOutput.value,
  protocol: nodes.memoryProtocolSummary.textContent,
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

    assert "Selected files" in payload["source"]
    assert "Loulan time-control scene asset project" in payload["project"]
    assert "horizontal_16_9" in payload["project"]
    assert "Zhou Tong school anchor" in payload["assets"]
    assert "approved" in payload["assets"]
    assert "Baseline Plan" in payload["lanes"]
    assert "Memory-backed Plan" in payload["lanes"]
    assert "character:zhou_tong_school_v1" in payload["provenance"]
    assert "blocked_until_api_workbench" in payload["protocol"]
    assert '"artifact_type": "agentflow_feedback_event"' in payload["feedback"]
    assert '"writes_long_term_memory": false' in payload["feedback"]


def test_web_memory_workbench_renders_loulan_api_workbench_plan() -> None:
    script = """
import { readFile } from "node:fs/promises";
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView } from "./apps/web/memory-workbench-controller.js";
import { renderMemoryWorkbench } from "./apps/web/memory-workbench-render.js";

function element(tagName) {
  return {
    tagName,
    className: "",
    children: [],
    dataset: {},
    style: { setProperty() {} },
    _text: "",
    _value: "",
    disabled: false,
    type: "",
    title: "",
    get classList() {
      return { toggle() {} };
    },
    set textContent(value) { this._text = String(value); },
    get textContent() { return [this._text, ...this.children.map((child) => child.textContent || "")].join(""); },
    set value(value) { this._value = String(value); },
    get value() { return this._value; },
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    setAttribute(name, value) { this[name] = String(value); },
    addEventListener() {},
    querySelectorAll() { return []; },
    querySelector() { return null; },
    focus() {},
    select() {},
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
    memoryDemoSummary: element("div"),
    memoryDemoChecklist: element("div"),
    memoryProtocolSummary: element("div"),
    memoryFocusSummary: element("div"),
    memoryOperatorDock: element("div"),
  };
}

const packageText = await readFile("examples/agentflow/loulan_memory_package.example.json", "utf8");
const apiPlanText = await readFile("examples/agentflow/loulan_api_workbench_plan.example.json", "utf8");
const workspace = normalizeWorkspace(await parseFiles([
  { name: "loulan_memory_package.example.json", text: async () => packageText },
  { name: "loulan_api_workbench_plan.example.json", text: async () => apiPlanText },
]));
const view = buildMemoryWorkbenchView(workspace, "selected_files");
const nodes = elements();
renderMemoryWorkbench(nodes, view, { statusLabels: {}, noDetails: "" });

console.log(JSON.stringify({
  bundle: nodes.memoryBundleSummary.textContent,
  protocol: nodes.memoryProtocolSummary.textContent,
  inspector: nodes.memoryArtifactInspector.textContent,
  timeline: nodes.memoryRunTimeline.textContent,
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

    assert "1 request previews" in payload["bundle"]
    assert "openai_compatible_image" in payload["protocol"]
    assert "pending_response" in payload["protocol"]
    assert "Loulan API workbench plan" in payload["inspector"]
    assert "provider_calls_started: false" in payload["inspector"]
    assert "API Workbench" in payload["timeline"]
