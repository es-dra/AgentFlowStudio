import { icon } from "./icons.js";
import { openAddNodeMenu } from "./panels/add-node-menu.js";
import { el, showPopover } from "./overlay.js";
import { fitVisibleCanvasViewport } from "./canvas-safe-area.js";

export function bindCanvasContextMenu(store, runtime, callbacks = {}) {
  const root = document.getElementById("canvas-root");
  if (!root) return;
  root.addEventListener("contextmenu", (event) => {
    if (event.target.closest(".node, .prompt-bar, #dock, #drawer, #topbar, #inspector")) return;
    event.preventDefault();
    openCanvasMenu(store, runtime, { x: event.clientX, y: event.clientY }, callbacks);
  });
}

function openCanvasMenu(store, runtime, point, callbacks) {
  let close = () => {};
  const menu = el("div", "canvas-context-menu");
  const state = store.get();
  const selectedCount = state.selection.nodeIds.length;
  menu.appendChild(sectionTitle("画布"));
  menu.appendChild(menuAction("添加节点", "在当前位置放一个新节点", "plus", () => {
    close();
    openAddNodeMenu(store, runtime, point);
  }));
  menu.appendChild(menuAction("整理画布", "按创作顺序自动排布", "grid", () => {
    close();
    callbacks.arrange?.();
  }, !callbacks.arrange));
  menu.appendChild(menuAction("适应画布", "把当前内容完整放进视野", "fit", () => {
    close();
    fitCurrentCanvas(store);
  }));

  menu.appendChild(sectionTitle("选择"));
  menu.appendChild(menuAction("全选节点", `${state.order.length} 个节点`, "copy", () => {
    close();
    store.set((s) => {
      s.selection = { nodeIds: [...s.order], edgeId: null };
    }, { history: false, persist: false });
  }, !state.order.length));
  menu.appendChild(menuAction("清除选择", selectedCount ? `${selectedCount} 个已选中` : "当前没有选择", "x", () => {
    close();
    store.set((s) => {
      s.selection = { nodeIds: [], edgeId: null };
    }, { history: false, persist: false });
  }, !selectedCount));

  menu.appendChild(sectionTitle("项目"));
  menu.appendChild(menuAction("打开素材库", "查看角色、场景和参考图", "library", () => {
    close();
    openDrawerTab(store, "assets");
  }));
  menu.appendChild(menuAction("打开作品库", "查看生成结果和创作过程", "frames", () => {
    close();
    openDrawerTab(store, "history");
  }));

  const anchor = virtualAnchor(point);
  close = showPopover(anchor, menu, { place: "bottom" });
}

function fitCurrentCanvas(store) {
  store.set((s) => {
    s.viewport = fitVisibleCanvasViewport(s.nodes);
  }, { history: false, persist: false });
}

function openDrawerTab(store, tab) {
  store.set((s) => {
    s.ui.drawerOpen = true;
    s.ui.drawerTab = tab;
  }, { history: false, persist: false });
}

function sectionTitle(text) {
  return el("div", "canvas-menu-title", text);
}

function menuAction(label, hint, iconName, onClick, disabled = false) {
  const item = el("button", "canvas-menu-item");
  item.type = "button";
  item.disabled = disabled;
  item.innerHTML = [
    `<span class="canvas-menu-icon">${icon(iconName, 14)}</span>`,
    `<span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(hint)}</small></span>`,
  ].join("");
  item.addEventListener("click", onClick);
  return item;
}

function virtualAnchor(point) {
  return {
    getBoundingClientRect() {
      return {
        left: point.x,
        right: point.x + 1,
        top: point.y,
        bottom: point.y + 1,
        width: 1,
        height: 1,
      };
    },
  };
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
