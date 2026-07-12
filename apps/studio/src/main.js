import { createStore } from "./store.js";
import { createRuntimeClient } from "./runtime-client.js";
import { checkingRuntimeSurfaceStatus, initialRuntimeSurfaceStatus, loadRuntimeSurfaceStatus } from "./runtime-surface-status.js";
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
import { refreshPendingKeyframeGenerations } from "./node-keyframe-actions.js";
import { WORKFLOW_STARTERS, createWorkflowStarter } from "./workflow-starters.js";
import { openProjectHub } from "./project-hub.js";
import { syncRuntimeAssets } from "./runtime-asset-sync.js";
import { arrangeCanvas, bindStudioKeyboard } from "./studio-keyboard.js";
import { icon } from "./icons.js";
import { QUALITY_FEEDBACK_EVENT } from "./quality-feedback.js";
import { handleQualityFeedbackRuntime } from "./quality-feedback-runtime-flow.js";
import { HUMAN_GATE_DECISION_EVENT, HUMAN_GATE_DECISION_RESULT_EVENT } from "./human-gate.js";
import { renderTopbar } from "./studio-topbar.js";
import { ensureAuthSession, signOut } from "./auth-gate.js";
import { initialProjectId } from "./studio-project-session.js";
import { createProjectController } from "./studio-project-controller.js";
import { renderSpriteWidget } from "./sprite-widget.js";
import { formatRuntimeError } from "./runtime-error-utils.js";
import { installClientErrorReporter, reportClientError } from "./client-error-reporter.js";

const VIDEO_ASSET_CARD_DRAFT_EVENT = "afs:video-asset-card-draft";

let runtime = createRuntimeClient(initialProjectId());
let runtimeSurfaceStatus = initialRuntimeSurfaceStatus();
let runtimeSurfaceStatusSequence = 0;
const runtimeRef = new Proxy({}, { get: (_, prop) => runtime[prop] });
const store = createStore(runtime.projectId);
store.attachRuntime(runtime);
installClientErrorReporter({
  getRuntime: () => runtime,
  getProjectId: () => runtime?.projectId || store.get().meta?.projectId || "",
});

const projectController = createProjectController({
  store,
  getRuntime: () => runtime,
  setRuntime: (nextRuntime) => {
    runtime = nextRuntime;
    store.attachRuntime(runtime);
    void refreshRuntimeSurfaceStatus();
  },
  onProjectReady: (runtimeClient) => refreshPendingKeyframeGenerations(store, runtimeClient),
  render: () => renderAll(store.get()),
});

bootstrap().catch((error) => {
  reportClientError({
    event_type: "bootstrap_failed",
    action: "studio_bootstrap",
    message: safeError(error),
    error,
    getRuntime: () => runtime,
    getProjectId: () => runtime?.projectId || store.get().meta?.projectId || "",
  });
  renderAll(store.get());
});

async function bootstrap() {
  projectController.rememberStartupProject(runtime.projectId);
  renderStarters();
  renderDock(store, runtimeRef);
  bindCanvasInput(store, runtimeRef);
  bindCanvasContextMenu(store, runtimeRef, { arrange: () => arrangeCanvas(store) });
  bindStudioKeyboard({ store, runtime: runtimeRef });
  bindQualityFeedback();
  bindHumanGateDecisionEvents();
  bindVideoAssetCardDraft();
  bindStudioWorkflowEvents();

  store.subscribe(renderAll);
  renderAll(store.get());
  void refreshRuntimeSurfaceStatus();

  const authState = await ensureAuthSession(runtime, {
    onAuthenticated: (user) => {
      projectController.setAuthUser(user);
      renderAll(store.get());
    },
  });
  projectController.setAuthUser(authState?.user);
  await refreshRuntimeSurfaceStatus({ authState });
  if (authState?.auth_status_unknown || authState?.blocked) return;
  if (authState?.auth_required && !authState?.authenticated) return;

  await projectController.ensureAccessibleStartupProject();
  await store.hydrateRuntime(runtime);
  await syncRuntimeAssets(store, runtime);
  await refreshPendingKeyframeGenerations(store, runtime);
  await projectController.refreshProjectSummaries();
}

function bindQualityFeedback() {
  window.addEventListener(QUALITY_FEEDBACK_EVENT, (event) => {
    handleQualityFeedbackRuntime({ event, runtime, store });
  });
}

function bindHumanGateDecisionEvents() {
  window.addEventListener(HUMAN_GATE_DECISION_EVENT, (event) => {
    handleHumanGateDecision(event);
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
  const node = resolveEventNode(event) || event.detail?.node;
  const nodeId = String(node?.id || event.detail?.node_id || "");
  if (!nodeId || !runtime?.draftAssetCard) return;
  const sourceVideoArtifactId = String(
    node?.params?.lastVideoArtifactId || node?.params?.lastVideoJobId || "",
  ).trim();
  if (!sourceVideoArtifactId) {
    store.set((s) => {
      const current = s.nodes[nodeId];
      if (!current) return;
      current.result = `${current.result || ""}\n请先生成视频，再识别视频资产卡。`.trim();
    });
    return;
  }
  store.set((s) => {
    const current = s.nodes[nodeId];
    if (!current) return;
    current.params.lastVideoAssetCardDraftStatus = "running";
    current.result = `${current.result || ""}\n正在识别视频资产卡...`.trim();
  }, { history: false, persist: false });
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
      current.result = `${current.result || ""}\n视频资产卡草稿：${response?.job?.status || "unknown"}`.trim();
    });
  } catch (error) {
    store.set((s) => {
      const current = s.nodes[nodeId];
      if (!current) return;
      current.params.lastVideoAssetCardDraftStatus = "failed";
      current.result = `${current.result || ""}\n视频资产卡识别失败：${safeError(error)}`.trim();
    });
  }
}

async function handleHumanGateDecision(event) {
  const requestId = String(event.detail?.request_id || "");
  const payload = event.detail?.payload;
  try {
    if (!payload || typeof payload !== "object") throw new Error("human gate payload is empty");
    const response = await runtime.recordHumanGateDecision(payload);
    const humanGateId = response?.human_gate_decision?.human_gate_id || response?.artifact?.artifact_id || "";
    recordHumanGateDecisionOnNode(payload, humanGateId, response?.job?.status || "succeeded");
    window.dispatchEvent(new CustomEvent(HUMAN_GATE_DECISION_RESULT_EVENT, {
      detail: { request_id: requestId, ok: true, human_gate_id: humanGateId },
    }));
  } catch (error) {
    window.dispatchEvent(new CustomEvent(HUMAN_GATE_DECISION_RESULT_EVENT, {
      detail: { request_id: requestId, ok: false, error: safeError(error) },
    }));
  }
}

function recordHumanGateDecisionOnNode(payload, humanGateId, status) {
  const nodeId = String(payload?.node_id || "");
  if (!nodeId) return;
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    const decisions = Array.isArray(node.params.humanGateDecisions) ? node.params.humanGateDecisions : [];
    node.params.humanGateDecisions = [
      ...decisions,
      {
        human_gate_id: String(humanGateId || ""),
        target_type: String(payload.target_type || ""),
        target_id: String(payload.target_id || ""),
        decision: String(payload.decision || ""),
        status: String(status || ""),
        recorded_at: new Date().toISOString(),
        writes_long_term_memory: false,
      },
    ].slice(-12);
  }, { history: false });
}

function renderAll(state) {
  renderTopbar({
    state,
    store,
    runtime,
    projectSummaries: projectController.summaries,
    projectOptions: projectController.projectOptions(state),
    hiddenProjectCount: projectController.hiddenProjectCount(state),
    showAllProjects: projectController.showAllProjects,
    onToggleProjectFilter: () => projectController.toggleProjectFilter(),
    onSwitchProject: projectController.switchProject,
    onCreateProject: projectController.createNewProject,
    onOpenHome: () => openStudioHome(state),
    onBeforeSiteHome: () => store.flushRuntimeSave(),
    authUser: projectController.authUser,
    runtimeSurfaceStatus,
    onSignOut: async () => {
      await signOut(runtime);
      projectController.setAuthUser(null);
      window.location.href = "/";
    },
  });
  renderCanvas(state, store);
  renderDrawer(state, store, runtimeRef);
  renderInspectorPanel(state, store, runtimeRef);
  renderPromptBar(state, store, runtime);
  renderSpriteWidget(state, runtimeRef);
}

function openStudioHome(state = store.get()) {
  return openProjectHub({
    state,
    runtime,
    projects: projectController.projectOptions(state),
    hiddenProjectCount: projectController.hiddenProjectCount(state),
    onSwitchProject: projectController.switchProject,
    onCreateProject: projectController.createNewProject,
    onDeleteProject: projectController.deleteProject,
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

async function launchStarter(id) {
  if (!hasActiveProject()) {
    const created = await promptCreateProjectBeforeStarter();
    if (!created) return;
  }
  const root = document.getElementById("canvas-root").getBoundingClientRect();
  const cx = (root.width / 2 - store.get().viewport.x) / store.get().viewport.scale;
  const cy = (root.height / 2 - store.get().viewport.y) / store.get().viewport.scale;
  createWorkflowStarter(store, id, { x: cx - 570, y: cy - 160 });
}

function hasActiveProject() {
  const projectId = runtime?.projectId || store.get().meta?.projectId || "";
  return Boolean(projectId && projectId !== "studio-empty" && projectController.summaries.some((item) => item.project_id === projectId));
}

function promptCreateProjectBeforeStarter() {
  return new Promise((resolve) => {
    const modal = el("div", "modal compact project-create-required-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "请先新建项目"));
    const closeBtn = el("button", "modal-close");
    closeBtn.innerHTML = icon("x", 15);
    head.appendChild(el("span", "head-spacer"));
    head.appendChild(closeBtn);

    const body = el("div", "modal-body project-create-required-body");
    body.appendChild(el("p", "", "当前没有项目，不能直接使用模板。"));
    body.appendChild(el("p", "", "请先新建项目，然后系统会在新项目里创建模板节点。"));

    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const create = el("button", "primary-btn", "新建项目");
    actions.append(cancel, create);
    modal.append(head, body, actions);

    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve(false); } });
    const finish = async (value) => {
      if (settled) return;
      settled = true;
      close();
      if (!value) {
        resolve(false);
        return;
      }
      resolve(Boolean(await projectController.createNewProject()));
    };
    cancel.addEventListener("click", () => finish(false));
    closeBtn.addEventListener("click", () => finish(false));
    create.addEventListener("click", () => finish(true));
  });
}

function safeError(error) {
  return formatRuntimeError(error, "unknown error");
}

async function refreshRuntimeSurfaceStatus({ authState = null } = {}) {
  const runtimeClient = runtime;
  const sequence = ++runtimeSurfaceStatusSequence;
  setRuntimeSurfaceStatus(checkingRuntimeSurfaceStatus(runtimeSurfaceStatus));
  const nextStatus = await loadRuntimeSurfaceStatus(runtimeClient, { authState, formatError: safeError });
  if (sequence !== runtimeSurfaceStatusSequence || runtimeClient !== runtime) return;
  setRuntimeSurfaceStatus(nextStatus);
}

function setRuntimeSurfaceStatus(nextStatus) {
  runtimeSurfaceStatus = {
    ...initialRuntimeSurfaceStatus(),
    ...(nextStatus || {}),
  };
  renderAll(store.get());
}
