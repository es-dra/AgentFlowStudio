export const DEFAULT_ZOOM = 1;
export const MIN_ZOOM = 0.55;
export const MAX_ZOOM = 1.6;
export const ZOOM_STEP = 0.1;
export const NODE_WIDTH = 330;
export const NODE_HEIGHT = 224;
export const CONNECT_GRID_SIZE = 12;

export function canvasTransformStyle(state) {
  const x = Math.round(Number(state?.canvasPanX || 0));
  const y = Math.round(Number(state?.canvasPanY || 0));
  const zoom = normalizedZoom(state);
  return `transform: translate3d(${x}px, ${y}px, 0) scale(${zoom});`;
}

export function zoomPercent(state) {
  return `${Math.round(normalizedZoom(state) * 100)}%`;
}

export function snapToGrid(value) {
  return Math.round(Number(value || 0) / CONNECT_GRID_SIZE) * CONNECT_GRID_SIZE;
}

export function zoomCanvas(state, delta) {
  state.canvasZoom = clamp(Math.round((normalizedZoom(state) + delta) * 100) / 100, MIN_ZOOM, MAX_ZOOM);
}

export function normalizedZoom(state) {
  return clamp(Number(state?.canvasZoom || DEFAULT_ZOOM), MIN_ZOOM, MAX_ZOOM);
}

export function pointerToWorld(stage, event, state) {
  const rect = stage.getBoundingClientRect();
  const zoom = normalizedZoom(state);
  return {
    x: (event.clientX - rect.left - Number(state.canvasPanX || 0)) / zoom,
    y: (event.clientY - rect.top - Number(state.canvasPanY || 0)) / zoom,
  };
}

export function nodePositionFromDom(node) {
  return {
    x: Number(node.getAttribute("data-node-x") || 0),
    y: Number(node.getAttribute("data-node-y") || 0),
  };
}

export function nodeCenterFromDom(node) {
  const position = nodePositionFromDom(node);
  return { x: position.x + NODE_WIDTH / 2, y: position.y + NODE_HEIGHT / 2 };
}

export function nodeInputPointFromDom(node) {
  const position = nodePositionFromDom(node);
  return { x: position.x, y: position.y + NODE_HEIGHT / 2 };
}

export function nodeOutputPointFromDom(node) {
  const position = nodePositionFromDom(node);
  return { x: position.x + NODE_WIDTH, y: position.y + NODE_HEIGHT / 2 };
}

export function nodeDragBases(stage, ids) {
  return ids.map((id) => {
    const node = stage.querySelector(`[data-node-id="${cssEscape(id)}"]`);
    return node ? { id, node, ...nodePositionFromDom(node) } : null;
  }).filter(Boolean);
}

export function selectedDragIdsForNode(state, nodeId) {
  const selected = Array.isArray(state.selectedNodeIds) ? state.selectedNodeIds.filter(Boolean) : [];
  if (nodeId && selected.includes(nodeId) && selected.length > 1) return selected;
  return nodeId ? [nodeId] : selected;
}

export function connectionTargetAt(stage, clientX, clientY, fromId = "") {
  const direct = document.elementFromPoint(clientX, clientY)?.closest?.("[data-connect-to]");
  const directNode = direct?.closest?.("[data-node-id]") || direct;
  if (directNode && directNode.getAttribute("data-connect-to") !== fromId) return directNode;
  return [...stage.querySelectorAll("[data-connect-to]")].find((node) => {
    if (node.getAttribute("data-connect-to") === fromId) return false;
    const rect = node.getBoundingClientRect();
    return clientX >= rect.left - 12 && clientX <= rect.right + 12 && clientY >= rect.top - 12 && clientY <= rect.bottom + 12;
  }) || null;
}

export function edgePathBetween(from, to) {
  const dx = Math.max(120, Math.abs(to.x - from.x) * 0.46);
  return `M ${from.x} ${from.y} C ${from.x + dx} ${from.y} ${to.x - dx} ${to.y} ${to.x} ${to.y}`;
}

export function rectsIntersect(a, b) {
  return a.left <= b.right && a.right >= b.left && a.top <= b.bottom && a.bottom >= b.top;
}

export function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}
