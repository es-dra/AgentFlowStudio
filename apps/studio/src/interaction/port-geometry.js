import { screenToWorld } from "../geometry.js";
import { effectiveHeight } from "../nodes.js";

export function nodePortWorldPoint(node, port, viewport) {
  if (!node) return null;
  const center = nodePortScreenCenter(node.id, port);
  if (!center || !viewport) return fallbackNodePortPoint(node, port);
  return screenToWorld(viewport, center.x, center.y);
}

export function nodeFramePortWorldPoint(node, port, viewport) {
  if (!node) return null;
  const fallback = fallbackNodePortPoint(node, port);
  const center = nodePortScreenCenter(node.id, port);
  if (!center || !viewport) return fallback;
  return screenToWorld(viewport, center.x, center.y);
}

export function fallbackNodePortPoint(node, port) {
  return {
    x: port === "in" ? node.x : node.x + node.w,
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

export function nodePortElement(nodeId, port) {
  const expected = String(nodeId || "");
  if (!expected || !document?.querySelectorAll) return null;
  for (const nodeEl of document.querySelectorAll(".node")) {
    if (nodeEl?.dataset?.nodeId !== expected) continue;
    return nodeEl.querySelector?.(`.node-port.${port}`) || null;
  }
  return null;
}
