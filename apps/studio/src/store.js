const STORAGE_KEY_PREFIX = "afs_studio_canvas_v2:";
const STORAGE_KEY = "afs_studio_canvas_v2";
const LEGACY_STORAGE_KEY = "afs_studio_canvas_v1";
const LEGACY_MIGRATION_MARKER = "afs_studio_canvas_v2:legacy_migrated";
const SAVE_DEBOUNCE_MS = 700;
const HISTORY_LIMIT = 80;

export function createStore(projectId = "studio-local-001") {
  migrateLegacyCanvasStorage(projectId);
  let state = loadPersisted(projectId) || initialState(projectId);
  const listeners = new Set();
  const history = { past: [], future: [] };
  let scheduled = false;
  let saveTimer = null;
  let runtimeClient = null;

  function get() {
    return state;
  }

  function set(mutator, options = {}) {
    const before = snapshotStudioState(state);
    mutator(state);
    const after = snapshotStudioState(state);
    const changed = serializableChanged(before, after);
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
      await runtimeClient.saveStudioState(snapshotStudioState(state));
      state.ui.saveState = "已保存";
      state.ui.saveMessage = "";
    } catch {
      state.ui.saveState = "本地暂存";
      state.ui.saveMessage = "运行服务保存失败，已保留本地暂存";
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

function initialState(projectId = "studio-local-001") {
  return {
    meta: {
      projectId,
      seq: 1,
      projectName: "未命名项目",
      canvasName: "画布 1",
      updated_at: new Date().toISOString(),
    },
    viewport: { x: 0, y: 0, scale: 1 },
    nodes: {},
    edges: {},
    groups: {},
    order: [],
    selection: { nodeIds: [], edgeId: null },
    assets: [],
    ui: {
      drawerOpen: true,
      drawerTab: "canvas",
      drawerSearch: "",
      navigatorSearch: "",
      inspectorOpen: true,
      promptExpand: false,
      lastConnectedEdgeId: null,
      saveState: "本地暂存",
      saveMessage: "",
    },
  };
}

function persist(state) {
  try {
    localStorage.setItem(storageKey(state.meta.projectId), JSON.stringify(snapshotStudioState(state)));
  } catch {
    /* 本地持久化失败时静默，画布仍可用 */
  }
}

function loadPersisted(projectId = "studio-local-001") {
  try {
    const raw = localStorage.getItem(storageKey(projectId));
    if (!raw) return null;
    const snap = normalizeSnapshot(JSON.parse(raw));
    if (!hasStudioContent(snap)) return null;
    const base = initialState(projectId);
    replaceSerializable(base, snap);
    base.meta.projectId = projectId;
    return base;
  } catch {
    return null;
  }
}

function migrateLegacyCanvasStorage(projectId = "studio-local-001") {
  try {
    if (localStorage.getItem(LEGACY_MIGRATION_MARKER)) return;
    const targetKey = storageKey(projectId);
    let raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) raw = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (raw && !localStorage.getItem(targetKey)) {
      const snap = normalizeSnapshot(JSON.parse(raw));
      if (hasStudioContent(snap)) {
        snap.meta.projectId = projectId;
        localStorage.setItem(targetKey, JSON.stringify(snap));
      }
    }
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(LEGACY_STORAGE_KEY);
    localStorage.setItem(LEGACY_MIGRATION_MARKER, new Date().toISOString());
  } catch {
    /* Legacy storage cleanup is best-effort; project-scoped state remains authoritative. */
  }
}

export function snapshotStudioState(state) {
  return normalizeSnapshot({
    meta: state.meta,
    viewport: state.viewport,
    nodes: state.nodes,
    edges: state.edges,
    order: state.order,
    assets: state.assets,
  });
}

function normalizeSnapshot(snap) {
  const base = initialState();
  const input = snap && typeof snap === "object" ? snap : {};
  return {
    meta: {
      projectId: String(input.meta?.projectId || base.meta.projectId),
      projectName: String(input.meta?.projectName || base.meta.projectName),
      canvasName: String(input.meta?.canvasName || base.meta.canvasName),
      seq: Number(input.meta?.seq || 1),
      updated_at: String(input.meta?.updated_at || new Date().toISOString()),
    },
    viewport: {
      x: Number(input.viewport?.x || 0),
      y: Number(input.viewport?.y || 0),
      scale: clamp(Number(input.viewport?.scale || 1), 0.18, 2.6),
    },
    nodes: hydrateNodePreviews(input.nodes && typeof input.nodes === "object" ? input.nodes : {}),
    edges: input.edges && typeof input.edges === "object" ? input.edges : {},
    order: Array.isArray(input.order) ? input.order : Object.keys(input.nodes || {}),
    assets: Array.isArray(input.assets) ? input.assets : base.assets,
  };
}

function replaceSerializable(state, snap) {
  state.meta = snap.meta;
  state.viewport = snap.viewport;
  state.nodes = snap.nodes;
  state.edges = snap.edges;
  state.order = snap.order;
  state.assets = snap.assets;
  state.groups = state.groups || {};
  state.selection = { nodeIds: [], edgeId: null };
  state.ui = { ...initialState().ui, ...state.ui };
}

function hydrateNodePreviews(nodes) {
  const result = {};
  for (const [id, node] of Object.entries(nodes || {})) {
    if (!node || typeof node !== "object") continue;
    const next = { ...node, params: { ...(node.params || {}) } };
    if (!next.previewUrl && next.type === "video" && next.params.lastVideoPreviewUrl) {
      next.previewUrl = next.params.lastVideoPreviewUrl;
    } else if (!next.previewUrl && next.type !== "video") {
      const uploads = Array.isArray(next.params.uploads) ? next.params.uploads : [];
      const last = uploads[uploads.length - 1] || null;
      if (last?.preview_url) next.previewUrl = last.preview_url;
    }
    if (next.type === "video" && next.previewUrl && !String(next.previewUrl).includes("/video-generations/")) {
      delete next.previewUrl;
    }
    result[id] = next;
  }
  return result;
}

function hasStudioContent(snap) {
  return Boolean(
    snap
      && (
        Object.keys(snap.nodes || {}).length
        || Object.keys(snap.edges || {}).length
        || (Array.isArray(snap.order) && snap.order.length)
      ),
  );
}

function hasStudioMeta(snap) {
  const meta = snap && typeof snap === "object" ? snap.meta : null;
  return Boolean(
    meta
      && typeof meta === "object"
      && (
        String(meta.projectName || "").trim()
        || String(meta.canvasName || "").trim()
        || String(meta.updated_at || "").trim()
      ),
  );
}

function serializableChanged(before, after) {
  return JSON.stringify(before) !== JSON.stringify(after);
}

function pushHistory(stack, snapshot) {
  stack.push(snapshot);
  if (stack.length > HISTORY_LIMIT) stack.shift();
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function storageKey(projectId) {
  return `${STORAGE_KEY_PREFIX}${projectId || "studio-local-001"}`;
}
