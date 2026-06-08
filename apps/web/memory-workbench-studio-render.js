import { clearNode, metaLine, node, row, statusPill } from "./render-helpers.js";

export function renderStudioStatus(elements, fixture, copy) {
  if (!elements.memoryStudioStatus) return;
  clearNode(elements.memoryStudioStatus);
  for (const card of studioStatusCards(fixture)) {
    const item = node("article", "");
    item.append(
      node("span", "", card.label),
      node("strong", "", card.value),
      statusPill(card.status, copy),
      metaLine(card.detail),
    );
    elements.memoryStudioStatus.append(item);
  }
}

export function renderOperatorDock(elements, fixture, copy, focusMemoryInspector) {
  if (!elements.memoryOperatorDock) return;
  clearNode(elements.memoryOperatorDock);
  for (const item of operatorSteps(fixture)) {
    const button = node("button", `memory-operator-step ${item.intent}`);
    button.type = "button";
    button.dataset.focusTarget = item.focus_target;
    button.setAttribute("aria-pressed", "false");
    button.title = item.title;
    button.addEventListener("click", () => focusMemoryInspector(elements, item.focus_target, fixture));
    button.append(
      node("span", "memory-operator-index", item.index),
      node("strong", "", item.label),
      statusPill(item.status, copy),
      metaLine(item.detail),
    );
    elements.memoryOperatorDock.append(button);
  }
}

export function renderActionStrip(elements, fixture, copy, focusMemoryInspector) {
  if (!elements.memoryActionStrip) return;
  clearNode(elements.memoryActionStrip);
  for (const item of fixture.workflow_actions || []) {
    const button = node("button", "memory-action-step");
    button.type = "button";
    button.dataset.focusTarget = item.focus_target;
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => focusMemoryInspector(elements, item.focus_target, fixture));
    button.append(node("strong", "", item.label), statusPill(item.status, copy));
    elements.memoryActionStrip.append(button);
  }
}

export function renderToolbar(elements) {
  if (!elements.memoryViewButtons?.length) return;
  for (const button of elements.memoryViewButtons) {
    const active = (button.dataset.memoryView || "flow") === elements.memoryWorkbench.dataset.view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
    button.onclick = () => {
      elements.memoryWorkbench.dataset.view = button.dataset.memoryView || "flow";
      for (const item of elements.memoryViewButtons) {
        const itemActive = item === button;
        item.classList.toggle("active", itemActive);
        item.setAttribute("aria-pressed", String(itemActive));
      }
    };
  }
}

function studioStatusCards(fixture) {
  const assets = Array.isArray(fixture.assets) ? fixture.assets : [];
  const memories = Array.isArray(fixture.memory_loaded) ? fixture.memory_loaded : [];
  const blockedAssets = assets.filter((item) => item.status === "blocked").length;
  const boundaryCount = Array.isArray(fixture.protocol_summary?.boundaries)
    ? fixture.protocol_summary.boundaries.length
    : 0;
  return [
    {
      label: "Current view",
      value: fixture.state || "empty",
      status: fixture.state === "blocked" ? "blocked" : "review ready",
      detail: fixture.project?.format || "select explicit local JSON",
    },
    {
      label: "Assets",
      value: String(assets.length),
      status: blockedAssets ? "blocked" : "review ready",
      detail: blockedAssets ? `${blockedAssets} blocked assets` : "no blocked assets in current view",
    },
    {
      label: "Do not claim",
      value: `${boundaryCount} boundaries`,
      status: "blocked",
      detail: `${memories.length} context refs; acceptance, business validation, and durable memory remain separate.`,
    },
  ];
}

function operatorSteps(fixture) {
  const lanes = Array.isArray(fixture.lanes) ? fixture.lanes : [];
  const baseline = lanes.find((lane) => lane.id === "baseline-lane") || lanes[0] || {};
  const memory = lanes.find((lane) => lane.id === "memory-lane") || lanes[1] || {};
  return [
    {
      index: "01",
      intent: "brief",
      label: "Brief",
      focus_target: "project",
      status: fixture.project?.title ? "planned" : "blocked",
      title: "Focus the script, target format, and route evidence",
      detail: fixture.project?.format || "No protocol loaded.",
    },
    {
      index: "02",
      intent: "asset",
      label: "Assets",
      focus_target: "assets",
      status: fixture.assets?.length ? "planned" : "blocked",
      title: "Focus character and scene assets",
      detail: `${fixture.assets?.length || 0} reviewed assets`,
    },
    {
      index: "03",
      intent: "memory",
      label: "Memory",
      focus_target: "memory-loaded",
      status: fixture.memory_loaded?.length ? "review ready" : "blocked",
      title: "Focus loaded memory provenance",
      detail: `${fixture.memory_loaded?.length || 0} eligible memories`,
    },
    {
      index: "04",
      intent: "generate",
      label: "Generate",
      focus_target: "baseline-run",
      status: baseline.status || "planned",
      title: "Focus the no-call generation plan",
      detail: "No provider call from this browser surface.",
    },
    {
      index: "05",
      intent: "compare",
      label: "Compare",
      focus_target: "memory-backed-run",
      status: memory.status || "planned",
      title: "Focus Baseline versus Memory-backed evidence",
      detail: "Two lanes stay visible for parity review.",
    },
    {
      index: "06",
      intent: "feedback",
      label: "Feedback",
      focus_target: "feedback",
      status: fixture.feedback?.status || "planned",
      title: "Focus feedback and next-pass reuse",
      detail: fixture.next_pass?.action || "Capture operator feedback before reuse.",
    },
  ];
}
