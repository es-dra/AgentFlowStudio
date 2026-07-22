import { edgeAccessibleLabel, relationLabel } from "./canvas-edge-state.js";
import { nodeFramePortWorldPoint } from "./interaction/port-geometry.js";
import { effectiveHeight } from "./nodes.js";

export function edgeRelationLayer() {
  return document.getElementById("node-layer");
}

export function pruneEdgeRelationButtons(layer, seenEdgeIds) {
  if (!layer) return;
  for (const item of [...layer.children]) {
    if (item.classList?.contains("edge-relation-button") && !seenEdgeIds.has(item.dataset.edgeId)) {
      item.remove();
    }
  }
}

export function syncEdgeRelationButton(layer, edge, from, to, state, store) {
  if (!layer) return;
  const start = nodeFramePortWorldPoint(from, "out", state.viewport)
    || { x: from.x + from.w, y: from.y + effectiveHeight(from) / 2 };
  const end = nodeFramePortWorldPoint(to, "in", state.viewport)
    || { x: to.x, y: to.y + effectiveHeight(to) / 2 };
  const relation = edge.relation_type || edge.relationType || "generation";
  let button = layer.querySelector(`[data-edge-id="${edge.id}"]`);
  if (!button) {
    button = document.createElement("button");
    button.type = "button";
    button.className = "edge-relation-button";
    button.dataset.edgeId = edge.id;
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      store.set((draft) => {
        draft.selection = { nodeIds: [], edgeId: edge.id };
      }, { history: false, persist: false });
    });
    layer.appendChild(button);
  }
  syncEdgeRelationButtonContent(button, edge, from, to, relation, state);
  syncEdgeRelationButtonPosition(button, start, end);
}

function syncEdgeRelationButtonContent(button, edge, from, to, relation, state) {
  const label = relationLabel(relation) || "生成";
  button.dataset.edgeFrom = edge.from || "";
  button.dataset.edgeTo = edge.to || "";
  button.dataset.edgeRelation = relation;
  button.dataset.edgeSelected = state.selection.edgeId === edge.id ? "true" : "false";
  button.textContent = label;
  button.setAttribute("aria-label", edgeAccessibleLabel(edge, from, to, relation));
  button.title = `连线：${label}`;
}

function syncEdgeRelationButtonPosition(button, start, end) {
  button.style.left = "0";
  button.style.top = "0";
  button.style.transform = `translate(${(start.x + end.x) / 2}px, ${(start.y + end.y) / 2 - 8}px) translate(-50%, -50%)`;
}
