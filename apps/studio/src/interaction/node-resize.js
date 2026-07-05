import { screenToWorld, snap } from "../geometry.js";
import { NODE_TYPES } from "../nodes.js";

export const NODE_RESIZE_LIMITS = {
  maxW: 900,
  maxH: 900,
};

export const NODE_RESIZE_SCALE_LIMITS = {
  min: 1,
  max: 2.6,
};

export function startNodeResizeSession(store, nodeId, event) {
  const node = store.get().nodes[nodeId];
  if (!node || node.collapsed) return null;
  const state = store.get();
  const base = nodeResizeBaseSize(node.type);
  const frame = boundedNodeFrame(node);
  const session = {
    kind: "resize-node",
    nodeId,
    type: node.type,
    base,
    startWorld: screenToWorld(state.viewport, event.clientX, event.clientY),
    origin: {
      w: frame.w,
      h: frame.h,
    },
    moved: false,
  };
  store.set((s) => {
    s.selection = { nodeIds: [nodeId], edgeId: null };
  }, { history: false, persist: false });
  nodeElement(nodeId)?.classList.add("resizing");
  return session;
}

export function moveNodeResizeSession(store, session, event) {
  const currentWorld = screenToWorld(store.get().viewport, event.clientX, event.clientY);
  const frame = resizedNodeFrame(session, currentWorld, { preserveAspect: event.shiftKey });
  if (Math.abs(frame.w - session.origin.w) + Math.abs(frame.h - session.origin.h) <= 2 && !session.moved) return;
  session.moved = true;
  store.set((s) => {
    const node = s.nodes[session.nodeId];
    if (!node || node.collapsed) return;
    node.w = frame.w;
    node.h = frame.h;
  }, { history: false });
}

export function finishNodeResizeSession(session) {
  nodeElement(session.nodeId)?.classList.remove("resizing");
}

export function resizedNodeFrame(session, currentWorld, options = {}) {
  const dx = currentWorld.x - session.startWorld.x;
  const dy = currentWorld.y - session.startWorld.y;
  const limits = nodeResizeLimits(session.type, session.base || session.origin);
  let width = session.origin.w + dx;
  let height = session.origin.h + dy;
  if (options.preserveAspect && session.origin.h > 0) {
    const ratio = session.origin.w / session.origin.h;
    if (Math.abs(dx) >= Math.abs(dy)) height = width / ratio;
    else width = height * ratio;
  }
  return {
    w: clamp(snap(width), limits.minW, limits.maxW),
    h: clamp(snap(height), limits.minH, limits.maxH),
  };
}

export function nodeResizeBaseSize(type) {
  const size = (NODE_TYPES[type] || NODE_TYPES.text).size || NODE_TYPES.text.size;
  return { w: Number(size.w || 280), h: Number(size.h || 280) };
}

export function nodeResizeLimits(type, baseOverride = null) {
  const base = baseOverride || nodeResizeBaseSize(type);
  return {
    minW: Math.ceil(Number(base.w || 280) * NODE_RESIZE_SCALE_LIMITS.min),
    minH: Math.ceil(Number(base.h || 280) * NODE_RESIZE_SCALE_LIMITS.min),
    maxW: NODE_RESIZE_LIMITS.maxW,
    maxH: NODE_RESIZE_LIMITS.maxH,
  };
}

export function boundedNodeFrame(node) {
  const limits = nodeResizeLimits(node?.type);
  const width = Number(node?.w || limits.minW);
  const height = Number(node?.h || limits.minH);
  return {
    w: clamp(width, limits.minW, limits.maxW),
    h: clamp(height, limits.minH, limits.maxH),
  };
}

export function nodeContentScale(node) {
  const base = nodeResizeBaseSize(node?.type);
  const frame = boundedNodeFrame(node);
  const scale = Math.min(frame.w / base.w, frame.h / base.h);
  return clamp(scale, 1, NODE_RESIZE_SCALE_LIMITS.max);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function nodeElement(id) {
  if (!globalThis.document?.querySelector) return null;
  return document.querySelector(`[data-node-id="${id}"]`);
}
