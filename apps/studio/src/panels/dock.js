import { el } from "../overlay.js";
import { openAddNodeMenu } from "./add-node-menu.js";
import { openShortcutsPanel } from "./shortcuts-panel.js";
import { fitVisibleCanvasViewport, visibleCanvasCenter } from "../canvas-safe-area.js";
import { icon } from "../icons.js";

export function renderDock(store, runtime) {
  const dock = document.getElementById("dock");
  if (!dock) {
    renderCorner(store, runtime);
    return;
  }
  if (dock.dataset.built) return;
  dock.dataset.built = "1";

  const addBtn = dockBtn("plus", "添加节点", "primary");
  addBtn.addEventListener("click", () => {
    openAddNodeMenu(store, runtime, visibleCanvasCenter(), addBtn);
  });
  dock.appendChild(addBtn);

  const fitBtn = dockBtn("fit", "适应画布");
  fitBtn.addEventListener("click", () => store.set((s) => {
    const viewport = fitVisibleCanvasViewport(s.nodes);
    if (viewport) s.viewport = viewport;
  }, { history: false, persist: false }));
  dock.appendChild(fitBtn);

  const keysBtn = dockBtn("keyboard", "快捷键");
  keysBtn.addEventListener("click", () => openShortcutsPanel());
  dock.appendChild(keysBtn);

  renderCorner(store, runtime);
}

function dockBtn(iconName, title, extra = "") {
  const btn = el("button", `dock-btn${extra ? ` ${extra}` : ""}`);
  btn.innerHTML = icon(iconName, 16);
  btn.title = title;
  return btn;
}

function renderCorner(store, runtime) {
  const corner = document.getElementById("corner-controls");
  if (!corner) return;
  if (corner.dataset.built) return;
  corner.dataset.built = "1";

  const add = el("button", "icon-btn");
  add.innerHTML = icon("plus", 14);
  add.title = "添加节点";
  add.setAttribute("aria-label", "添加节点");
  add.addEventListener("click", () => openAddNodeMenu(store, runtime, visibleCanvasCenter(), add));
  corner.appendChild(add);

  const fit = el("button", "icon-btn");
  fit.innerHTML = icon("fit", 14);
  fit.title = "适应画布";
  fit.setAttribute("aria-label", "适应画布");
  fit.addEventListener("click", () => store.set((s) => {
    const viewport = fitVisibleCanvasViewport(s.nodes);
    if (viewport) s.viewport = viewport;
  }));
  corner.appendChild(fit);

  corner.appendChild(el("span", "zoom-label", "100%"));
}
