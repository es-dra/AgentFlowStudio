import { findPortAtPoint, finishConnectSession, moveConnectSession, startConnectSession } from "./canvas-connection.js";
import { handleCanvasNodeClick } from "./canvas-node-action-handler.js";
import { dragSession, isEditable, selectInRect, updatePortHover } from "./canvas-selection.js";
import { clientToCanvasPoint, clientToWorld, zoomAt } from "./geometry.js";
import { applyEdgeAutoPan } from "./interaction/auto-pan.js";
import { beginDragFeedback, finishDragFeedback, updateDragFeedback } from "./interaction/feedback-layer.js";
import { clearPortMagnet, outputPortFromMagnet, updatePortMagnet } from "./interaction/port-magnet.js";
import { animateInertiaPan, createPointerKinematics } from "./interaction/pointer-kinematics.js";
import { resolveDragSnap } from "./interaction/snap-engine.js";
import { duplicateNode } from "./nodes.js";
import { hasOpenOverlay } from "./overlay.js";
import { openAddNodeMenu } from "./panels/add-node-menu.js";
import { openNodeMenu } from "./panels/node-menu.js";
import { closestFromEvent } from "./dom-event-targets.js";

export function bindCanvasInput(store, runtime) {
  const viewportEl = document.getElementById("canvas-viewport");
  const rootEl = document.getElementById("canvas-root");
  let spaceHeld = false;
  let session = null;
  let lastBlankPointerUp = null;
  let cancelPanMomentum = null;
  const stopPanMomentum = () => {
    if (cancelPanMomentum) cancelPanMomentum();
    cancelPanMomentum = null;
  };

  bindSpacePan(viewportEl, (value) => { spaceHeld = value; });
  bindViewportWheel(rootEl, store, stopPanMomentum);
  bindQuickMenus(rootEl, store, runtime);
  rootEl.addEventListener("pointerover", updatePortHover);
  rootEl.addEventListener("pointerout", updatePortHover);
  rootEl.addEventListener("pointerleave", clearPortMagnet);
  rootEl.addEventListener("pointerdown", (e) => {
    stopPanMomentum();
    clearPortMagnet();
    session = handlePointerDown(e, { store, runtime, rootEl, viewportEl, spaceHeld });
  });
  rootEl.addEventListener("pointermove", (e) => {
    if (!session) {
      updatePortMagnet(e);
      return;
    }
    handlePointerMove(e, { store, session, rootEl });
  });
  rootEl.addEventListener("mousemove", (e) => {
    if (!session) updatePortMagnet(e);
  });
  rootEl.addEventListener("pointerup", (e) => {
    if (!session) return;
    const finishedSession = session;
    cancelPanMomentum = handlePointerUp(e, { store, runtime, session, viewportEl, rootEl });
    lastBlankPointerUp = maybeOpenBlankPointerMenu(e, { session: finishedSession, runtime, store, previous: lastBlankPointerUp });
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

function bindViewportWheel(rootEl, store, stopPanMomentum) {
  rootEl.addEventListener("wheel", (e) => {
    if (
      e.target.closest(".prompt-bar")
      || e.target.closest(".popover")
      || e.target.closest(".modal-backdrop")
      || e.target.closest(".node-content-editor")
      || e.target.closest(".text-content-view")
    ) return;
    stopPanMomentum();
    e.preventDefault();
    store.set((s) => {
      if (e.ctrlKey || e.metaKey) {
        const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
        const point = clientToCanvasPoint(e.clientX, e.clientY, rootEl);
        s.viewport = zoomAt(s.viewport, point.x, point.y, factor);
      } else {
        s.viewport.x -= e.shiftKey ? e.deltaY : e.deltaX;
        s.viewport.y -= e.shiftKey ? 0 : e.deltaY;
      }
    }, { history: false, persist: false });
  }, { passive: false });
}

function bindQuickMenus(rootEl, store, runtime) {
  let lastBlankClick = null;
  rootEl.addEventListener("click", (e) => {
    if (hasOpenOverlay()) {
      lastBlankClick = null;
      return;
    }
    if (!isBlankCanvasDoubleClick(e)) {
      lastBlankClick = null;
      return;
    }
    const now = performance.now();
    const previous = lastBlankClick;
    lastBlankClick = { x: e.clientX, y: e.clientY, at: now };
    if (!previous) return;
    const closeInTime = now - previous.at <= 460;
    const closeInSpace = Math.abs(e.clientX - previous.x) + Math.abs(e.clientY - previous.y) <= 10;
    if (!closeInTime || !closeInSpace) return;
    lastBlankClick = null;
    e.preventDefault();
    openAddNodeMenu(store, runtime, { x: e.clientX, y: e.clientY });
  });
  rootEl.addEventListener("dblclick", (e) => {
    if (hasOpenOverlay()) return;
    const nodeEl = closestFromEvent(e, ".node");
    if (nodeEl) {
      if (!closestFromEvent(e, ".node-content-editor")) {
        e.preventDefault();
        openNodePromptEditor(store, nodeEl.dataset.nodeId);
      }
      return;
    }
    if (!isBlankCanvasDoubleClick(e)) return;
    lastBlankClick = null;
    openAddNodeMenu(store, runtime, { x: e.clientX, y: e.clientY });
  });
  rootEl.addEventListener("contextmenu", (e) => {
    const nodeEl = closestFromEvent(e, ".node");
    if (!nodeEl) return;
    e.preventDefault();
    openNodeMenu(store, runtime, nodeEl.dataset.nodeId, { x: e.clientX, y: e.clientY });
  });
}

function maybeOpenBlankPointerMenu(e, { session, runtime, store, previous }) {
  if (hasOpenOverlay()) return null;
  if (session?.kind !== "marquee" || session.rect) return null;
  if (!isBlankCanvasDoubleClick(e)) return null;
  const now = performance.now();
  const current = { x: e.clientX, y: e.clientY, at: now };
  if (!previous) return current;
  const closeInTime = now - previous.at <= 460;
  const closeInSpace = Math.abs(e.clientX - previous.x) + Math.abs(e.clientY - previous.y) <= 10;
  if (!closeInTime || !closeInSpace) return current;
  e.preventDefault();
  openAddNodeMenu(store, runtime, { x: e.clientX, y: e.clientY });
  return null;
}

function isBlankCanvasDoubleClick(e) {
  if (e.target.closest(".prompt-bar")
    || e.target.closest(".popover")
    || e.target.closest(".modal-backdrop")
    || e.target.closest("#dock")
    || e.target.closest("#drawer")
    || e.target.closest("#topbar")
    || e.target.closest("#corner-controls")
    || e.target.closest("#starter-row")
    || e.target.closest("button,input,textarea,select,a")) return false;
  if (e.target.closest("#canvas-empty-hint")) return true;
  const blankIds = new Set(["canvas-root", "canvas-viewport", "world", "node-layer"]);
  return blankIds.has(e.target.id);
}

function openNodePromptEditor(store, nodeId) {
  if (!nodeId) return;
  store.set((s) => {
    if (!s.nodes[nodeId]) return;
    s.selection = { nodeIds: [nodeId], edgeId: null };
    s.ui.promptBarNodeId = nodeId;
  }, { history: false, persist: false });
}

function handlePointerDown(e, env) {
  const { rootEl, viewportEl, spaceHeld, store, runtime } = env;
  if (e.button === 1 || (spaceHeld && e.button === 0)) {
    const session = {
      kind: "pan",
      startX: e.clientX,
      startY: e.clientY,
      vp: { ...store.get().viewport },
      kinematics: createPointerKinematics(e),
    };
    viewportEl.classList.add("panning");
    rootEl.setPointerCapture(e.pointerId);
    e.preventDefault();
    return session;
  }
  if (e.button !== 0) return null;

  const stackedOutputPort = findPortAtPoint(e) || outputPortFromMagnet(e);
  const portBtn = stackedOutputPort || e.target.closest(".node-port");
  const nodeEl = stackedOutputPort ? stackedOutputPort.closest(".node") : e.target.closest(".node");
  if (portBtn && nodeEl) {
    const session = startConnectSession(store, nodeEl.dataset.nodeId, portBtn.dataset.port, e);
    rootEl.setPointerCapture(e.pointerId);
    e.preventDefault();
    return session;
  }
  if (portBtn) return null;
  if (isChromeTarget(e)) return null;
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
  if (session) {
    rootEl.setPointerCapture(e.pointerId);
    beginDragFeedback(rootEl, session);
  }
  return session;
}

function cloneDragSession(store, nodeId, e) {
  const clone = duplicateNode(store, nodeId);
  return clone ? dragSession(store, [clone.id], e, { primaryId: clone.id }) : null;
}

function handlePointerMove(e, { store, session, rootEl }) {
  if (session.kind === "pan") {
    session.kinematics?.sample(e);
    store.set((s) => {
      s.viewport.x = session.vp.x + (e.clientX - session.startX);
      s.viewport.y = session.vp.y + (e.clientY - session.startY);
    }, { history: false, persist: false });
    return;
  }
  if (session.kind === "connect") return moveConnectSession(store, session, e);
  if (session.kind === "drag-node") return moveNodeSession(store, session, e, rootEl);
  if (session.kind === "marquee") return moveMarquee(session, e);
}

function moveNodeSession(store, session, e, rootEl) {
  applyEdgeAutoPan(store, rootEl, e);
  const state = store.get();
  session.startWorld = session.startWorld || clientToWorld(state.viewport, session.startX, session.startY, rootEl);
  const currentWorld = clientToWorld(state.viewport, e.clientX, e.clientY, rootEl);
  const dx = currentWorld.x - session.startWorld.x;
  const dy = currentWorld.y - session.startWorld.y;
  if (Math.abs(dx) + Math.abs(dy) <= 2 && !session.moved) return;
  session.moved = true;
  const snapResult = resolveDragSnap(state, session, {
    dx,
    dy,
    shiftKey: e.shiftKey,
    ctrlKey: e.ctrlKey,
    metaKey: e.metaKey,
  });
  store.set((s) => {
    for (const [id, position] of Object.entries(snapResult.positions)) {
      const node = s.nodes[id];
      if (!node) continue;
      node.x = position.x;
      node.y = position.y;
    }
  }, { history: false });
  updateDragFeedback(rootEl, store.get(), snapResult);
}

function moveMarquee(session, e) {
  if (!session.el) {
    session.el = document.createElement("div");
    session.el.id = "marquee";
    document.getElementById("canvas-root").appendChild(session.el);
  }
  const start = clientToCanvasPoint(session.startX, session.startY);
  const current = clientToCanvasPoint(e.clientX, e.clientY);
  const x = Math.min(start.x, current.x);
  const y = Math.min(start.y, current.y);
  const w = Math.abs(current.x - start.x);
  const h = Math.abs(current.y - start.y);
  Object.assign(session.el.style, { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` });
  session.rect = { x, y, w, h };
}

function handlePointerUp(e, { store, runtime, session, viewportEl, rootEl }) {
  if (session.kind === "pan") {
    viewportEl.classList.remove("panning");
    return animateInertiaPan(store, session.kinematics?.velocity?.() || { x: 0, y: 0 });
  }
  if (session.kind === "connect") finishConnectSession(store, runtime, session, e);
  if (session.kind === "drag-node") finishDragFeedback(rootEl, session, { land: session.moved });
  if (session.kind === "drag-node" && !session.moved && session.primaryId && !session.additive) {
    store.set((s) => { s.selection = { nodeIds: [session.primaryId], edgeId: null }; }, { history: false, persist: false });
  }
  if (session.kind === "marquee") finishMarquee(store, session);
  return null;
}

function finishMarquee(store, session) {
  if (session.el) session.el.remove();
  const rect = session.rect;
  if (rect && (rect.w > 6 || rect.h > 6)) selectInRect(store, rect);
  else if (!hasOpenOverlay()) store.set((s) => { s.selection = { nodeIds: [], edgeId: null }; }, { history: false, persist: false });
}

function isChromeTarget(e) {
  return e.target.closest(".prompt-bar")
    || e.target.closest("#canvas-empty-hint")
    || e.target.closest("button,input,textarea,select,a")
    || e.target.closest("#dock")
    || e.target.closest("#drawer")
    || e.target.closest("#topbar")
    || e.target.closest("#corner-controls")
    || e.target.closest("#starter-row");
}
