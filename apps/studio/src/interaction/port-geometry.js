import { clientToCanvasPoint, screenToWorld } from "../geometry.js";
import { effectiveHeight } from "../nodes.js";

const PORT_CENTER_OUTSET = 21;

export function nodePortWorldPoint(node, port, viewport) {
  if (!node) return null;
  const center = nodePortCanvasCenter(node.id, port);
  if (!center || !viewport) return fallbackNodePortPoint(node, port);
  return screenToWorld(viewport, center.x, center.y);
}

export function nodeFramePortWorldPoint(node, port, viewport) {
  if (!node) return null;
  const fallback = fallbackNodePortPoint(node, port);
  const screenCenter = nodePortScreenCenter(node.id, port);
  if (!screenCenter || !viewport) return fallback;
  const canvasRoot = typeof document !== "undefined" && typeof document.getElementById === "function"
    ? document.getElementById("canvas-root")
    : null;
  const rootRect = canvasRoot?.getBoundingClientRect?.();
  const canvasCenter = rootRect
    ? clientToCanvasPoint(screenCenter.x, screenCenter.y, canvasRoot)
    : null;
  if (canvasCenter) return screenToWorld(viewport, canvasCenter.x, canvasCenter.y);
  const visibleCenter = screenToWorld(viewport, screenCenter.x, screenCenter.y);
  return {
    x: port === "in" ? node.x : node.x + node.w,
    y: visibleCenter.y,
  };
}

export function fallbackNodePortPoint(node, port) {
  return {
    x: port === "in" ? node.x - PORT_CENTER_OUTSET : node.x + node.w + PORT_CENTER_OUTSET,
    y: node.y + effectiveHeight(node) / 2,
  };
}

export function nodePortScreenCenter(nodeId, port) {
  const portEl = nodePortElement(nodeId, port);
  if (!portEl?.getBoundingClientRect) return null;
  const rect = portEl.getBoundingClientRect();
  if (!rect.width && !rect.height) return null;
  return {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  };
}

export function nodePortCanvasCenter(nodeId, port) {
  const center = nodePortScreenCenter(nodeId, port);
  if (!center) return null;
  return clientToCanvasPoint(center.x, center.y);
}

export function nodePortElement(nodeId, port) {
  const expected = String(nodeId || "");
  if (!expected || !document?.querySelectorAll) return null;
  for (const nodeEl of document.querySelectorAll(".node")) {
    if (nodeEl?.dataset?.nodeId !== expected) continue;
    return nodeEl.querySelector?.(`.node-port.${port}`) || null;
  }
  return null;
}
