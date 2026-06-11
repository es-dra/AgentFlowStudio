const STORAGE_KEY = "afs_studio_canvas_v1";

export function createStore() {
  const state = loadPersisted() || initialState();
  const listeners = new Set();
  let scheduled = false;

  function get() {
    return state;
  }

  function set(mutator) {
    mutator(state);
    persist(state);
    if (!scheduled) {
      scheduled = true;
      queueMicrotask(() => {
        scheduled = false;
        listeners.forEach((fn) => fn(state));
      });
    }
  }

  function subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  function nextId(prefix) {
    state.meta.seq += 1;
    return `${prefix}_${state.meta.seq}`;
  }

  return { get, set, subscribe, nextId };
}

function initialState() {
  return {
    meta: { seq: 1, projectName: "未命名项目", canvasName: "画布 1" },
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
      promptExpand: false,
      lastConnectedEdgeId: null,
    },
  };
}

function persist(state) {
  try {
    const snapshot = {
      meta: state.meta,
      viewport: state.viewport,
      nodes: state.nodes,
      edges: state.edges,
      groups: state.groups,
      order: state.order,
      assets: state.assets,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  } catch {
    /* 本地持久化失败时静默，画布仍可用 */
  }
}

function loadPersisted() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const snap = JSON.parse(raw);
    if (!snap || typeof snap !== "object" || !snap.nodes) return null;
    return {
      ...initialState(),
      meta: snap.meta || initialState().meta,
      viewport: snap.viewport || { x: 0, y: 0, scale: 1 },
      nodes: snap.nodes || {},
      edges: snap.edges || {},
      groups: snap.groups || {},
      order: snap.order || Object.keys(snap.nodes || {}),
      assets: snap.assets || [],
    };
  } catch {
    return null;
  }
}

export function clearPersisted() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* noop */
  }
}
