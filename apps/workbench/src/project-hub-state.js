function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeProjectHub(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Project hub"),
    summary: String(source.summary || ""),
    active_project: normalizeActiveProject(source.active_project),
    counts: normalizeProjectCounts(source.counts),
    next_command: normalizeNextCommand(source.next_command),
    recent_jobs: asArray(source.recent_jobs).map(normalizeRecentJob),
    non_claims: asArray(source.non_claims).map(String),
  };
}

function normalizeActiveProject(value) {
  const source = asObject(value);
  return {
    project_id: String(source.project_id || ""),
    project_type: String(source.project_type || ""),
    goal: String(source.goal || ""),
    status: String(source.status || "in_progress"),
    artifact_id: String(source.artifact_id || ""),
  };
}

function normalizeProjectCounts(value) {
  const source = asObject(value);
  return {
    source_assets: Number(source.source_assets || 0),
    content_cards: Number(source.content_cards || 0),
    runs: Number(source.runs || 0),
    jobs: Number(source.jobs || 0),
    feedback_refs: Number(source.feedback_refs || 0),
    profile_versions: Number(source.profile_versions || 0),
  };
}

function normalizeNextCommand(value) {
  const source = asObject(value);
  return {
    command_id: String(source.command_id || ""),
    label: String(source.label || "Continue"),
    backend_action: String(source.backend_action || ""),
    ui_action: String(source.ui_action || ""),
    view: String(source.view || "Create"),
    summary: String(source.summary || ""),
    enabled: source.enabled === true,
    blocked_reason: String(source.blocked_reason || ""),
    requires_input: asArray(source.requires_input).map(String),
  };
}

function normalizeRecentJob(value) {
  const source = asObject(value);
  return {
    job_id: String(source.job_id || ""),
    title: String(source.title || "Runtime job"),
    action: String(source.action || ""),
    status: String(source.status || "not_started"),
    primary_artifact_id: String(source.primary_artifact_id || ""),
    artifact_ids: asArray(source.artifact_ids).map(String),
    artifact_count: Number(source.artifact_count || 0),
  };
}
