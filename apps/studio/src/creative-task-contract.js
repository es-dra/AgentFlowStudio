export const CREATIVE_TASK_PHASES = [
  "queued",
  "context",
  "dispatching",
  "validating",
  "preview_ready",
  "applying",
  "applied",
  "recovering",
  "failed",
];

export function createLocalCreativeTask(node, actionId, actionType, mode, sourceText = "") {
  return {
    schema_version: "afs.creative_task.v0.1",
    task_id: actionId,
    project_id: "",
    node_id: node?.id || "",
    node_type: node?.type || "",
    node_version: nodeVersion(node, sourceText),
    action_type: actionType,
    mode,
    state: "running",
    phase: "dispatching",
    completed_phases: ["queued", "context"],
    cancel_requested: false,
    result_scope: actionType === "shot_breakdown" ? "candidate_storyboard_subgraph" : "same_node_revision",
    started_at: new Date().toISOString(),
    elapsed_ms: 0,
  };
}

export function normalizeCreativeTask(value, fallback = {}) {
  const raw = value && typeof value === "object" ? value : {};
  const state = safeToken(raw.state || fallback.state || "running", 40);
  const phase = safeToken(raw.phase || fallback.phase || state, 40);
  return {
    schema_version: "afs.creative_task.v0.1",
    task_id: safeToken(raw.task_id || fallback.task_id, 160),
    project_id: safeToken(raw.project_id || fallback.project_id, 120),
    node_id: safeToken(raw.node_id || fallback.node_id, 160),
    node_type: safeToken(raw.node_type || fallback.node_type, 80),
    node_version: safeToken(raw.node_version || fallback.node_version, 120),
    action_type: safeToken(raw.action_type || fallback.action_type, 80),
    mode: safeToken(raw.mode || fallback.mode, 80),
    state,
    phase,
    completed_phases: Array.isArray(raw.completed_phases)
      ? raw.completed_phases.map((item) => safeToken(item, 40)).filter(Boolean)
      : [...(fallback.completed_phases || [])],
    cancel_requested: raw.cancel_requested === true,
    result_scope: safeToken(raw.result_scope || fallback.result_scope, 80),
    error_owner: safeToken(raw.error_owner || fallback.error_owner, 80),
    error_category: safeToken(raw.error_category || fallback.error_category, 120),
    error_detail: safePublicText(raw.error_detail || fallback.error_detail, 360),
    started_at: safeToken(raw.started_at || fallback.started_at, 80),
    completed_at: safeToken(raw.completed_at || fallback.completed_at, 80),
    elapsed_ms: Number(raw.elapsed_ms || fallback.elapsed_ms || 0),
  };
}

export function completeCreativeTask(task, state = "preview_ready", phase = "preview_ready") {
  const next = normalizeCreativeTask(task, { state, phase });
  next.state = state;
  next.phase = phase;
  next.completed_at = new Date().toISOString();
  next.completed_phases = uniquePhases([...(next.completed_phases || []), phase]);
  next.elapsed_ms = elapsedMs(next.started_at);
  return next;
}

export function failCreativeTask(task, category = "", options = {}) {
  const next = completeCreativeTask(task, "failed", "failed");
  const detail = typeof options === "string" ? options : options?.error_detail || options?.detail || "";
  next.error_category = safeToken(category, 140) || "task_failed";
  next.error_owner = safeToken(options?.error_owner || next.error_owner, 80);
  next.error_detail = safePublicText(detail, 360);
  return next;
}

export function taskStateLabel(task) {
  const state = String(task?.state || task?.phase || "").trim();
  if (state === "preview_ready") return "预览可审";
  if (state === "running") return "正在处理";
  if (state === "applying") return "正在应用";
  if (state === "applied") return "已应用";
  if (state === "failed") return "需要处理";
  if (state === "cancelled") return "已取消";
  return "任务状态";
}

export function taskPhaseLabel(phase) {
  return {
    queued: "已排队",
    context: "整理上下文",
    dispatching: "调用文本模型",
    validating: "校验结构",
    preview_ready: "预览可审",
    applying: "写入当前图",
    applied: "已写入",
    recovering: "恢复中",
    failed: "失败",
  }[String(phase || "")] || String(phase || "处理中").replace(/_/g, " ");
}

export function activeEmbeddedTask(node) {
  const action = node?.params?.embeddedCreativeAction;
  if (!action || ["cancelled", "applied"].includes(action.status)) return null;
  return action.creative_task || action.creativeTask || null;
}

export function screenplayCandidateSummary(candidate) {
  const scenes = Array.isArray(candidate?.scenes) ? candidate.scenes : [];
  const chars = Array.isArray(candidate?.characters) ? candidate.characters : [];
  return {
    title: String(candidate?.title || "剧本候选").trim(),
    version: String(candidate?.version_label || "v1").trim(),
    scene_count: scenes.length,
    character_count: chars.length,
    dialogue_blocks: scenes.reduce((sum, scene) => sum + (scene.blocks || []).filter((block) => block.type === "dialogue").length, 0),
    action_blocks: scenes.reduce((sum, scene) => sum + (scene.blocks || []).filter((block) => block.type === "action").length, 0),
  };
}

export function shotPlanSummary(plan) {
  const scenes = Array.isArray(plan?.scenes) ? plan.scenes : [];
  const shotItems = shotPlanShotItems(plan);
  const shots = shotItems.length || Number(plan?.total_shots || 0);
  const validDurations = shotItems.map((shot) => normalizedDurationSeconds(shot?.duration_sec));
  const hasCanonicalShotDurations = validDurations.length > 0 && validDurations.every((value) => value !== null);
  const shotDurationSum = hasCanonicalShotDurations
    ? validDurations.reduce((sum, value) => sum + value, 0)
    : 0;
  const providerEstimate = normalizedDurationSeconds(plan?.estimated_duration_sec);
  const visibleDuration = hasCanonicalShotDurations
    ? shotDurationSum
    : providerEstimate ?? 0;
  return {
    scene_count: scenes.length,
    shot_count: shots,
    estimated_duration_sec: visibleDuration,
    shot_duration_sec_sum: shotDurationSum,
    provider_estimated_duration_sec: providerEstimate ?? 0,
    duration_source: hasCanonicalShotDurations ? "per_shot_sum" : "provider_estimate",
  };
}

export function shotPlanShotItems(plan) {
  const scenes = Array.isArray(plan?.scenes) ? plan.scenes : [];
  return scenes.flatMap((scene) => Array.isArray(scene?.shots) ? scene.shots : []);
}

export function normalizedDurationSeconds(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

export function appliedCreativeActionReceiptText(action = {}) {
  if (action.action_type === "shot_breakdown") {
    const subgraph = action.applied_subgraph || {};
    const plan = subgraph.shot_plan || action.preview?.shot_plan || {};
    const summary = shotPlanSummary(plan);
    const sceneCount = summary.scene_count || Number(subgraph.scene_count || 0);
    const shotCount = summary.shot_count || Number(subgraph.shot_count || 0);
    const duration = Math.round(summary.estimated_duration_sec || Number(subgraph.estimated_duration_sec || 0));
    return `动态分镜已应用：${sceneCount} 场 · ${shotCount} 镜头 · 总时长约 ${duration} 秒。已写入可重载候选分镜子图，请到「故事板」审阅。`;
  }
  return "节点内修订已应用到当前节点；保存后重载会恢复该版本。";
}

export function creativeActionFailureInfo(action = {}) {
  const task = action.creative_task || action.creativeTask || {};
  const category = safeToken(action.error_category || task.error_category || "task_failed", 120) || "task_failed";
  const detail = safePublicText(action.error_detail || task.error_detail || action.error || action.message || "", 420);
  const preserved = safePublicText(action.preserved_state, 360)
    || (action.action_type === "shot_breakdown"
      ? "当前节点和已应用剧本已保留；制作内容没有改变。"
      : "原文已保留并可继续编辑；制作内容没有改变。");
  const nextAction = safePublicText(action.next_action, 360) || failureNextAction(category, action.action_type);
  return {
    category,
    label: failureCategoryLabel(category),
    detail,
    preserved_state: preserved,
    next_action: nextAction,
  };
}

export function failureCategoryLabel(category) {
  return {
    stale_node_version: "节点版本已变化",
    studio_state_conflict: "画布版本冲突",
    studio_state_persistence: "画布状态保存失败",
    runtime_unavailable: "运行服务不可用",
    provider_output_validation: "AI 输出结构未通过校验",
    unsafe_or_invalid_llm_preview: "AI 输出结构未通过校验",
    screenplay_candidate_missing: "剧本结构缺失",
    shot_plan_missing: "分镜结构缺失",
    shot_plan_empty: "分镜为空",
    timeout: "任务超时",
    client_runtime_state: "本地任务状态异常",
    task_failed: "任务失败",
  }[safeToken(category, 120)] || "任务失败";
}

export function nodeVersion(node, sourceText = "") {
  return [
    node?.id || "",
    node?.type || "",
    String(sourceText || node?.content || node?.prompt || "").length,
    node?.params?.currentRevisionId || "",
  ].join(":");
}

function uniquePhases(phases) {
  const seen = new Set();
  return phases.filter((phase) => {
    const key = safeToken(phase, 40);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function failureNextAction(category, actionType) {
  if (category === "stale_node_version" || category === "studio_state_conflict") {
    return "刷新当前项目状态后，从当前节点重新预览。";
  }
  if (category === "provider_output_validation" || category === "unsafe_or_invalid_llm_preview") {
    return actionType === "shot_breakdown"
      ? "保留已扩写剧本，重新预览分镜；若再次失败，先检查剧本是否有清晰场次。"
      : "保留原节点，重新预览剧本化修订。";
  }
  if (category === "timeout") return "可以重新运行文本优化；这次只处理文字内容。";
  return "使用 AI 创作搭档中的重新预览继续；确认前不会改动画布。";
}

function elapsedMs(startedAt) {
  const started = Date.parse(startedAt || "");
  if (!Number.isFinite(started)) return 0;
  return Math.max(0, Date.now() - started);
}

function safePublicText(value, limit) {
  return String(value || "")
    .replace(/\bBearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/\/(?:home|Users|mnt|var|tmp|opt)\/[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

function safeToken(value, limit) {
  return String(value || "").replace(/[^A-Za-z0-9_.: -]/g, "_").trim().slice(0, limit);
}
