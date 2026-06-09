function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeOperationsWorkspace(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Operations workspace"),
    summary: String(source.summary || ""),
    selected_job_id: String(source.selected_job_id || ""),
    counts: normalizeOperationsCounts(source.counts),
    job_queue: asArray(source.job_queue).map(normalizeJobItem),
    latest_activity: asArray(source.latest_activity).map(normalizeOperationActivity),
    provider_gate: normalizeProviderGate(source.provider_gate),
    provider_controls: normalizeProviderControls(source.provider_controls),
    polling: normalizePolling(source.polling),
    non_claims: asArray(source.non_claims).map(String),
  };
}

export function normalizeJobCenter(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Job center"),
    summary: String(source.summary || ""),
    counts: normalizeJobCounts(source.counts),
    items: asArray(source.items).map(normalizeJobItem),
    polling: normalizePolling(source.polling),
    non_claims: asArray(source.non_claims).map(String),
  };
}

export function normalizeJobCounts(value) {
  const source = asObject(value);
  return {
    total: Number(source.total || 0),
    running: Number(source.running || 0),
    blocked: Number(source.blocked || 0),
    failed: Number(source.failed || 0),
    succeeded: Number(source.succeeded || 0),
  };
}

export function normalizeJobItem(value) {
  const source = asObject(value);
  return {
    job_id: String(source.job_id || ""),
    action: String(source.action || ""),
    title: String(source.title || "Runtime job"),
    status: String(source.status || "not_started"),
    stage: String(source.stage || ""),
    percent: Number(source.percent || 0),
    terminal: source.terminal === true,
    primary_artifact_id: String(source.primary_artifact_id || ""),
    artifact_ids: asArray(source.artifact_ids).map(String),
    artifact_count: Number(source.artifact_count || 0),
    guidance: String(source.guidance || ""),
  };
}

function normalizeOperationsCounts(value) {
  const source = asObject(value);
  return {
    jobs: Number(source.jobs || 0),
    running: Number(source.running || 0),
    blocked: Number(source.blocked || 0),
    failed: Number(source.failed || 0),
    succeeded: Number(source.succeeded || 0),
    activities: Number(source.activities || 0),
    artifact_refs: Number(source.artifact_refs || 0),
    provider_blockers: Number(source.provider_blockers || 0),
  };
}

function normalizeOperationActivity(value) {
  const source = asObject(value);
  return {
    event_id: String(source.event_id || "activity"),
    title: String(source.title || "Runtime event"),
    action: String(source.action || ""),
    status: String(source.status || "not_started"),
    job_id: String(source.job_id || ""),
    primary_artifact_id: String(source.primary_artifact_id || ""),
    artifact_ids: asArray(source.artifact_ids).map(String),
    artifact_count: Number(source.artifact_count || 0),
  };
}

function normalizeProviderGate(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "ready_not_run"),
    title: String(source.title || "Provider preflight"),
    summary: String(source.summary || "Provider preflight has not run."),
    primary_artifact_id: String(source.primary_artifact_id || ""),
    blockers: asArray(source.blockers).map(normalizeBlocker),
    actions: asArray(source.actions).map(String),
  };
}

function normalizeProviderControls(value) {
  const source = asObject(value);
  return {
    primary_action: String(source.primary_action || "run_provider_preflight"),
    primary_label: String(source.primary_label || "Run provider preflight"),
    ui_action: String(source.ui_action || ""),
    enabled: source.enabled === true,
    handoff_view: String(source.handoff_view || "Jobs"),
    summary: String(source.summary || ""),
    blocked_reason: String(source.blocked_reason || ""),
    requires_input: asArray(source.requires_input).map(String),
  };
}

function normalizePolling(value) {
  const source = asObject(value);
  return {
    enabled: source.enabled === true,
    manual_refresh_action: String(source.manual_refresh_action || "refresh"),
    suggested_interval_ms: Number(source.suggested_interval_ms || 5000),
    scope: String(source.scope || "current_project_jobs"),
  };
}

function normalizeBlocker(value) {
  const source = asObject(value);
  if (!Object.keys(source).length) {
    const text = String(value || "blocked");
    return { blocker_id: text, message: text, user_action: "" };
  }
  return {
    blocker_id: String(source.blocker_id || source.reason || "blocked"),
    message: String(source.message || source.summary || source.reason || "blocked"),
    user_action: String(source.user_action || ""),
  };
}
