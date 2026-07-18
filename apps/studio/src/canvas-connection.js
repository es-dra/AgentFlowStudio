import { bezier, clientToWorld } from "./geometry.js";
import { pulseConnectionSource } from "./interaction/feedback-layer.js";
import { nodePortWorldPoint } from "./interaction/port-geometry.js";
import { effectiveHeight, connect } from "./nodes.js";
import { getPendingEdgeGroup } from "./canvas-edges.js";
import { openReferenceMenu } from "./panels/add-node-menu.js";

const CLICK_SLOP = 5;

export function findPortAtPoint(e) {
  const stack = document.elementsFromPoint(e.clientX, e.clientY);
  for (const el of stack) {
    const port = el.closest?.(".node-port");
    if (port) return port;
  }
  return null;
}

export function startConnectSession(store, fromId, port, e) {
  const from = store.get().nodes[fromId];
  const direction = port === "in" ? "upstream" : "downstream";
  const startPort = direction === "upstream" ? "in" : "out";
  const start = nodePortWorldPoint(from, startPort, store.get().viewport)
    || {
      x: startPort === "in" ? from.x : from.x + from.w,
      y: from.y + effectiveHeight(from) / 2,
    };
  const group = getPendingEdgeGroup();
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.classList.add("pending");
  group.appendChild(path);
  pulseConnectionSource(fromId, true);
  return {
    kind: "connect",
    fromId,
    direction,
    startX: e.clientX,
    startY: e.clientY,
    path,
    targetId: null,
    targetEl: null,
    start,
  };
}

export function moveConnectSession(store, session, e) {
  const state = store.get();
  const cursor = clientToWorld(state.viewport, e.clientX, e.clientY);
  const target = hitTargetNode(session, e);
  clearPreviousTarget(session, target);
  let end = cursor;
  if (target) {
    session.targetId = target.id;
    session.targetEl = target.el;
    target.el.classList.add("drop-target");
    const node = state.nodes[target.id];
    if (node) {
      const targetPort = session.direction === "upstream" ? "out" : "in";
      end = nodePortWorldPoint(node, targetPort, state.viewport)
        || {
          x: targetPort === "in" ? node.x : node.x + node.w,
          y: node.y + effectiveHeight(node) / 2,
        };
    }
    session.path.classList.add("target-locked");
  } else {
    session.path.classList.remove("target-locked");
  }
  session.path.setAttribute("d", bezier(session.start.x, session.start.y, end.x, end.y));
}

export function finishConnectSession(store, runtime, session, e) {
  session.path.remove();
  pulseConnectionSource(session.fromId, false);
  if (session.targetEl) session.targetEl.classList.remove("drop-target");
  const moved = Math.abs(e.clientX - session.startX) + Math.abs(e.clientY - session.startY) > CLICK_SLOP;
  if (!moved) {
    const node = store.get().nodes[session.fromId];
    const portName = session.direction === "upstream" ? "in" : "out";
    const portEl = document.querySelector(`[data-node-id="${session.fromId}"] .node-port.${portName}`);
    if (node && portEl) openReferenceMenu(store, runtime, node, portEl, { direction: session.direction });
    return;
  }
  if (session.targetId && session.targetId !== session.fromId) {
    if (session.direction === "upstream") connect(store, session.targetId, session.fromId);
    else connect(store, session.fromId, session.targetId);
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
