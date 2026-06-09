function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeStudioWorkspace(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Studio workspace"),
    summary: String(source.summary || ""),
    active_project: normalizeProject(source.active_project),
    primary_command: normalizeCommand(source.primary_command),
    provider_status: String(source.provider_status || "ready_not_run"),
    counts: normalizeCounts(source.counts),
    canvas: normalizeCanvas(source.canvas),
    inspector: normalizeInspector(source.inspector),
    run_controls: normalizeRunControls(source.run_controls),
    filmstrip: asArray(source.filmstrip).map(normalizeFilmstripItem),
    side_rail: normalizeSideRail(source.side_rail),
    operations_summary: normalizeOperationsSummary(source.operations_summary),
    non_claims: asArray(source.non_claims).map(String),
  };
}

function normalizeProject(value) {
  const source = asObject(value);
  return {
    project_id: String(source.project_id || ""),
    goal: String(source.goal || ""),
    status: String(source.status || "not_started"),
    artifact_id: String(source.artifact_id || ""),
  };
}

function normalizeCommand(value) {
  const source = asObject(value);
  return {
    backend_action: String(source.backend_action || ""),
    label: String(source.label || "Continue"),
    ui_action: String(source.ui_action || ""),
    view: String(source.view || "Create"),
    summary: String(source.summary || ""),
    enabled: source.enabled === true,
    blocked_reason: String(source.blocked_reason || ""),
    requires_input: asArray(source.requires_input).map(String),
  };
}

function normalizeCounts(value) {
  const source = asObject(value);
  return {
    assets: Number(source.assets || 0),
    canvas_cards: Number(source.canvas_cards || 0),
    filmstrip_items: Number(source.filmstrip_items || 0),
    review_candidates: Number(source.review_candidates || 0),
    runtime_jobs: Number(source.runtime_jobs || 0),
    provider_blockers: Number(source.provider_blockers || 0),
    reusable_preferences: Number(source.reusable_preferences || 0),
  };
}

function normalizeCanvas(value) {
  const source = asObject(value);
  return {
    selected_card_id: String(source.selected_card_id || ""),
    cards: asArray(source.cards).map(normalizeCard),
  };
}

function normalizeCard(value) {
  const source = asObject(value);
  return {
    card_id: String(source.card_id || ""),
    kind: String(source.kind || ""),
    title: String(source.title || "Untitled"),
    status: String(source.status || "not_started"),
    summary: String(source.summary || ""),
    primary_artifact_id: String(source.primary_artifact_id || ""),
    blockers: asArray(source.blockers).map(normalizeBlocker),
    refs: asArray(source.refs).map(normalizeRef),
    inspector: normalizeFields(source.inspector),
  };
}

function normalizeInspector(value) {
  const source = asObject(value);
  return {
    card_id: String(source.card_id || ""),
    mode: String(source.mode || "setup"),
    title: String(source.title || "No card selected"),
    status: String(source.status || "not_started"),
    summary: String(source.summary || ""),
    primary_artifact_id: String(source.primary_artifact_id || ""),
    fields: normalizeFields(source.fields),
    actions: asArray(source.actions).map(String),
    refs: asArray(source.refs).map(normalizeRef),
    blockers: asArray(source.blockers).map(normalizeBlocker),
  };
}

function normalizeRunControls(value) {
  const source = asObject(value);
  return { ...normalizeCommand(source), primary_action: String(source.primary_action || source.backend_action || "") };
}

function normalizeSideRail(value) {
  const source = asObject(value);
  return {
    assets: asArray(source.assets).map(normalizeAsset),
    style_profile: normalizeStyleProfile(source.style_profile),
    review_candidates: asArray(source.review_candidates).map(normalizeReviewCandidate),
    next_round_controls: normalizeRunControls(source.next_round_controls),
  };
}

function normalizeAsset(value) {
  const source = asObject(value);
  return {
    asset_id: String(source.asset_id || ""),
    asset_type: String(source.asset_type || "reference"),
    label: String(source.label || "Asset"),
    summary: String(source.summary || ""),
  };
}

function normalizeStyleProfile(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Project style memory"),
    summary: String(source.summary || ""),
    latest_profile_artifact_id: String(source.latest_profile_artifact_id || ""),
    reusable_preferences: asArray(source.reusable_preferences).map(String),
    next_pass_usage: String(source.next_pass_usage || ""),
  };
}

function normalizeReviewCandidate(value) {
  const source = asObject(value);
  return {
    candidate_id: String(source.candidate_id || ""),
    title: String(source.title || "Review candidate"),
    status: String(source.status || "needs_review"),
    stage: String(source.stage || ""),
    artifact_id: String(source.artifact_id || ""),
    summary: String(source.summary || ""),
  };
}

function normalizeOperationsSummary(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    selected_job_id: String(source.selected_job_id || ""),
    counts: asObject(source.counts),
    primary_artifact_id: String(source.primary_artifact_id || ""),
    provider_blockers: asArray(source.provider_blockers).map(normalizeBlocker),
  };
}

function normalizeFilmstripItem(value) {
  const source = asObject(value);
  return {
    card_id: String(source.card_id || ""),
    title: String(source.title || "Scene"),
    status: String(source.status || "ready_not_run"),
    summary: String(source.summary || ""),
  };
}

function normalizeFields(value) {
  const source = asObject(value);
  return {
    prompt: String(source.prompt || ""),
    reference_summary: String(source.reference_summary || ""),
    style_direction: String(source.style_direction || ""),
    retry_intent: String(source.retry_intent || ""),
  };
}

function normalizeRef(value) {
  const source = asObject(value);
  return {
    label: String(source.label || "ref"),
    artifact_id: String(source.artifact_id || ""),
    artifact_type: String(source.artifact_type || ""),
    summary: String(source.summary || ""),
  };
}

function normalizeBlocker(value) {
  const source = asObject(value);
  return {
    blocker_id: String(source.blocker_id || "blocked"),
    message: String(source.message || source.summary || source.blocker_id || "blocked"),
    user_action: String(source.user_action || ""),
  };
}
