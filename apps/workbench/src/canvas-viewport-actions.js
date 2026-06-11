import { DEFAULT_ZOOM, MAX_ZOOM, MIN_ZOOM, clamp, normalizedZoom } from "./canvas-interaction-geometry.js";
import { NODE_SIZE, nodePosition, workflowNodes } from "./studio-workflow-graph.js";

const CONTENT_OFFSET_X = 32;
const CONTENT_OFFSET_Y = 96;
const VIEWPORT_SAFE_X = 96;
const VIEWPORT_SAFE_Y = 230;

export function fitCanvasToNodes(state, ids = []) {
  const bounds = canvasBounds(state, ids);
  if (!bounds) return;
  const width = Math.max(360, window.innerWidth - VIEWPORT_SAFE_X);
  const height = Math.max(360, window.innerHeight - VIEWPORT_SAFE_Y);
  const zoom = clamp(Math.min(width / bounds.width, height / bounds.height), MIN_ZOOM, 1.1);
  state.canvasZoom = Math.round(zoom * 100) / 100;
  centerCanvasOnPoint(state, bounds.centerX, bounds.centerY);
}

export function centerCanvasOnSelection(state) {
  const selected = Array.isArray(state.selectedNodeIds) ? state.selectedNodeIds.filter(Boolean) : [];
  if (selected.length > 1) {
    fitCanvasToNodes(state, selected);
    return;
  }
  centerCanvasOnNode(state, selected[0] || state.selectedCardId || "script-input");
}

export function centerCanvasOnNode(state, id) {
  const nodes = workflowNodes(state);
  const index = nodes.findIndex((node) => node[0] === id);
  if (index < 0) return;
  const position = nodePosition(state, id, index);
  centerCanvasOnPoint(state, position.x + NODE_SIZE.width / 2, position.y + NODE_SIZE.height / 2);
}

export function resetCanvasViewport(state) {
  state.canvasZoom = DEFAULT_ZOOM;
  state.canvasPanX = 0;
  state.canvasPanY = 0;
}

export function canvasNavigatorMetrics(state) {
  const bounds = canvasBounds(state) || { left: 0, top: 0, right: 2600, bottom: 1700, width: 2600, height: 1700, centerX: 1300, centerY: 850 };
  const zoom = normalizedZoom(state);
  const viewportRect = {
    left: (-Number(state.canvasPanX || 0) - CONTENT_OFFSET_X) / zoom,
    top: (-Number(state.canvasPanY || 0) - CONTENT_OFFSET_Y) / zoom,
    width: window.innerWidth / zoom,
    height: window.innerHeight / zoom,
  };
  return { bounds, viewportRect, nodes: navigatorNodes(state, bounds) };
}

export function canvasBounds(state, ids = []) {
  const idSet = ids.length ? new Set(ids) : null;
  const nodes = workflowNodes(state)
    .map((node, index) => ({ id: node[0], ...nodePosition(state, node[0], index) }))
    .filter((node) => !idSet || idSet.has(node.id));
  if (!nodes.length) return null;
  const left = Math.min(...nodes.map((node) => node.x)) - 80;
  const top = Math.min(...nodes.map((node) => node.y)) - 80;
  const right = Math.max(...nodes.map((node) => node.x + NODE_SIZE.width)) + 80;
  const bottom = Math.max(...nodes.map((node) => node.y + NODE_SIZE.height)) + 80;
  return { left, top, right, bottom, width: right - left, height: bottom - top, centerX: (left + right) / 2, centerY: (top + bottom) / 2 };
}

function centerCanvasOnPoint(state, x, y) {
  const zoom = normalizedZoom(state);
  const centerX = window.innerWidth / 2;
  const centerY = (window.innerHeight - 78) / 2;
  state.canvasPanX = Math.round(centerX - CONTENT_OFFSET_X - x * zoom);
  state.canvasPanY = Math.round(centerY - CONTENT_OFFSET_Y - y * zoom);
}

function navigatorNodes(state, bounds) {
  const selected = new Set(Array.isArray(state.selectedNodeIds) ? state.selectedNodeIds.filter(Boolean) : []);
  return workflowNodes(state).map((node, index) => {
    const position = nodePosition(state, node[0], index);
    return { id: node[0], selected: selected.has(node[0]), x: position.x + NODE_SIZE.width / 2 - bounds.left, y: position.y + NODE_SIZE.height / 2 - bounds.top };
  });
}
