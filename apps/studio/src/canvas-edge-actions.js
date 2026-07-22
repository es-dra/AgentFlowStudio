import { removeEdge } from "./nodes.js";

export function bindEdgeActionButton(item, edge, store) {
  if (!store || item.dataset.edgeActionBound === "true") return;
  item.dataset.edgeActionBound = "true";
  item.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    event.stopPropagation();
    const edgeId = item.dataset.edgeId || edge.id;
    if (event.target.closest?.(".edge-disconnect-button")) return;
    selectEdge(store, edgeId);
  });
  item.addEventListener("click", (event) => {
    const edgeId = item.dataset.edgeId || edge.id;
    if (!event.target.closest?.(".edge-disconnect-button")) {
      selectEdge(store, edgeId);
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    disconnectEdge(store, edgeId);
  });
}

export function selectEdge(store, edgeId) {
  if (!edgeId || !store.get().edges?.[edgeId]) return;
  store.set((state) => {
    state.selection = { nodeIds: [], edgeId };
  }, { history: false, persist: false, renderScope: "selection-context" });
}

export function disconnectEdge(store, edgeId) {
  removeEdge(store, edgeId);
}
