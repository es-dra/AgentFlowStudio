const STORAGE_KEY_PREFIX = "afs_studio_canvas_v2:";
const STORAGE_KEY = "afs_studio_canvas_v2";
const LEGACY_STORAGE_KEY = "afs_studio_canvas_v1";
const SAVE_DEBOUNCE_MS = 700;
const HISTORY_LIMIT = 80;

export function createStore(projectId = "studio-local-001") {
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
    try {
      state.ui.saveState = "同步中";
      notifySoon();
      const payload = await runtime.loadStudioState();
      const remote = normalizeSnapshot(payload?.state);
      if (payload?.source === "runtime" && hasStudioContent(remote)) {
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
    state = loadPersisted(projectId) || initialState(projectId);
    state.meta.projectId = projectId;
    notifySoon();
    return hydrateRuntime(runtime);
  }

  function scheduleRuntimeSave() {
    if (!runtimeClient?.saveStudioState) return;
    clearTimeout(saveTimer);
    state.ui.saveState = "保存中";
    saveTimer = setTimeout(async () => {
      try {
        await runtimeClient.saveStudioState(snapshotStudioState(state));
        state.ui.saveState = "已保存";
        state.ui.saveMessage = "";
      } catch {
        state.ui.saveState = "本地暂存";
        state.ui.saveMessage = "运行服务保存失败，已保留本地暂存";
      }
      notifySoon();
    }, SAVE_DEBOUNCE_MS);
  }

  function notifySoon() {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      listeners.forEach((fn) => fn(state));
    });
  }

  return { get, set, subscribe, nextId, attachRuntime, hydrateRuntime, switchProject, undo, redo };
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
    assets: seedAssets(),
    ui: {
      drawerOpen: true,
      drawerTab: "canvas",
      promptExpand: false,
      lastConnectedEdgeId: null,
      saveState: "本地暂存",
      saveMessage: "",
    },
  };
}

function seedAssets() {
  return [
    {
      id: "asset_director_seed",
      kind: "director_setup",
      title: "夜间卧室布光参考",
      safe_summary: "1 个机位 / 1 个主体 / 3 盏灯，低照度情绪场景。",
      thumbnail_ref: "director-board",
      source_node_id: null,
      status: "reference",
    },
    {
      id: "asset_character_seed",
      kind: "character_turnaround",
      title: "角色三视图占位",
      safe_summary: "保持服装、发型、体态连续性的角色参考。",
      thumbnail_ref: "character-sheet",
      source_node_id: null,
      status: "reference",
    },
    {
      id: "asset_keyframe_seed",
      kind: "keyframe",
      title: "电影感关键帧占位",
      safe_summary: "用于测试关键帧提示词、镜头和灯光约束。",
      thumbnail_ref: "keyframe",
      source_node_id: null,
      status: "reference",
    },
  ];
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
    const raw = localStorage.getItem(storageKey(projectId)) || localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
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
    if (!next.previewUrl) {
      const uploads = Array.isArray(next.params.uploads) ? next.params.uploads : [];
      const last = uploads[uploads.length - 1] || null;
      if (last?.preview_url) next.previewUrl = last.preview_url;
    }
    result[id] = next;
  }
  return result;
}

function hasStudioContent(snap) {
  return Boolean(snap && (Object.keys(snap.nodes || {}).length || Object.keys(snap.edges || {}).length || (snap.assets || []).length));
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
