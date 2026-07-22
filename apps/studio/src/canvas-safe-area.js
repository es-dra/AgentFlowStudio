import { fitViewport } from "./geometry.js";

const SAFE_OVERLAYS = [
  "#drawer",
  "#inspector",
  "#topbar",
  "#dock",
  ".studio-agent-chat",
  ".studio-context-drawer",
  ".product-mobile-nav",
];

export function fitVisibleCanvasViewport(nodes, padding = 90) {
  const frame = visibleCanvasFrame();
  if (!isVisibleCanvasFrameUsable(frame)) return null;
  return fitViewport(nodes, frame.width, frame.height, padding, frame.safeArea);
}

export function visibleCanvasFrame() {
  const root = document.getElementById("canvas-root");
  const rect = root?.getBoundingClientRect();
  if (!rect) return { width: 0, height: 0, safeArea: {}, visible: false };
  const style = window.getComputedStyle(root);
  const visible = root.isConnected
    && !root.hidden
    && style.display !== "none"
    && style.visibility !== "hidden"
    && rect.width > 0
    && rect.height > 0;
  const safeArea = { left: 0, right: 0, top: 0, bottom: 0 };
  for (const selector of SAFE_OVERLAYS) {
    applyOverlayInset(safeArea, rect, document.querySelector(selector));
  }
  return { width: rect.width, height: rect.height, safeArea, visible };
}

export function visibleCanvasCenter() {
  const frame = visibleCanvasFrame();
  const left = frame.safeArea?.left || 0;
  const right = frame.safeArea?.right || 0;
  const top = frame.safeArea?.top || 0;
  const bottom = frame.safeArea?.bottom || 0;
  return {
    x: left + (frame.width - left - right) / 2,
    y: top + (frame.height - top - bottom) / 2,
    coordinateSpace: "canvas",
  };
}

export function isVisibleCanvasFrameUsable(frame = visibleCanvasFrame()) {
  return Boolean(frame.visible && frame.width >= 160 && frame.height >= 160);
}

function applyOverlayInset(safeArea, rootRect, overlay) {
  if (!overlay || overlay.hidden || overlay.classList?.contains("collapsed")) return;
  const style = window.getComputedStyle(overlay);
  if (style.display === "none" || style.visibility === "hidden" || style.pointerEvents === "none") return;
  const rect = overlay.getBoundingClientRect();
  const overlapX = Math.min(rootRect.right, rect.right) - Math.max(rootRect.left, rect.left);
  const overlapY = Math.min(rootRect.bottom, rect.bottom) - Math.max(rootRect.top, rect.top);
  if (overlapX <= 0 || overlapY <= 0) return;
  const sideOverlay = overlapY >= rootRect.height * 0.45 && rect.width <= rootRect.width * 0.72;
  const horizontalOverlay = overlapX >= rootRect.width * 0.38 && rect.height <= rootRect.height * 0.72;
  if (sideOverlay && rect.left <= rootRect.left + 24 && rect.width > 80) {
    safeArea.left = Math.max(safeArea.left, Math.min(rootRect.width - 160, rect.right - rootRect.left));
  }
  if (sideOverlay && rect.right >= rootRect.right - 24 && rect.width > 80) {
    safeArea.right = Math.max(safeArea.right, Math.min(rootRect.width - 160, rootRect.right - rect.left));
  }
  if (horizontalOverlay && rect.top <= rootRect.top + 24 && rect.height > 48) {
    safeArea.top = Math.max(safeArea.top, Math.min(rootRect.height - 160, rect.bottom - rootRect.top));
  }
  if (horizontalOverlay && rect.bottom >= rootRect.bottom - 24 && rect.height > 48) {
    safeArea.bottom = Math.max(safeArea.bottom, Math.min(rootRect.height - 160, rootRect.bottom - rect.top));
  }
}
