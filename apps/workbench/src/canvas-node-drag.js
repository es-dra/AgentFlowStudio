import {
  NODE_HEIGHT,
  NODE_WIDTH,
  cssEscape,
  edgePathBetween,
  nodeDragBases,
  nodePositionFromDom,
  normalizedZoom,
  selectedDragIdsForNode,
  snapToGrid,
} from "./canvas-interaction-geometry.js";

let nodeDragState = null;

export function beginNodeDrag(handle, event, state) {
  event.preventDefault();
  event.stopPropagation();
  const node = handle.closest(".libtv-node");
  if (!node) return;
  const nodeId = handle.getAttribute("data-node-drag-handle") || node.dataset.nodeId || "";
  const stage = handle.closest("[data-canvas-surface]");
  const groupNodes = stage ? nodesForGroupDrag(stage, state, nodeId) : [{ id: nodeId, node, ...nodePositionFromDom(node) }];
  nodeDragState = {
    id: event.pointerId,
    nodeId,
    groupNodes,
    stage,
    startX: event.clientX,
    startY: event.clientY,
    dx: 0,
    dy: 0,
  };
  state.draggedNodeId = nodeId;
  state.selectedCardId = nodeId || state.selectedCardId;
  state.selectedNodeIds = groupNodes.length > 1 ? groupNodes.map((item) => item.id) : (nodeId ? [nodeId] : state.selectedNodeIds);
  groupNodes.forEach((item) => item.node.classList.add("is-dragging"));
  node.setPointerCapture?.(event.pointerId);
}

export function isNodeDragging(pointerId) {
  return Boolean(nodeDragState && nodeDragState.id === pointerId);
}

export function moveNodeDrag(event, state) {
  if (!isNodeDragging(event.pointerId)) return;
  const zoom = normalizedZoom(state);
  nodeDragState.dx = snapToGrid(((event.clientX - nodeDragState.startX) / zoom) * 0.84);
  nodeDragState.dy = snapToGrid(((event.clientY - nodeDragState.startY) / zoom) * 0.84);
  nodeDragState.groupNodes.forEach((item) => {
    item.node.style.transform = `translate3d(${nodeDragState.dx}px, ${nodeDragState.dy}px, 0)`;
  });
  updateConnectedEdgesDuringDrag();
}

export function endNodeDrag(pointerId, state, repaint) {
  if (!isNodeDragging(pointerId)) return false;
  const nextPositions = {};
  nodeDragState.groupNodes.forEach((item) => {
    nextPositions[item.id] = {
      x: snapToGrid(item.x + nodeDragState.dx),
      y: snapToGrid(item.y + nodeDragState.dy),
    };
  });
  const viewportShift = safeViewportShift(nodeDragState.stage, nodeDragState.groupNodes);
  if (viewportShift.x || viewportShift.y) {
    state.canvasPanX = Math.round(Number(state.canvasPanX || 0) + viewportShift.x);
    state.canvasPanY = Math.round(Number(state.canvasPanY || 0) + viewportShift.y);
  }
  nodeDragState.groupNodes.forEach((item) => {
    item.node.classList.remove("is-dragging");
    item.node.style.transform = "";
  });
  state.canvasNodePositions = {
    ...(state.canvasNodePositions || {}),
    ...nextPositions,
  };
  nodeDragState = null;
  state.draggedNodeId = "";
  repaint();
  return true;
}

function nodesForGroupDrag(stage, state, nodeId) {
  const ids = selectedDragIdsForNode(state, nodeId);
  return nodeDragBases(stage, ids);
}

function updateConnectedEdgesDuringDrag() {
  if (!nodeDragState?.stage) return;
  nodeDragState.stage.querySelectorAll(".studio-canvas-edge.connected[data-linked-node-id]").forEach((edge) => {
    const [from, to] = String(edge.getAttribute("data-linked-node-id") || "").split(":");
    if (!from || !to || !dragTouchesEdge(from, to)) return;
    const start = portPoint(from, "output");
    const end = portPoint(to, "input");
    if (start && end) edge.setAttribute("d", edgePathBetween(start, end));
  });
}

function dragTouchesEdge(from, to) {
  return nodeDragState.groupNodes.some((item) => item.id === from || item.id === to);
}

function portPoint(id, side) {
  const dragged = nodeDragState.groupNodes.find((item) => item.id === id);
  const node = dragged ? null : nodeDragState.stage.querySelector(`[data-node-id="${cssEscape(id)}"]`);
  const position = dragged ? { x: dragged.x + nodeDragState.dx, y: dragged.y + nodeDragState.dy } : (node ? nodePositionFromDom(node) : null);
  if (!position) return null;
  return { x: position.x + (side === "output" ? NODE_WIDTH : 0), y: position.y + NODE_HEIGHT / 2 };
}

function safeViewportShift(stage, nodes) {
  if (!stage || !nodes.length) return { x: 0, y: 0 };
  const rects = nodes.map((item) => item.node.getBoundingClientRect());
  const stageRect = stage.getBoundingClientRect();
  const topbar = document.querySelector(".libtv-topbar, .canvas-topbar");
  const dock = document.querySelector(".libtv-bottom-bar");
  const safe = {
    left: stageRect.left + 18,
    right: stageRect.right - 18,
    top: (topbar?.getBoundingClientRect().bottom || stageRect.top) + 18,
    bottom: (dock?.getBoundingClientRect().top || stageRect.bottom) - 18,
  };
  const bounds = {
    left: Math.min(...rects.map((rect) => rect.left)),
    right: Math.max(...rects.map((rect) => rect.right)),
    top: Math.min(...rects.map((rect) => rect.top)),
    bottom: Math.max(...rects.map((rect) => rect.bottom)),
  };
  return {
    x: bounds.left < safe.left ? safe.left - bounds.left : bounds.right > safe.right ? safe.right - bounds.right : 0,
    y: bounds.top < safe.top ? safe.top - bounds.top : bounds.bottom > safe.bottom ? safe.bottom - bounds.bottom : 0,
  };
}
