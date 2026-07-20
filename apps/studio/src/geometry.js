export const GRID_SNAP = 12;
export const MIN_SCALE = 0.2;
export const MAX_SCALE = 2.5;

export function screenToWorld(viewport, sx, sy) {
  return {
    x: (sx - viewport.x) / viewport.scale,
    y: (sy - viewport.y) / viewport.scale,
  };
}

export function clientToCanvasPoint(clientX, clientY, root = null) {
  const canvasRoot = root || (
    typeof document !== "undefined" && typeof document.getElementById === "function"
      ? document.getElementById("canvas-root")
      : null
  );
  const rect = canvasRoot?.getBoundingClientRect?.();
  if (!rect) return { x: clientX, y: clientY };
  return {
    x: clientX - rect.left,
    y: clientY - rect.top,
  };
}

export function clientToWorld(viewport, clientX, clientY, root = null) {
  const point = clientToCanvasPoint(clientX, clientY, root);
  return screenToWorld(viewport, point.x, point.y);
}

export function worldToScreen(viewport, wx, wy) {
  return {
    x: wx * viewport.scale + viewport.x,
    y: wy * viewport.scale + viewport.y,
  };
}

export function snap(value, step = GRID_SNAP) {
  return Math.round(value / step) * step;
}

export function clampScale(scale) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

export function zoomAt(viewport, sx, sy, factor) {
  const scale = clampScale(viewport.scale * factor);
  const world = screenToWorld(viewport, sx, sy);
  return {
    scale,
    x: sx - world.x * scale,
    y: sy - world.y * scale,
  };
}

export function nodesBounds(nodes) {
  const list = Object.values(nodes);
  if (!list.length) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const n of list) {
    minX = Math.min(minX, n.x);
    minY = Math.min(minY, n.y - 26);
    maxX = Math.max(maxX, n.x + n.w);
    maxY = Math.max(maxY, n.y + n.h);
  }
  return { minX, minY, maxX, maxY };
}

export function fitViewport(nodes, viewW, viewH, padding = 90, safeArea = {}) {
  const b = nodesBounds(nodes);
  if (!b) return { x: 0, y: 0, scale: 1 };
  const w = b.maxX - b.minX;
  const h = b.maxY - b.minY;
  const left = Math.max(0, Number(safeArea.left || 0));
  const right = Math.max(0, Number(safeArea.right || 0));
  const top = Math.max(0, Number(safeArea.top || 0));
  const bottom = Math.max(0, Number(safeArea.bottom || 0));
  const availableW = Math.max(160, viewW - left - right);
  const availableH = Math.max(160, viewH - top - bottom);
  const scale = clampScale(Math.min((availableW - padding * 2) / w, (availableH - padding * 2) / h, 1));
  return {
    scale,
    x: left + (availableW - w * scale) / 2 - b.minX * scale,
    y: top + (availableH - h * scale) / 2 - b.minY * scale,
  };
}

export function rectsIntersect(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

export function edgePath(fromNode, toNode) {
  const x1 = fromNode.x + fromNode.w;
  const y1 = fromNode.y + fromNode.h / 2;
  const x2 = toNode.x;
  const y2 = toNode.y + toNode.h / 2;
  return bezier(x1, y1, x2, y2);
}

export function bezier(x1, y1, x2, y2) {
  const dx = Math.max(48, Math.abs(x2 - x1) * 0.45);
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
}
