import { createStore } from "./store.js";
import { createRuntimeClient } from "./runtime-client.js";
import { renderCanvas } from "./canvas-view.js";
import { bindCanvasInput } from "./canvas-input.js";
import { renderPromptBar } from "./prompt-bar.js";
import { renderDrawer } from "./panels/drawer.js";
import { renderDock } from "./panels/dock.js";
import { openAddNodeMenu } from "./panels/add-node-menu.js";
import { openShortcutsPanel } from "./panels/shortcuts-panel.js";
import { closeTop, hasOpenOverlay, el } from "./overlay.js";
import { createNode, deleteNodes, duplicateNode } from "./nodes.js";
import { startNodeGeneration, spawnSampleScriptFlow } from "./node-actions.js";
import { STARTERS } from "./presets/starters.js";
import { fitViewport, zoomAt } from "./geometry.js";
import { icon } from "./icons.js";

const ACTIVE_PROJECT_KEY = "afs_studio_active_project_id";
let runtime = createRuntimeClient(initialProjectId());
const runtimeRef = new Proxy({}, { get: (_, prop) => runtime[prop] });
const store = createStore(runtime.projectId);
store.attachRuntime(runtime);
let projectSummaries = [];

renderStarters();
renderDock(store, runtimeRef);
bindCanvasInput(store, runtimeRef);
bindKeyboard();

store.subscribe(renderAll);
renderAll(store.get());
store.hydrateRuntime(runtime).then(syncRuntimeAssets);
refreshProjectSummaries();

function initialProjectId() {
  const params = new URLSearchParams(window.location.search || "");
  const fromQuery = safeProjectId(params.get("project"));
  if (fromQuery) return fromQuery;
  const stored = safeProjectId(localStorage.getItem(ACTIVE_PROJECT_KEY));
  return stored || "studio-local-001";
}

function safeProjectId(value) {
  const text = String(value || "").trim().replace(/[^a-zA-Z0-9_.-]+/g, "-").replace(/^[-._]+|[-._]+$/g, "");
  return text || "";
}

async function refreshProjectSummaries() {
  try {
    const payload = await runtime.listProjects();
    projectSummaries = Array.isArray(payload?.projects) ? payload.projects : [];
    renderAll(store.get());
  } catch {
    projectSummaries = [];
  }
}

async function switchProject(projectId) {
  const safe = safeProjectId(projectId) || "studio-local-001";
  localStorage.setItem(ACTIVE_PROJECT_KEY, safe);
  syncProjectUrl(safe);
  runtime = createRuntimeClient(safe);
  store.attachRuntime(runtime);
  await store.switchProject(safe, runtime);
  await syncRuntimeAssets();
  await refreshProjectSummaries();
}

function syncProjectUrl(projectId) {
  const url = new URL(window.location.href);
  url.searchParams.set("project", projectId);
  window.history.replaceState({}, "", url);
}

async function createNewProject() {
  const name = window.prompt("项目名称", "AFS 内测项目");
  if (name === null) return;
  const suffix = Math.random().toString(36).slice(2, 8);
  const projectId = safeProjectId(`studio-${Date.now()}-${suffix}`);
  runtime = createRuntimeClient(projectId);
  await runtime.createProject({ project_id: projectId, goal: name.trim() || "AFS Studio project" });
  localStorage.setItem(ACTIVE_PROJECT_KEY, projectId);
  syncProjectUrl(projectId);
  await store.switchProject(projectId, runtime);
  store.set((s) => {
    s.meta.projectName = name.trim() || "AFS Studio project";
    s.meta.canvasName = "画布 1";
  }, { history: false });
  await runtime.saveStudioState(store.get());
  await syncRuntimeAssets();
  await refreshProjectSummaries();
}

async function syncRuntimeAssets() {
  const [imagePayload, visualPayload] = await Promise.allSettled([
    runtime.listImageAssets?.(),
    runtime.listVisualAssets?.("fixed"),
  ]);
  const imageAssets = imagePayload.status === "fulfilled" && Array.isArray(imagePayload.value?.assets) ? imagePayload.value.assets : [];
  const visualAssets = visualPayload.status === "fulfilled" && Array.isArray(visualPayload.value?.assets) ? visualPayload.value.assets : [];
  store.set((s) => {
    const generated = [
      ...visualAssets.map((asset) => ({
        id: `visual_${asset.asset_id}`,
        kind: asset.asset_type === "scene" ? "scene_asset" : "character_asset",
        title: asset.label || asset.asset_id,
        safe_summary: asset.signature || "",
        thumbnail_ref: "character-sheet",
        source_node_id: asset.source_node_id || null,
        status: asset.status || "fixed",
        asset_id: asset.asset_id,
      })),
      ...imageAssets.map((asset) => ({
        id: `image_${asset.asset_id}`,
        kind: "image_reference",
        title: asset.filename || asset.asset_id,
        safe_summary: asset.role || "image asset",
        thumbnail_ref: "keyframe",
        source_node_id: asset.source_node_id || null,
        status: "ready",
        asset_id: asset.asset_id,
        preview_url: asset.preview_url,
      })),
    ];
    const ids = new Set(generated.map((item) => item.id));
    s.assets = [...generated, ...s.assets.filter((item) => !ids.has(item.id))];
  }, { history: false });
}

function projectLabel(item) {
  const meta = item?.studio_state_meta || {};
  return meta.projectName || item?.goal || item?.project_id || "studio-local-001";
}

function projectOptions(state) {
  const currentId = state.meta.projectId || runtime.projectId;
  const current = { project_id: currentId, studio_state_meta: { projectName: state.meta.projectName, canvasName: state.meta.canvasName } };
  const known = projectSummaries.length ? [...projectSummaries] : [];
  if (currentId && !known.some((item) => item.project_id === currentId)) known.unshift(current);
  return known.length ? known : [current];
}

function renderAll(state) {
  renderTopbar(state, store);
  renderCanvas(state);
  renderDrawer(state, store);
  renderPromptBar(state, store, runtime);
}

function renderTopbar(state, store) {
  const topbar = document.getElementById("topbar");
  const signature = [
    state.meta.projectId,
    state.ui.drawerOpen,
    state.meta.projectName,
    state.meta.canvasName,
    state.ui.saveState,
    state.ui.saveMessage,
    projectSummaries.map((item) => item.project_id).join(","),
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

    const projectSelect = el("select", "project-select");
    projectSelect.title = "切换项目";
    const known = projectOptions(state);
    for (const item of known) {
      const option = document.createElement("option");
      option.value = item.project_id;
      option.textContent = projectLabel(item);
      option.selected = item.project_id === runtime.projectId;
      projectSelect.appendChild(option);
    }
    projectSelect.addEventListener("change", () => switchProject(projectSelect.value));
    topbar.appendChild(projectSelect);

    const newProject = el("button", "icon-btn");
    newProject.innerHTML = icon("plus", 14);
    newProject.title = "新建项目";
    newProject.addEventListener("click", createNewProject);
    topbar.appendChild(newProject);
  }

  if (state.ui.drawerOpen) {
    appendProjectControls(topbar, state);
  }

  topbar.appendChild(el("div", "topbar-spacer"));

  const right = el("div", "topbar-right");
  const save = el("span", `save-pill ${saveClass(state.ui.saveState)}`, state.ui.saveState || "本地暂存");
  if (state.ui.saveMessage) save.title = state.ui.saveMessage;
  right.appendChild(save);
  // 分享/作品库/账户尚未实现:内测版本不展示无功能按钮,待功能落地后恢复。
  topbar.appendChild(right);
}

function appendProjectControls(topbar, state) {
  const projectSelect = el("select", "project-select");
  projectSelect.title = "切换项目";
  const known = projectOptions(state);
  for (const item of known) {
    const option = document.createElement("option");
    option.value = item.project_id;
    option.textContent = projectLabel(item);
    option.selected = item.project_id === runtime.projectId;
    projectSelect.appendChild(option);
  }
  projectSelect.addEventListener("change", () => switchProject(projectSelect.value));
  topbar.appendChild(projectSelect);

  const newProject = el("button", "icon-btn");
  newProject.innerHTML = icon("plus", 14);
  newProject.title = "新建项目";
  newProject.addEventListener("click", createNewProject);
  topbar.appendChild(newProject);
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
      if (sel.length === 1) startNodeGeneration(store, runtime, store.get().nodes[sel[0]]);
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
      return;
    }
    if (e.key === "?") {
      e.preventDefault();
      openShortcutsPanel();
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
  // 按连线拓扑分层排列:上游在左、下游在右,同层纵向排布;孤立节点排在最后一层之后。
  store.set((s) => {
    const gapX = 400;
    const gapY = 330;
    const layers = topologicalLayers(s);
    layers.forEach((ids, layerIndex) => {
      ids.forEach((id, rowIndex) => {
        const node = s.nodes[id];
        if (!node) return;
        node.x = layerIndex * gapX - 520;
        node.y = rowIndex * gapY - 180 - Math.floor(ids.length / 2) * 40;
      });
    });
  });
}

function topologicalLayers(state) {
  const upstreamOf = {};
  for (const edge of Object.values(state.edges)) {
    (upstreamOf[edge.to] = upstreamOf[edge.to] || []).push(edge.from);
  }
  const layerOf = {};
  const resolve = (id, depth = 0) => {
    if (layerOf[id] !== undefined) return layerOf[id];
    if (depth > 32) return 0;
    const ups = (upstreamOf[id] || []).filter((up) => state.nodes[up]);
    layerOf[id] = ups.length ? Math.max(...ups.map((up) => resolve(up, depth + 1))) + 1 : 0;
    return layerOf[id];
  };
  const connected = new Set(Object.values(state.edges).flatMap((e) => [e.from, e.to]));
  const layers = [];
  const isolated = [];
  for (const id of state.order) {
    if (!state.nodes[id]) continue;
    if (!connected.has(id)) { isolated.push(id); continue; }
    const layer = resolve(id);
    (layers[layer] = layers[layer] || []).push(id);
  }
  const result = layers.filter(Boolean);
  for (let i = 0; i < isolated.length; i += 3) {
    result.push(isolated.slice(i, i + 3));
  }
  return result;
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
