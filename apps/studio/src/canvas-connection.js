import { bezier, screenToWorld } from "./geometry.js";
import { effectiveHeight, connect } from "./nodes.js";
import { getPendingEdgeGroup } from "./canvas-view.js";
import { openReferenceMenu } from "./panels/add-node-menu.js";

const CLICK_SLOP = 5;

export function findOutputPortAtPoint(e) {
  const stack = document.elementsFromPoint(e.clientX, e.clientY);
  for (const el of stack) {
    const port = el.closest?.(".node-port.out");
    if (port) return port;
  }
  return null;
}

export function startConnectSession(store, fromId, e) {
  const from = store.get().nodes[fromId];
  const group = getPendingEdgeGroup();
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.classList.add("pending");
  group.appendChild(path);
  return {
    kind: "connect",
    fromId,
    startX: e.clientX,
    startY: e.clientY,
    path,
    targetId: null,
    targetEl: null,
    start: { x: from.x + from.w, y: from.y + effectiveHeight(from) / 2 },
  };
}

export function moveConnectSession(store, session, e) {
  const state = store.get();
  const cursor = screenToWorld(state.viewport, e.clientX, e.clientY);
  const target = hitTargetNode(session, e);
  clearPreviousTarget(session, target);
  let end = cursor;
  if (target) {
    session.targetId = target.id;
    session.targetEl = target.el;
    target.el.classList.add("drop-target");
    const node = state.nodes[target.id];
    if (node) end = { x: node.x, y: node.y + effectiveHeight(node) / 2 };
    session.path.classList.add("target-locked");
  } else {
    session.path.classList.remove("target-locked");
  }
  session.path.setAttribute("d", bezier(session.start.x, session.start.y, end.x, end.y));
}

export function finishConnectSession(store, runtime, session, e) {
  session.path.remove();
  if (session.targetEl) session.targetEl.classList.remove("drop-target");
  const moved = Math.abs(e.clientX - session.startX) + Math.abs(e.clientY - session.startY) > CLICK_SLOP;
  if (!moved) {
    const from = store.get().nodes[session.fromId];
    const portEl = document.querySelector(`[data-node-id="${session.fromId}"] .node-port.out`);
    if (from && portEl) openReferenceMenu(store, runtime, from, portEl);
    return;
  }
  if (session.targetId && session.targetId !== session.fromId) {
    connect(store, session.fromId, session.targetId);
  }
}

function clearPreviousTarget(session, target) {
  if (!session.targetEl || session.targetEl === target?.el) return;
  session.targetEl.classList.remove("drop-target");
  session.targetEl = null;
  session.targetId = null;
}

function hitTargetNode(session, e) {
  const stack = document.elementsFromPoint(e.clientX, e.clientY);
  for (const el of stack) {
    const nodeEl = el.closest?.(".node");
    if (nodeEl && nodeEl.dataset.nodeId !== session.fromId) {
      return { id: nodeEl.dataset.nodeId, el: nodeEl };
    }
  }
  return null;
}
