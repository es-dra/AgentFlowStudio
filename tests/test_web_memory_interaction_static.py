from __future__ import annotations

import json
import subprocess


def test_web_memory_canvas_nodes_focus_related_inspector_cards() -> None:
    script = """
import { renderMemoryWorkbench } from "./apps/web/memory-workbench-render.js";

function element(tagName) {
  return {
    tagName,
    className: "",
    children: [],
    dataset: {},
    attributes: {},
    listeners: {},
    _text: "",
    get classList() {
      const owner = this;
      return {
        toggle(name, force) {
          const classes = new Set(owner.className.split(/\\s+/).filter(Boolean));
          if (force) classes.add(name);
          else classes.delete(name);
          owner.className = [...classes].join(" ");
        },
        contains(name) {
          return owner.className.split(/\\s+/).includes(name);
        },
      };
    },
    set textContent(value) {
      this._text = value;
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
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
    getAttribute(name) {
      return this.attributes[name];
    },
    addEventListener(name, handler) {
      this.listeners[name] = handler;
    },
    querySelectorAll(selector) {
      const className = selector.startsWith(".") ? selector.slice(1) : "";
      const out = [];
      const visit = (node) => {
        if (className && node.className?.split(/\\s+/).includes(className)) out.push(node);
        for (const child of node.children || []) visit(child);
      };
      visit(this);
      return out;
    },
  };
}

globalThis.document = { createElement: element };

const elements = {
  memoryWorkbench: element("section"),
  memoryProjectSummary: element("div"),
  memoryAssetSummary: element("div"),
  memoryBundleSummary: element("div"),
  memoryArtifactInspector: element("div"),
  memoryOperatorDock: element("div"),
  memoryActionStrip: element("div"),
  memoryStateStrip: element("div"),
  memoryCanvasStage: element("div"),
  memoryLaneGrid: element("div"),
  memoryRunTimeline: element("div"),
  memoryProvenancePanel: element("div"),
};

const fixture = {
  state: "review ready",
  project: { brief: "brief", format: "format", route: "route", title: "title" },
  assets: [],
  bundle_summary: [],
  workflow_actions: [
    { id: "inspect_evidence", label: "Inspect evidence", focus_target: "review", status: "review ready" },
    { id: "capture_feedback", label: "Capture feedback", focus_target: "feedback", status: "feedback captured" },
  ],
  artifact_inspector: [
    { id: "review", artifact_type: "agentflow_memory_video_pipeline_review", focus_targets: ["review"], title: "Review artifact", status: "review ready", detail: "review", facts: [] },
    { id: "feedback", artifact_type: "agentflow_feedback_event", focus_targets: ["feedback"], title: "Feedback draft", status: "feedback captured", detail: "feedback", facts: [] },
    { id: "memory", artifact_type: "agentflow_memory_video_pipeline_package", focus_targets: ["memory-backed-run"], title: "Memory package", status: "review ready", detail: "memory", facts: [] },
  ],
  memory_loaded: [],
  lanes: [
    { id: "baseline-lane", title: "Baseline Run", status: "review ready", input: "in", output: "out" },
    { id: "memory-lane", title: "Memory-backed Run", status: "review ready", input: "in", output: "out" },
  ],
  review: { storyboard_adherence: "story", visual_consistency: "visual" },
  feedback: { summary: "feedback" },
  next_pass: { action: "next" },
  state_labels: ["review ready"],
  timeline: [],
};

renderMemoryWorkbench(elements, fixture, { statusLabels: {}, noDetails: "" });
const reviewNode = elements.memoryCanvasStage.querySelectorAll(".memory-node").find((node) => node.dataset.focusTarget === "review");
reviewNode.listeners.click();
const reviewAction = elements.memoryActionStrip.querySelectorAll(".memory-action-step").find((node) => node.dataset.focusTarget === "review");
const feedbackAction = elements.memoryActionStrip.querySelectorAll(".memory-action-step").find((node) => node.dataset.focusTarget === "feedback");
feedbackAction.listeners.click();
const operatorSteps = elements.memoryOperatorDock.querySelectorAll(".memory-operator-step");
const compareStep = operatorSteps.find((node) => node.textContent.includes("Compare"));
compareStep.listeners.click();
const memoryNode = elements.memoryCanvasStage.querySelectorAll(".memory-node").find((node) => node.dataset.focusTarget === "memory-backed-run");
const inspectorCards = elements.memoryArtifactInspector.querySelectorAll(".memory-inspector-card");
console.log(JSON.stringify({
  reviewNodePressedAfterReviewClick: reviewNode.getAttribute("aria-pressed"),
  reviewActionPressedAfterReviewClick: reviewAction.getAttribute("aria-pressed"),
  feedbackActionPressedAfterFeedbackClick: feedbackAction.getAttribute("aria-pressed"),
  operatorStepCount: operatorSteps.length,
  compareStepPressedAfterCompareClick: compareStep.getAttribute("aria-pressed"),
  memoryNodePressedAfterCompareClick: memoryNode.getAttribute("aria-pressed"),
  activeCards: inspectorCards.filter((card) => card.classList.contains("active")).map((card) => card.dataset.artifactType),
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

    assert payload["reviewNodePressedAfterReviewClick"] == "false"
    assert payload["reviewActionPressedAfterReviewClick"] == "false"
    assert payload["feedbackActionPressedAfterFeedbackClick"] == "false"
    assert payload["operatorStepCount"] == 6
    assert payload["compareStepPressedAfterCompareClick"] == "true"
    assert payload["memoryNodePressedAfterCompareClick"] == "true"
    assert payload["activeCards"] == ["agentflow_memory_video_pipeline_package"]
