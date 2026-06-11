import { createRuntimeClient } from "./runtime-client.js";
import { createActionHandlers } from "./app-actions.js";
import { selectedCard } from "./app-selection.js";
import { syncInputs } from "./input-sync.js";
import { normalizeWorkbenchState } from "./workbench-state.js";
import { renderApp } from "./render.js?v=libtv-shell-reset-003";
import { state } from "./state.js";
import { configureJobPolling } from "./polling.js";
import { applyProjectTemplate } from "./presets.js";
import { bindCanvasInteractions } from "./canvas-interactions.js";
import { bindCanvasHeaderEvents } from "./studio-canvas-header-events.js";
import { bindStudioExperienceEvents } from "./studio-experience-events.js";
import { directorPromptContext, directorSetupAsset } from "./director-setup-model.js";
import { createCanvasNode, openCanvasNode } from "./studio-node-actions.js";
import { applyCanvasEdgeAction, applyCanvasSelectionAction } from "./canvas-selection-actions.js";
const root = document.querySelector("#app-root");
let silentRefreshInFlight = false;
state.debugMode = new URLSearchParams(window.location.search).get("debug") === "1";

function client() {
  return createRuntimeClient(state.baseUrl);
}

async function run(action) {
  syncInputs(root, state);
  state.loading = true;
  state.error = "";
  paint();
  try {
    await action();
  } catch (error) {
    state.error = error instanceof Error ? error.message : String(error);
  } finally {
    state.loading = false;
    paint();
  }
}

async function connectRuntime() {
  const runtime = client();
  const [health, capabilities, projectsPayload] = await Promise.all([
    runtime.health(),
    runtime.capabilities(),
    runtime.projects(),
  ]);
  state.health = health;
  state.capabilities = capabilities;
  state.projects = Array.isArray(projectsPayload.projects) ? projectsPayload.projects : [];
}

async function loadWorkbench() {
  if (!state.projectId) throw new Error("请先选择项目。");
  const payload = await client().workbenchState(state.projectId);
  state.workbench = normalizeWorkbenchState(payload);
  state.selectedCardId = state.selectedCardId || "script-input";
  state.selectedArtifactId = selectedCard(state)?.primary_artifact_id || state.selectedArtifactId;
}

async function refreshWorkbench() {
  await connectRuntime();
  selectAvailableProject();
  await loadWorkbench();
}

async function refreshWorkbenchSilently() {
  if (!state.projectId || silentRefreshInFlight) return;
  silentRefreshInFlight = true;
  try {
    await connectRuntime();
    await loadWorkbench();
    state.error = "";
  } catch (error) {
    state.error = error instanceof Error ? error.message : String(error);
  } finally {
    silentRefreshInFlight = false;
    paint();
  }
}

const actionHandlers = createActionHandlers({ state, client, refreshWorkbench });

function selectAvailableProject() {
  if (!state.projects.length) return;
  if (state.projects.some((project) => project.project_id === state.projectId)) return;
  state.projectId = preferredProject(state.projects)?.project_id || state.projectId;
  syncProjectInputs(state.projectId);
}

function preferredProject(projects) {
  return [...projects].sort((left, right) => projectScore(right) - projectScore(left))[0];
}

function projectScore(project) {
  const ready = project.status === "ready_for_next_round" ? 10000 : 0;
  const feedback = Number(project.feedback_count || 0) * 100;
  const runs = Number(project.run_count || 0) * 10;
  return ready + feedback + runs + Number(project.content_card_count || 0);
}

function syncProjectInputs(projectId) {
  root.querySelectorAll("#project-id-action, #project-id").forEach((node) => {
    node.value = projectId;
  });
}

function runAction(action, dataset = {}) {
  if (action === "run-node-generation-preview") {
    const surface = dataset.nodeGenerateSurface || "node";
    state.pendingNodeGenerationSurface = surface;
    state.nodeGenerationStatus = {
      ...state.nodeGenerationStatus,
      [surface]: {
        status: "generating",
        message: "正在生成本地预览",
        updatedAt: new Date().toISOString(),
      },
    };
  }
  const handlers = {
    "apply-project-template": () => applyProjectTemplate(state, dataset.templateId),
    "save-director-setup": saveDirectorSetup,
    "apply-director-setup-to-shot": applyDirectorSetupToShot,
    connect: connectRuntime,
    "load-project": refreshWorkbench,
    refresh: refreshWorkbench,
    ...actionHandlers,
  };
  if (handlers[action]) run(() => handlers[action](dataset));
}

function saveDirectorSetup() {
  const timestamp = Date.now();
  state.directorSavedSetupId = state.directorSavedSetupId || `director-setup-${timestamp}`;
  state.directorSaveStatus = "已保存为场景资产";
  state.selectedAssetType = "director_setup";
  state.selectedVisibleAssetId = directorSetupAsset(state).asset_id;
  state.lastResult = {
    status: "director_setup_saved",
    message: directorSetupAsset(state).safe_summary,
  };
}

function applyDirectorSetupToShot() {
  state.directorAppliedShotContext = directorPromptContext(state);
  state.directorSaveStatus = "已应用到当前镜头";
  state.lastResult = {
    status: "director_setup_applied",
    message: "导演台布光、机位和人物站位已作为当前镜头上下文。",
  };
}

function bindEvents() {
  bindActionButtons();
  bindViewButtons();
  bindPortalButtons();
  bindStudioButtons();
  bindSelectionButtons();
  bindCanvasInteractions(root, state, paint);
  bindCanvasHeaderEvents(root, state, paint);
  bindStudioExperienceEvents(root, state, paint);
  state.promptOptimizationOpen = Boolean(state.promptOptimizationOpen);
}

function bindActionButtons() {
  root.querySelectorAll("[data-action]").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.dataset.action === "select-project") {
        state.projectId = node.dataset.projectId || state.projectId;
        syncProjectInputs(state.projectId);
        run(refreshWorkbench);
        return;
      }
      runAction(node.dataset.action, node.dataset);
    });
  });
}

function bindViewButtons() {
  root.querySelectorAll("[data-view]").forEach((node) => {
    node.addEventListener("click", () => {
      state.activeView = node.dataset.view || state.activeView;
      if (node.dataset.studioStarter === "open") {
        state.studioStarterMode = true;
        state.studioAddedNodeKind = "";
      }
      if (node.dataset.studioStarter === "close") {
        state.studioStarterMode = false;
        state.studioStarterKind = "";
        state.studioAddedNodeKind = "";
        state.studioResourceMode = "";
        state.openedCanvasNodeId = "";
        state.nodeOpenTransition = "return";
      }
      paint();
    });
  });
}

function bindPortalButtons() {
  root.querySelectorAll("[data-project-portal]").forEach((node) => {
    node.addEventListener("click", () => {
      state.projectPortalMode = node.dataset.projectPortal || "home";
      paint();
    });
  });
}

function bindStudioButtons() {
  root.querySelectorAll("[data-studio-tool]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioPanel = state.studioPanel === node.dataset.studioTool ? "" : node.dataset.studioTool || "";
      paint();
    });
  });
  root.querySelectorAll("[data-add-node-kind]").forEach((node) => {
    node.addEventListener("click", () => {
      if (state.pendingNodePosition) {
        createCanvasNode(state, node.dataset.addNodeKind || "text");
        paint();
        return;
      }
      state.studioAddedNodeKind = node.dataset.addNodeKind || "";
      state.studioStarterKind = "";
      state.studioResourceMode = "";
      state.studioStarterMode = false;
      state.openedCanvasNodeId = "";
      state.studioPanel = "";
      paint();
    });
  });
  root.querySelectorAll("[data-add-resource-kind]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioAddedNodeKind = "";
      state.studioStarterKind = "";
      state.studioStarterMode = false;
      state.openedCanvasNodeId = "";
      state.studioPanel = "";
      state.studioResourceMode = node.dataset.addResourceKind || "";
      paint();
    });
  });
}

function bindSelectionButtons() {
  root.querySelectorAll("[data-canvas-selection-action]").forEach((node) => {
    node.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      applyCanvasSelectionAction(state, node.dataset.canvasSelectionAction || "clear");
      paint();
    });
  });
  root.querySelectorAll("[data-canvas-edge-action]").forEach((node) => {
    node.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      applyCanvasEdgeAction(state, node.dataset.canvasEdgeAction || "center-edge");
      paint();
    });
  });
  root.querySelectorAll("[data-open-node-kind]").forEach((node) => {
    node.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openCanvasNode(state, node.dataset.openNodeId || state.selectedCardId, node.dataset.openNodeKind || "text");
      paint();
    });
  });
  root.querySelectorAll("[data-card-id]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedCardId = node.dataset.cardId || "script-input";
      state.selectedNodeIds = [state.selectedCardId];
      state.selectedArtifactId = selectedCard(state)?.primary_artifact_id || "";
      state.studioAddedNodeKind = "";
      paint();
    });
  });
  root.querySelectorAll("[data-action='open-artifact-ref']").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedArtifactId = node.dataset.artifactId || state.selectedArtifactId;
      run(actionHandlers["open-selected-artifact"]);
    });
  });
}

function paint() {
  renderApp(root, state);
  bindEvents();
  configureJobPolling(state, refreshWorkbenchSilently);
}

document.addEventListener("keydown", (event) => {
  if (event.altKey && event.key.toLowerCase() === "d") {
    state.debugMode = !state.debugMode;
    paint();
  }
});

paint();
run(refreshWorkbench);
