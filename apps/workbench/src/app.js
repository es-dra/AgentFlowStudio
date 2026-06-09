import { createRuntimeClient } from "./runtime-client.js";
import { createActionHandlers } from "./app-actions.js";
import { latestJobId, selectedCard } from "./app-selection.js";
import { syncInputs } from "./input-sync.js";
import { normalizeWorkbenchState } from "./workbench-state.js";
import { renderApp } from "./render.js?v=stage7-rc";
import { state } from "./state.js";
import { configureJobPolling } from "./polling.js";
import { applyProjectTemplate, applySourcePreset } from "./presets.js";

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
      paint();
    });
  });
  root.querySelectorAll("[data-studio-focus]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioFocus = node.dataset.studioFocus || state.studioFocus;
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
}

function paint() {
  renderApp(root, state);
  bindEvents();
  configureJobPolling(state, refreshWorkbenchSilently);
}

paint();
run(refreshWorkbench);
