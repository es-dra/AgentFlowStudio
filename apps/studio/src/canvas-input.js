import { screenToWorld, zoomAt, snap, rectsIntersect, bezier } from "./geometry.js";
import { effectiveHeight, connect, duplicateNode } from "./nodes.js";
import { getPendingEdgeGroup } from "./canvas-view.js";
import { openAddNodeMenu, openReferenceMenu } from "./panels/add-node-menu.js";
import { openNodeMenu } from "./panels/node-menu.js";
import { openAssetDetailPopover } from "./panels/asset-detail-popover.js";
import { fixNodeVisualAsset, handleNodeIntent, pollNodeVideoGeneration, startNodeGeneration, uploadNodeImage } from "./node-actions.js";
import { openDirectorShell } from "./panels/director-shell.js";
import { hasOpenOverlay } from "./overlay.js";

const CLICK_SLOP = 5;

// 指针输入状态机：pan / marquee / drag-node / connect（端口拖线）。
export function bindCanvasInput(store, runtime) {
  const viewportEl = document.getElementById("canvas-viewport");
  const rootEl = document.getElementById("canvas-root");
  let spaceHeld = false;
  let session = null;

  window.addEventListener("keydown", (e) => {
    if (e.code === "Space" && !isEditable(e.target)) {
      spaceHeld = true;
      viewportEl.classList.add("space-pan");
      e.preventDefault();
    }
  });
  window.addEventListener("keyup", (e) => {
    if (e.code === "Space") {
      spaceHeld = false;
      viewportEl.classList.remove("space-pan");
    }
  });

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

  rootEl.addEventListener("pointerdown", (e) => {
    if (e.button === 1 || (spaceHeld && e.button === 0)) {
      session = { kind: "pan", startX: e.clientX, startY: e.clientY, vp: { ...store.get().viewport } };
      viewportEl.classList.add("panning");
      rootEl.setPointerCapture(e.pointerId);
      e.preventDefault();
      return;
    }
    if (e.button !== 0) return;
    if (e.target.closest(".prompt-bar") || e.target.closest("#dock") || e.target.closest("#drawer") || e.target.closest("#topbar") || e.target.closest("#corner-controls") || e.target.closest("#starter-row")) return;

    const stackedOutputPort = findOutputPortAtPoint(e);
    const portBtn = stackedOutputPort || e.target.closest(".node-port");
    const nodeEl = stackedOutputPort ? stackedOutputPort.closest(".node") : e.target.closest(".node");

    if (portBtn && nodeEl && portBtn.dataset.port === "out") {
      session = startConnectSession(store, nodeEl.dataset.nodeId, e);
      rootEl.setPointerCapture(e.pointerId);
      e.preventDefault();
      return;
    }
    if (portBtn) return; // 输入端口：暂不发起反向连线

    if (nodeEl) {
      const nodeId = nodeEl.dataset.nodeId;
      if (e.target.closest("button")) return; // 节点内按钮走 click
      const state = store.get();
      const selected = state.selection.nodeIds.includes(nodeId) ? [...state.selection.nodeIds] : [nodeId];
      if (!state.selection.nodeIds.includes(nodeId)) {
        store.set((s) => { s.selection = { nodeIds: [nodeId], edgeId: null }; }, { history: false, persist: false });
      }
      if (e.altKey) {
        const clone = duplicateNode(store, nodeId);
        if (!clone) return;
        session = dragSession(store, [clone.id], e);
      } else {
        session = dragSession(store, selected, e);
      }
      rootEl.setPointerCapture(e.pointerId);
      return;
    }

    session = { kind: "marquee", startX: e.clientX, startY: e.clientY, el: null };
    rootEl.setPointerCapture(e.pointerId);
  });

  rootEl.addEventListener("pointermove", (e) => {
    if (!session) return;
    if (session.kind === "pan") {
      store.set((s) => {
        s.viewport.x = session.vp.x + (e.clientX - session.startX);
        s.viewport.y = session.vp.y + (e.clientY - session.startY);
      }, { history: false, persist: false });
      return;
    }
    if (session.kind === "connect") {
      moveConnectSession(store, session, e);
      return;
    }
    if (session.kind === "drag-node") {
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
      return;
    }
    if (session.kind === "marquee") {
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
  });

  rootEl.addEventListener("pointerup", (e) => {
    if (!session) return;
    if (session.kind === "pan") viewportEl.classList.remove("panning");
    if (session.kind === "connect") finishConnectSession(store, runtime, session, e);
    if (session.kind === "marquee") {
      if (session.el) session.el.remove();
      const rect = session.rect;
      if (rect && (rect.w > 6 || rect.h > 6)) {
        selectInRect(store, rect);
      } else if (!hasOpenOverlay()) {
        store.set((s) => { s.selection = { nodeIds: [], edgeId: null }; }, { history: false, persist: false });
      }
    }
    session = null;
  });

  // 节点内按钮点击
  rootEl.addEventListener("click", (e) => {
    const nodeEl = e.target.closest(".node");
    if (!nodeEl) return;
    const nodeId = nodeEl.dataset.nodeId;
    const node = store.get().nodes[nodeId];
    if (!node) return;
    const actionEl = e.target.closest("[data-action]");
    const action = actionEl?.dataset.action;
    if (!action) return;
    if (action === "intent") handleNodeIntent(store, node, actionEl.dataset.intent);
    else if (action === "open-director") openDirectorShell(store, node);
    else if (action === "asset-detail") openAssetDetailPopover(store, runtime, node.params?.visualAssets?.[0], actionEl);
    else if (action === "upload") uploadNodeImage(store, runtime, node);
    else if (action === "fix-visual-asset") fixNodeVisualAsset(store, runtime, node);
    else if (action === "run") startNodeGeneration(store, runtime, node);
    else if (action === "video-poll") pollNodeVideoGeneration(store, runtime, node);
    else if (action === "duplicate") duplicateNode(store, nodeId);
    else if (action === "toggle-collapse") store.set((s) => { const n = s.nodes[nodeId]; if (n) n.collapsed = !n.collapsed; });
    else if (action === "node-menu") openNodeMenu(store, runtime, nodeId, actionEl);
  });
}

function dragSession(store, nodeIds, e) {
  return {
    kind: "drag-node",
    nodeIds,
    startX: e.clientX,
    startY: e.clientY,
    origins: Object.fromEntries(nodeIds.map((id) => {
      const n = store.get().nodes[id];
      return [id, { x: n.x, y: n.y }];
    })),
    moved: false,
  };
}

// ---------- 端口拖线 ----------

function startConnectSession(store, fromId, e) {
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

function moveConnectSession(store, session, e) {
  const state = store.get();
  const cursor = screenToWorld(state.viewport, e.clientX, e.clientY);
  const target = hitTargetNode(session, e);
  if (session.targetEl && session.targetEl !== target?.el) {
    session.targetEl.classList.remove("drop-target");
    session.targetEl = null;
    session.targetId = null;
  }
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

function finishConnectSession(store, runtime, session, e) {
  session.path.remove();
  if (session.targetEl) session.targetEl.classList.remove("drop-target");
  const moved = Math.abs(e.clientX - session.startX) + Math.abs(e.clientY - session.startY) > CLICK_SLOP;
  if (!moved) {
    // 视为点击端口：打开「引用该节点生成」菜单
    const from = store.get().nodes[session.fromId];
    const portEl = document.querySelector(`[data-node-id="${session.fromId}"] .node-port.out`);
    if (from && portEl) openReferenceMenu(store, runtime, from, portEl);
    return;
  }
  if (session.targetId && session.targetId !== session.fromId) {
    connect(store, session.fromId, session.targetId);
  }
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

function findOutputPortAtPoint(e) {
  const stack = document.elementsFromPoint(e.clientX, e.clientY);
  for (const el of stack) {
    const port = el.closest?.(".node-port.out");
    if (port) return port;
  }
  return null;
}

function selectInRect(store, rectScreen) {
  const state = store.get();
  const vp = state.viewport;
  const topLeft = screenToWorld(vp, rectScreen.x, rectScreen.y);
  const bottomRight = screenToWorld(vp, rectScreen.x + rectScreen.w, rectScreen.y + rectScreen.h);
  const worldRect = { x: topLeft.x, y: topLeft.y, w: bottomRight.x - topLeft.x, h: bottomRight.y - topLeft.y };
  const hit = Object.values(state.nodes)
    .filter((n) => rectsIntersect(worldRect, { x: n.x, y: n.y, w: n.w, h: effectiveHeight(n) }))
    .map((n) => n.id);
  store.set((s) => { s.selection = { nodeIds: hit, edgeId: null }; }, { history: false, persist: false });
}

function isEditable(target) {
  return target && (target.tagName === "TEXTAREA" || target.tagName === "INPUT" || target.isContentEditable);
}
