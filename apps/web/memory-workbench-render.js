import { clearNode, metaLine, node, row, statusPill } from "./render-helpers.js";
import { renderDemoReadyChecklist } from "./memory-workbench-demo-checklist-render.js";
import { renderDemoEvidenceSummary } from "./memory-workbench-demo-render.js";
import { renderActionStrip, renderOperatorDock, renderStudioStatus, renderToolbar } from "./memory-workbench-studio-render.js";

const LOOP_NODES = [
  { label: "Project", x: 1, y: 2 },
  { label: "Assets", x: 2, y: 1 },
  { label: "Memory Loaded", x: 3, y: 1 },
  { label: "Baseline Run", x: 4, y: 2 },
  { label: "Memory-backed Run", x: 4, y: 3 },
  { label: "Review", x: 5, y: 2 },
  { label: "Feedback", x: 6, y: 2 },
  { label: "Next Pass", x: 7, y: 1 },
];

const DEFAULT_FOCUS = "project";

export function renderMemoryWorkbench(elements, fixture, copy) {
  if (!elements.memoryWorkbench) return;
  const activeView = elements.memoryWorkbench.dataset.view || "flow";
  elements.memoryWorkbench.dataset.view = activeView;
  renderSummary(elements, fixture, copy);
  renderBundleSummary(elements, fixture, copy);
  renderArtifactInspector(elements, fixture, copy);
  renderFeedbackDraft(elements, fixture, copy);
  renderToolbar(elements);
  renderOperatorDock(elements, fixture, copy, focusMemoryInspector);
  renderActionStrip(elements, fixture, copy, focusMemoryInspector);
  renderDemoReadyChecklist(elements, fixture.demo_checklist, copy);
  renderDemoEvidenceSummary(elements, fixture.demo_summary, copy);
  renderStateStrip(elements, fixture, copy);
  renderCanvas(elements, fixture, copy);
  renderProtocolSummary(elements, fixture, copy);
  renderProvenance(elements, fixture, copy);
  renderTimeline(elements, fixture, copy);
  focusMemoryInspector(elements, DEFAULT_FOCUS, fixture);
}

function renderSummary(elements, fixture, copy) {
  clearNode(elements.memoryProjectSummary);
  const project = fixture.project;
  renderSourceStatus(elements, fixture, copy);
  renderStudioStatus(elements, fixture, copy);
  elements.memoryProjectSummary.append(
    metaLine(project.brief),
    metaLine(`Format: ${project.format}`),
    metaLine(`Route: ${project.route}`),
  );

  clearNode(elements.memoryAssetSummary);
  for (const asset of fixture.assets) {
    elements.memoryAssetSummary.append(row(asset.label, statusPill(asset.status, copy)), metaLine(asset.detail));
  }
}

function renderSourceStatus(elements, fixture, copy) {
  if (!elements.memorySourceStatus) return;
  const source = fixture.source_status || {};
  clearNode(elements.memorySourceStatus);
  elements.memorySourceStatus.append(
    row(source.label || "Fixture", statusPill(source.status || "planned", copy)),
    metaLine(source.detail || "Built-in static fixture only."),
  );
}

function renderBundleSummary(elements, fixture, copy) {
  if (!elements.memoryBundleSummary) return;
  clearNode(elements.memoryBundleSummary);
  for (const item of fixture.bundle_summary || []) {
    const card = node("article", "memory-bundle-card");
    card.append(row(item.title, statusPill(item.status, copy)), metaLine(item.detail));
    elements.memoryBundleSummary.append(card);
  }
}

function renderArtifactInspector(elements, fixture, copy) {
  if (!elements.memoryArtifactInspector) return;
  clearNode(elements.memoryArtifactInspector);
  for (const item of fixture.artifact_inspector || []) {
    const card = node("article", "memory-inspector-card");
    card.dataset.focusTargets = (item.focus_targets || []).join(" ");
    card.dataset.artifactType = item.artifact_type || "";
    card.append(row(item.title, statusPill(item.status, copy)), metaLine(item.detail));
    for (const fact of item.facts || []) {
      card.append(metaLine(`${fact.label}: ${fact.value}`));
    }
    elements.memoryArtifactInspector.append(card);
  }
}

function renderFeedbackDraft(elements, fixture, copy) {
  if (!elements.memoryFeedbackPreview) return;
  const draft = fixture.feedback_draft || {};
  clearNode(elements.memoryFeedbackPreview);
  elements.memoryFeedbackPreview.append(
    row(draft.title || "Feedback Draft Preview", statusPill(draft.status || "planned", copy)),
    metaLine(draft.detail || "Select memory artifacts to preview a feedback draft."),
  );

  if (elements.memoryFeedbackOutput) {
    elements.memoryFeedbackOutput.value = draft.json_text || "";
  }
  if (elements.memoryFeedbackStatus) {
    elements.memoryFeedbackStatus.textContent = draft.copy_enabled
      ? "Draft is browser-local and not persisted."
      : "Select a memory package before copying.";
  }
  if (!elements.memoryFeedbackCopy) return;
  elements.memoryFeedbackCopy.disabled = !draft.copy_enabled;
  elements.memoryFeedbackCopy.onclick = async () => {
    const text = elements.memoryFeedbackOutput?.value || "";
    if (!text) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        elements.memoryFeedbackStatus.textContent = "Copied feedback draft JSON.";
        return;
      }
    } catch (_error) {
      // Fall through to manual-copy hint.
    }
    elements.memoryFeedbackOutput?.focus();
    elements.memoryFeedbackOutput?.select();
    elements.memoryFeedbackStatus.textContent = "Clipboard unavailable; copy from the textarea.";
  };
}

function renderStateStrip(elements, fixture, copy) {
  clearNode(elements.memoryStateStrip);
  for (const label of fixture.state_labels) {
    const chip = node("span", `memory-state-chip${label === fixture.state ? " active" : ""}`, label);
    elements.memoryStateStrip.append(chip);
  }
}

function renderCanvas(elements, fixture, copy) {
  clearNode(elements.memoryCanvasStage);
  for (const item of LOOP_NODES) {
    const label = item.label;
    const focusKey = nodeClass(label);
    const block = node("button", `memory-node ${focusKey}`);
    block.type = "button";
    block.dataset.focusTarget = focusKey;
    block.title = `Focus ${label} evidence`;
    block.style?.setProperty?.("--node-x", item.x);
    block.style?.setProperty?.("--node-y", item.y);
    block.setAttribute("aria-pressed", "false");
    block.addEventListener("click", () => focusMemoryInspector(elements, focusKey, fixture));
    block.append(node("span", "memory-node-kicker", nodeKicker(label)), node("strong", "", label), metaLine(nodeDetail(label, fixture)));
    elements.memoryCanvasStage.append(block);
  }

  clearNode(elements.memoryLaneGrid);
  for (const lane of fixture.lanes) {
    const card = node("article", `memory-lane ${lane.id}`);
    card.append(row(lane.title, statusPill(lane.status, copy)), metaLine(`Input: ${lane.input}`), metaLine(`Output: ${lane.output}`));
    elements.memoryLaneGrid.append(card);
  }
}

function renderProtocolSummary(elements, fixture, copy) {
  if (!elements.memoryProtocolSummary) return;
  clearNode(elements.memoryProtocolSummary);
  const summary = fixture.protocol_summary || {};
  const header = node("article", "memory-protocol-card memory-protocol-header");
  header.append(row(summary.title || "Baseline parity protocol", statusPill(summary.status || "planned", copy)));
  elements.memoryProtocolSummary.append(header);
  for (const item of summary.controls || []) {
    const card = node("article", "memory-protocol-card");
    card.append(row(item.label, statusPill(item.status, copy)), metaLine(item.detail));
    elements.memoryProtocolSummary.append(card);
  }
  for (const item of summary.boundaries || []) {
    const card = node("article", "memory-protocol-card boundary");
    card.append(row(item.label, statusPill(item.status, copy)), metaLine(item.detail));
    elements.memoryProtocolSummary.append(card);
  }
}

function focusMemoryInspector(elements, focusKey, fixture = null) {
  const nodes = elements.memoryCanvasStage.querySelectorAll(".memory-node");
  for (const item of nodes) {
    const active = item.dataset.focusTarget === focusKey;
    item.classList.toggle("active", active);
    item.setAttribute("aria-pressed", String(active));
  }
  if (elements.memoryActionStrip) {
    const actions = elements.memoryActionStrip.querySelectorAll(".memory-action-step");
    for (const item of actions) {
      const active = item.dataset.focusTarget === focusKey;
      item.classList.toggle("active", active);
      item.setAttribute("aria-pressed", String(active));
    }
  }
  if (elements.memoryOperatorDock) {
    const steps = elements.memoryOperatorDock.querySelectorAll(".memory-operator-step");
    for (const item of steps) {
      const active = item.dataset.focusTarget === focusKey;
      item.classList.toggle("active", active);
      item.setAttribute("aria-pressed", String(active));
    }
  }
  renderFocusSummary(elements, focusKey, fixture);
  if (!elements.memoryArtifactInspector) return;
  const cards = elements.memoryArtifactInspector.querySelectorAll(".memory-inspector-card");
  let matched = false;
  for (const card of cards) {
    const targets = (card.dataset.focusTargets || "").split(" ").filter(Boolean);
    const active = targets.includes(focusKey);
    card.classList.toggle("active", active);
    matched = matched || active;
  }
  elements.memoryArtifactInspector.classList.toggle("has-focus", matched);
}

function renderFocusSummary(elements, focusKey, fixture) {
  if (!elements.memoryFocusSummary) return;
  clearNode(elements.memoryFocusSummary);
  const label = LOOP_NODES.find((item) => nodeClass(item.label) === focusKey)?.label || focusKey;
  elements.memoryFocusSummary.append(
    node("span", "memory-focus-kicker", "Focused node"),
    node("strong", "", label),
    metaLine(fixture ? nodeDetail(label, fixture) : "Select a canvas node to inspect its evidence."),
    metaLine("Click canvas nodes or workflow steps to focus related evidence only."),
  );
}

function renderProvenance(elements, fixture, copy) {
  clearNode(elements.memoryProvenancePanel);
  for (const memory of fixture.memory_loaded) {
    const card = node("article", "memory-provenance-card");
    card.append(
      row(memory.title, statusPill(memory.promotion_status, copy)),
      metaLine(`Loaded: ${memory.id}`),
      metaLine(`Eligible: ${memory.why_eligible}`),
      metaLine(`Evidence: ${memory.source_evidence_refs.join(" / ")}`),
      metaLine(`Request projection: ${memory.request_projection}`),
      metaLine(`Feedback effect: ${memory.feedback_effect}`),
    );
    elements.memoryProvenancePanel.append(card);
  }
}

function renderTimeline(elements, fixture, copy) {
  clearNode(elements.memoryRunTimeline);
  for (const item of fixture.timeline) {
    const step = node("article", "memory-timeline-step");
    step.append(row(item.label, statusPill(item.status, copy)), metaLine(item.detail));
    elements.memoryRunTimeline.append(step);
  }
}

function nodeClass(label) {
  return label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function nodeKicker(label) {
  if (label === "Baseline Run") return "stateless";
  if (label === "Memory-backed Run") return "context";
  if (label === "Memory Loaded") return "provenance";
  return "loop";
}

function nodeDetail(label, fixture) {
  if (label === "Project") return fixture.project.title;
  if (label === "Assets") return `${fixture.assets.length} reviewed assets`;
  if (label === "Memory Loaded") return `${fixture.memory_loaded.length} eligible memories`;
  if (label === "Baseline Run") return fixture.lanes[0].output;
  if (label === "Memory-backed Run") return fixture.lanes[1].output;
  if (label === "Review") return fixture.review.storyboard_adherence;
  if (label === "Feedback") return fixture.feedback.summary;
  return fixture.next_pass.action;
}
