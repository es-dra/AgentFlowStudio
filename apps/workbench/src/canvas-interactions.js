import {
  NODE_HEIGHT, NODE_WIDTH, ZOOM_STEP, canvasTransformStyle, clamp,
  connectionTargetAt, cssEscape, edgePathBetween, nodeInputPointFromDom, nodeOutputPointFromDom,
  pointerToWorld, rectsIntersect, snapToGrid, zoomCanvas, zoomPercent,
} from "./canvas-interaction-geometry.js";
import { beginNodeDrag, endNodeDrag, isNodeDragging, moveNodeDrag } from "./canvas-node-drag.js";
import { centerCanvasOnNode, centerCanvasOnSelection, fitCanvasToNodes, resetCanvasViewport } from "./canvas-viewport-actions.js";
export { canvasTransformStyle, snapToGrid, zoomPercent };
const MARQUEE_DELAY_MS = 180;
const PAN_THRESHOLD_PX = 5;
let pointerState = null;
let connectionState = null;
let marqueeElement = null;
export function bindCanvasInteractions(root, state, repaint) {
  const stage = root.querySelector("[data-canvas-surface]");
  if (!stage) return;
  stage.addEventListener("dblclick", (event) => {
    if (isCanvasControl(event.target)) return;
    event.preventDefault();
    const point = pointerToWorld(stage, event, state);
    state.pendingNodePosition = { x: snapToGrid(point.x - NODE_WIDTH / 2), y: snapToGrid(point.y - NODE_HEIGHT / 2) };
    state.canvasAddMenuScreenX = clamp(event.clientX, 12, window.innerWidth - 310);
    state.canvasAddMenuScreenY = clamp(event.clientY, 12, window.innerHeight - 660);
    state.studioPanel = "add";
    repaint();
  });
  stage.addEventListener("pointerdown", (event) => {
    const connector = event.target?.closest?.("[data-connect-from]");
    if (connector) {
      beginConnection(stage, connector, event, state);
      return;
    }

    const handle = event.target?.closest?.("[data-node-drag-handle]");
    if (handle) {
      beginNodeDrag(handle, event, state);
      return;
    }

    if (event.button !== 0 || isCanvasControl(event.target)) return;
    beginCanvasPointer(stage, event, state);
  });
  stage.addEventListener("pointermove", (event) => {
    if (connectionState && connectionState.id === event.pointerId) {
      moveConnection(stage, event, state);
      return;
    }
    if (isNodeDragging(event.pointerId)) {
      moveNodeDrag(event, state);
      return;
    }
    if (!pointerState || pointerState.id !== event.pointerId) return;
    moveCanvasPointer(stage, event, state);
  });
  stage.addEventListener("pointerup", (event) => {
    const connectionEnded = endConnection(stage, event, state, repaint);
    const nodeDragEnded = endNodeDrag(event.pointerId, state, repaint);
    const canvasEnded = endCanvasPointer(stage, event, state, repaint);
    if (!connectionEnded && !nodeDragEnded && !canvasEnded) return;
  });
  stage.addEventListener("pointercancel", (event) => {
    cancelConnection(stage, event.pointerId, state, repaint);
    endNodeDrag(event.pointerId, state, repaint);
    endCanvasPointer(stage, event, state, repaint);
  });
  stage.addEventListener("wheel", (event) => {
    if (isCanvasControl(event.target)) return;
    event.preventDefault();
    zoomCanvas(state, event.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP);
    repaint();
  }, { passive: false });
  root.querySelectorAll("[data-canvas-action]").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.dataset.canvasAction === "zoom-in") zoomCanvas(state, ZOOM_STEP);
      if (node.dataset.canvasAction === "zoom-out") zoomCanvas(state, -ZOOM_STEP);
      if (node.dataset.canvasAction === "zoom-reset") resetCanvasViewport(state);
      if (node.dataset.canvasAction === "fit-view") fitCanvasToNodes(state);
      if (node.dataset.canvasAction === "center-selection") centerCanvasOnSelection(state);
      if (node.dataset.canvasAction === "center-node") centerCanvasOnNode(state, node.dataset.canvasNodeId || state.selectedCardId);
      repaint();
    });
  });
  root.querySelectorAll("[data-linked-node-id]").forEach((node) => {
    node.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      selectCanvasEdge(node.getAttribute("data-linked-node-id") || "", state);
      repaint();
    });
  });
}
function beginCanvasPointer(stage, event, state) {
  clearPointerTimer();
  pointerState = {
    id: event.pointerId,
    mode: "pending",
    startX: event.clientX,
    startY: event.clientY,
    x: event.clientX,
    y: event.clientY,
    startTime: Date.now(),
    timer: window.setTimeout(() => {
      if (!pointerState || pointerState.id !== event.pointerId || pointerState.mode !== "pending") return;
      pointerState.mode = "marquee";
      stage.classList.add("is-selecting");
      marqueeElement = ensureMarquee(stage);
      updateMarquee(event.clientX, event.clientY);
    }, MARQUEE_DELAY_MS),
  };
  stage.setPointerCapture?.(event.pointerId);
}
function moveCanvasPointer(stage, event, state) {
  if (pointerState.mode === "pending") {
    if (Date.now() - pointerState.startTime >= MARQUEE_DELAY_MS) {
      clearPointerTimer();
      pointerState.mode = "marquee";
      stage.classList.add("is-selecting");
      marqueeElement = ensureMarquee(stage);
      updateMarquee(event.clientX, event.clientY);
    }
    const distance = Math.hypot(event.clientX - pointerState.startX, event.clientY - pointerState.startY);
    if (pointerState.mode === "pending" && distance > PAN_THRESHOLD_PX) {
      clearPointerTimer();
      pointerState.mode = "pan";
      stage.classList.add("is-panning");
    }
  }

  if (pointerState.mode === "pan") {
    const dx = event.clientX - pointerState.x;
    const dy = event.clientY - pointerState.y;
    pointerState.x = event.clientX;
    pointerState.y = event.clientY;
    state.canvasPanX = Math.round(Number(state.canvasPanX || 0) + dx);
    state.canvasPanY = Math.round(Number(state.canvasPanY || 0) + dy);
    updateCanvasTransform(stage, state);
    return;
  }

  if (pointerState.mode === "marquee") {
    updateMarquee(event.clientX, event.clientY);
  }
}

function endCanvasPointer(stage, event, state, repaint) {
  if (!pointerState || pointerState.id !== event.pointerId) return false;
  clearPointerTimer();
  const wasMarquee = pointerState.mode === "marquee";
  const wasPan = pointerState.mode === "pan";
  if (wasMarquee) {
    state.selectedNodeIds = selectedNodesInMarquee(stage);
    state.selectedCardId = state.selectedNodeIds[0] || state.selectedCardId;
  }
  pointerState = null;
  stage.classList.remove("is-panning", "is-selecting");
  removeMarquee();
  if (wasMarquee) repaint();
  return wasMarquee || wasPan;
}

function beginConnection(stage, connector, event, state) {
  event.preventDefault();
  event.stopPropagation();
  const from = connector.getAttribute("data-connect-from") || "";
  if (!from) return;
  const point = pointerToWorld(stage, event, state);
  connectionState = { id: event.pointerId, from };
  state.connectingFromNodeId = from;
  state.connectionDraft = { from, x: point.x, y: point.y };
  stage.classList.add("is-connecting");
  stage.setPointerCapture?.(event.pointerId);
  updatePendingEdge(stage, state);
}

function moveConnection(stage, event, state) {
  const point = pointerToWorld(stage, event, state);
  const target = connectionTargetAt(stage, event.clientX, event.clientY, connectionState.from);
  const targetNodeId = target?.getAttribute?.("data-connect-to") || "";
  const endpoint = target ? nodeInputPointFromDom(target) : point;
  state.connectionDraft = { from: connectionState.from, x: endpoint.x, y: endpoint.y, targetNodeId };
  setConnectionTarget(stage, targetNodeId);
  updatePendingEdge(stage, state);
}

function endConnection(stage, event, state, repaint) {
  if (!connectionState || connectionState.id !== event.pointerId) return false;
  const target = connectionTargetAt(stage, event.clientX, event.clientY, connectionState.from);
  const to = state.connectionDraft?.targetNodeId || target?.getAttribute?.("data-connect-to") || "";
  if (to && to !== connectionState.from) {
    addCanvasEdge(state, connectionState.from, to);
    state.lastConnectedEdgeKey = `${connectionState.from}:${to}`;
  }
  state.selectedCardId = to || state.selectedCardId;
  if (to) state.selectedNodeIds = [to];
  clearConnection(stage, state);
  repaint();
  return true;
}

function cancelConnection(stage, pointerId, state, repaint) {
  if (!connectionState || connectionState.id !== pointerId) return false;
  clearConnection(stage, state);
  repaint();
  return true;
}

function clearConnection(stage, state) {
  connectionState = null;
  state.connectingFromNodeId = "";
  state.connectionDraft = null;
  setConnectionTarget(stage, "");
  stage.classList.remove("is-connecting");
}

function setConnectionTarget(stage, targetNodeId) {
  stage.querySelectorAll(".canvas-connection-target").forEach((node) => node.classList.remove("canvas-connection-target"));
  if (!targetNodeId) return;
  stage.querySelector(`[data-node-id="${cssEscape(targetNodeId)}"]`)?.classList.add("canvas-connection-target");
}

function addCanvasEdge(state, from, to) {
  const edges = Array.isArray(state.canvasEdges) ? state.canvasEdges : [];
  if (edges.some((edge) => edge.from === from && edge.to === to)) return;
  state.canvasEdges = [...edges, { from, to }];
}

function selectCanvasEdge(edgeKey, state) {
  const [from, to] = edgeKey.split(":");
  if (!from || !to) return;
  state.selectedEdgeKey = edgeKey;
  state.selectedNodeIds = [from, to];
  state.selectedCardId = to;
}

function updateCanvasTransform(stage, state) {
  stage.querySelectorAll("[data-canvas-content]").forEach((node) => {
    node.style.transform = canvasTransformStyle(state).replace("transform: ", "").replace(";", "");
  });
}

function updatePendingEdge(stage, state) {
  let edge = stage.querySelector(".studio-canvas-edge.pending");
  if (!state.connectionDraft) return;
  if (!edge) {
    const svg = stage.querySelector(".studio-edge-layer");
    if (!svg) return;
    edge = document.createElementNS("http://www.w3.org/2000/svg", "path");
    edge.setAttribute("class", "studio-canvas-edge pending");
    svg.append(edge);
  }
  const source = stage.querySelector(`[data-node-id="${cssEscape(state.connectionDraft.from)}"]`);
  const start = source ? nodeOutputPointFromDom(source) : { x: 0, y: 0 };
  edge.setAttribute("class", `studio-canvas-edge pending${state.connectionDraft.targetNodeId ? " target-locked" : ""}`);
  edge.setAttribute("d", edgePathBetween(start, state.connectionDraft));
}

function ensureMarquee(stage) {
  const existing = stage.querySelector(".canvas-marquee");
  if (existing) return existing;
  const node = document.createElement("div");
  node.className = "canvas-marquee";
  node.setAttribute("data-canvas-marquee", "true");
  stage.append(node);
  return node;
}

function updateMarquee(x, y) {
  if (!pointerState || !marqueeElement) return;
  const left = Math.min(pointerState.startX, x);
  const top = Math.min(pointerState.startY, y);
  const width = Math.abs(x - pointerState.startX);
  const height = Math.abs(y - pointerState.startY);
  marqueeElement.style.left = `${left}px`;
  marqueeElement.style.top = `${top}px`;
  marqueeElement.style.width = `${width}px`;
  marqueeElement.style.height = `${height}px`;
}

function selectedNodesInMarquee(stage) {
  if (!marqueeElement) return [];
  const marquee = marqueeElement.getBoundingClientRect();
  return [...stage.querySelectorAll("[data-node-id]")]
    .filter((node) => rectsIntersect(marquee, node.getBoundingClientRect()))
    .map((node) => node.getAttribute("data-node-id"))
    .filter(Boolean);
}

function removeMarquee() {
  marqueeElement?.remove();
  marqueeElement = null;
}

function clearPointerTimer() {
  if (pointerState?.timer) window.clearTimeout(pointerState.timer);
}

function isCanvasControl(target) {
  return Boolean(target?.closest?.("button, input, textarea, select, .libtv-node, .libtv-script-flow, .libtv-character-flow, .libtv-image-video-flow, .libtv-audio-video-flow, .libtv-director-flow, .director-desk-board, .libtv-floating, .libtv-side-panel, .libtv-bottom-bar, .libtv-topbar, .canvas-topbar, .canvas-marquee"));
}
