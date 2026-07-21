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
  if (projectController.currentProjectIsReadOnlyProjection?.()) {
    store.setRuntimePersistenceMode?.("production_graph_read_only");
    return;
  }

  await store.hydrateRuntime(runtime);
  await refreshProjectRuntimeDecorations({
    store,
    runtimeClient: runtime,
    refreshScriptCoreTruth,
    refreshProductionPlanTruth,
    syncAssets: true,
  });
}

export function createProjectReadyHandler({
  isEditorMounted,
  store,
  refreshScriptCoreTruth,
  refreshProductionPlanTruth,
  refreshProductOverview,
}) {
  return async function handleProjectReady(runtimeClient) {
    if (isEditorMounted()) {
      await refreshProjectRuntimeDecorations({
        store,
        runtimeClient,
        refreshScriptCoreTruth,
        refreshProductionPlanTruth,
      });
    }
    await refreshProductOverview();
  };
}

export async function refreshProjectRuntimeDecorations({
  store,
  runtimeClient,
  refreshScriptCoreTruth,
  refreshProductionPlanTruth,
  syncAssets = false,
}) {
  if (syncAssets) await syncRuntimeAssets(store, runtimeClient);
  await restoreCandidateSelectionsAfterLoad(store, runtimeClient);
  await refreshPendingKeyframeGenerations(store, runtimeClient);
  await refreshScriptCoreTruth(runtimeClient);
  await refreshProductionPlanTruth(runtimeClient);
}
