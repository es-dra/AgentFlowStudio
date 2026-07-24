import { restoreCandidateSelectionsAfterLoad } from "./candidate-selection-controller.js";
import { refreshPendingKeyframeGenerations } from "./node-keyframe-actions.js";
import { syncRuntimeAssets } from "./runtime-asset-sync.js";

export async function hydrateStartupProject({
  store,
  runtime,
  projectController,
  hasActiveProject,
  refreshScriptCoreTruth,
  refreshProductionPlanTruth,
}) {
  await projectController.ensureAccessibleStartupProject();
  if (!hasActiveProject()) return;
  const readOnlyProjection = projectController.currentProjectIsReadOnlyProjection?.();
  if (readOnlyProjection) {
    store.setRuntimePersistenceMode?.("production_graph_read_only");
    if (!projectController.currentProjectHasCanonicalGraphAuthority?.()) return;
  }

  await refreshProjectRuntimeDecorations({
    store,
    runtimeClient: runtime,
    refreshScriptCoreTruth,
    refreshProductionPlanTruth,
    syncAssets: true,
    readOnlyProjection,
  });
}

export function createProjectReadyHandler({
  isEditorMounted,
  store,
  refreshScriptCoreTruth,
  refreshProductionPlanTruth,
  refreshProductOverview,
}) {
  return async function handleProjectReady(runtimeClient, options = {}) {
    if (isEditorMounted()) {
      await refreshProjectRuntimeDecorations({
        store,
        runtimeClient,
        refreshScriptCoreTruth,
        refreshProductionPlanTruth,
        isCurrent: options.isCurrent,
      });
    }
    if (options.isCurrent && !options.isCurrent()) return;
    await refreshProductOverview();
  };
}

export async function refreshProjectRuntimeDecorations({
  store,
  runtimeClient,
  refreshScriptCoreTruth,
  refreshProductionPlanTruth,
  syncAssets = false,
  readOnlyProjection = false,
  isCurrent = null,
}) {
  const current = () => !isCurrent || isCurrent();
  if (syncAssets && !readOnlyProjection) await syncRuntimeAssets(store, runtimeClient, { isCurrent: current });
  if (!current()) return { skipped: "stale_project_transition" };
  await restoreCandidateSelectionsAfterLoad(store, runtimeClient, { isCurrent: current });
  if (!current()) return { skipped: "stale_project_transition" };
  await refreshPendingKeyframeGenerations(store, runtimeClient, { isCurrent: current });
  if (!current()) return { skipped: "stale_project_transition" };
  await refreshScriptCoreTruth(runtimeClient);
  if (!current()) return { skipped: "stale_project_transition" };
  await refreshProductionPlanTruth(runtimeClient);
  return current() ? { refreshed: true } : { skipped: "stale_project_transition" };
}
