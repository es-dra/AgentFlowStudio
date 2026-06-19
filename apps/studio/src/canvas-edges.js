import { bindEdgeActionButton } from "./canvas-edge-actions.js";
import { bezier } from "./geometry.js";
import { nodeFramePortWorldPoint } from "./interaction/port-geometry.js";
import { effectiveHeight } from "./nodes.js";

const EDGE_OFFSET = 20000;

export function renderEdges(state, relations, store) {
  const group = edgeGroup("edges");
  const seen = new Set();
  for (const edge of Object.values(state.edges)) {
    const from = state.nodes[edge.from];
    const to = state.nodes[edge.to];
    if (!from || !to) continue;
    seen.add(edge.id);
    const item = edgeElement(group, edge.id);
    syncEdgeElement(item, edge, from, to, state, relations, store);
  }
  for (const item of [...group.children]) {
    if (!seen.has(item.dataset.edgeId)) item.remove();
  }
}

function edgeElement(group, edgeId) {
  let item = group.querySelector(`[data-edge-id="${edgeId}"]`);
  if (item) return item;
  item = document.createElementNS("http://www.w3.org/2000/svg", "g");
  item.dataset.edgeId = edgeId;
  const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
  label.classList.add("edge-label");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.classList.add("edge-flow");
  const spark = document.createElementNS("http://www.w3.org/2000/svg", "path");
  spark.classList.add("edge-spark");
  const action = document.createElementNS("http://www.w3.org/2000/svg", "g");
  action.classList.add("edge-disconnect-button");
  action.setAttribute("role", "button");
  action.setAttribute("aria-label", "断开连线");
  action.innerHTML = '<circle r="12"></circle><path d="M-4 -4l8 8M4 -4l-8 8"></path>';
  item.append(path, spark, label, action);
  group.appendChild(item);
  return item;
}

function syncEdgeElement(item, edge, from, to, state, relations, store) {
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
  path.setAttribute("d", d);
  spark.setAttribute("d", d);
  path.classList.toggle("director-edge", relation === "director");
  path.classList.toggle("reference-edge", relation === "reference");
  path.classList.toggle("selected-edge", state.selection.edgeId === edge.id);
  path.classList.toggle("just-connected", state.ui.lastConnectedEdgeId === edge.id);
  item.dataset.edgeSelected = state.selection.edgeId === edge.id ? "true" : "false";
  path.classList.remove("rel-up-edge", "rel-down-edge", "rel-dim-edge");
  label.textContent = relation === "director" ? "导演台" : relation === "reference" ? "参考" : "";
  label.setAttribute("x", String((x1 + x2) / 2));
  label.setAttribute("y", String((y1 + y2) / 2 - 8));
  label.classList.toggle("visible", Boolean(label.textContent));
  syncEdgeActionButton(action, item, edge, store, (x1 + x2) / 2, (y1 + y2) / 2, state.selection.edgeId === edge.id);
  syncEdgeRelationClass(path, edge, relations);
  syncEdgeSpark(spark, edge, state);
}

function syncEdgeActionButton(action, item, edge, store, x, y, selected) {
  action.setAttribute("transform", `translate(${x}, ${y})`);
  action.style.opacity = selected ? "1" : "";
  action.style.pointerEvents = selected ? "auto" : "";
  bindEdgeActionButton(item, edge, store);
}

function syncEdgeSpark(spark, edge, state) {
  const selected = new Set(state.selection.nodeIds || []);
  const touchesSelection = selected.has(edge.from) || selected.has(edge.to) || state.selection.edgeId === edge.id;
  const reverse = selected.has(edge.to) && !selected.has(edge.from);
  spark.classList.toggle("active", touchesSelection);
  spark.classList.toggle("reverse", reverse);
}

function syncEdgeRelationClass(path, edge, relations) {
  if (!relations) return;
  const upSide = (relations.upstream.has(edge.from) || edge.from === relations.focus)
    && (relations.upstream.has(edge.to) || edge.to === relations.focus);
  const downSide = (relations.downstream.has(edge.to) || edge.to === relations.focus)
    && (relations.downstream.has(edge.from) || edge.from === relations.focus);
  if (edge.to === relations.focus || (upSide && relations.upstream.has(edge.from))) path.classList.add("rel-up-edge");
  else if (edge.from === relations.focus || (downSide && relations.downstream.has(edge.to))) path.classList.add("rel-down-edge");
  else path.classList.add("rel-dim-edge");
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
