import { createStore } from "./store.js";
import { createRuntimeClient } from "./runtime-client.js";
import { checkingRuntimeSurfaceStatus, initialRuntimeSurfaceStatus, loadRuntimeSurfaceStatus } from "./runtime-surface-status.js";
import { renderCanvas } from "./canvas-view.js";
import { bindCanvasInput } from "./canvas-input.js";
import { bindCanvasContextMenu } from "./canvas-context-menu.js";
import { bindCanvasReferenceEntry } from "./canvas-reference-entry.js";
import { renderPromptBar } from "./prompt-bar.js";
import { renderDrawer } from "./panels/drawer.js";
import { renderInspectorPanel } from "./panels/inspector-panel.js";
import { renderDock } from "./panels/dock.js";
import { el, showModal } from "./overlay.js";
import { WORKFLOW_STARTERS, createWorkflowStarter } from "./workflow-starters.js";
import { openProjectHub } from "./project-hub.js";
import { arrangeCanvas, bindStudioKeyboard } from "./studio-keyboard.js";
import { icon } from "./icons.js";
import { QUALITY_FEEDBACK_EVENT } from "./quality-feedback.js";
import { handleQualityFeedbackRuntime } from "./quality-feedback-runtime-flow.js";
import { renderTopbar } from "./studio-topbar.js";
import { ensureAuthSession, signOut } from "./auth-gate.js";
import { clearProjectSession, initialProjectId } from "./studio-project-session.js";
import { clearIdentityScopedStudioState, prepareIdentityStorage } from "./store-persistence.js";
import { createProjectController } from "./studio-project-controller.js";
import { showSecureEntry } from "./product-shell.js";
import { createStudioProductShell, mountStudioDom } from "./studio-product-bootstrap.js";
import { renderSpriteWidget } from "./sprite-widget.js";
import { formatRuntimeError } from "./runtime-error-utils.js";
import { installClientErrorReporter, reportClientError } from "./client-error-reporter.js";
import { createDomainCrewController } from "./domain-crew-controller.js";
import { openDomainCrewPanel } from "./panels/domain-crew-panel.js";
import { openExternalVideoDemoPanel } from "./external-video-demo.js";
import { applyScriptCoreTruthProjection } from "./script-core-truth-projection.js";
import { applyProductionPlanProjection } from "./production-plan-projection.js";
import { fitVisibleCanvasViewport } from "./canvas-safe-area.js";
import { bindHumanGateDecisionEvents, bindStudioWorkflowEvents, bindVideoAssetCardDraft } from "./studio-runtime-events.js";
import { createProjectReadyHandler, hydrateStartupProject } from "./studio-startup-project.js";
import { bindCanvasEmptyOnboarding } from "./studio-canvas-onboarding.js";
import { beginProjectIdentityLoad, clearProjectIdentity } from "./project-identity-gate.js";

let runtime = createRuntimeClient("studio-pending");
let runtimeSurfaceStatus = initialRuntimeSurfaceStatus();
let runtimeSurfaceStatusSequence = 0;
const runtimeRef = new Proxy({}, { get: (_, prop) => runtime[prop] });
let store = null;
let domainCrewController = null;
let projectController = null;
let productShell = null;
let editorMounted = false;
let editorShell = null;
let editorParking = null;
let identityBoundaryInFlight = false;

bootstrap().catch((error) => {
  reportClientError({
    event_type: "bootstrap_failed",
    action: "studio_bootstrap",
    message: safeError(error),
    error,
    getRuntime: () => runtime,
    getProjectId: () => runtime?.projectId || store?.get?.().meta?.projectId || "",
  });
  showSecureEntry("暂时无法打开工作空间，请检查连接后重试。", { error: true });
});
async function bootstrap() {
  showSecureEntry("正在确认账户状态…");
  const authRuntime = createRuntimeClient("studio-pending");
  const authState = await ensureAuthSession(authRuntime);
  if (authState?.auth_status_unknown || authState?.blocked) return;
  if (authState?.auth_required && !authState?.authenticated) return;
  prepareIdentityStorage(authState?.user?.user_id || "local-runtime-user");
  ({ editorMounted, editorParking, editorShell } = mountStudioDom());
  initializeStudio(authState?.user || null);
  projectController.rememberStartupProject(runtime.projectId);
  if (editorMounted) {
    renderDock(store, runtimeRef);
    bindCanvasEmptyOnboarding(store);
    bindCanvasInput(store, runtimeRef);
    bindCanvasContextMenu(store, runtimeRef, { arrange: () => arrangeCanvas(store) });
    bindCanvasReferenceEntry({ store, runtime: runtimeRef });
    bindStudioKeyboard({ store, runtime: runtimeRef });
  }
  bindQualityFeedback();
  bindHumanGateDecisionEvents({ getRuntime: () => runtime, store, safeError });
  bindVideoAssetCardDraft({ getRuntime: () => runtime, store, safeError });
  bindStudioWorkflowEvents({ store, runtimeRef });
  bindCanvasSafeAreaEvents();
  bindDomainCrewEvents();
  bindSaveAuthRecovery();
  bindProjectAccessRecovery();
  bindProjectHistoryNavigation();
  bindSessionExpiryBoundary();

  store.subscribe(renderAll);
  renderAll(store.get());
  void refreshRuntimeSurfaceStatus();
  projectController.setAuthUser(authState?.user);
  await refreshRuntimeSurfaceStatus({ authState });

  await hydrateStartupProject({
    store,
    runtime,
    projectController,
    hasActiveProject,
    refreshScriptCoreTruth,
    refreshProductionPlanTruth,
  });
  await projectController.refreshProjectSummaries(); await refreshProductOverview();
}
function initializeStudio(authUser) {
  runtime = createRuntimeClient(initialProjectId());
  beginProjectIdentityLoad(runtime.projectId, authUser?.user_id || "");
  store = createStore(runtime.projectId, { deferProjectLoad: true });
  domainCrewController = createDomainCrewController({
    getRuntime: () => runtime,
    onNavigateNode: (nodeId) => window.dispatchEvent(new CustomEvent("afs:studio-select-node", { detail: { node_id: nodeId } })),
  });
  productShell = createStudioProductShell({
    onOpenCanvas: openCanvasWorkspace,
    getStore: () => store,
    getCanvasShell: () => editorShell,
    getCanvasParking: () => editorParking,
    getRuntime: () => runtime,
    onSignOut: handleSignOut,
    onSwitchProject: async (projectId) => {
      await projectController.switchProject(projectId);
    },
    onRetry: async () => {
      if (store.get().ui?.projectIdentity?.status === "blocked") {
        await projectController.retryCurrentProject();
      }
      await refreshProductOverview();
    },
    onCreateProject: async () => { if (await projectController?.createNewProject()) await refreshProductOverview(); },
    onDeleteProject: async (project) => { await projectController?.deleteProject(project); await refreshProductOverview(); },
    onOpenExternalVideoDemo: async () => ((!hasActiveProject() && !(await promptCreateProjectBeforeStarter())) ? null : openExternalVideoDemoPanel({ runtime, formatError: safeError })),
    createRuntime: createRuntimeClient,
    isRuntimeCurrent: (candidate) => candidate === runtime,
    formatError: safeError,
    onProjectIdentityInvalid: (error) => projectController.recoverProjectAccessDenied(error),
  });
  productShell.render({ authUser });
  installClientErrorReporter({
    getRuntime: () => runtime,
    getProjectId: () => runtime?.projectId || store?.get?.().meta?.projectId || "",
  });
  projectController = createProjectController({
    store,
    getRuntime: () => runtime,
    setRuntime: (nextRuntime, { attachStore = true } = {}) => {
      runtime = nextRuntime;
      if (attachStore) store.attachRuntime(runtime);
      domainCrewController.setContext({ runtime, userId: projectController.authUser?.user_id || "" });
      void refreshRuntimeSurfaceStatus();
    },
    onProjectReady: createProjectReadyHandler({
      isEditorMounted: () => editorMounted,
      store,
      refreshScriptCoreTruth,
      refreshProductionPlanTruth,
      refreshProductOverview,
    }),
    render: () => renderAll(store.get()),
  });
  projectController.setAuthUser(authUser);
}
async function refreshScriptCoreTruth(runtimeClient = runtime) {
  if (!runtimeClient?.loadScriptTruth || !store) return;
  try {
    const payload = await runtimeClient.loadScriptTruth();
    if (runtimeClient !== runtime) return;
    store.set((state) => {
      applyScriptCoreTruthProjection(state, payload?.projection || {});
      fitCanvasProjection(state);
    }, { history: false, persist: false });
  } catch (error) {
    reportClientError({
      event_type: "script_core_truth_refresh_failed",
      severity: "warning",
      action: "refresh_script_core_truth",
      message: safeError(error),
      error,
      getRuntime: () => runtime,
      getProjectId: () => runtime?.projectId || store?.get?.().meta?.projectId || "",
    });
  }
}
async function refreshProductionPlanTruth(runtimeClient = runtime) {
  if (!runtimeClient?.loadProductionPlanTruth || !store) return;
  try {
    const payload = await runtimeClient.loadProductionPlanTruth();
    if (runtimeClient !== runtime) return;
    store.set((state) => {
      applyProductionPlanProjection(state, payload?.projection || {});
      fitCanvasProjection(state);
    }, { history: false, persist: false });
  } catch (error) {
    reportClientError({
      event_type: "production_plan_truth_refresh_failed",
      severity: "warning",
      action: "refresh_production_plan_truth",
      message: safeError(error),
      error,
      getRuntime: () => runtime,
      getProjectId: () => runtime?.projectId || store?.get?.().meta?.projectId || "",
    });
  }
}
function bindDomainCrewEvents() {
  window.addEventListener("afs:studio-open-domain-crew", () => { syncDomainCrewContext(); openDomainCrewPanel(domainCrewController); });
}
function bindQualityFeedback() {
  window.addEventListener(QUALITY_FEEDBACK_EVENT, (event) => handleQualityFeedbackRuntime({ event, runtime, store }));
}
function bindSaveAuthRecovery() {
  let recoveryInFlight = false;
  window.addEventListener("afs:studio-save-auth-required", (event) => {
    if (recoveryInFlight) return;
    recoveryInFlight = true;
    void recoverSaveAuthBoundary(event.detail?.status).finally(() => {
      recoveryInFlight = false;
    });
  });
}
async function recoverSaveAuthBoundary(status) {
  if (Number(status) === 401 || Number(status) === 403) {
    await recoverExpiredSession();
    return;
  }
  await store.flushRuntimeSave();
}
function bindProjectAccessRecovery() {
  window.addEventListener("afs:project-access-denied", (event) => {
    const deniedProjectId = String(event.detail?.project_id || "");
    if (deniedProjectId && deniedProjectId !== runtime?.projectId) return;
    void projectController.recoverProjectAccessDenied({
      status: 403,
      errorCode: "project_access_denied",
    });
  });
  window.addEventListener("afs:project-identity-invalid", (event) => {
    const invalidProjectId = String(event.detail?.project_id || "");
    if (invalidProjectId && invalidProjectId !== runtime?.projectId) return;
    void projectController.recoverProjectAccessDenied({
      status: Number(event.detail?.status || 0),
      errorCode: String(event.detail?.error_code || ""),
    });
  });
}
function bindProjectHistoryNavigation() {
  window.addEventListener("popstate", () => {
    const projectId = new URLSearchParams(window.location.search || "").get("project") || "studio-empty";
    void projectController.loadRequestedProject(projectId);
  });
}
function bindSessionExpiryBoundary() {
  window.addEventListener("afs:auth-session-expired", () => void recoverExpiredSession());
}
function renderAll(state, meta = {}) {
  syncDomainCrewContext();
  productShell?.updateStudioState(state, { render: shouldRenderProductShell(meta) });
  if (!editorMounted) return;
  bindCanvasEmptyOnboarding(store);
  if (document.getElementById("topbar")) {
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
      onOpenExternalVideoDemo: async () => ((!hasActiveProject() && !(await promptCreateProjectBeforeStarter())) ? null : openExternalVideoDemoPanel({ runtime, formatError: safeError })),
      onOpenHome: openProductOverview,
      onBeforeSiteHome: () => store.flushRuntimeSave(),
      authUser: projectController.authUser,
      onRetrySave: () => store.flushRuntimeSave(),
      runtimeSurfaceStatus,
      onSignOut: handleSignOut,
    });
  }
  renderCanvas(state, store);
  if (document.getElementById("drawer")) renderDrawer(state, store, runtimeRef);
  if (document.getElementById("inspector")) renderInspectorPanel(state, store, runtimeRef);
  renderPromptBar(state, store, runtime);
  renderSpriteWidget(state, runtimeRef);
}

function shouldRenderProductShell(meta = {}) {
  if (meta.full) return true;
  const scopes = Array.isArray(meta.renderScopes) ? meta.renderScopes : [];
  if (scopes.includes("selection-context")) return true;
  if (isCanvasTextEditingActive()) return false;
  if (!scopes.length) return true;
  const shellSafeScopes = new Set(["canvas-local-edit", "save-status"]);
  return !scopes.every((scope) => shellSafeScopes.has(scope));
}

function isCanvasTextEditingActive() {
  const active = document.activeElement;
  if (!active || !["TEXTAREA", "INPUT"].includes(active.tagName)) return false;
  return Boolean(active.closest?.(".node-content-editor, .prompt-bar, .canvas-empty-onboarding"));
}
function syncDomainCrewContext() {
  if (!domainCrewController || !projectController) return;
  domainCrewController.setContext({ runtime, userId: projectController.authUser?.user_id || "" });
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
function openProductOverview() {
  productShell?.showCanvas();
  void refreshProductOverview();
}
function openCanvasWorkspace() {
  if (!editorMounted) return false;
  store.set((state) => {
    state.ui.inspectorOpen = false;
  }, { history: false, persist: false });
  const opened = productShell?.showCanvas() === true;
  if (opened) renderAll(store.get());
  return opened;
}
function renderStarters() {
  const row = document.getElementById("starter-row");
  if (!row) return;
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
  return formatRuntimeError(error, "暂时无法读取制作状态，请稍后重试。");
}

function fitCanvasProjection(state) {
  const nodes = state?.nodes || {};
  if (!document.getElementById("canvas-root") || !Object.keys(nodes).length) return;
  const viewport = fitVisibleCanvasViewport(nodes);
  if (viewport) state.viewport = viewport;
}

function bindCanvasSafeAreaEvents() {
  let raf = 0;
  window.addEventListener("afs:canvas-safe-area-changed", () => {
    window.cancelAnimationFrame(raf);
    raf = window.requestAnimationFrame(() => {
      if (!store || !document.getElementById("canvas-root")) return;
      store.set((state) => {
        if (window.__afsSuppressNextSafeAreaFit) {
          window.__afsSuppressNextSafeAreaFit = false;
          return;
        }
        fitCanvasProjection(state);
      }, { history: false, persist: false });
    });
  });
}

async function refreshProductOverview() {
  if (runtime?.workspaceOverview && productShell) await productShell.refresh(runtime, projectController?.authUser || null);
}

async function handleSignOut() {
  if (identityBoundaryInFlight) return;
  identityBoundaryInFlight = true;
  editorMounted = false;
  const logoutRuntime = runtime;
  store?.resetIdentityState?.();
  clearProjectIdentity();
  projectController?.setAuthUser(null);
  clearProjectSession();
  clearIdentityScopedStudioState();
  showSecureEntry("正在安全退出…");
  try {
    await signOut(logoutRuntime);
  } finally {
    window.location.replace("/studio/");
  }
}
async function recoverExpiredSession() {
  if (identityBoundaryInFlight) return;
  identityBoundaryInFlight = true;
  editorMounted = false;
  store?.resetIdentityState?.();
  clearProjectIdentity();
  projectController?.setAuthUser(null);
  clearProjectSession();
  clearIdentityScopedStudioState();
  showSecureEntry("登录已过期，请重新登录后继续。");
  await signOut(runtime);
  const authState = await ensureAuthSession(createRuntimeClient("studio-pending"), {
    onAuthenticated: () => window.location.reload(),
  });
  if (!authState?.auth_required || authState?.authenticated) window.location.reload();
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
  runtimeSurfaceStatus = { ...initialRuntimeSurfaceStatus(), ...(nextStatus || {}) };
  if (store) renderAll(store.get());
}
