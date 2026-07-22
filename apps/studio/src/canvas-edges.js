import { bindEdgeActionButton } from "./canvas-edge-actions.js";
import { edgeRelationLayer, pruneEdgeRelationButtons, syncEdgeRelationButton } from "./canvas-edge-relation-buttons.js";
import {
  edgeAccessibleLabel,
  edgeLifecycleState,
  edgeRelatedToFocus,
  relationLabel,
  syncEdgeRelationClass,
  syncEdgeStateClass,
} from "./canvas-edge-state.js";
import { bezier } from "./geometry.js";
import { nodeFramePortWorldPoint } from "./interaction/port-geometry.js";
import { effectiveHeight } from "./nodes.js";

const EDGE_OFFSET = 20000;

export function renderEdges(state, relations, store) {
  const group = edgeGroup("edges");
  const actionLayer = edgeRelationLayer();
  const seen = new Set();
  for (const edge of Object.values(state.edges)) {
    const from = state.nodes[edge.from];
    const to = state.nodes[edge.to];
    if (!from || !to) continue;
    seen.add(edge.id);
    const item = edgeElement(group, edge.id);
    syncEdgeElement(item, edge, from, to, state, relations, store);
    syncEdgeRelationButton(actionLayer, edge, from, to, state, store);
  }
  for (const item of [...group.children]) {
    if (!seen.has(item.dataset.edgeId)) item.remove();
  }
  pruneEdgeRelationButtons(actionLayer, seen);
}

function edgeElement(group, edgeId) {
  let item = group.querySelector(`[data-edge-id="${edgeId}"]`);
  if (item) return item;
  item = document.createElementNS("http://www.w3.org/2000/svg", "g");
  item.dataset.edgeId = edgeId;
  const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
  label.classList.add("edge-label");
  const hit = document.createElementNS("http://www.w3.org/2000/svg", "path");
  hit.classList.add("edge-hit");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.classList.add("edge-flow");
  const spark = document.createElementNS("http://www.w3.org/2000/svg", "path");
  spark.classList.add("edge-spark");
  const action = document.createElementNS("http://www.w3.org/2000/svg", "g");
  action.classList.add("edge-disconnect-button");
  action.setAttribute("role", "button");
  action.setAttribute("aria-label", "断开连线");
  action.innerHTML = '<circle r="12"></circle><path d="M-4 -4l8 8M4 -4l-8 8"></path>';
  item.append(hit, path, spark, label, action);
  group.appendChild(item);
  return item;
}

function syncEdgeElement(item, edge, from, to, state, relations, store) {
  const hit = item.querySelector("path.edge-hit");
  const path = item.querySelector("path.edge-flow");
  const spark = item.querySelector("path.edge-spark");
  const label = item.querySelector(".edge-label");
  const action = item.querySelector(".edge-disconnect-button");
  const start = nodeFramePortWorldPoint(from, "out", state.viewport)
    || { x: from.x + from.w, y: from.y + effectiveHeight(from) / 2 };
  const end = nodeFramePortWorldPoint(to, "in", state.viewport)
    || { x: to.x, y: to.y + effectiveHeight(to) / 2 };
  const x1 = start.x;
  const y1 = start.y;
  const x2 = end.x;
  const y2 = end.y;
  const relation = edge.relation_type || edge.relationType || "generation";
  const d = bezier(x1, y1, x2, y2);
  item.dataset.edgeFrom = edge.from || "";
  item.dataset.edgeTo = edge.to || "";
  item.dataset.edgeRelation = relation;
  hit.setAttribute("d", d);
  path.setAttribute("d", d);
  spark.setAttribute("d", d);
  path.classList.toggle("director-edge", relation === "director");
  path.classList.toggle("reference-edge", relation === "reference");
  path.classList.toggle("fork-edge", relation === "fork");
  path.classList.toggle("sequence-edge", relation === "sequence");
  path.classList.toggle("proposed-edge", relation === "proposed");
  path.classList.toggle("selected-edge", state.selection.edgeId === edge.id);
  path.classList.toggle("just-connected", state.ui?.lastConnectedEdgeId === edge.id);
  syncEdgeStateClass(path, item, edge, state);
  item.dataset.edgeSelected = state.selection.edgeId === edge.id ? "true" : "false";
  path.classList.remove("rel-up-edge", "rel-down-edge", "rel-dim-edge");
  item.setAttribute("aria-label", edgeAccessibleLabel(edge, from, to, relation));
  label.textContent = relationLabel(relation);
  label.setAttribute("x", String((x1 + x2) / 2));
  label.setAttribute("y", String((y1 + y2) / 2 - 8));
  label.classList.toggle("visible", Boolean(label.textContent));
  syncEdgeActionButton(action, item, edge, store, (x1 + x2) / 2, (y1 + y2) / 2, state.selection.edgeId === edge.id);
  syncEdgeRelationClass(path, edge, relations);
  syncEdgeSpark(spark, edge, state, relations);
}

function syncEdgeActionButton(action, item, edge, store, x, y, selected) {
  action.setAttribute("transform", `translate(${x}, ${y})`);
  action.style.opacity = selected ? "1" : "0";
  action.style.pointerEvents = selected ? "auto" : "none";
  action.setAttribute("aria-hidden", selected ? "false" : "true");
  bindEdgeActionButton(item, edge, store);
}

function syncEdgeSpark(spark, edge, state, relations) {
  const lifecycle = edgeLifecycleState(edge, state);
  const selected = state.selection.edgeId === edge.id;
  const relatedToFocus = edgeRelatedToFocus(edge, relations);
  const active = ["pending", "running", "recovery"].includes(lifecycle)
    || selected
    || relatedToFocus
    || state.ui?.lastConnectedEdgeId === edge.id;
  const reverse = lifecycle === "recovery";
  spark.classList.toggle("active", active);
  spark.classList.toggle("selected-path", selected || relatedToFocus);
  spark.classList.toggle("reverse", reverse);
  spark.dataset.lifecycle = lifecycle;
}

export function getPendingEdgeGroup() {
  return edgeGroup("pending");
}

function edgeGroup(role) {
  const svg = document.getElementById("edge-layer");
  let group = svg.querySelector(`g[data-role='${role}']`);
  if (!group) {
    group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.dataset.role = role;
    group.setAttribute("transform", `translate(${EDGE_OFFSET}, ${EDGE_OFFSET})`);
    svg.appendChild(group);
  }
  return group;
}
