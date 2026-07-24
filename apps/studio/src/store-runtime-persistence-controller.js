import { snapshotStudioState } from "./store-state.js";
import { runtimeSaveFailureState, snapshotKey } from "./store-runtime-save.js";

const SAVE_DEBOUNCE_MS = 700;
const STUDIO_STATE_MODE = "studio_state";
const GRAPH_READ_ONLY_MODE = "production_graph_read_only";
const IDENTITY_READ_ONLY_MODE = "identity_read_only";

export function createRuntimePersistenceController({ getRuntime, getState, notify }) {
  let mode = STUDIO_STATE_MODE;
  let stateVersion = "";
  let lastSavedSnapshot = "";
  let saveInFlight = false;
  let saveQueuedAfterSuccess = false;
  let saveTimer = null;

  function reset() {
    clearTimeout(saveTimer);
    mode = STUDIO_STATE_MODE;
    stateVersion = "";
    lastSavedSnapshot = "";
    saveInFlight = false;
    saveQueuedAfterSuccess = false;
    saveTimer = null;
  }

  function markHydrated(nextStateVersion, snapshot) {
    stateVersion = String(nextStateVersion || "");
    lastSavedSnapshot = snapshotKey(snapshot);
  }

  function cancelPendingSave() {
    clearTimeout(saveTimer);
    saveTimer = null;
    saveQueuedAfterSuccess = false;
  }

  function publishGraphReadOnlyStatus() {
    const state = getState();
    state.ui.saveState = "制作图同步";
    state.ui.saveMessage = "画布与故事板由同一制作图版本投影。";
    notify({ renderScope: "save-status" });
  }

  function setMode(requestedMode = STUDIO_STATE_MODE) {
    mode = requestedMode === GRAPH_READ_ONLY_MODE
      ? GRAPH_READ_ONLY_MODE
      : requestedMode === IDENTITY_READ_ONLY_MODE
        ? IDENTITY_READ_ONLY_MODE
        : STUDIO_STATE_MODE;
    if (mode === STUDIO_STATE_MODE) return;
    cancelPendingSave();
    if (mode === IDENTITY_READ_ONLY_MODE) {
      const state = getState();
      state.ui.saveState = "只读缓存";
      state.ui.saveMessage = "连接恢复并重新验证当前项目后，才可继续修改。";
      notify({ renderScope: "save-status" });
      return;
    }
    publishGraphReadOnlyStatus();
  }

  function schedule() {
    const state = getState();
    if (mode !== STUDIO_STATE_MODE || !getRuntime()?.saveStudioState) return;
    if (saveInFlight) {
      saveQueuedAfterSuccess = true;
      state.ui.saveState = "保存中";
      notify({ renderScope: "save-status" });
      return;
    }
    clearTimeout(saveTimer);
    state.ui.saveState = "保存中";
    saveTimer = setTimeout(flush, SAVE_DEBOUNCE_MS);
  }

  async function flush() {
    const runtime = getRuntime();
    const state = getState();
    if (mode !== STUDIO_STATE_MODE || !runtime?.saveStudioState) return;
    clearTimeout(saveTimer);
    saveTimer = null;
    if (saveInFlight) {
      saveQueuedAfterSuccess = true;
      return;
    }
    const snapshot = snapshotStudioState(state);
    const savingSnapshotKey = snapshotKey(snapshot);
    if (lastSavedSnapshot && savingSnapshotKey === lastSavedSnapshot) {
      state.ui.saveState = "已保存";
      state.ui.saveMessage = "";
      notify({ renderScope: "save-status" });
      return;
    }
    saveInFlight = true;
    saveQueuedAfterSuccess = false;
    let flushQueued = false;
    try {
      state.ui.saveState = "保存中";
      notify({ renderScope: "save-status" });
      const payload = await runtime.saveStudioState(snapshot, stateVersion);
      stateVersion = String(payload?.state_version || stateVersion || "");
      lastSavedSnapshot = savingSnapshotKey;
      if (snapshotKey(snapshotStudioState(state)) === savingSnapshotKey) {
        state.ui.saveState = "已保存";
        state.ui.saveMessage = "";
      } else {
        state.ui.saveState = "保存中";
        state.ui.saveMessage = "新修改尚未完成保存，正在继续同步。";
        flushQueued = true;
      }
    } catch (error) {
      const failure = runtimeSaveFailureState(error);
      state.ui.saveState = failure.saveState;
      state.ui.saveMessage = failure.saveMessage;
      saveQueuedAfterSuccess = false;
    } finally {
      saveInFlight = false;
      if (mode === STUDIO_STATE_MODE && (flushQueued || saveQueuedAfterSuccess)) {
        saveQueuedAfterSuccess = false;
        schedule();
      }
      notify({ renderScope: "save-status" });
    }
  }

  return { flush, markHydrated, reset, schedule, setMode };
}
