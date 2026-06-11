import { createStore } from "./store.js";
import { createRuntimeClient } from "./runtime-client.js";
import { renderCanvas } from "./canvas-view.js";
import { bindCanvasInput } from "./canvas-input.js";
import { renderPromptBar } from "./prompt-bar.js";
import { renderDrawer } from "./panels/drawer.js";
import { renderDock } from "./panels/dock.js";
import { openAddNodeMenu } from "./panels/add-node-menu.js";
import { closeTop, hasOpenOverlay, el } from "./overlay.js";
import { createNode, deleteNodes, duplicateNode } from "./nodes.js";
import { startLocalPreview, spawnSampleScriptFlow } from "./node-actions.js";
import { STARTERS } from "./presets/starters.js";
import { fitViewport, zoomAt } from "./geometry.js";
import { icon } from "./icons.js";

const store = createStore();
const runtime = createRuntimeClient("studio-local-001");
store.attachRuntime(runtime);

renderStarters();
renderDock(store, runtime);
bindCanvasInput(store, runtime);
bindKeyboard();

store.subscribe(renderAll);
renderAll(store.get());
store.hydrateRuntime(runtime);

function renderAll(state) {
  renderTopbar(state, store);
  renderCanvas(state);
  renderDrawer(state, store);
  renderPromptBar(state, store, runtime);
}

function renderTopbar(state, store) {
  const topbar = document.getElementById("topbar");
  const signature = [
    state.ui.drawerOpen,
    state.meta.projectName,
    state.meta.canvasName,
    state.ui.saveState,
    state.ui.saveMessage,
  ].join("|");
  if (topbar.dataset.signature === signature) return;
  topbar.dataset.signature = signature;
  topbar.classList.toggle("drawer-open", state.ui.drawerOpen);
  topbar.replaceChildren();

  if (!state.ui.drawerOpen) {
    const openDrawer = el("button", "icon-btn drawer-restore");
    openDrawer.innerHTML = icon("panel", 15);
    openDrawer.title = "展开侧栏";
    openDrawer.addEventListener("click", () => store.set((s) => { s.ui.drawerOpen = true; }, { history: false, persist: false }));
    topbar.appendChild(openDrawer);

    const logo = el("div", "topbar-logo", "AFS");
    topbar.appendChild(logo);

    const title = el("div", "topbar-title compact-project");
    title.appendChild(el("span", "proj-name", state.meta.projectName));
    title.appendChild(el("span", "divider"));
    title.appendChild(el("span", "canvas-name", `${state.meta.canvasName} ▾`));
    topbar.appendChild(title);
  }

  topbar.appendChild(el("div", "topbar-spacer"));

  const right = el("div", "topbar-right");
  const save = el("span", `save-pill ${saveClass(state.ui.saveState)}`, state.ui.saveState || "本地暂存");
  if (state.ui.saveMessage) save.title = state.ui.saveMessage;
  right.appendChild(save);

  for (const [iconName, label] of [["share", "分享"], ["archive", "作品库"], ["user", "账户"]]) {
    const btn = el("button", "icon-btn");
    btn.innerHTML = icon(iconName, 15);
    btn.title = label;
    right.appendChild(btn);
  }
  topbar.appendChild(right);
}

function renderStarters() {
  const row = document.getElementById("starter-row");
  row.replaceChildren();
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
    store.set((s) => { s.nodes[script.id].title = "剧本分镜"; });
    spawnSampleScriptFlow(store, script);
  } else if (id === "character_sheet") {
    const node = createNode(store, "image", cx - 140, cy - 140);
    store.set((s) => {
      s.nodes[node.id].title = "角色三视图";
      s.nodes[node.id].prompt = "生成角色正面、侧面、背面三视图，保持服装、发型、体态一致。";
    });
  } else if (id === "director_board") {
    const node = createNode(store, "director", cx - 140, cy - 140);
    store.set((s) => { s.nodes[node.id].title = "二维导演台"; });
  } else if (id === "keyframe_prompt") {
    const node = createNode(store, "image", cx - 140, cy - 140);
    store.set((s) => {
      s.nodes[node.id].title = "关键帧提示词";
      s.nodes[node.id].prompt = "生成一个电影感关键帧：主体明确，镜头构图清晰，灯光有动机。";
    });
  } else if (id === "first_frame_video") {
    const node = createNode(store, "video", cx - 140, cy - 140);
    store.set((s) => {
      s.nodes[node.id].title = "5s 视频片段";
      s.nodes[node.id].prompt = "基于首帧生成 5 秒视频片段，运动幅度克制，保持主体身份和场景连续。";
    });
  }
}

function bindKeyboard() {
  window.addEventListener("keydown", (e) => {
    const editable = e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT" || e.target.isContentEditable;

    if (e.key === "Escape") {
      if (hasOpenOverlay()) { closeTop(); return; }
      if (store.get().selection.nodeIds.length) {
        store.set((s) => { s.selection = { nodeIds: [], edgeId: null }; }, { history: false, persist: false });
        return;
      }
      store.set((s) => { s.ui.drawerOpen = !s.ui.drawerOpen; }, { history: false, persist: false });
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
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
      e.preventDefault();
      if (e.shiftKey) store.redo();
      else store.undo();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
      e.preventDefault();
      store.redo();
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
      }, { history: false, persist: false });
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "l") {
      e.preventDefault();
      arrangeCanvas();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") {
      e.preventDefault();
      duplicateSelected();
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
  }, { history: false, persist: false });
}

function arrangeCanvas() {
  store.set((s) => {
    const columns = 4;
    const gapX = 360;
    const gapY = 320;
    s.order.forEach((id, index) => {
      const node = s.nodes[id];
      if (!node) return;
      node.x = (index % columns) * gapX - 520;
      node.y = Math.floor(index / columns) * gapY - 180;
    });
  });
}

function duplicateSelected() {
  const ids = [...store.get().selection.nodeIds];
  for (const id of ids) duplicateNode(store, id, 32, 32);
}

function saveClass(state) {
  if (state === "已保存") return "saved";
  if (state === "保存中" || state === "同步中") return "saving";
  return "local";
}
