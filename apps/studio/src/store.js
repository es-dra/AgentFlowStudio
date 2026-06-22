import { loadPersisted, migrateLegacyCanvasStorage, persist } from "./store-persistence.js";
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

export function createStore(projectId = "studio-local-001") {
  migrateLegacyCanvasStorage(projectId);
  let state = loadPersisted(projectId) || initialState(projectId);
  const listeners = new Set();
  const history = { past: [], future: [] };
  let scheduled = false;
  let saveTimer = null;
  let runtimeClient = null;
  let runtimeStateVersion = "";

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
      const remote = normalizeSnapshot(remoteState);
      runtimeStateVersion = String(payload?.state_version || "");
      if (shouldKeepLocalOverRemote(state, remote, payload)) {
        await flushRuntimeSave();
        return { source: "local_newer" };
      }
      if (payload?.source === "runtime" && (hasStudioContent(remote) || hasStudioMeta(remoteState))) {
        remote.meta.projectId = runtime.projectId || state.meta.projectId;
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
    runtimeStateVersion = "";
    clearTimeout(saveTimer);
    state = loadPersisted(projectId) || initialState(projectId);
    state.meta.projectId = projectId;
    history.past = [];
    history.future = [];
    notifySoon();
    return hydrateRuntime(runtime);
  }

  function scheduleRuntimeSave() {
    if (!runtimeClient?.saveStudioState) return;
    clearTimeout(saveTimer);
    state.ui.saveState = "保存中";
    saveTimer = setTimeout(async () => {
      await flushRuntimeSave();
    }, SAVE_DEBOUNCE_MS);
  }

  async function flushRuntimeSave() {
    if (!runtimeClient?.saveStudioState) return;
    clearTimeout(saveTimer);
    try {
      state.ui.saveState = "保存中";
      notifySoon();
      const payload = await runtimeClient.saveStudioState(snapshotStudioState(state), runtimeStateVersion);
      runtimeStateVersion = String(payload?.state_version || runtimeStateVersion || "");
      state.ui.saveState = "已保存";
      state.ui.saveMessage = "";
    } catch (error) {
      state.ui.saveState = "本地暂存";
      state.ui.saveMessage = error?.status === 409
        ? "项目已在其他窗口更新，当前修改已保留在本地暂存；刷新后再继续编辑"
        : "运行服务保存失败，已保留本地暂存";
    }
    notifySoon();
  }

  function notifySoon() {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      listeners.forEach((fn) => fn(state));
    });
  }

  return { get, set, subscribe, nextId, attachRuntime, hydrateRuntime, switchProject, flushRuntimeSave, undo, redo };
}

function shouldKeepLocalOverRemote(localState, remoteState, payload) {
  if (!hasStudioContent(localState) || payload?.source !== "runtime") return false;
  const localUpdated = timestampMs(localState.meta?.updated_at);
  const remoteUpdated = Math.max(
    timestampMs(payload?.saved_at),
    timestampMs(remoteState?.meta?.updated_at),
  );
  return localUpdated > remoteUpdated;
}

function timestampMs(value) {
  const parsed = Date.parse(String(value || ""));
  return Number.isFinite(parsed) ? parsed : 0;
}
