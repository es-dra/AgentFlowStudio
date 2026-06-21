const KIND_LABELS = {
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
const INDETERMINATE_ACTIVE_STATUSES = new Set(["pending", "running"]);
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
  if (override === null || ACTIVE_STATUSES.has(status)) return null;
  const explicit = override
    ?? response?.job?.progress?.percent
    ?? response?.job?.progress_percent
    ?? response?.progress?.percent
    ?? response?.progress_percent;
  if (explicit == null || explicit === "") return STATUS_PROGRESS[status] ?? (isTerminalStatus(status) ? 100 : null);
  const explicitPercent = Number(explicit);
  if (Number.isFinite(explicitPercent)) return clampPercent(explicitPercent);
  return STATUS_PROGRESS[status] ?? (isTerminalStatus(status) ? 100 : null);
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
  if (status === "succeeded") return "预览已加载到节点，可继续生成、保存素材或整理卡片。";
  if (status === "submitted" || status === "pending") {
    const position = response?.job?.progress?.queue_position ?? response?.progress?.queue_position;
    const pendingCount = response?.job?.progress?.pending_count ?? response?.progress?.pending_count;
    if (Number(position) > 0) return `任务已进入队列，当前排第 ${position} 位${Number(pendingCount) > 0 ? `，队列共 ${pendingCount} 个` : ""}。`;
    return jobId ? `任务 ${jobId} 已进入队列，保持页面打开即可。` : "任务已进入队列，保持页面打开即可。";
  }
  if (status === "running") {
    return jobId ? `任务 ${jobId} 正在生成，完成后会自动显示预览。` : "任务正在生成，完成后会自动显示预览。";
  }
  if (status === "cancelled_local_only" || status === "cancelled") {
    return "这里只停止页面继续刷新，不代表平台侧任务已取消。";
  }
  return "本次没有拿到可用预览，请检查节点菜单中的错误摘要。";
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
