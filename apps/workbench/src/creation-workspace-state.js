function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeCreationWorkspace(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Creation workspace"),
    summary: String(source.summary || ""),
    selected_card_id: String(source.selected_card_id || ""),
    counts: normalizeCounts(source.counts),
    canvas_cards: asArray(source.canvas_cards).map(normalizeCard),
    inspector: normalizeInspector(source.inspector),
    filmstrip: asArray(source.filmstrip).map(normalizeFilmstripItem),
    run_controls: normalizeRunControls(source.run_controls),
    non_claims: asArray(source.non_claims).map(String),
  };
}

function normalizeCounts(value) {
  const source = asObject(value);
  return {
    canvas_cards: Number(source.canvas_cards || 0),
    filmstrip_items: Number(source.filmstrip_items || 0),
    editable_scene_cards: Number(source.editable_scene_cards || 0),
    artifact_refs: Number(source.artifact_refs || 0),
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
    actions: asArray(source.actions).map(String),
    blockers: asArray(source.blockers).map(normalizeBlocker),
    refs: asArray(source.refs).map(normalizeRef),
    artifact_refs: asArray(source.artifact_refs).map(String),
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
  return {
    primary_action: String(source.primary_action || ""),
    primary_label: String(source.primary_label || "Continue"),
    ui_action: String(source.ui_action || ""),
    enabled: source.enabled === true,
    handoff_view: String(source.handoff_view || "Create"),
    summary: String(source.summary || ""),
    blocked_reason: String(source.blocked_reason || ""),
    requires_input: asArray(source.requires_input).map(String),
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

function normalizeFilmstripItem(value) {
  const source = asObject(value);
  return {
    card_id: String(source.card_id || ""),
    title: String(source.title || "Scene"),
    status: String(source.status || "ready_not_run"),
    summary: String(source.summary || ""),
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
