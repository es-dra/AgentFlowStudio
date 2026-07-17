import { el } from "../overlay.js";
import { openAddNodeMenu } from "./add-node-menu.js";
import { openShortcutsPanel } from "./shortcuts-panel.js";
import { fitVisibleCanvasViewport, visibleCanvasCenter } from "../canvas-safe-area.js";
import { icon } from "../icons.js";

export function renderDock(store, runtime) {
  const dock = document.getElementById("dock");
  if (!dock) return;
  if (dock.dataset.built) return;
  dock.dataset.built = "1";

  const addBtn = dockBtn("plus", "添加节点", "primary");
  addBtn.addEventListener("click", () => {
    openAddNodeMenu(store, runtime, visibleCanvasCenter(), addBtn);
  });
  dock.appendChild(addBtn);

  const fitBtn = dockBtn("fit", "适应画布");
  fitBtn.addEventListener("click", () => store.set((s) => {
    s.viewport = fitVisibleCanvasViewport(s.nodes);
  }, { history: false, persist: false }));
  dock.appendChild(fitBtn);

  const keysBtn = dockBtn("keyboard", "快捷键");
  keysBtn.addEventListener("click", () => openShortcutsPanel());
  dock.appendChild(keysBtn);

  renderCorner(store);
}

function dockBtn(iconName, title, extra = "") {
  const btn = el("button", `dock-btn${extra ? ` ${extra}` : ""}`);
  btn.innerHTML = icon(iconName, 16);
  btn.title = title;
  return btn;
}

function renderCorner(store) {
  const corner = document.getElementById("corner-controls");
  if (!corner) return;
  if (corner.dataset.built) return;
  corner.dataset.built = "1";

  const assets = el("button", "icon-btn");
  assets.innerHTML = `${icon("panel", 14)}<span>资产管理</span>`;
  assets.addEventListener("click", () => store.set((s) => {
    s.ui.drawerOpen = !s.ui.drawerOpen;
    s.ui.drawerTab = "assets";
  }));
  corner.appendChild(assets);

  const fit = el("button", "icon-btn");
  fit.innerHTML = icon("fit", 14);
  fit.title = "适应画布";
  fit.addEventListener("click", () => store.set((s) => {
    s.viewport = fitVisibleCanvasViewport(s.nodes);
  }));
  corner.appendChild(fit);

  corner.appendChild(el("span", "zoom-label", "100%"));
}
