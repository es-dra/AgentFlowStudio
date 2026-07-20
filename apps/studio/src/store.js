import { loadPersisted, migrateLegacyCanvasStorage, persist } from "./store-persistence.js";
import { emptyNotifyMeta, mergeNotifyMeta } from "./store-notify-meta.js";
import { createRuntimePersistenceController } from "./store-runtime-persistence-controller.js";
import { shouldKeepLocalOverRemote } from "./store-runtime-save.js";
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

export function createStore(projectId = "") {
  migrateLegacyCanvasStorage(projectId);
  let state = loadPersisted(projectId) || initialState(projectId);
  const listeners = new Set();
  const history = { past: [], future: [] };
  let scheduled = false;
  let runtimeClient = null;
  let pendingNotifyMeta = emptyNotifyMeta();
  const runtimePersistence = createRuntimePersistenceController({
    getRuntime: () => runtimeClient,
    getState: () => state,
    notify: notifySoon,
  });

  function get() { return state; }

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
    notifySoon(options);
  }

  function subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }

  function nextId(prefix) { state.meta.seq += 1; return `${prefix}_${state.meta.seq}`; }

  function attachRuntime(runtime) {
    runtimeClient = runtime;
    runtimePersistence.reset();
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
      runtimePersistence.markHydrated(payload?.state_version, snapshotStudioState(remote));
      if (shouldKeepLocalOverRemote(state, remote, payload)) {
        await flushRuntimeSave();
        return { source: "local_newer" };
      }
      if (payload?.source === "runtime" && (hasStudioContent(remote) || hasStudioMeta(remoteState))) {
        replaceSerializable(state, remote);
        persist(state);
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
    runtimePersistence.reset();
    state = loadPersisted(projectId) || initialState(projectId);
    state.meta.projectId = projectId;
    history.past = [];
    history.future = [];
    notifySoon();
    return hydrateRuntime(runtime);
  }

  function resetIdentityState() {
    runtimePersistence.reset();
    runtimeClient = null;
    state = initialState("studio-empty");
    state.meta.projectName = "";
    state.meta.canvasName = "";
    state.nodes = {};
    state.edges = {};
    state.order = [];
    state.assets = [];
    state.selection = { nodeIds: [], edgeId: null };
    history.past = [];
    history.future = [];
    notifySoon();
  }
  function scheduleRuntimeSave() { runtimePersistence.schedule(); }
  async function flushRuntimeSave() { return runtimePersistence.flush(); }
  function setRuntimePersistenceMode(mode = "studio_state") { runtimePersistence.setMode(mode); }

  function notifySoon(meta = {}) {
    pendingNotifyMeta = mergeNotifyMeta(pendingNotifyMeta, meta);
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      const meta = pendingNotifyMeta;
      pendingNotifyMeta = emptyNotifyMeta();
      listeners.forEach((fn) => fn(state, meta));
    });
  }

  return { get, set, subscribe, nextId, attachRuntime, hydrateRuntime, switchProject, resetIdentityState, flushRuntimeSave, setRuntimePersistenceMode, undo, redo };
}
