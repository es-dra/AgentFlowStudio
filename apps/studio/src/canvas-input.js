import { findOutputPortAtPoint, finishConnectSession, moveConnectSession, startConnectSession } from "./canvas-connection.js";
import { handleCanvasNodeClick } from "./canvas-node-action-handler.js";
import { dragSession, isEditable, selectInRect, updatePortHover } from "./canvas-selection.js";
import { zoomAt, snap } from "./geometry.js";
import { duplicateNode } from "./nodes.js";
import { hasOpenOverlay } from "./overlay.js";
import { openAddNodeMenu } from "./panels/add-node-menu.js";
import { openNodeMenu } from "./panels/node-menu.js";

export function bindCanvasInput(store, runtime) {
  const viewportEl = document.getElementById("canvas-viewport");
  const rootEl = document.getElementById("canvas-root");
  let spaceHeld = false;
  let session = null;

  bindSpacePan(viewportEl, (value) => { spaceHeld = value; });
  bindViewportWheel(rootEl, store);
  bindQuickMenus(rootEl, store, runtime);
  rootEl.addEventListener("pointerover", updatePortHover);
  rootEl.addEventListener("pointerout", updatePortHover);
  rootEl.addEventListener("pointerdown", (e) => {
    session = handlePointerDown(e, { store, runtime, rootEl, viewportEl, spaceHeld });
  });
  rootEl.addEventListener("pointermove", (e) => {
    if (!session) return;
    handlePointerMove(e, { store, session });
  });
  rootEl.addEventListener("pointerup", (e) => {
    if (!session) return;
    handlePointerUp(e, { store, runtime, session, viewportEl });
    session = null;
  });
  rootEl.addEventListener("click", (e) => handleCanvasNodeClick(store, runtime, e));
}

function bindSpacePan(viewportEl, setSpaceHeld) {
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space" && !isEditable(e.target)) {
      setSpaceHeld(true);
      viewportEl.classList.add("space-pan");
      e.preventDefault();
    }
  });
  window.addEventListener("keyup", (e) => {
    if (e.code === "Space") {
      setSpaceHeld(false);
      viewportEl.classList.remove("space-pan");
    }
  });
}

function bindViewportWheel(rootEl, store) {
  rootEl.addEventListener("wheel", (e) => {
    if (e.target.closest(".prompt-bar") || e.target.closest(".popover") || e.target.closest(".modal-backdrop")) return;
    e.preventDefault();
    store.set((s) => {
      if (e.ctrlKey || e.metaKey) {
        const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
        s.viewport = zoomAt(s.viewport, e.clientX, e.clientY, factor);
      } else {
        s.viewport.x -= e.shiftKey ? e.deltaY : e.deltaX;
        s.viewport.y -= e.shiftKey ? 0 : e.deltaY;
      }
    }, { history: false, persist: false });
  }, { passive: false });
}

function bindQuickMenus(rootEl, store, runtime) {
  rootEl.addEventListener("dblclick", (e) => {
    if (e.target.closest(".node") || e.target.closest(".prompt-bar") || e.target.closest("#dock")) return;
    openAddNodeMenu(store, runtime, { x: e.clientX, y: e.clientY });
  });
  rootEl.addEventListener("contextmenu", (e) => {
    const nodeEl = e.target.closest(".node");
    if (!nodeEl) return;
    e.preventDefault();
    openNodeMenu(store, runtime, nodeEl.dataset.nodeId, { x: e.clientX, y: e.clientY });
  });
}

function handlePointerDown(e, env) {
  const { rootEl, viewportEl, spaceHeld, store, runtime } = env;
  if (e.button === 1 || (spaceHeld && e.button === 0)) {
    const session = { kind: "pan", startX: e.clientX, startY: e.clientY, vp: { ...store.get().viewport } };
    viewportEl.classList.add("panning");
    rootEl.setPointerCapture(e.pointerId);
    e.preventDefault();
    return session;
  }
  if (e.button !== 0 || isChromeTarget(e)) return null;

  const stackedOutputPort = findOutputPortAtPoint(e);
  const portBtn = stackedOutputPort || e.target.closest(".node-port");
  const nodeEl = stackedOutputPort ? stackedOutputPort.closest(".node") : e.target.closest(".node");
  if (portBtn && nodeEl && portBtn.dataset.port === "out") {
    const session = startConnectSession(store, nodeEl.dataset.nodeId, e);
    rootEl.setPointerCapture(e.pointerId);
    e.preventDefault();
    return session;
  }
  if (portBtn) return null;
  if (nodeEl) return beginNodeDrag(e, { store, rootEl, nodeEl });

  const session = { kind: "marquee", startX: e.clientX, startY: e.clientY, el: null };
  rootEl.setPointerCapture(e.pointerId);
  return session;
}

function beginNodeDrag(e, { store, rootEl, nodeEl }) {
  const nodeId = nodeEl.dataset.nodeId;
  if (e.target.closest("button")) return null;
  const state = store.get();
  const additive = e.shiftKey || e.ctrlKey || e.metaKey;
  const alreadySelected = state.selection.nodeIds.includes(nodeId);
  let selected = alreadySelected ? [...state.selection.nodeIds] : [nodeId];
  if (additive) {
    selected = alreadySelected
      ? state.selection.nodeIds.filter((id) => id !== nodeId)
      : [...state.selection.nodeIds, nodeId];
  }
  if (additive || !alreadySelected) {
    store.set((s) => { s.selection = { nodeIds: selected, edgeId: null }; }, { history: false, persist: false });
  }
  if (!selected.includes(nodeId)) return null;
  const session = e.altKey ? cloneDragSession(store, nodeId, e) : dragSession(store, selected, e, { primaryId: nodeId, additive });
  if (session) rootEl.setPointerCapture(e.pointerId);
  return session;
}

function cloneDragSession(store, nodeId, e) {
  const clone = duplicateNode(store, nodeId);
  return clone ? dragSession(store, [clone.id], e, { primaryId: clone.id }) : null;
}

function handlePointerMove(e, { store, session }) {
  if (session.kind === "pan") {
    store.set((s) => {
      s.viewport.x = session.vp.x + (e.clientX - session.startX);
      s.viewport.y = session.vp.y + (e.clientY - session.startY);
    }, { history: false, persist: false });
    return;
  }
  if (session.kind === "connect") return moveConnectSession(store, session, e);
  if (session.kind === "drag-node") return moveNodeSession(store, session, e);
  if (session.kind === "marquee") return moveMarquee(session, e);
}

function moveNodeSession(store, session, e) {
  const scale = store.get().viewport.scale;
  const dx = (e.clientX - session.startX) / scale;
  const dy = (e.clientY - session.startY) / scale;
  if (Math.abs(dx) + Math.abs(dy) > 2) session.moved = true;
  store.set((s) => {
    for (const id of session.nodeIds) {
      const node = s.nodes[id];
      const origin = session.origins[id];
      if (!node || !origin) continue;
      node.x = snap(origin.x + dx);
      node.y = snap(origin.y + dy);
    }
  }, { history: false });
}

function moveMarquee(session, e) {
  if (!session.el) {
    session.el = document.createElement("div");
    session.el.id = "marquee";
    document.getElementById("canvas-root").appendChild(session.el);
  }
  const x = Math.min(session.startX, e.clientX);
  const y = Math.min(session.startY, e.clientY);
  const w = Math.abs(e.clientX - session.startX);
  const h = Math.abs(e.clientY - session.startY);
  Object.assign(session.el.style, { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` });
  session.rect = { x, y, w, h };
}

function handlePointerUp(e, { store, runtime, session, viewportEl }) {
  if (session.kind === "pan") viewportEl.classList.remove("panning");
  if (session.kind === "connect") finishConnectSession(store, runtime, session, e);
  if (session.kind === "drag-node" && !session.moved && session.primaryId && !session.additive) {
    store.set((s) => { s.selection = { nodeIds: [session.primaryId], edgeId: null }; }, { history: false, persist: false });
  }
  if (session.kind === "marquee") finishMarquee(store, session);
}

function finishMarquee(store, session) {
  if (session.el) session.el.remove();
  const rect = session.rect;
  if (rect && (rect.w > 6 || rect.h > 6)) selectInRect(store, rect);
  else if (!hasOpenOverlay()) store.set((s) => { s.selection = { nodeIds: [], edgeId: null }; }, { history: false, persist: false });
}

function isChromeTarget(e) {
  return e.target.closest(".prompt-bar")
    || e.target.closest("#dock")
    || e.target.closest("#drawer")
    || e.target.closest("#topbar")
    || e.target.closest("#corner-controls")
    || e.target.closest("#starter-row");
}
