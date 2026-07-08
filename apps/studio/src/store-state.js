const HISTORY_LIMIT = 80;
const SAFE_PREVIEW_ROUTE_RE = /^\/projects\/([a-zA-Z0-9_.-]+)\/(?:image-assets\/[a-zA-Z0-9_.-]+\/preview|keyframe-generations\/[a-zA-Z0-9_.-]+\/candidates\/[a-zA-Z0-9_.-]+\/preview|video-generations\/[a-zA-Z0-9_.-]+\/candidates\/[a-zA-Z0-9_.-]+\/preview)$/;
const HTML_ERROR_RE = /<\/?(html|head|body|center|title|h1|hr)\b/i;
const MEDIA_FILENAME_FRAGMENT_RE = /\.(mp4|mov)\b/i;
const FORBIDDEN_RAW_PROVIDER_KEYS = new Set([
  "provider_raw",
  "providerraw",
  "raw_provider",
  "rawprovider",
  "raw_provider_response",
  "rawproviderresponse",
  "provider_raw_response",
  "providerrawresponse",
  "provider_response",
  "providerresponse",
  "raw_response",
  "rawresponse",
  "provider_output_raw",
  "provideroutputraw",
]);

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
      drawerWidth: 196,
      inspectorOpen: true,
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
  const normalized = {
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
  return sanitizeSnapshotForPersistence(normalized);
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

function sanitizeSnapshotForPersistence(snapshot) {
  const projectId = safeProjectId(snapshot?.meta?.projectId);
  const nodes = {};
  for (const [id, node] of Object.entries(snapshot.nodes || {})) {
    if (!node || typeof node !== "object") continue;
    nodes[id] = sanitizeNodeForPersistence(node, projectId);
  }
  return {
    ...snapshot,
    nodes,
    assets: sanitizeAssetsForPersistence(snapshot.assets || [], projectId),
  };
}

function sanitizeNodeForPersistence(node, projectId) {
  const params = sanitizeParamsForPersistence(node.params || {}, projectId);
  const next = stripForbiddenRawProviderFields({ ...node, params });
  const previewUrl = safeRuntimePreviewUrl(next.previewUrl, projectId);
  if (previewUrl && (next.type !== "video" || previewUrl.includes("/video-generations/"))) {
    next.previewUrl = previewUrl;
  } else {
    delete next.previewUrl;
  }
  if (HTML_ERROR_RE.test(String(next.result || ""))) {
    next.result = "图像生成等待超时，已尝试从素材库恢复结果。";
  }
  return next;
}

function sanitizeParamsForPersistence(params, projectId) {
  const next = stripForbiddenRawProviderFields(params);
  if ("uploads" in next) next.uploads = sanitizePreviewList(next.uploads, projectId);
  if ("visualAssets" in next) next.visualAssets = sanitizePreviewList(next.visualAssets, projectId);
  if ("candidatePreviewUrls" in next) {
    next.candidatePreviewUrls = sanitizeCandidatePreviews(next.candidatePreviewUrls, projectId);
  }
  if ("lastVideoPreviewUrl" in next) {
    const lastVideoPreviewUrl = safeRuntimePreviewUrl(next.lastVideoPreviewUrl, projectId);
    if (lastVideoPreviewUrl && lastVideoPreviewUrl.includes("/video-generations/")) {
      next.lastVideoPreviewUrl = lastVideoPreviewUrl;
    } else {
      delete next.lastVideoPreviewUrl;
    }
  } else {
    delete next.lastVideoPreviewUrl;
  }
  return next;
}

function sanitizeAssetsForPersistence(assets, projectId) {
  if (!Array.isArray(assets)) return [];
  return sanitizePreviewList(stripForbiddenRawProviderFields(assets), projectId);
}

function sanitizePreviewList(value, projectId) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => sanitizePreviewObject(item, projectId))
    .filter(Boolean);
}

function sanitizeCandidatePreviews(value, projectId) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === "string") {
        const url = safeRuntimePreviewUrl(item, projectId);
        return url ? { url, preview_url: url } : null;
      }
      const next = sanitizePreviewObject(item, projectId);
      if (!next?.preview_url) return null;
      next.url = next.preview_url;
      return next;
    })
    .filter(Boolean);
}

function sanitizePreviewObject(item, projectId) {
  if (!item || typeof item !== "object") return null;
  const next = stripForbiddenRawProviderFields(item);
  sanitizeMediaRefDisplayFields(next);
  const previewUrl = safeRuntimePreviewUrl(next.preview_url || next.url, projectId);
  if (previewUrl) {
    next.preview_url = previewUrl;
    if ("url" in next) next.url = previewUrl;
  } else {
    delete next.preview_url;
    delete next.url;
  }
  return next;
}

function stripForbiddenRawProviderFields(value, seen = new WeakSet()) {
  if (!value || typeof value !== "object") return value;
  if (seen.has(value)) return null;
  seen.add(value);
  try {
    if (Array.isArray(value)) {
      return value.map((item) => stripForbiddenRawProviderFields(item, seen));
    }
    const next = {};
    for (const [key, item] of Object.entries(value)) {
      if (isForbiddenRawProviderKey(key)) continue;
      next[key] = stripForbiddenRawProviderFields(item, seen);
    }
    return next;
  } finally {
    seen.delete(value);
  }
}

function isForbiddenRawProviderKey(key) {
  const normalized = String(key || "").replace(/[^a-zA-Z0-9]+/g, "").toLowerCase();
  return FORBIDDEN_RAW_PROVIDER_KEYS.has(String(key || "").toLowerCase()) || FORBIDDEN_RAW_PROVIDER_KEYS.has(normalized);
}

function sanitizeMediaRefDisplayFields(item) {
  for (const key of ["title", "safe_summary", "thumbnail_ref", "label"]) {
    if (!(key in item)) continue;
    item[key] = stripMediaFilenameFragment(item[key]);
    if (!item[key]) delete item[key];
  }
  for (const key of ["filename", "download_filename"]) {
    if (!(key in item)) continue;
    if (hasMediaFilenameFragment(item[key])) delete item[key];
    else item[key] = String(item[key] || "").replace(/[\\/]/g, "").trim();
  }
}

function stripMediaFilenameFragment(value) {
  return String(value || "").replace(MEDIA_FILENAME_FRAGMENT_RE, "").trim();
}

function hasMediaFilenameFragment(value) {
  return MEDIA_FILENAME_FRAGMENT_RE.test(String(value || ""));
}

function safeRuntimePreviewUrl(value, projectId) {
  const text = String(value || "").trim();
  if (!text) return "";
  const match = SAFE_PREVIEW_ROUTE_RE.exec(text);
  if (!match) return "";
  if (projectId && match[1] !== projectId) return "";
  return text;
}

function safeProjectId(value) {
  return String(value || "")
    .trim()
    .replace(/[^a-zA-Z0-9_.-]+/g, "-")
    .replace(/^[-._]+|[-._]+$/g, "");
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
