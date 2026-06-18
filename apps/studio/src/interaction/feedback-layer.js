import { worldToScreen } from "../geometry.js";
import { MOTION, prefersReducedMotion } from "./motion-tokens.js";

export function beginDragFeedback(rootEl, session) {
  ensureFeedbackLayer(rootEl);
  rootEl.classList.add("interaction-drag-active");
  setIncidentEdgesDragging(session.nodeIds, true);
  for (const id of session.nodeIds || []) {
    const nodeEl = nodeElement(id);
    nodeEl?.classList.add("drag-moving");
    nodeEl?.classList.toggle("drag-primary", id === session.primaryId);
  }
}

export function updateDragFeedback(rootEl, state, result) {
  const layer = ensureFeedbackLayer(rootEl);
  syncGuide(layer, state, result?.guides?.find((guide) => guide.axis === "x"), "x");
  syncGuide(layer, state, result?.guides?.find((guide) => guide.axis === "y"), "y");
  syncChip(layer, state, result);
}

export function finishDragFeedback(rootEl, session, options = {}) {
  const layer = ensureFeedbackLayer(rootEl);
  rootEl.classList.remove("interaction-drag-active");
  setIncidentEdgesDragging(session.nodeIds, false);
  clearGuides(layer);
  for (const id of session.nodeIds || []) {
    const nodeEl = nodeElement(id);
    if (!nodeEl) continue;
    nodeEl.classList.remove("drag-moving", "drag-primary");
    if (options.land && !prefersReducedMotion()) {
      nodeEl.classList.add("drag-landed");
      setTimeout(() => nodeEl.classList.remove("drag-landed"), MOTION.dragLandMs + 40);
    }
  }
}

export function pulseConnectionSource(nodeId, active) {
  nodeElement(nodeId)?.classList.toggle("connection-source", Boolean(active));
}

export function setIncidentEdgesDragging(nodeIds = [], active = false) {
  const ids = new Set(nodeIds);
  if (!ids.size) return;
  for (const edgeEl of document.querySelectorAll("#edge-layer [data-edge-id]")) {
    const edgeId = edgeEl.dataset.edgeId || "";
    const incident = [...ids].some((id) => edgeId.includes(`_${id}__`) || edgeId.endsWith(`__${id}`));
    edgeEl.classList.toggle("drag-incident-edge", Boolean(active && incident));
  }
}

function ensureFeedbackLayer(rootEl) {
  let layer = rootEl.querySelector("#interaction-feedback-layer");
  if (layer) return layer;
  layer = document.createElement("div");
  layer.id = "interaction-feedback-layer";
  layer.innerHTML = [
    '<div class="if-guide if-guide-x" data-axis="x"></div>',
    '<div class="if-guide if-guide-y" data-axis="y"></div>',
    '<div class="if-snap-chip"></div>',
  ].join("");
  rootEl.appendChild(layer);
  return layer;
}

function syncGuide(layer, state, guide, axis) {
  const el = layer.querySelector(`[data-axis="${axis}"]`);
  if (!guide) {
    el.classList.remove("visible");
    return;
  }
  const screen = worldToScreen(state.viewport, guide.axis === "x" ? guide.value : 0, guide.axis === "y" ? guide.value : 0);
  el.style.transform = axis === "x" ? `translateX(${screen.x}px)` : `translateY(${screen.y}px)`;
  el.classList.add("visible");
}

function syncChip(layer, state, result) {
  const chip = layer.querySelector(".if-snap-chip");
  if (!result?.primaryPosition || result.kind === "none") {
    chip.classList.remove("visible");
    return;
  }
  const point = worldToScreen(state.viewport, result.primaryPosition.x, result.primaryPosition.y);
  chip.textContent = result.kind === "align" ? "Align snap" : "Grid snap";
  chip.style.transform = `translate(${point.x + 12}px, ${point.y - 32}px)`;
  chip.classList.add("visible");
  chip.dataset.kind = result.kind;
}

function clearGuides(layer) {
  for (const el of layer.querySelectorAll(".if-guide, .if-snap-chip")) {
    el.classList.remove("visible");
  }
}

function nodeElement(id) {
  return document.querySelector(`[data-node-id="${id}"]`);
}
