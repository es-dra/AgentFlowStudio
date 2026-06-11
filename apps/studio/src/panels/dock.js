import { el, showPopover } from "../overlay.js";
import { openAddNodeMenu } from "./add-node-menu.js";
import { openGalleryModal } from "./gallery-modal.js";
import { openHistoryModal } from "./history-modal.js";
import { openShortcutsPanel } from "./shortcuts-panel.js";
import { fitViewport } from "../geometry.js";
import { icon } from "../icons.js";

export function renderDock(store, runtime) {
  const dock = document.getElementById("dock");
  if (dock.dataset.built) return;
  dock.dataset.built = "1";

  const addBtn = dockBtn("plus", "添加节点", "primary");
  addBtn.addEventListener("click", () => {
    const root = document.getElementById("canvas-root").getBoundingClientRect();
    openAddNodeMenu(store, runtime, { x: root.left + root.width / 2, y: root.top + root.height / 2 }, addBtn);
  });
  dock.appendChild(addBtn);

  const toolboxBtn = dockBtn("grid", "我的工具箱");
  toolboxBtn.addEventListener("click", () => openGalleryModal(store, "toolbox", null));
  dock.appendChild(toolboxBtn);

  const libraryBtn = dockBtn("wand", "素材库");
  libraryBtn.appendChild(el("span", "dot"));
  libraryBtn.addEventListener("click", () => {
    const pop = el("div");
    pop.appendChild(el("div", "menu-title", "素材库"));
    const styleItem = el("button", "menu-item");
    styleItem.innerHTML = `<span class="mi-icon">${icon("wand", 13)}</span><span>风格库</span><span class="mi-tag new">NEW</span>`;
    styleItem.addEventListener("click", () => { close(); openGalleryModal(store, "styles", selectedNodeId(store)); });
    const effectItem = el("button", "menu-item");
    effectItem.innerHTML = `<span class="mi-icon">${icon("sparkles", 13)}</span><span>特效库</span><span class="mi-tag new">NEW</span>`;
    effectItem.addEventListener("click", () => { close(); openGalleryModal(store, "effects", selectedNodeId(store)); });
    pop.appendChild(styleItem);
    pop.appendChild(effectItem);
    const close = showPopover(libraryBtn, pop, { place: "top" });
  });
  dock.appendChild(libraryBtn);

  const historyBtn = dockBtn("clock", "历史资产");
  historyBtn.addEventListener("click", () => openHistoryModal(store));
  dock.appendChild(historyBtn);

  dock.appendChild(el("span", "dock-sep"));

  const keysBtn = dockBtn("keyboard", "快捷键");
  keysBtn.addEventListener("click", () => openShortcutsPanel());
  dock.appendChild(keysBtn);

  const helpBtn = dockBtn("help", "帮助");
  helpBtn.addEventListener("click", () => openShortcutsPanel());
  dock.appendChild(helpBtn);

  renderCorner(store);
}

function selectedNodeId(store) {
  const sel = store.get().selection.nodeIds;
  return sel.length === 1 ? sel[0] : null;
}

function dockBtn(iconName, title, extra = "") {
  const btn = el("button", `dock-btn${extra ? ` ${extra}` : ""}`);
  btn.innerHTML = icon(iconName, 16);
  btn.title = title;
  return btn;
}

function renderCorner(store) {
  const corner = document.getElementById("corner-controls");
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
    const root = document.getElementById("canvas-root").getBoundingClientRect();
    s.viewport = fitViewport(s.nodes, root.width, root.height);
  }));
  corner.appendChild(fit);

  corner.appendChild(el("span", "zoom-label", "100%"));
}
