import { loadPersisted, migrateLegacyCanvasStorage, persist } from "./store-persistence.js";
import { runtimeSaveFailureState, shouldKeepLocalOverRemote, snapshotKey } from "./store-runtime-save.js";
import {
  hasStudioContent,
  hasStudioMeta,
  initialState,
  normalizeSnapshot,
  pushHistory,
  replaceSerializable,
  serializableChanged,
  snapshotStudioState,
} from "./store-state.js";

const SAVE_DEBOUNCE_MS = 700;

export function createStore(projectId = "") {
  migrateLegacyCanvasStorage(projectId);
  let state = loadPersisted(projectId) || initialState(projectId);
  const listeners = new Set();
  const history = { past: [], future: [] };
  let scheduled = false;
  let saveTimer = null;
  let runtimeClient = null;
  let runtimeStateVersion = "";
  let lastRuntimeSavedSnapshot = "";
  let saveInFlight = false;
  let saveQueuedAfterSuccess = false;

  function get() {
    return state;
  }

  function set(mutator, options = {}) {
    const before = snapshotStudioState(state);
    mutator(state);
    let after = snapshotStudioState(state);
    const changed = serializableChanged(before, after);
    if (options.persist !== false && changed) {
      state.meta.updated_at = new Date().toISOString();
      after = snapshotStudioState(state);
    }
    if (options.history !== false && changed) {
      pushHistory(history.past, before);
      history.future = [];
    }
    persist(state);
    if (options.persist !== false && changed) scheduleRuntimeSave();
    notifySoon();
  }

  function subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  function nextId(prefix) {
    state.meta.seq += 1;
    return `${prefix}_${state.meta.seq}`;
  }

  function attachRuntime(runtime) {
    runtimeClient = runtime;
    runtimeStateVersion = "";
    lastRuntimeSavedSnapshot = "";
    saveInFlight = false;
    saveQueuedAfterSuccess = false;
    if (runtime?.projectId) state.meta.projectId = runtime.projectId;
    state.ui.saveState = "本地暂存";
    notifySoon();
  }

  async function hydrateRuntime(runtime = runtimeClient) {
    if (!runtime?.loadStudioState) return { source: "local" };
    const targetProjectId = runtime.projectId || state.meta.projectId;
    try {
      state.ui.saveState = "同步中";
      notifySoon();
      const payload = await runtime.loadStudioState();
      if (targetProjectId && state.meta.projectId !== targetProjectId) {
        return { source: "stale", projectId: targetProjectId };
      }
      const remoteState = payload?.state;
      const remote = normalizeSnapshot(targetProjectId ? {
        ...(remoteState && typeof remoteState === "object" ? remoteState : {}),
        meta: { ...(remoteState?.meta && typeof remoteState.meta === "object" ? remoteState.meta : {}), projectId: targetProjectId },
      } : remoteState);
      runtimeStateVersion = String(payload?.state_version || "");
      if (shouldKeepLocalOverRemote(state, remote, payload)) {
        await flushRuntimeSave();
        return { source: "local_newer" };
      }
      if (payload?.source === "runtime" && (hasStudioContent(remote) || hasStudioMeta(remoteState))) {
        replaceSerializable(state, remote);
        persist(state);
        lastRuntimeSavedSnapshot = snapshotKey(snapshotStudioState(state));
        state.ui.saveState = "已保存";
        state.ui.saveMessage = "";
        notifySoon();
        return { source: "runtime" };
      }
      state.ui.saveState = "本地暂存";
      notifySoon();
      return { source: payload?.source || "empty" };
    } catch (error) {
      state.ui.saveState = "本地暂存";
      state.ui.saveMessage = "运行服务不可用，已使用本地暂存";
      notifySoon();
      return { source: "local", error };
    }
  }

  function undo() {
    const previous = history.past.pop();
    if (!previous) return;
    history.future.push(snapshotStudioState(state));
    replaceSerializable(state, previous);
    persist(state);
    scheduleRuntimeSave();
    notifySoon();
  }

  function redo() {
    const next = history.future.pop();
    if (!next) return;
    history.past.push(snapshotStudioState(state));
    replaceSerializable(state, next);
    persist(state);
    scheduleRuntimeSave();
    notifySoon();
  }

  async function switchProject(projectId, runtime) {
    runtimeClient = runtime;
    runtimeStateVersion = "";
    lastRuntimeSavedSnapshot = "";
    saveInFlight = false;
    saveQueuedAfterSuccess = false;
    clearTimeout(saveTimer);
    state = loadPersisted(projectId) || initialState(projectId);
    state.meta.projectId = projectId;
    history.past = [];
    history.future = [];
    notifySoon();
    return hydrateRuntime(runtime);
  }

  function resetIdentityState() { clearTimeout(saveTimer); saveTimer = null; runtimeClient = null; runtimeStateVersion = ""; lastRuntimeSavedSnapshot = ""; saveInFlight = false; saveQueuedAfterSuccess = false; state = initialState("studio-empty"); state.meta.projectName = ""; state.meta.canvasName = ""; state.nodes = {}; state.edges = {}; state.order = []; state.assets = []; state.selection = { nodeIds: [], edgeId: null }; history.past = []; history.future = []; notifySoon(); }
  function scheduleRuntimeSave() {
    if (!runtimeClient?.saveStudioState) return;
    if (saveInFlight) {
      saveQueuedAfterSuccess = true;
      state.ui.saveState = "保存中";
      notifySoon();
      return;
    }
    clearTimeout(saveTimer);
    state.ui.saveState = "保存中";
    saveTimer = setTimeout(async () => {
      await flushRuntimeSave();
    }, SAVE_DEBOUNCE_MS);
  }
  async function flushRuntimeSave() {
    if (!runtimeClient?.saveStudioState) return;
    clearTimeout(saveTimer);
    saveTimer = null;
    if (saveInFlight) {
      saveQueuedAfterSuccess = true;
      return;
    }
    const snapshot = snapshotStudioState(state);
    const savingSnapshotKey = snapshotKey(snapshot);
    if (lastRuntimeSavedSnapshot && savingSnapshotKey === lastRuntimeSavedSnapshot) {
      state.ui.saveState = "已保存";
      state.ui.saveMessage = "";
      notifySoon();
      return;
    }
    saveInFlight = true;
    saveQueuedAfterSuccess = false;
    let flushQueued = false;
    try {
      state.ui.saveState = "保存中";
      notifySoon();
      const payload = await runtimeClient.saveStudioState(snapshot, runtimeStateVersion);
      runtimeStateVersion = String(payload?.state_version || runtimeStateVersion || "");
      lastRuntimeSavedSnapshot = savingSnapshotKey;
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
      if (flushQueued || saveQueuedAfterSuccess) {
        saveQueuedAfterSuccess = false;
        scheduleRuntimeSave();
      }
      notifySoon();
    }
  }

  function notifySoon() {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      listeners.forEach((fn) => fn(state));
    });
  }

  return { get, set, subscribe, nextId, attachRuntime, hydrateRuntime, switchProject, resetIdentityState, flushRuntimeSave, undo, redo };
}
