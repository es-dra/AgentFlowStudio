import { responseStatusSummary } from "./generation-status-policy.js";
import { selectReusableAssetAuthority, validatedCandidatePreviewRoute } from "./reusable-asset-authority.js";
import { redactUnsafeText } from "./safe-text-redaction.js";

const KIND_LABELS = {
  asset: "资产图生成",
  keyframe: "图片生成",
  video: "视频生成",
  video_revision: "视频重生成尝试",
};

const STATUS_PROGRESS = {
  succeeded: 100,
  failed: 100,
  blocked: 100,
  error: 100,
  cancelled: 100,
  cancelled_local_only: 100,
};
const ACTIVE_STATUS_PROGRESS = {
  submitted: 8,
  pending: 18,
  running: 58,
};
const ACTIVE_STATUSES = new Set(["submitted", "pending", "running"]);
const SAFE_PREVIEW_ROUTE_RE = /^\/projects\/[a-zA-Z0-9_.-]+\/(?:image-assets\/[a-zA-Z0-9_.-]+\/preview|keyframe-generations\/[a-zA-Z0-9_.-]+\/candidates\/[a-zA-Z0-9_.-]+\/preview|video-generations\/[a-zA-Z0-9_.-]+\/candidates\/[a-zA-Z0-9_.-]+\/preview)$/;
const SAFE_IDENTIFIER_RE = /^[a-zA-Z0-9_.:-]+$/;
const UNSAFE_IDENTIFIER_FRAGMENT_RE = /(?:authorization|auth|token|secret|credential|api[_-]?key|cookie|session)/i;
const ALLOWED_FAILURE_CLASSES = new Set([
  "provider_timeout",
  "provider_gate_closed",
  "provider_policy_block",
  "provider_http_error",
  "provider_not_ready",
  "provider_output_missing",
  "provider_failed",
  "provider_error",
  "validation_block",
  "skipped",
  "remote_vision_gate_closed",
  "remote_vision_provider_not_ready",
]);

export function setSubmittingGenerationState(node, kind, options = {}) {
  const params = ensureParams(node);
  const label = options.label || `${kindLabel(kind)}已提交`;
  const hint = options.hint || "正在等待创作服务返回进度，页面会自动刷新节点。";
  params.jobProgress = {
    percent: options.percent == null ? null : clampPercent(options.percent),
    label,
    hint,
    status: "submitted",
    mode: "queued",
    terminal: false,
  };
  params.progressPercent = params.jobProgress.percent;
  params.generationPolicyStatus = options.retrying ? "retrying" : "";
  params.generationStatusDetail = options.retrying
    ? "Retrying failed items. Preserved outputs remain visible."
    : "Waiting for generation status. Keep the page open.";
  params.generationBlockedReason = "";
  params.generationNextAction = options.retrying
    ? "Wait for Runtime status; provider quota may be used."
    : "Wait for Runtime status; completed outputs will remain visible.";
  params.retryFailedItemsOnly = Boolean(options.retrying);
  if (options.clearPreview !== false) {
    params.candidatePreviewUrls = [];
  }
}

export function updateNodeGenerationState(node, response, options = {}) {
  const params = ensureParams(node);
  const status = String(options.status || response?.job?.status || "blocked");
  const kind = options.kind || "keyframe";
  const progress = {
    percent: progressPercent(response, status, options.percent),
    label: options.label || progressLabel(kind, status),
    hint: options.hint || progressHint(kind, status, response),
    status,
    mode: progressMode(response, status),
    terminal: isTerminalStatus(status),
  };
  params.jobProgress = progress;
  params.progressPercent = progress.percent;
  if (progress.terminal) params.terminalProgress = progress;
  const summary = responseStatusSummary(response, { retrying: options.retrying });
  params.generationPolicyStatus = summary.policyStatus;
  params.generationStatusDetail = summary.detail;
  params.generationBlockedReason = summary.blockedReason;
  params.generationNextAction = summary.nextAction;
  params.generationSafeRefs = summary.safeRefs;
  params.retryFailedItemsOnly = summary.policyStatus === "retrying";
  const candidates = candidatePreviewItems(response);
  if (candidates.length) {
    params.candidatePreviewUrls = candidates;
  }
  return progress;
}

export function candidatePreviewItems(response) {
  const candidates = [];
  const byKey = new Map();
  const blocks = candidateFailureBlocks(response);
  const parentJobId = safeIdentifier(response?.job?.job_id, 160);
  const projectId = trustedEnvelopeProjectId(response);
  const recoveryOutputs = Array.isArray(response?.runtime_recovery?.outputs) ? response.runtime_recovery.outputs : [];
  for (const output of recoveryOutputs) {
    addCandidatePreview(candidates, byKey, normalizeRecoveryCandidate(output, blocks, parentJobId, projectId));
  }
  const raw = Array.isArray(response?.candidate_previews) ? response.candidate_previews : [];
  for (const item of raw) {
    addCandidatePreview(candidates, byKey, normalizeCandidatePreview(item, parentJobId, projectId));
  }
  if (!recoveryOutputs.length) {
    for (const block of blocks) addCandidatePreview(candidates, byKey, normalizeFailedCandidate(block));
  }
  return bindReusableAssetAuthorities(candidates, response?.reusable_image_assets)
    .filter(hasCandidateEvidence);
}

export function firstCandidatePreview(response) {
  return candidatePreviewItems(response).find((item) => item.url || item.preview_url) || null;
}

function normalizeCandidatePreview(item, parentJobId = "", projectId = "") {
  if (typeof item === "string") {
    const url = safePreviewUrl(item);
    if (!url) return null;
    return {
      candidate_id: candidateIdFromUrl(url),
      url,
      preview_url: url,
      status: "succeeded",
      state: "complete",
      preserved: true,
    };
  }
  if (!item || typeof item !== "object") return null;
  const identity = normalizedCandidateIdentity(item, parentJobId, projectId);
  return compactCandidate({
    candidate_id: identity.candidateId,
    canonical_digest: safeSha256(item.canonical_digest || item.sha256),
    parent_job_id: identity.parentJobId,
    project_id: identity.projectId,
    parent_candidate_id: safeIdentifier(item.parent_candidate_id, 160),
    shot_id: safeIdentifier(item.shot_id, 160),
    url: identity.previewUrl,
    preview_url: identity.previewUrl,
    width: safeOptionalCount(item.width, 20000),
    height: safeOptionalCount(item.height, 20000),
    aspect_ratio: safeAspectRatio(item.aspect_ratio),
    artifact_id: safeIdentifier(item.artifact_id, 160),
    byte_count: safeOptionalCount(item.byte_count, 100000000),
    attempt_index: safeOptionalCount(item.attempt_index, 9999),
    requested_count: safeOptionalCount(item.requested_count, 9999),
    returned_count: safeOptionalCount(item.returned_count, 9999),
    status: "succeeded",
    state: "complete",
    preserved: true,
  });
}

function normalizeRecoveryCandidate(item, blocks, parentJobId = "", projectId = "") {
  if (!item || typeof item !== "object") return null;
  const identity = normalizedCandidateIdentity(item, parentJobId, projectId, true);
  const candidateId = identity.candidateId;
  const block = blocks.find((candidateBlock) => safeCandidateId(candidateBlock.candidate_id) === candidateId) || {};
  const url = identity.previewUrl;
  const status = candidateStatus(item.status || item.state || (url ? "succeeded" : ""));
  const state = candidateState(item.state || item.status || status);
  return compactCandidate({
    candidate_id: candidateId,
    canonical_digest: safeSha256(item.canonical_digest || item.sha256),
    parent_job_id: identity.parentJobId,
    project_id: identity.projectId,
    parent_candidate_id: safeIdentifier(item.parent_candidate_id, 160),
    shot_id: safeIdentifier(item.shot_id, 160),
    url,
    preview_url: url,
    width: safeOptionalCount(item.width, 20000),
    height: safeOptionalCount(item.height, 20000),
    aspect_ratio: safeAspectRatio(item.aspect_ratio),
    artifact_id: safeIdentifier(item.artifact_id, 160),
    byte_count: safeOptionalCount(item.byte_count, 100000000),
    attempt_index: safeOptionalCount(item.attempt_index, 9999),
    requested_count: safeOptionalCount(item.requested_count, 9999),
    returned_count: safeOptionalCount(item.returned_count, 9999),
    status,
    state: state || (status === "succeeded" ? "complete" : status),
    preserved: Boolean(item.preserved || status === "succeeded" || state === "complete"),
    failure_class: safeFailureClass(item.failure_class || block.failure_class || block.block_id),
    reason: safeReason(item.reason || block.reason || ""),
  });
}

function normalizeFailedCandidate(block) {
  if (!block || typeof block !== "object") return null;
  return compactCandidate({
    candidate_id: safeCandidateId(block.candidate_id || block.item_id || block.id),
    status: "failed",
    state: "failed",
    preserved: false,
    failure_class: safeFailureClass(block.failure_class || block.block_id || block.reason),
    reason: safeReason(block.reason || block.message || block.error || ""),
    attempt_index: safeOptionalCount(block.attempt_index, 9999),
    requested_count: safeOptionalCount(block.requested_count, 9999),
    returned_count: safeOptionalCount(block.returned_count, 9999),
  });
}

function candidateFailureBlocks(response) {
  const blocks = Array.isArray(response?.safe_manifest?.blocks) ? response.safe_manifest.blocks : [];
  return blocks.filter((block) => block && typeof block === "object");
}

function bindReusableAssetAuthorities(candidates, assets) {
  return candidates.map((candidate) => {
    const authority = selectReusableAssetAuthority(candidate, assets);
    return authority
      ? { ...candidate, reusable_asset_authority: authority, image_asset_id: authority.asset_id }
      : candidate;
  });
}

function normalizedCandidateIdentity(item, parentJobId, projectId, recovery = false) {
  const firstUrl = recovery
    ? firstSafePreviewUrl(item.preview_url, item.previewUrl, item.image_asset_preview_url, item.imageAssetPreviewUrl, item.url)
    : firstSafePreviewUrl(item.preview_url, item.previewUrl, item.url, item.image_asset_preview_url, item.imageAssetPreviewUrl);
  const candidateId = safeCandidateId(
    recovery ? item.item_id || item.candidate_id || item.id : item.candidate_id || item.item_id || item.id,
  ) || candidateIdFromUrl(firstUrl);
  const envelopeJobId = safeIdentifier(parentJobId, 160);
  const rawItemJobId = String(item.parent_job_id || "").trim();
  const itemJobId = safeIdentifier(rawItemJobId, 160);
  const itemJobMatchesEnvelope = !rawItemJobId || (itemJobId && itemJobId === envelopeJobId);
  const normalizedParentJobId = envelopeJobId && itemJobMatchesEnvelope ? envelopeJobId : "";
  const envelopeProjectId = safeIdentifier(projectId, 160);
  const visibilityProjectId = envelopeProjectId || projectIdFromCandidateUrl(firstUrl);
  const route = normalizedParentJobId
    ? validatedCandidatePreviewRoute({
      candidate_id: candidateId,
      parent_job_id: normalizedParentJobId,
      project_id: visibilityProjectId,
      preview_url: item.preview_url,
      url: item.url,
      previewUrl: item.previewUrl,
      image_asset_preview_url: item.image_asset_preview_url,
      imageAssetPreviewUrl: item.imageAssetPreviewUrl,
    })
    : null;
  return {
    candidateId,
    parentJobId: normalizedParentJobId,
    projectId: envelopeProjectId,
    previewUrl: route?.preview_url || "",
  };
}

function trustedEnvelopeProjectId(response) {
  const rawProjectId = String(response?.project_id || "").trim();
  const rawJobProjectId = String(response?.job?.project_id || "").trim();
  const projectId = safeIdentifier(rawProjectId, 160);
  const jobProjectId = safeIdentifier(rawJobProjectId, 160);
  if ((rawProjectId && !projectId) || (rawJobProjectId && !jobProjectId)) return "";
  if (projectId && jobProjectId && projectId !== jobProjectId) return "";
  return projectId || jobProjectId;
}

function projectIdFromCandidateUrl(url) {
  const match = String(url || "").match(/^\/projects\/([^/]+)\/keyframe-generations\//);
  return safeIdentifier(match?.[1], 160);
}

function addCandidatePreview(candidates, byKey, candidate) {
  if (!hasCandidateEvidence(candidate)) return;
  const key = candidateKey(candidate, candidates.length);
  if (byKey.has(key)) {
    Object.assign(byKey.get(key), mergeCandidatePreview(byKey.get(key), candidate));
    return;
  }
  byKey.set(key, candidate);
  candidates.push(candidate);
}

function mergeCandidatePreview(current, next) {
  const merged = { ...current };
  for (const [key, value] of Object.entries(next)) {
    if (value === "" || value == null) continue;
    merged[key] = value;
  }
  if (!next.url && current.url) merged.url = current.url;
  if (!next.preview_url && current.preview_url) merged.preview_url = current.preview_url;
  if (current.status === "succeeded" || next.status === "succeeded") merged.status = "succeeded";
  if (current.state === "complete" || next.state === "complete") merged.state = "complete";
  merged.preserved = Boolean(current.preserved || next.preserved || merged.status === "succeeded");
  return merged;
}

function candidateKey(candidate, fallbackIndex) {
  return candidate.candidate_id || candidate.url || candidate.preview_url || `candidate_${fallbackIndex + 1}`;
}

function hasCandidateEvidence(candidate) {
  return Boolean(candidate && (candidate.url || candidate.preview_url || candidate.candidate_id || candidate.status));
}

function candidateStatus(value) {
  const status = redactedLowerText(value, 80);
  const normalized = status.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (["complete", "completed", "success", "succeeded", "preserved"].includes(normalized)) return "succeeded";
  if (["failed", "failure", "error", "timeout", "timed_out", "poll_failed"].includes(normalized)) return "failed";
  if (["blocked", "needs_attention", "cancelled", "retryable", "partial"].includes(normalized)) return normalized;
  if (/\b(?:complete|completed|success|succeeded|preserved)\b/.test(status)) return "succeeded";
  if (/\b(?:failed|failure|error|timeout|timed out|timed_out|poll_failed)\b/.test(status)) return "failed";
  if (/\b(?:blocked|gate)\b/.test(status)) return "blocked";
  if (/\bneeds[_\s-]?attention\b/.test(status)) return "needs_attention";
  if (/\bcancel/.test(status)) return "cancelled";
  if (/\bretry/.test(status)) return "retryable";
  if (/\bpartial\b/.test(status)) return "partial";
  return "";
}

function safeCandidateId(value) {
  return safeIdentifier(value, 40);
}

function safeSha256(value) {
  const digest = String(value || "").trim().toLowerCase();
  return /^[a-f0-9]{64}$/.test(digest) ? digest : "";
}

function safeReason(value) {
  return redactUnsafeText(value, 180);
}

function candidateState(value) {
  const state = redactedLowerText(value, 80);
  const normalized = state.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (["complete", "completed"].includes(normalized)) return "complete";
  if (/\bcomplete(?:d)?\b/.test(state)) return "complete";
  return candidateStatus(value);
}

function safeFailureClass(value) {
  const text = redactedLowerText(value, 140);
  if (!text) return "";
  const normalized = text.replace(/<redacted>/g, "").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (ALLOWED_FAILURE_CLASSES.has(normalized)) return normalized;
  if (text.includes("timeout") || text.includes("timed out")) return "provider_timeout";
  if (text.includes("gate_closed") || text.includes("gate closed")) return "provider_gate_closed";
  if (text.includes("policy") || text.includes("copyright")) return "provider_policy_block";
  if (text.includes("validation") || text.includes("invalid") || text.includes("unsupported")) return "validation_block";
  if (text.includes("not_ready") || text.includes("not ready") || text.includes("service_not_found")) return "provider_not_ready";
  if (text.includes("missing")) return "provider_output_missing";
  if (text.includes("http")) return "provider_http_error";
  if (text.includes("skipped")) return "skipped";
  return "provider_failed";
}

function safeIdentifier(value, limit) {
  const original = String(value || "").trim();
  if (!original || original.length > limit) return "";
  const redacted = redactUnsafeText(original, 512);
  if (redacted !== original) return "";
  if (UNSAFE_IDENTIFIER_FRAGMENT_RE.test(original)) return "";
  return SAFE_IDENTIFIER_RE.test(original) ? original : "";
}

function firstSafePreviewUrl(...values) {
  for (const value of values) {
    const url = safePreviewUrl(value);
    if (url) return url;
  }
  return "";
}

function safePreviewUrl(value) {
  const original = String(value || "").trim();
  if (!original) return "";
  const redacted = redactUnsafeText(original, 512);
  if (redacted !== original) return "";
  return SAFE_PREVIEW_ROUTE_RE.test(original) ? original : "";
}

function candidateIdFromUrl(url) {
  const match = String(url || "").match(/\/candidates\/([^/]+)\/preview$/);
  return safeCandidateId(match?.[1]);
}

function safeAspectRatio(value) {
  const original = String(value || "").trim();
  if (!original || original.length > 20) return null;
  const redacted = redactUnsafeText(original, 80);
  if (redacted !== original) return null;
  const match = original.match(/^([1-9]\d?):([1-9]\d?)$/);
  return match ? `${Number(match[1])}:${Number(match[2])}` : null;
}

function safeOptionalCount(value, max) {
  if (value == null || value === "") return null;
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Math.max(0, Math.min(max, Math.round(number)));
}

function compactCandidate(candidate) {
  const result = {};
  for (const [key, value] of Object.entries(candidate)) {
    if (value === "" || value == null) continue;
    result[key] = value;
  }
  return result;
}

function redactedLowerText(value, limit) {
  return redactUnsafeText(value, limit).toLowerCase();
}

function progressPercent(response, status, override) {
  if (override === null) return null;
  const mode = response?.job?.progress?.mode || response?.progress?.mode;
  if (String(mode || "") === "indeterminate") return null;
  const explicit = override
    ?? response?.job?.progress?.percent
    ?? response?.job?.progress_percent
    ?? response?.progress?.percent
    ?? response?.progress_percent;
  if (explicit == null || explicit === "") {
    return STATUS_PROGRESS[status]
      ?? ACTIVE_STATUS_PROGRESS[status]
      ?? (isTerminalStatus(status) ? 100 : null);
  }
  const explicitPercent = Number(explicit);
  if (Number.isFinite(explicitPercent)) return clampPercent(explicitPercent);
  return STATUS_PROGRESS[status]
    ?? ACTIVE_STATUS_PROGRESS[status]
    ?? (isTerminalStatus(status) ? 100 : null);
}

function progressMode(response, status) {
  const mode = response?.job?.progress?.mode || response?.progress?.mode;
  if (mode) return String(mode);
  if (status === "submitted" || status === "pending") return "queued";
  if (status === "running") return "indeterminate";
  if (isTerminalStatus(status)) return "complete";
  return "idle";
}

function progressLabel(kind, status) {
  const label = kindLabel(kind);
  if (status === "succeeded") return `${label}已完成`;
  if (status === "submitted" || status === "pending") return `${label}排队中`;
  if (status === "running") return `${label}进行中`;
  if (status === "cancelled_local_only" || status === "cancelled") return "已停止本地刷新";
  return `${label}需要检查`;
}

function progressHint(kind, status, response) {
  const jobId = response?.job?.job_id;
  const timing = progressTiming(response);
  if (status === "succeeded") return "预览已加载到节点，可继续检查、调整或生成下游内容。";
  if (status === "submitted" || status === "pending") {
    const position = response?.job?.progress?.queue_position ?? response?.progress?.queue_position;
    const pendingCount = response?.job?.progress?.pending_count ?? response?.progress?.pending_count;
    const elapsed = timing.elapsed_sec ? `，已等待 ${formatSeconds(timing.elapsed_sec)}` : "";
    if (Number(position) > 0) return `任务已进入队列，当前排第 ${position} 位${Number(pendingCount) > 0 ? `，队列共 ${pendingCount} 个` : ""}${elapsed}。`;
    return jobId ? `任务 ${jobId} 已进入队列${elapsed}，保持页面打开即可。` : `任务已进入队列${elapsed}，保持页面打开即可。`;
  }
  if (status === "running") {
    const running = timing.running_sec ? `，本次生成已运行 ${formatSeconds(timing.running_sec)}` : "";
    const queued = timing.queued_sec ? `，此前排队 ${formatSeconds(timing.queued_sec)}` : "";
    return jobId ? `任务 ${jobId} 正在生成${running}${queued}，完成后会自动显示预览。` : `任务正在生成${running}${queued}，完成后会自动显示预览。`;
  }
  if (status === "cancelled_local_only" || status === "cancelled") {
    return "这里只停止页面继续刷新，不代表平台侧任务已取消。";
  }
  return "本次没有拿到可用预览，请检查节点菜单中的错误摘要。";
}

function progressTiming(response) {
  return response?.job?.progress || response?.progress || {};
}

function formatSeconds(value) {
  const total = Math.max(0, Math.round(Number(value) || 0));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  if (minutes <= 0) return `${seconds}秒`;
  if (seconds === 0) return `${minutes}分`;
  return `${minutes}分${seconds}秒`;
}

function kindLabel(kind) {
  return KIND_LABELS[kind] || "生成";
}

function isTerminalStatus(status) {
  return !ACTIVE_STATUSES.has(status);
}

function ensureParams(node) {
  if (!node.params || typeof node.params !== "object") node.params = {};
  return node.params;
}

function clampPercent(value) {
  return Math.max(0, Math.min(100, Math.round(Number(value) || 0)));
}
