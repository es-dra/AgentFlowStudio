import { responseStatusSummary } from "./generation-status-policy.js";

const KIND_LABELS = {
  asset: "资产图生成",
  keyframe: "图片生成",
  video: "视频生成",
  video_revision: "视频修订",
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
  const raw = Array.isArray(response?.candidate_previews) ? response.candidate_previews : [];
  return raw
    .map((item) => normalizeCandidatePreview(item))
    .filter((item) => item.url);
}

export function firstCandidatePreview(response) {
  return candidatePreviewItems(response)[0] || null;
}

function normalizeCandidatePreview(item) {
  if (typeof item === "string") return { url: item };
  const url = item?.preview_url || item?.url || "";
  return {
    url,
    preview_url: item?.preview_url || url,
    width: item?.width || null,
    height: item?.height || null,
    aspect_ratio: item?.aspect_ratio || null,
    artifact_id: item?.artifact_id || null,
  };
}

function progressPercent(response, status, override) {
  if (override === null) return null;
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
