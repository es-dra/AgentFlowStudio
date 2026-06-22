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
import { el } from "./overlay.js";
import { fixNodeVisualAsset, startNodeGeneration } from "./node-actions.js";
import { refreshPendingKeyframeGenerations } from "./node-keyframe-actions.js";
import { WORKFLOW_STARTERS, createWorkflowStarter } from "./workflow-starters.js";
import { openProjectHub } from "./project-hub.js";
import { syncRuntimeAssets } from "./runtime-asset-sync.js";
import { arrangeCanvas, bindStudioKeyboard } from "./studio-keyboard.js";
import { icon } from "./icons.js";
import { QUALITY_FEEDBACK_EVENT, QUALITY_FEEDBACK_RESULT_EVENT } from "./quality-feedback.js";
import { renderTopbar } from "./studio-topbar.js";
import { ensureAuthSession, signOut } from "./auth-gate.js";
import { initialProjectId } from "./studio-project-session.js";
import { createProjectController } from "./studio-project-controller.js";
import { renderSpriteWidget } from "./sprite-widget.js";

const VIDEO_ASSET_CARD_DRAFT_EVENT = "afs:video-asset-card-draft";

let runtime = createRuntimeClient(initialProjectId());
const runtimeRef = new Proxy({}, { get: (_, prop) => runtime[prop] });
const store = createStore(runtime.projectId);
store.attachRuntime(runtime);

const projectController = createProjectController({
  store,
  getRuntime: () => runtime,
  setRuntime: (nextRuntime) => {
    runtime = nextRuntime;
    store.attachRuntime(runtime);
  },
  onProjectReady: (runtimeClient) => refreshPendingKeyframeGenerations(store, runtimeClient),
  render: () => renderAll(store.get()),
});

bootstrap().catch((error) => {
  console.error("AFS Studio bootstrap failed", safeError(error));
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
  bindVideoAssetCardDraft();
  bindStudioWorkflowEvents();

  store.subscribe(renderAll);
  renderAll(store.get());

  const authState = await ensureAuthSession(runtime, {
    onAuthenticated: (user) => {
      projectController.setAuthUser(user);
      renderAll(store.get());
    },
  });
  projectController.setAuthUser(authState?.user);
  if (authState?.auth_required && !authState?.authenticated) return;

  await projectController.ensureAccessibleStartupProject();
  await store.hydrateRuntime(runtime);
  await syncRuntimeAssets(store, runtime);
  await refreshPendingKeyframeGenerations(store, runtime);
  await projectController.refreshProjectSummaries();
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
  const sourceVideoArtifactId = String(
    node?.params?.lastVideoArtifactId || node?.params?.lastVideoJobId || "",
  ).trim();
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

function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  return message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 180);
}
