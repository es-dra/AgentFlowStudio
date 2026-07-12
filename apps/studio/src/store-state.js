import { redactUnsafeText } from "./safe-text-redaction.js";

const HISTORY_LIMIT = 80;
const SAFE_PREVIEW_ROUTE_RE = /^\/projects\/([a-zA-Z0-9_.-]+)\/(?:image-assets\/[a-zA-Z0-9_.-]+\/preview|keyframe-generations\/[a-zA-Z0-9_.-]+\/candidates\/[a-zA-Z0-9_.-]+\/preview|video-generations\/[a-zA-Z0-9_.-]+\/candidates\/[a-zA-Z0-9_.-]+\/preview)$/;
const HTML_ERROR_RE = /<\/?(html|head|body|center|title|h1|hr)\b/i;
const MEDIA_FILENAME_FRAGMENT_RE = /\.(mp4|mov)\b/i;
const FORBIDDEN_RAW_PROVIDER_KEYS = new Set([
  "provider_raw",
  "providerraw",
  "provider_raw_persisted",
  "providerrawpersisted",
  "raw_provider",
  "rawprovider",
  "raw_provider_response",
  "rawproviderresponse",
  "raw_provider_response_stored",
  "rawproviderresponsestored",
  "provider_raw_response",
  "providerrawresponse",
  "provider_raw_response_stored",
  "providerrawresponsestored",
  "provider_response",
  "providerresponse",
  "raw_response",
  "rawresponse",
  "raw_response_stored",
  "rawresponsestored",
  "provider_output_raw",
  "provideroutputraw",
]);
const SAFE_PUBLIC_PROVIDER_KEYS = new Set([
  "no_provider_raw",
  "noproviderraw",
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
  if ("lastGenerationManifest" in next) {
    next.lastGenerationManifest = sanitizeGenerationManifestSummary(next.lastGenerationManifest);
  }
  if ("lastSafeManifest" in next) {
    next.lastSafeManifest = sanitizeGenerationManifestSummary(next.lastSafeManifest);
  }
  if ("lastModelCallContextSummary" in next) {
    next.lastModelCallContextSummary = sanitizeModelCallContextSummary(next.lastModelCallContextSummary);
  }
  for (const key of ["generationStatusDetail", "generationBlockedReason", "generationNextAction"]) {
    if (key in next) next[key] = safePublicStatusText(next[key], 360);
  }
  if ("generationPolicyStatus" in next) {
    const allowed = new Set(["complete", "partially_complete", "failed", "retrying", "needs_attention"]);
    const status = safeToken(next.generationPolicyStatus, 40);
    if (allowed.has(status)) next.generationPolicyStatus = status;
    else delete next.generationPolicyStatus;
  }
  if ("generationSafeRefs" in next) next.generationSafeRefs = sanitizeGenerationSafeRefs(next.generationSafeRefs);
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
    .map((item) => sanitizeCandidatePreview(item, projectId))
    .filter(Boolean)
    .slice(0, 9);
}

function sanitizeCandidatePreview(item, projectId) {
  if (typeof item === "string") {
    const url = safeRuntimePreviewUrl(item, projectId);
    return url ? { url, preview_url: url, status: "succeeded" } : null;
  }
  if (!item || typeof item !== "object") return null;
  const source = stripForbiddenRawProviderFields(item);
  const previewUrl = safeRuntimePreviewUrl(source.preview_url || source.url, projectId);
  const candidate = stripEmpty({
    candidate_id: safeToken(source.candidate_id || source.item_id || source.id, 40),
    status: safeCandidateStatus(source.status || source.state),
    state: safeCandidateState(source.state),
    artifact_id: safeToken(source.artifact_id, 160),
    image_asset_id: safeToken(source.image_asset_id || source.asset_id, 160),
    failure_class: safeToken(source.failure_class || source.block_id, 80),
    reason: safePublicStatusText(source.reason || source.message || source.error, 180),
    width: safeOptionalCount(source.width),
    height: safeOptionalCount(source.height),
    byte_count: safeOptionalCount(source.byte_count),
    aspect_ratio: safeShortText(source.aspect_ratio, 20),
    preserved: Boolean(source.preserved),
  });
  if (previewUrl) {
    candidate.preview_url = previewUrl;
    candidate.url = previewUrl;
    if (!candidate.status) candidate.status = "succeeded";
    if (!candidate.state) candidate.state = "complete";
    candidate.preserved = true;
  }
  if (!candidate.preview_url && !candidate.candidate_id && !candidate.status) return null;
  return candidate;
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
  const lowered = String(key || "").toLowerCase();
  const normalized = lowered.replace(/[^a-zA-Z0-9]+/g, "");
  if (SAFE_PUBLIC_PROVIDER_KEYS.has(lowered) || SAFE_PUBLIC_PROVIDER_KEYS.has(normalized)) return false;
  for (const forbidden of FORBIDDEN_RAW_PROVIDER_KEYS) {
    const forbiddenNorm = forbidden.replace(/[^a-zA-Z0-9]+/g, "");
    if (lowered === forbidden || normalized === forbiddenNorm) return true;
    if (lowered.includes(forbidden) || normalized.includes(forbiddenNorm)) return true;
  }
  return false;
}

function sanitizeGenerationManifestSummary(value) {
  const source = value && typeof value === "object" && !Array.isArray(value)
    ? stripForbiddenRawProviderFields(value)
    : {};
  const blocks = Array.isArray(source.blocks)
    ? source.blocks.map((item) => sanitizeGenerationBlock(item)).filter(Boolean).slice(0, 8)
    : [];
  const retry = source.retry && typeof source.retry === "object" ? source.retry : {};
  const batchSummary = source.batch_summary && typeof source.batch_summary === "object" ? source.batch_summary : {};
  const diagnostics = source.provider_diagnostics && typeof source.provider_diagnostics === "object"
    ? source.provider_diagnostics
    : {};
  return stripEmpty({
    status: safeShortText(source.status, 40),
    batch_status: safeShortText(source.batch_status, 40),
    stage: safeShortText(source.stage || diagnostics.provider_stage, 80),
    failure_class: safeShortText(source.failure_class || diagnostics.failure_class, 80),
    job_id: safeToken(source.job_id, 160),
    node_id: safeToken(source.node_id, 160),
    output_count: safeCount(source.output_count),
    reference_image_count: safeCount(source.reference_image_count),
    retry_count: safeCount(source.retry_count ?? retry.retry_count),
    provider_calls_started: Boolean(source.provider_calls_started),
    provider_diagnostics: sanitizeProviderDiagnostics(diagnostics),
    batch_summary: stripEmpty({
      requested_count: safeCount(batchSummary.requested_count),
      complete_count: safeCount(batchSummary.complete_count),
      retryable_count: safeCount(batchSummary.retryable_count),
      needs_attention_count: safeCount(batchSummary.needs_attention_count),
    }),
    retry: sanitizeRetrySummary(retry),
    blocks,
    review_preview_refs: Array.isArray(source.review_preview_refs)
      ? source.review_preview_refs.map((item) => sanitizePreviewMetadata(item)).filter(Boolean).slice(0, 8)
      : [],
  });
}

function sanitizeGenerationBlock(value) {
  if (!value || typeof value !== "object") return null;
  return stripEmpty({
    block_id: safeToken(value.block_id || value.code, 100),
    candidate_id: safeToken(value.candidate_id, 32),
    reason: safePublicStatusText(value.reason || value.message || value.error, 260),
    required_gate: safeToken(value.required_gate, 80),
    failure_class: safeToken(value.failure_class, 80),
    provider_stage: safeToken(value.provider_stage, 80),
    retry_count: safeCount(value.retry_count),
    attempt_count: safeCount(value.attempt_count),
    provider_elapsed_ms: safeNumber(value.provider_elapsed_ms),
  });
}

function sanitizeProviderDiagnostics(value) {
  if (!value || typeof value !== "object") return {};
  return stripEmpty({
    provider_stage: safeToken(value.provider_stage, 80),
    failure_class: safeToken(value.failure_class, 80),
    error_type: safeToken(value.error_type, 80),
    reason: safePublicStatusText(value.reason, 260),
    required_gate: safeToken(value.required_gate, 80),
    retry_count: safeCount(value.retry_count),
    attempt_count: safeCount(value.attempt_count),
    provider_elapsed_ms: safeNumber(value.provider_elapsed_ms),
  });
}

function sanitizeRetrySummary(value) {
  if (!value || typeof value !== "object") return {};
  return stripEmpty({
    retry_count: safeCount(value.retry_count),
    default_scope: safeToken(value.default_scope, 80),
    retryable_item_ids: safeTokenList(value.retryable_item_ids, 16, 80),
    preserved_item_ids: safeTokenList(value.preserved_item_ids, 16, 80),
    preserve_successful_outputs: Boolean(value.preserve_successful_outputs),
  });
}

function sanitizeGenerationSafeRefs(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    if (!item || typeof item !== "object") return null;
    const ref = {
      label: safeShortText(item.label, 80),
      value: safeToken(item.value, 160),
    };
    return ref.label && ref.value ? ref : null;
  }).filter(Boolean).slice(0, 8);
}

function sanitizePreviewMetadata(value) {
  if (!value || typeof value !== "object") return null;
  const preview = stripEmpty({
    job_id: safeToken(value.job_id, 160),
    candidate_id: safeToken(value.candidate_id, 40),
    safe_preview_ref: safePublicStatusText(value.safe_preview_ref, 220),
    byte_count: safeCount(value.byte_count),
    width: safeCount(value.width),
    height: safeCount(value.height),
    aspect_ratio: safeShortText(value.aspect_ratio, 20),
  });
  return Object.keys(preview).length ? preview : null;
}

function sanitizeModelCallContextSummary(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const source = stripForbiddenRawProviderFields(value);
  return stripEmpty({
    context_id: safeToken(source.context_id, 160),
    schema_version: safeShortText(source.schema_version, 80),
    operation_intent: safeShortText(source.operation_intent, 80),
    generation_target: safeShortText(source.generation_target, 80),
    artifact: sanitizeArtifactRef(source.artifact),
    context_sources: sanitizeCountMap(source.context_sources),
    asset_context: stripEmpty({
      context_eligible_asset_count: safeCount(source.asset_context?.context_eligible_asset_count),
      draft_assets_enter_context: Boolean(source.asset_context?.draft_assets_enter_context),
    }),
    reference_context: sanitizeCountMap(source.reference_context),
    provider_constraints: stripEmpty({
      capability: safeToken(source.provider_constraints?.capability, 40),
      provider_gate: safeToken(source.provider_constraints?.provider_gate, 80),
    }),
    trace_summary: {
      warning_ids: safeTokenList(source.trace_summary?.warning_ids, 12, 160),
      feedback_context_overlay_ids: safeTokenList(source.trace_summary?.feedback_context_overlay_ids, 12, 180),
    },
    safety_boundary: stripEmpty({
      no_secrets: Boolean(source.safety_boundary?.no_secrets),
      no_provider_raw: Boolean(source.safety_boundary?.no_provider_raw),
      no_credentialed_url: Boolean(source.safety_boundary?.no_credentialed_url),
      no_local_path: Boolean(source.safety_boundary?.no_local_path),
      no_media_bytes: Boolean(source.safety_boundary?.no_media_bytes),
      feedback_is_not_memory: Boolean(source.safety_boundary?.feedback_is_not_memory),
      draft_assets_are_not_context_truth: Boolean(source.safety_boundary?.draft_assets_are_not_context_truth),
    }),
    non_claims: safeTokenList(source.non_claims, 12, 160),
  });
}

function sanitizeArtifactRef(value) {
  if (!value || typeof value !== "object") return null;
  return stripEmpty({
    artifact_id: safeToken(value.artifact_id, 160),
    artifact_type: safeToken(value.artifact_type, 120),
    filename: safeFilename(value.filename, 120),
    role: safeToken(value.role, 80),
    media_type: safeToken(value.media_type, 80),
  });
}

function sanitizeCountMap(value) {
  if (!value || typeof value !== "object") return {};
  const result = {};
  for (const [key, item] of Object.entries(value).slice(0, 16)) {
    const safeKey = safeToken(key, 80);
    if (!safeKey) continue;
    if (typeof item === "boolean") result[safeKey] = item;
    else result[safeKey] = safeCount(item);
  }
  return result;
}

function safePublicStatusText(value, limit) {
  return redactUnsafeText(String(value || "")
    .replace(/provider[_\s-]*raw(?:[_\s-]*(?:response|persisted|stored))?/gi, "<provider-response-redacted>")
    .replace(/raw[_\s-]*provider[_\s-]*response(?:[_\s-]*stored)?/gi, "<provider-response-redacted>")
    .replace(/raw[_\s-]*response(?:[_\s-]*stored)?/gi, "<provider-response-redacted>")
    .replace(/provider[_\s-]*response/gi, "<provider-response-redacted>")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>"), limit);
}

function safeShortText(value, limit) {
  return safePublicStatusText(value, limit).replace(/[<>]/g, "").trim();
}

function safeToken(value, limit) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, limit);
}

function safeTokenList(value, maxItems, maxLength) {
  if (!Array.isArray(value)) return [];
  const result = [];
  for (const item of value) {
    const token = safeToken(item, maxLength);
    if (token && !result.includes(token)) result.push(token);
    if (result.length >= maxItems) break;
  }
  return result;
}

function safeFilename(value, limit) {
  return String(value || "").replace(/[\\/]/g, "").replace(/[^a-zA-Z0-9_.-]+/g, "_").slice(0, limit);
}

function safeCount(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(999999, Math.round(number)));
}

function safeOptionalCount(value) {
  if (value == null || value === "") return null;
  return safeCount(value);
}

function safeNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.round(number * 100) / 100);
}

function stripEmpty(value) {
  const result = {};
  for (const [key, item] of Object.entries(value || {})) {
    if (item === "" || item == null) continue;
    if (Array.isArray(item) && !item.length) continue;
    if (typeof item === "object" && !Array.isArray(item) && !Object.keys(item).length) continue;
    result[key] = item;
  }
  return result;
}

function safeCandidateStatus(value) {
  const normalized = safeToken(value, 40).toLowerCase();
  if (["complete", "completed", "success", "succeeded", "preserved"].includes(normalized)) return "succeeded";
  if (["failed", "failure", "error", "timeout", "timed_out"].includes(normalized)) return "failed";
  if (["blocked", "needs_attention", "cancelled", "retryable", "partial"].includes(normalized)) return normalized;
  return "";
}

function safeCandidateState(value) {
  const normalized = safeToken(value, 40).toLowerCase();
  if (["complete", "completed", "failed", "blocked", "retryable", "cancelled", "partial"].includes(normalized)) return normalized;
  return "";
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
