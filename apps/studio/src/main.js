import { createStore } from "./store.js";
import { createRuntimeClient } from "./runtime-client.js";
import { renderCanvas } from "./canvas-view.js";
import { bindCanvasInput } from "./canvas-input.js";
import { bindCanvasContextMenu } from "./canvas-context-menu.js";
import { renderPromptBar } from "./prompt-bar.js";
import { renderDrawer } from "./panels/drawer.js";
import { renderInspectorPanel } from "./panels/inspector-panel.js";
import { openGenerationPanel } from "./panels/generation-panel.js";
import { openCreationProcessPanel } from "./panels/creation-process-panel.js";
import { renderDock } from "./panels/dock.js";
import { el, showModal } from "./overlay.js";
import { fixNodeVisualAsset, startNodeGeneration } from "./node-actions.js";
import { WORKFLOW_STARTERS, createWorkflowStarter } from "./workflow-starters.js";
import { openProjectHub } from "./project-hub.js";
import { syncRuntimeAssets } from "./runtime-asset-sync.js";
import { arrangeCanvas, bindStudioKeyboard } from "./studio-keyboard.js";
import { icon } from "./icons.js";
import { QUALITY_FEEDBACK_EVENT, QUALITY_FEEDBACK_RESULT_EVENT } from "./quality-feedback.js";
import { renderTopbar } from "./studio-topbar.js";
import { ensureAuthSession, signOut } from "./auth-gate.js";

const ACTIVE_PROJECT_KEY = "afs_studio_active_project_id";
const RECENT_PROJECTS_KEY = "afs_studio_recent_project_ids";
const VIDEO_ASSET_CARD_DRAFT_EVENT = "afs:video-asset-card-draft";
let runtime = createRuntimeClient(initialProjectId());
const runtimeRef = new Proxy({}, { get: (_, prop) => runtime[prop] });
const store = createStore(runtime.projectId);
store.attachRuntime(runtime);
let projectSummaries = [];
let showAllProjects = false;
let currentAuthUser = null;

bootstrap();

async function bootstrap() {
  rememberProject(runtime.projectId);
  renderStarters();
  renderDock(store, runtimeRef);
  bindCanvasInput(store, runtimeRef);
  bindCanvasContextMenu(store, runtimeRef, { arrange: () => arrangeCanvas(store) });
  bindStudioKeyboard({ store, runtime: runtimeRef });
  bindQualityFeedback();
  bindVideoAssetCardDraft();
  bindStudioWorkflowEvents();

  store.subscribe(renderAll);
  renderAll(store.get());

  const authState = await ensureAuthSession(runtime, {
    onAuthenticated: (user) => {
      currentAuthUser = user || null;
      renderAll(store.get());
    },
  });
  currentAuthUser = authState?.user || null;
  if (authState?.auth_required && !authState?.authenticated) return;

  await ensureAccessibleStartupProject();
  await store.hydrateRuntime(runtime);
  await syncRuntimeAssets(store, runtime);
  await refreshProjectSummaries();
}

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

async function ensureAccessibleStartupProject() {
  let payload;
  try {
    payload = await runtime.listProjects();
  } catch {
    projectSummaries = [];
    return;
  }
  projectSummaries = Array.isArray(payload?.projects) ? payload.projects : [];
  syncCurrentProjectMetaFromSummaries();
  if (projectSummaries.some((item) => item.project_id === runtime.projectId)) return;
  if (projectSummaries.length) {
    await switchProject(projectSummaries[0].project_id);
    return;
  }
  if (!currentAuthUser?.user_id) return;
  const projectId = safeProjectId(`studio-${currentAuthUser.user_id}-home`);
  const projectName = `${currentAuthUser.display_name || "AFS"} 的项目`;
  runtime = createRuntimeClient(projectId);
  await runtime.createProject({ project_id: projectId, goal: projectName });
  localStorage.setItem(ACTIVE_PROJECT_KEY, projectId);
  rememberProject(projectId);
  syncProjectUrl(projectId);
  store.attachRuntime(runtime);
  await store.switchProject(projectId, runtime);
  store.set((s) => {
    s.meta.projectName = projectName;
    s.meta.canvasName = "画布 1";
  }, { history: false });
  await store.flushRuntimeSave();
  await refreshProjectSummaries();
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
  await syncRuntimeAssets(store, runtime);
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
    await store.flushRuntimeSave();
    await syncRuntimeAssets(store, runtime);
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

function bindStudioWorkflowEvents() {
  window.addEventListener("afs:studio-open-generation-panel", (event) => {
    openGenerationForNode(event.detail?.node);
  });
  window.addEventListener("afs:studio-open-creation-process", (event) => {
    const node = resolveEventNode(event);
    if (node) openCreationProcessPanel(store.get(), node);
  });
  window.addEventListener("afs:studio-fix-visual-asset", (event) => {
    const node = resolveEventNode(event);
    if (node) fixNodeVisualAsset(store, runtimeRef, node);
  });
  window.addEventListener("afs:studio-select-node", (event) => {
    const node = resolveEventNode(event);
    if (!node) return;
    store.set((s) => {
      s.selection = { nodeIds: [node.id], edgeId: null };
    }, { history: false, persist: false });
  });
}

function openGenerationForNode(inputNode) {
  const node = inputNode?.id ? store.get().nodes[inputNode.id] : selectedNode();
  if (!node) return null;
  return openGenerationPanel({
    store,
    node,
    onRun: (fresh) => startNodeGeneration(store, runtimeRef, fresh),
  });
}

function resolveEventNode(event) {
  const nodeId = String(event.detail?.node_id || event.detail?.node?.id || "");
  if (!nodeId) return selectedNode();
  return store.get().nodes[nodeId] || null;
}

function selectedNode() {
  const id = store.get().selection.nodeIds[0];
  return id ? store.get().nodes[id] || null : null;
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
      provider_service_id: "vision_video",
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
  const normal = known.filter((item) => !isTestProject(item)).slice(0, 5);
  const normalIds = new Set(normal.map((item) => item.project_id));
  const visible = showAllProjects ? known : known.filter((item) =>
    item.project_id === currentId || recent.includes(item.project_id) || normalIds.has(item.project_id));
  return visible.length ? visible : [current];
}

function hiddenProjectCount(state) {
  const currentId = state.meta.projectId || runtime.projectId;
  if (showAllProjects) return 0;
  const visibleIds = new Set(projectOptions(state).map((item) => item.project_id));
  return projectSummaries.filter((item) => item.project_id !== currentId && !visibleIds.has(item.project_id)).length;
}

function isTestProject(item) {
  const id = String(item?.project_id || "").toLowerCase();
  const goal = String(item?.goal || "").toLowerCase();
  const name = String(item?.studio_state_meta?.projectName || "").toLowerCase();
  return /(smoke|qa|debug|test|browser|walkthrough|proj_|codex|frontend|review|loop|joint|gate|regression|probe|upload|optimize|empty)/.test(`${id} ${goal} ${name}`);
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
  renderTopbar({
    state,
    store,
    runtime,
    projectSummaries,
    projectOptions: projectOptions(state),
    hiddenProjectCount: hiddenProjectCount(state),
    showAllProjects,
    onToggleProjectFilter: () => {
      showAllProjects = !showAllProjects;
      renderAll(store.get());
    },
    onSwitchProject: switchProject,
    onCreateProject: createNewProject,
    onOpenHome: () => openStudioHome(state),
    authUser: currentAuthUser,
    onSignOut: async () => {
      await signOut(runtime);
      currentAuthUser = null;
      window.location.href = "/";
    },
  });
  renderCanvas(state);
  renderDrawer(state, store, runtimeRef);
  renderInspectorPanel(state, store, runtimeRef);
  renderPromptBar(state, store, runtime);
}

function openStudioHome(state = store.get()) {
  return openProjectHub({
    state,
    runtime,
    projects: projectOptions(state),
    hiddenProjectCount: hiddenProjectCount(state),
    onSwitchProject: switchProject,
    onCreateProject: createNewProject,
    onStartWorkflow: launchStarter,
    onOpenAssets: () => store.set((s) => {
      s.ui.drawerOpen = true;
      s.ui.drawerTab = "assets";
    }, { history: false, persist: false }),
    onOpenHistory: () => store.set((s) => {
      s.ui.drawerOpen = true;
      s.ui.drawerTab = "history";
    }, { history: false, persist: false }),
  });
}

function renderStarters() {
  const row = document.getElementById("starter-row");
  row.replaceChildren();
  for (const starter of WORKFLOW_STARTERS) {
    const card = el("button", "starter-card workflow-starter-card");
    card.dataset.tone = starter.tone || "story";
    card.innerHTML = [
      `<span class="starter-icon">${icon(starter.icon, 15)}</span>`,
      `<span class="starter-copy"><strong>${starter.label}</strong><small>${starter.summary}</small></span>`,
      `<span class="starter-tag">${starter.tag}</span>`,
    ].join("");
    card.addEventListener("click", () => launchStarter(starter.id));
    row.appendChild(card);
  }
}

function launchStarter(id) {
  const root = document.getElementById("canvas-root").getBoundingClientRect();
  const cx = (root.width / 2 - store.get().viewport.x) / store.get().viewport.scale;
  const cy = (root.height / 2 - store.get().viewport.y) / store.get().viewport.scale;
  createWorkflowStarter(store, id, { x: cx - 570, y: cy - 160 });
}
