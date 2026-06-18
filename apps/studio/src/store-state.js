const HISTORY_LIMIT = 80;

export function initialState(projectId = "studio-local-001") {
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
      assetLifecycleFilter: "all",
      navigatorSearch: "",
      inspectorOpen: true,
      promptExpand: false,
      lastConnectedEdgeId: null,
      saveState: "本地暂存",
      saveMessage: "",
    },
  };
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

export function normalizeSnapshot(snap) {
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

export function replaceSerializable(state, snap) {
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

export function hasStudioContent(snap) {
  return Boolean(
    snap
      && (
        Object.keys(snap.nodes || {}).length
        || Object.keys(snap.edges || {}).length
        || (Array.isArray(snap.order) && snap.order.length)
      ),
  );
}

export function hasStudioMeta(snap) {
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

export function serializableChanged(before, after) {
  return JSON.stringify(before) !== JSON.stringify(after);
}

export function pushHistory(stack, snapshot) {
  stack.push(snapshot);
  if (stack.length > HISTORY_LIMIT) stack.shift();
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

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
