import { createStore } from "./store.js";
import { createRuntimeClient } from "./runtime-client.js";
import { renderCanvas } from "./canvas-view.js";
import { bindCanvasInput } from "./canvas-input.js";
import { renderPromptBar } from "./prompt-bar.js";
import { renderDrawer } from "./panels/drawer.js";
import { renderDock } from "./panels/dock.js";
import { openAddNodeMenu } from "./panels/add-node-menu.js";
import { closeTop, hasOpenOverlay, el } from "./overlay.js";
import { createNode, deleteNodes } from "./nodes.js";
import { startLocalPreview, spawnSampleScriptFlow } from "./node-actions.js";
import { STARTERS } from "./presets/starters.js";
import { fitViewport, zoomAt } from "./geometry.js";
import { icon } from "./icons.js";

const store = createStore();
const runtime = createRuntimeClient("studio-local-001");

renderStarters();
renderDock(store, runtime);
bindCanvasInput(store, runtime);
bindKeyboard();

store.subscribe(renderAll);
renderAll(store.get());

function renderAll(state) {
  renderTopbar(state, store);
  renderCanvas(state);
  renderDrawer(state, store);
  renderPromptBar(state, store, runtime);
}

function renderTopbar(state, store) {
  const topbar = document.getElementById("topbar");
  const signature = [state.ui.drawerOpen, state.meta.projectName, state.meta.canvasName].join("|");
  if (topbar.dataset.signature === signature) return;
  topbar.dataset.signature = signature;
  topbar.classList.toggle("drawer-open", state.ui.drawerOpen);
  topbar.replaceChildren();

  if (!state.ui.drawerOpen) {
    const openDrawer = el("button", "icon-btn drawer-restore");
    openDrawer.innerHTML = icon("panel", 15);
    openDrawer.title = "展开侧栏";
    openDrawer.addEventListener("click", () => store.set((s) => { s.ui.drawerOpen = true; }));
    topbar.appendChild(openDrawer);

    const logo = el("div", "topbar-logo", "▣");
    topbar.appendChild(logo);

    const title = el("div", "topbar-title compact-project");
    title.appendChild(el("span", "proj-name", state.meta.projectName));
    title.appendChild(el("span", "divider"));
    title.appendChild(el("span", "canvas-name", `${state.meta.canvasName} ▾`));
    topbar.appendChild(title);
  }

  topbar.appendChild(el("div", "topbar-spacer"));

  const right = el("div", "topbar-right");
  for (const [iconName, label] of [["share", "分享"], ["archive", "作品集"], ["user", "账户"]]) {
    const btn = el("button", "icon-btn");
    btn.innerHTML = icon(iconName, 15);
    btn.title = label;
    right.appendChild(btn);
  }
  topbar.appendChild(right);
}

function renderStarters() {
  const row = document.getElementById("starter-row");
  for (const starter of STARTERS) {
    const card = el("button", "starter-card");
    card.innerHTML = `<span class="starter-icon">${icon(starter.icon, 15)}</span><span>${starter.label}</span>`;
    card.addEventListener("click", () => launchStarter(starter.id));
    row.appendChild(card);
  }
}

function launchStarter(id) {
  const root = document.getElementById("canvas-root").getBoundingClientRect();
  const cx = (root.width / 2 - store.get().viewport.x) / store.get().viewport.scale;
  const cy = (root.height / 2 - store.get().viewport.y) / store.get().viewport.scale;
  if (id === "story_script") {
    const script = createNode(store, "script", cx + 60, cy - 160);
    spawnSampleScriptFlow(store, script);
  } else if (id === "character_sheet") {
    createNode(store, "image", cx - 140, cy - 140);
  } else if (id === "first_frame_video") {
    createNode(store, "video", cx - 140, cy - 140);
  } else if (id === "audio_video") {
    createNode(store, "audio", cx - 140, cy - 140);
  }
}

function bindKeyboard() {
  window.addEventListener("keydown", (e) => {
    const editable = e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT" || e.target.isContentEditable;

    if (e.key === "Escape") {
      if (hasOpenOverlay()) { closeTop(); return; }
      if (store.get().selection.nodeIds.length) {
        store.set((s) => { s.selection = { nodeIds: [], edgeId: null }; });
        return;
      }
      store.set((s) => { s.ui.drawerOpen = !s.ui.drawerOpen; });
      return;
    }
    if (editable) return;

    if (e.key === "Tab") {
      e.preventDefault();
      const root = document.getElementById("canvas-root").getBoundingClientRect();
      openAddNodeMenu(store, runtime, { x: root.width / 2, y: root.height / 2 });
      return;
    }
    if ((e.key === "Delete" || e.key === "Backspace") && store.get().selection.nodeIds.length) {
      deleteNodes(store, store.get().selection.nodeIds);
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      const sel = store.get().selection.nodeIds;
      if (sel.length === 1) startLocalPreview(store, store.get().nodes[sel[0]]);
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "0") {
      e.preventDefault();
      store.set((s) => {
        const root = document.getElementById("canvas-root").getBoundingClientRect();
        s.viewport = fitViewport(s.nodes, root.width, root.height);
      });
      return;
    }
    if ((e.ctrlKey || e.metaKey) && (e.key === "=" || e.key === "+")) {
      e.preventDefault();
      zoomCenter(1.15);
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "-") {
      e.preventDefault();
      zoomCenter(1 / 1.15);
    }
  });
}

function zoomCenter(factor) {
  const root = document.getElementById("canvas-root").getBoundingClientRect();
  store.set((s) => {
    s.viewport = zoomAt(s.viewport, root.width / 2, root.height / 2, factor);
  });
}
