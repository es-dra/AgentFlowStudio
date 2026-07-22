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

export function failCreativeTask(task, message = "") {
  const next = completeCreativeTask(task, "failed", "failed");
  next.error_category = safeToken(message, 140) || "task_failed";
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
  const shots = scenes.reduce((sum, scene) => sum + (Array.isArray(scene.shots) ? scene.shots.length : 0), 0);
  return {
    scene_count: scenes.length,
    shot_count: shots || Number(plan?.total_shots || 0),
    estimated_duration_sec: Number(plan?.estimated_duration_sec || 0),
  };
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

function elapsedMs(startedAt) {
  const started = Date.parse(startedAt || "");
  if (!Number.isFinite(started)) return 0;
  return Math.max(0, Date.now() - started);
}

function safeToken(value, limit) {
  return String(value || "").replace(/[^A-Za-z0-9_.: -]/g, "_").trim().slice(0, limit);
}
