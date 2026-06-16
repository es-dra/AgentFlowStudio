import { createStore } from "./store.js";
import { createRuntimeClient } from "./runtime-client.js";
import { renderCanvas } from "./canvas-view.js";
import { bindCanvasInput } from "./canvas-input.js";
import { renderPromptBar } from "./prompt-bar.js";
import { renderDrawer } from "./panels/drawer.js";
import { renderDock } from "./panels/dock.js";
import { openAddNodeMenu } from "./panels/add-node-menu.js";
import { openShortcutsPanel } from "./panels/shortcuts-panel.js";
import { closeTop, hasOpenOverlay, el, showModal } from "./overlay.js";
import { createNode, deleteNodes, duplicateNode } from "./nodes.js";
import { startNodeGeneration, spawnSampleScriptFlow } from "./node-actions.js";
import { STARTERS } from "./presets/starters.js";
import { fitViewport, zoomAt } from "./geometry.js";
import { icon } from "./icons.js";
import { QUALITY_FEEDBACK_EVENT, QUALITY_FEEDBACK_RESULT_EVENT } from "./quality-feedback.js";

const ACTIVE_PROJECT_KEY = "afs_studio_active_project_id";
const RECENT_PROJECTS_KEY = "afs_studio_recent_project_ids";
const VIDEO_ASSET_CARD_DRAFT_EVENT = "afs:video-asset-card-draft";
let runtime = createRuntimeClient(initialProjectId());
const runtimeRef = new Proxy({}, { get: (_, prop) => runtime[prop] });
const store = createStore(runtime.projectId);
store.attachRuntime(runtime);
let projectSummaries = [];
let showAllProjects = false;
rememberProject(runtime.projectId);

renderStarters();
renderDock(store, runtimeRef);
bindCanvasInput(store, runtimeRef);
bindKeyboard();
bindQualityFeedback();
bindVideoAssetCardDraft();

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
    syncCurrentProjectMetaFromSummaries();
    renderAll(store.get());
  } catch {
    projectSummaries = [];
  }
}

function syncCurrentProjectMetaFromSummaries() {
  const currentId = runtime.projectId || store.get().meta.projectId;
  const found = projectSummaries.find((item) => item.project_id === currentId);
  const meta = found?.studio_state_meta || {};
  const projectName = String(meta.projectName || "").trim();
  const canvasName = String(meta.canvasName || "").trim();
  if (!projectName && !canvasName) return;
  store.set((s) => {
    if (projectName) s.meta.projectName = projectName;
    if (canvasName) s.meta.canvasName = canvasName;
  }, { history: false, persist: false });
}

async function switchProject(projectId) {
  const safe = safeProjectId(projectId) || "studio-local-001";
  localStorage.setItem(ACTIVE_PROJECT_KEY, safe);
  rememberProject(safe);
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
  const name = await requestProjectName();
  if (name === null) return;
  const suffix = Math.random().toString(36).slice(2, 8);
  const projectId = safeProjectId(`studio-${Date.now()}-${suffix}`);
  const projectName = name.trim() || "AFS Studio project";
  try {
    runtime = createRuntimeClient(projectId);
    await runtime.createProject({ project_id: projectId, goal: projectName });
    localStorage.setItem(ACTIVE_PROJECT_KEY, projectId);
    rememberProject(projectId);
    syncProjectUrl(projectId);
    await store.switchProject(projectId, runtime);
    store.set((s) => {
      s.meta.projectName = projectName;
      s.meta.canvasName = "画布 1";
    }, { history: false });
    await runtime.saveStudioState(store.get());
    await syncRuntimeAssets();
    await refreshProjectSummaries();
  } catch (error) {
    showProjectCreateError(error);
  }
}

function requestProjectName() {
  return new Promise((resolve) => {
    const modal = el("div", "modal compact project-create-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "新建项目"));
    const closeBtn = el("button", "modal-close");
    closeBtn.innerHTML = icon("x", 15);
    head.appendChild(el("span", "head-spacer"));
    head.appendChild(closeBtn);

    const body = el("div", "modal-body project-create-body");
    const field = el("label", "modal-field");
    field.appendChild(el("span", "", "项目名称"));
    const input = document.createElement("input");
    input.type = "text";
    input.value = "AFS 内测项目";
    input.maxLength = 80;
    field.appendChild(input);
    const error = el("div", "modal-error");
    error.hidden = true;
    body.append(field, error);

    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const confirm = el("button", "primary-btn", "创建并切换");
    actions.append(cancel, confirm);

    modal.append(head, body, actions);
    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve(null); } });
    const finish = (value) => {
      if (settled) return;
      settled = true;
      close();
      resolve(value);
    };
    closeBtn.addEventListener("click", () => finish(null));
    cancel.addEventListener("click", () => finish(null));
    confirm.addEventListener("click", () => {
      const name = input.value.trim();
      if (!name) {
        error.textContent = "请先填写项目名称。";
        error.hidden = false;
        input.focus();
        return;
      }
      finish(name);
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") confirm.click();
    });
    requestAnimationFrame(() => {
      input.focus();
      input.select();
    });
  });
}

function showProjectCreateError(error) {
  const modal = el("div", "modal compact project-create-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("strong", "", "项目创建失败"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);
  const body = el("div", "modal-body project-create-body");
  body.appendChild(el("div", "modal-error", `Runtime 没有完成项目创建：${safeError(error)}`));
  const actions = el("div", "modal-actions");
  const ok = el("button", "primary-btn", "知道了");
  actions.appendChild(ok);
  modal.append(head, body, actions);
  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  ok.addEventListener("click", close);
}

function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  return message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 180);
}

function bindQualityFeedback() {
  window.addEventListener(QUALITY_FEEDBACK_EVENT, (event) => {
    handleQualityFeedback(event);
  });
}

function bindVideoAssetCardDraft() {
  window.addEventListener(VIDEO_ASSET_CARD_DRAFT_EVENT, (event) => {
    handleVideoAssetCardDraft(event);
  });
}

async function handleVideoAssetCardDraft(event) {
  const node = event.detail?.node;
  const nodeId = String(node?.id || "");
  if (!nodeId || !runtime?.draftAssetCard) return;
  const sourceVideoArtifactId = String(node?.params?.lastVideoArtifactId || node?.params?.lastVideoJobId || "").trim();
  if (!sourceVideoArtifactId) return;
  try {
    const response = await runtime.draftAssetCard({
      asset_type: "video",
      source_video_artifact_id: sourceVideoArtifactId,
      sampled_image_asset_refs: [],
      node_id: nodeId,
      prompt_text: node.prompt || node.result || node.title || "",
      provider_service_id: "fake_vision",
      generated_at: new Date().toISOString(),
    });
    store.set((s) => {
      const current = s.nodes[nodeId];
      if (!current) return;
      current.params.lastVideoAssetCardDraft = response?.draft || null;
      current.params.lastVideoAssetCardDraftStatus = response?.job?.status || "unknown";
      current.result = `${current.result || ""}\nVideo asset draft: ${response?.job?.status || "unknown"}`.trim();
    });
  } catch (error) {
    store.set((s) => {
      const current = s.nodes[nodeId];
      if (!current) return;
      current.result = `${current.result || ""}\nVideo asset draft failed: ${safeError(error)}`.trim();
    });
  }
}

async function handleQualityFeedback(event) {
  const requestId = String(event.detail?.request_id || "");
  try {
    const feedback = event.detail?.feedback;
    if (!feedback || typeof feedback !== "object") throw new Error("feedback payload is empty");
    const response = await runtime.recordFeedback(feedback);
    window.dispatchEvent(new CustomEvent(QUALITY_FEEDBACK_RESULT_EVENT, {
      detail: {
        request_id: requestId,
        ok: true,
        feedback_id: response?.feedback_event?.feedback_id || response?.artifact?.artifact_id || "",
      },
    }));
  } catch (error) {
    window.dispatchEvent(new CustomEvent(QUALITY_FEEDBACK_RESULT_EVENT, {
      detail: { request_id: requestId, ok: false, error: safeError(error) },
    }));
  }
}

async function syncRuntimeAssets() {
  const [imagePayload, visualPayload] = await Promise.allSettled([
    runtime.listImageAssets?.(),
    runtime.listVisualAssets?.("fixed"),
  ]);
  const imageAssets = imagePayload.status === "fulfilled" && Array.isArray(imagePayload.value?.assets) ? imagePayload.value.assets : [];
  const visualAssets = visualPayload.status === "fulfilled" && Array.isArray(visualPayload.value?.assets) ? visualPayload.value.assets : [];
  const imagePreviewById = new Map(imageAssets.map((asset) => [asset.asset_id, asset.preview_url]).filter(([assetId, previewUrl]) => assetId && previewUrl));
  store.set((s) => {
    const existingByKey = new Map();
    for (const item of s.assets || []) {
      const key = assetStableKey(item);
      if (key && !existingByKey.has(key)) existingByKey.set(key, item);
    }
    const generated = [
      ...visualAssets.map((asset) => ({
        id: `visual_${asset.asset_id}`,
        kind: asset.asset_type === "scene" ? "scene_asset" : "character_asset",
        title: asset.label || asset.asset_id,
        safe_summary: asset.signature || "",
        thumbnail_ref: asset.asset_type === "scene" ? "scene-board" : "character-sheet",
        source_node_id: asset.source_node_id || null,
        status: asset.status || "fixed",
        asset_id: asset.asset_id,
        visual_asset_id: asset.asset_id,
        asset_type: asset.asset_type || null,
        image_asset_refs: Array.isArray(asset.image_asset_refs) ? asset.image_asset_refs : [],
        preview_url: visualAssetPreviewUrl(asset, imagePreviewById),
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
    ].map((item) => mergeAsset(existingByKey.get(assetStableKey(item)), item));
    const generatedKeys = new Set(generated.map(assetStableKey).filter(Boolean));
    s.assets = [
      ...generated,
      ...s.assets.filter((item) => {
        const key = assetStableKey(item);
        return !key || !generatedKeys.has(key);
      }),
    ];
  }, { history: false });
}

function assetStableKey(asset) {
  const visualId = String(asset?.visual_asset_id || (isVisualAssetKind(asset?.kind) ? asset?.asset_id : "") || "").trim();
  if (visualId) return `visual:${visualId}`;
  const imageId = String(asset?.asset_id || "").trim();
  if (imageId) return `image:${imageId}`;
  return "";
}

function isVisualAssetKind(kind) {
  return ["visual_asset", "character_asset", "scene_asset"].includes(String(kind || ""));
}

function mergeAsset(existing, generated) {
  if (!existing) return generated;
  return {
    ...generated,
    ...existing,
    id: generated.id,
    kind: generated.kind,
    title: generated.title || existing.title,
    safe_summary: generated.safe_summary || existing.safe_summary,
    thumbnail_ref: generated.thumbnail_ref || existing.thumbnail_ref,
    source_node_id: generated.source_node_id || existing.source_node_id || null,
    status: generated.status || existing.status,
    asset_id: generated.asset_id || existing.asset_id,
    visual_asset_id: generated.visual_asset_id || existing.visual_asset_id,
    preview_url: generated.preview_url || existing.preview_url,
    asset_type: generated.asset_type || existing.asset_type,
    image_asset_refs: generated.image_asset_refs || existing.image_asset_refs,
  };
}

function visualAssetPreviewUrl(asset, imagePreviewById) {
  const refs = Array.isArray(asset?.image_asset_refs) ? asset.image_asset_refs : [];
  const firstRef = String(refs[0] || "").trim();
  if (!firstRef) return "";
  const fromImageList = imagePreviewById.get(firstRef);
  if (fromImageList) return fromImageList;
  return `/projects/${encodeURIComponent(runtime.projectId)}/image-assets/${encodeURIComponent(firstRef)}/preview`;
}

function projectLabel(item) {
  const meta = item?.studio_state_meta || {};
  return meta.projectName || item?.project_id || "studio-local-001";
}

function projectOptions(state) {
  const currentId = runtime.projectId || state.meta.projectId;
  const current = { project_id: currentId, studio_state_meta: { projectName: state.meta.projectName, canvasName: state.meta.canvasName } };
  const known = projectSummaries.length ? [...projectSummaries] : [];
  if (currentId && !known.some((item) => item.project_id === currentId)) known.unshift(current);
  const recent = recentProjectIds();
  const visible = showAllProjects ? known : known.filter((item) =>
    item.project_id === currentId || recent.includes(item.project_id) || !isTestProject(item));
  return visible.length ? visible : [current];
}

function hiddenProjectCount(state) {
  const currentId = state.meta.projectId || runtime.projectId;
  if (showAllProjects) return 0;
  return projectSummaries.filter((item) => item.project_id !== currentId && isTestProject(item)).length;
}

function isTestProject(item) {
  const id = String(item?.project_id || "").toLowerCase();
  const goal = String(item?.goal || "").toLowerCase();
  const name = String(item?.studio_state_meta?.projectName || "").toLowerCase();
  return /(smoke|qa|debug|test|browser|walkthrough|proj_)/.test(`${id} ${goal} ${name}`);
}

function rememberProject(projectId) {
  const safe = safeProjectId(projectId);
  if (!safe) return;
  const ids = [safe, ...recentProjectIds().filter((item) => item !== safe)].slice(0, 8);
  try {
    localStorage.setItem(RECENT_PROJECTS_KEY, JSON.stringify(ids));
  } catch {
    /* local recent project cache is best-effort */
  }
}

function recentProjectIds() {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECENT_PROJECTS_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.map(safeProjectId).filter(Boolean).slice(0, 8) : [];
  } catch {
    return [];
  }
}

function renderAll(state) {
  renderTopbar(state, store);
  renderCanvas(state);
  renderDrawer(state, store, runtimeRef);
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
    showAllProjects ? "all-projects" : "studio-projects",
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

    appendProjectFilterToggle(topbar, state);
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
  appendProjectFilterToggle(topbar, state);
}

function appendProjectFilterToggle(topbar, state) {
  const hidden = hiddenProjectCount(state);
  if (!hidden && !showAllProjects) return;
  const toggle = el("button", "icon-btn");
  toggle.innerHTML = icon("more", 14);
  toggle.title = showAllProjects ? "收起测试项目" : `显示全部项目（隐藏 ${hidden} 个测试项目）`;
  toggle.addEventListener("click", () => {
    showAllProjects = !showAllProjects;
    renderAll(store.get());
  });
  topbar.appendChild(toggle);
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
