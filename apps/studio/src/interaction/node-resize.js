import { screenToWorld, snap } from "../geometry.js";

export const NODE_RESIZE_LIMITS = {
  minW: 220,
  minH: 180,
  maxW: 900,
  maxH: 900,
};

export function startNodeResizeSession(store, nodeId, event) {
  const node = store.get().nodes[nodeId];
  if (!node || node.collapsed) return null;
  const state = store.get();
  const session = {
    kind: "resize-node",
    nodeId,
    startWorld: screenToWorld(state.viewport, event.clientX, event.clientY),
    origin: {
      w: Number(node.w || 280),
      h: Number(node.h || 250),
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
  let width = session.origin.w + dx;
  let height = session.origin.h + dy;
  if (options.preserveAspect && session.origin.h > 0) {
    const ratio = session.origin.w / session.origin.h;
    if (Math.abs(dx) >= Math.abs(dy)) height = width / ratio;
    else width = height * ratio;
  }
  return {
    w: clamp(snap(width), NODE_RESIZE_LIMITS.minW, NODE_RESIZE_LIMITS.maxW),
    h: clamp(snap(height), NODE_RESIZE_LIMITS.minH, NODE_RESIZE_LIMITS.maxH),
  };
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function nodeElement(id) {
  if (!globalThis.document?.querySelector) return null;
  return document.querySelector(`[data-node-id="${id}"]`);
}
