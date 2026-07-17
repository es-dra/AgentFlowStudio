import { zoomAt } from "./geometry.js";
import { fitVisibleCanvasViewport, visibleCanvasCenter, visibleCanvasFrame } from "./canvas-safe-area.js";
import { deleteNodes, duplicateNode, removeEdge } from "./nodes.js";
import { canRunNodeGeneration, startNodeGeneration } from "./node-actions.js";
import { closeTop, hasOpenOverlay } from "./overlay.js";
import { openAddNodeMenu } from "./panels/add-node-menu.js";
import { openShortcutsPanel } from "./panels/shortcuts-panel.js";

export function bindStudioKeyboard({ store, runtime }) {
  window.addEventListener("keydown", (e) => {
    const editable = e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT" || e.target.isContentEditable;
    if (handleEscape(e, store)) return;
    if (editable) return;
    if (handleNodeCommands(e, store, runtime)) return;
    if (handleCanvasCommands(e, store, runtime)) return;
    if (e.key === "?") {
      e.preventDefault();
      openShortcutsPanel();
    }
  });
}

export function arrangeCanvas(store) {
  store.set((s) => {
    const gapX = 400;
    const gapY = 330;
    const layers = topologicalLayers(s);
    layers.forEach((ids, layerIndex) => {
      ids.forEach((id, rowIndex) => {
        const node = s.nodes[id];
        if (!node) return;
        node.x = layerIndex * gapX - 520;
        node.y = rowIndex * gapY - 180 - Math.floor(ids.length / 2) * 40;
      });
    });
    s.viewport = fitVisibleCanvasViewport(s.nodes);
  });
}

function handleEscape(e, store) {
  if (e.key !== "Escape") return false;
  if (hasOpenOverlay()) {
    closeTop("escape");
    return true;
  }
  if (store.get().selection.nodeIds.length || store.get().selection.edgeId) {
    store.set((s) => { s.selection = { nodeIds: [], edgeId: null }; }, { history: false, persist: false });
    return true;
  }
  if (!document.getElementById("drawer")) return false;
  store.set((s) => { s.ui.drawerOpen = !s.ui.drawerOpen; }, { history: false, persist: false });
  return true;
}

function handleNodeCommands(e, store, runtime) {
  if (handleSelectedEdgeDelete(e, store)) return true;
  if ((e.key === "Delete" || e.key === "Backspace") && store.get().selection.nodeIds.length) {
    deleteNodes(store, store.get().selection.nodeIds);
    return true;
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    const sel = store.get().selection.nodeIds;
    const node = sel.length === 1 ? store.get().nodes[sel[0]] : null;
    if (node && canRunNodeGeneration(node)) startNodeGeneration(store, runtime, node);
    return true;
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") {
    e.preventDefault();
    duplicateSelected(store);
    return true;
  }
  return false;
}

function handleSelectedEdgeDelete(e, store) {
  if (e.key !== "Delete" && e.key !== "Backspace") return false;
  const edgeId = store.get().selection.edgeId;
  if (!edgeId) return false;
  e.preventDefault();
  removeEdge(store, edgeId);
  return true;
}

function handleCanvasCommands(e, store, runtime) {
  if (e.key === "Tab") {
    e.preventDefault();
    openAddNodeMenu(store, runtime, visibleCanvasCenter());
    return true;
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
    e.preventDefault();
    if (e.shiftKey) store.redo();
    else store.undo();
    return true;
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
    e.preventDefault();
    store.redo();
    return true;
  }
  return handleViewportCommands(e, store);
}

function handleViewportCommands(e, store) {
  if ((e.ctrlKey || e.metaKey) && e.key === "0") {
    e.preventDefault();
    store.set((s) => {
      s.viewport = fitVisibleCanvasViewport(s.nodes);
    }, { history: false, persist: false });
    return true;
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "l") {
    e.preventDefault();
    arrangeCanvas(store);
    return true;
  }
  if ((e.ctrlKey || e.metaKey) && (e.key === "=" || e.key === "+")) {
    e.preventDefault();
    zoomCenter(store, 1.15);
    return true;
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "-") {
    e.preventDefault();
    zoomCenter(store, 1 / 1.15);
    return true;
  }
  return false;
}

function zoomCenter(store, factor) {
  const frame = visibleCanvasFrame();
  store.set((s) => {
    const left = frame.safeArea?.left || 0;
    const right = frame.safeArea?.right || 0;
    const top = frame.safeArea?.top || 0;
    const bottom = frame.safeArea?.bottom || 0;
    s.viewport = zoomAt(s.viewport, left + (frame.width - left - right) / 2, top + (frame.height - top - bottom) / 2, factor);
  }, { history: false, persist: false });
}

function topologicalLayers(state) {
  const upstreamOf = {};
  for (const edge of Object.values(state.edges)) {
    (upstreamOf[edge.to] = upstreamOf[edge.to] || []).push(edge.from);
  }
  const layerOf = {};
  const resolve = (id, depth = 0) => {
    if (layerOf[id] !== undefined) return layerOf[id];
    if (depth > 32) return 0;
    const ups = (upstreamOf[id] || []).filter((up) => state.nodes[up]);
    layerOf[id] = ups.length ? Math.max(...ups.map((up) => resolve(up, depth + 1))) + 1 : 0;
    return layerOf[id];
  };
  const connected = new Set(Object.values(state.edges).flatMap((e) => [e.from, e.to]));
  const layers = [];
  const isolated = [];
  for (const id of state.order) {
    if (!state.nodes[id]) continue;
    if (!connected.has(id)) { isolated.push(id); continue; }
    const layer = resolve(id);
    (layers[layer] = layers[layer] || []).push(id);
  }
  const result = layers.filter(Boolean);
  for (let i = 0; i < isolated.length; i += 3) result.push(isolated.slice(i, i + 3));
  return result;
}

function duplicateSelected(store) {
  const ids = [...store.get().selection.nodeIds];
  for (const id of ids) duplicateNode(store, id, 32, 32);
}
