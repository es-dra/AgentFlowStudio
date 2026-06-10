import { createRuntimeClient } from "./runtime-client.js";
import { createActionHandlers } from "./app-actions.js";
import { latestJobId, selectedCard } from "./app-selection.js";
import { syncInputs } from "./input-sync.js";
import { normalizeWorkbenchState } from "./workbench-state.js";
import { renderApp } from "./render.js?v=stage7-rc";
import { state } from "./state.js";
import { configureJobPolling } from "./polling.js";
import { applyProjectTemplate, applySourcePreset } from "./presets.js";
import { bindCanvasInteractions } from "./canvas-interactions.js";
import { bindCanvasHeaderEvents } from "./studio-canvas-header-events.js";

const root = document.querySelector("#app-root");
let silentRefreshInFlight = false;
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
  if (!state.projectId) throw new Error("Project id required.");
  const payload = await client().workbenchState(state.projectId);
  state.workbench = normalizeWorkbenchState(payload);
  const currentExists = state.workbench.canvas_cards.some((card) => card.id === state.selectedCardId);
  state.selectedCardId = currentExists ? state.selectedCardId : state.workbench.canvas_cards[0]?.id || "";
  const variantExists = state.workbench.review_room?.candidates.some((candidate) => candidate.candidate_id === state.selectedVariantId);
  state.selectedVariantId = variantExists ? state.selectedVariantId : state.workbench.review_room?.candidates[0]?.candidate_id || "";
  state.latestAssetTestJobId = latestJobId(state, "asset_test_run");
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
  const selected = state.projects.some((project) => project.project_id === state.projectId);
  if (!selected) {
    state.projectId = preferredProject(state.projects)?.project_id || state.projectId;
    syncProjectInputs(state.projectId);
  }
}

function preferredProject(projects) {
  return [...projects].sort((left, right) => {
    const score = projectScore(right) - projectScore(left);
    if (score) return score;
    return String(right.project_id || "").localeCompare(String(left.project_id || ""));
  })[0];
}

function projectScore(project) {
  const ready = project.status === "ready_for_next_round" ? 10000 : 0;
  const profile = Number(project.profile_version_count || 0) * 1000;
  const feedback = Number(project.feedback_count || 0) * 100;
  const runs = Number(project.run_count || 0) * 10;
  const cards = Number(project.content_card_count || 0);
  return ready + profile + feedback + runs + cards;
}

function syncProjectInputs(projectId) {
  root.querySelectorAll("#project-id-action, #project-id").forEach((node) => {
    node.value = projectId;
  });
}

function runAction(action, dataset = {}) {
  const handlers = {
    "apply-project-template": () => applyProjectTemplate(state, dataset.templateId),
    "apply-source-preset": () => applySourcePreset(state, dataset.sourcePresetId),
    "set-review-intent": () => {
      state.selectedCardId = dataset.cardId || state.selectedCardId;
      state.selectedVariantId = dataset.variantId || state.selectedVariantId;
      state.selectedArtifactId = dataset.artifactId || state.selectedArtifactId;
      state.reviewDecision = dataset.decision || state.reviewDecision;
      state.activeView = dataset.nextView || "Review";
    },
    connect: connectRuntime,
    "load-project": refreshWorkbench,
    refresh: refreshWorkbench,
    ...actionHandlers,
  };
  if (handlers[action]) run(handlers[action]);
}

function bindEvents() {
  root.querySelectorAll("[data-action]").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.dataset.action === "select-project") {
        state.projectId = node.dataset.projectId || state.projectId;
        syncProjectInputs(state.projectId);
        run(refreshWorkbench);
      } else {
        runAction(node.dataset.action, node.dataset);
      }
    });
  });
  root.querySelectorAll("[data-view]").forEach((node) => {
    node.addEventListener("click", () => {
      state.activeView = node.dataset.view || state.activeView;
      if (node.dataset.studioStarter === "open") {
        state.studioStarterMode = true;
        state.studioAddedNodeKind = "";
      }
      paint();
    });
  });
  root.querySelectorAll("[data-studio-starter-kind]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioStarterKind = node.dataset.studioStarterKind || "";
      state.studioAddedNodeKind = "";
      state.studioPanel = ["script", "character", "image", "audio"].includes(state.studioStarterKind) ? "" : "inspector";
      paint();
    });
  });
  root.querySelectorAll("[data-studio-starter]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioStarterMode = node.dataset.studioStarter === "open";
      state.studioAddedNodeKind = "";
      paint();
    });
  });
  root.querySelectorAll("[data-project-portal]").forEach((node) => {
    node.addEventListener("click", () => {
      state.projectPortalMode = node.dataset.projectPortal || "home";
      state.selectedShowcaseId = node.dataset.showcaseId || state.selectedShowcaseId;
      state.portalMenuOpen = false;
      if (state.projectPortalMode !== "showcase-detail") state.showcaseProcessOpen = false;
      paint();
    });
  });
  root.querySelectorAll("[data-portal-menu]").forEach((node) => {
    node.addEventListener("click", () => {
      state.portalMenuOpen = node.dataset.portalMenu === "open";
      paint();
    });
  });
  root.querySelectorAll("[data-showcase-process]").forEach((node) => {
    node.addEventListener("click", () => {
      const intent = node.dataset.showcaseProcess || "";
      if (intent === "open") state.showcaseProcessOpen = true;
      if (intent === "close") state.showcaseProcessOpen = false;
      if (intent === "copy") {
        state.showcaseProcessOpen = false;
        state.projectPortalMode = "home";
        state.activeView = "Create";
      }
      paint();
    });
  });
  root.querySelectorAll("[data-showcase-filter]").forEach((node) => {
    node.addEventListener("click", () => {
      state.showcaseFilter = node.dataset.showcaseFilter || "全部";
      paint();
    });
  });
  root.querySelectorAll("[data-showcase-search]").forEach((node) => {
    node.addEventListener("input", () => {
      state.showcaseQuery = node.value || "";
      paint();
    });
  });
  root.querySelectorAll("[data-process-node]").forEach((node) => {
    node.addEventListener("click", () => {
      state.showcaseProcessNode = node.dataset.processNode || state.showcaseProcessNode;
      paint();
    });
  });
  root.querySelectorAll("[data-studio-tool]").forEach((node) => {
    node.addEventListener("click", () => {
      const panel = node.dataset.studioTool || "";
      if (panel === "add") {
        state.studioAddedNodeKind = "";
        state.studioResourceMode = "";
        state.studioStarterMode = false;
        state.studioStarterKind = "";
      }
      state.studioPanel = state.studioPanel === panel ? "" : panel;
      paint();
    });
  });
  root.querySelectorAll("[data-add-node-kind]").forEach((node) => {
    node.addEventListener("click", () => {
      const cards = state.workbench?.studio_workspace?.canvas?.cards || [];
      const match = cards.find((card) => String(card.kind || "").includes(node.dataset.addNodeKind || ""));
      state.studioAddedNodeKind = node.dataset.addNodeKind || "";
      state.studioResourceMode = "";
      state.studioStarterMode = false;
      state.studioStarterKind = "";
      if (match) {
        state.selectedCardId = match.card_id;
        state.selectedArtifactId = match.primary_artifact_id || "";
      }
      state.studioPanel = "";
      paint();
    });
  });
  root.querySelectorAll("[data-add-resource-kind]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioAddedNodeKind = "";
      state.studioStarterMode = false;
      state.studioStarterKind = "";
      state.studioResourceMode = node.dataset.addResourceKind || "";
      state.studioPanel = "resource";
      paint();
    });
  });
  root.querySelectorAll("[data-execution-intent]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioExecutionIntent = node.dataset.executionIntent || "";
      paint();
    });
  });
  root.querySelectorAll("[data-toolbox-intent]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioToolIntent = node.dataset.toolboxIntent || "";
      paint();
    });
  });
  root.querySelectorAll("[data-card-id]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedCardId = node.dataset.cardId || "";
      state.selectedArtifactId = selectedCard(state)?.primary_artifact_id || "";
      paint();
    });
  });
  root.querySelectorAll("[data-variant-id]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedVariantId = node.dataset.variantId || "";
      state.selectedArtifactId = node.dataset.artifactId || state.selectedArtifactId;
      paint();
    });
  });
  root.querySelectorAll("[data-action='open-artifact-ref']").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedArtifactId = node.dataset.artifactId || state.selectedArtifactId;
      run(actionHandlers["open-selected-artifact"]);
    });
  });
  bindCanvasHeaderEvents(root, state, paint);
  bindCanvasInteractions(root, state, paint);
}

function paint() {
  const portalScrollTop = root.querySelector(".project-portal")?.scrollTop || 0;
  renderApp(root, state);
  bindEvents();
  const portal = root.querySelector(".project-portal");
  if (state.activeView === "Projects" && state.projectPortalMode === "home" && portal) {
    portal.scrollTop = portalScrollTop;
  }
  configureJobPolling(state, refreshWorkbenchSilently);
}

paint();
run(refreshWorkbench);
