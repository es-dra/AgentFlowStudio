function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeMemoryWorkspace(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Memory workspace"),
    summary: String(source.summary || ""),
    selected_candidate_id: String(source.selected_candidate_id || ""),
    counts: normalizeMemoryCounts(source.counts),
    candidates: asArray(source.candidates).map(normalizeReviewCandidate),
    decision_counts: normalizeDecisionCounts(source.decision_counts),
    latest_decisions: asArray(source.latest_decisions).map(normalizeReviewDecision),
    style_profile: normalizeStyleMemory(source.style_profile),
    feedback_controls: normalizeControls(source.feedback_controls),
    next_round_controls: normalizeControls(source.next_round_controls),
    non_claims: asArray(source.non_claims).map(String),
  };
}

export function normalizeReviewRoom(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Review room"),
    summary: String(source.summary || ""),
    candidates: asArray(source.candidates).map(normalizeReviewCandidate),
    decision_counts: normalizeDecisionCounts(source.decision_counts),
    latest_decisions: asArray(source.latest_decisions).map(normalizeReviewDecision),
    non_claims: asArray(source.non_claims).map(String),
  };
}

export function normalizeStyleMemory(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Project style memory"),
    summary: String(source.summary || ""),
    profile_version_count: Number(source.profile_version_count || 0),
    feedback_count: Number(source.feedback_count || 0),
    latest_profile_artifact_id: String(source.latest_profile_artifact_id || ""),
    reusable_preferences: asArray(source.reusable_preferences).map(String),
    next_pass_usage: String(source.next_pass_usage || ""),
    non_claims: asArray(source.non_claims).map(String),
  };
}

function normalizeMemoryCounts(value) {
  const source = asObject(value);
  return {
    candidates: Number(source.candidates || 0),
    decisions: Number(source.decisions || 0),
    feedback_refs: Number(source.feedback_refs || 0),
    profile_versions: Number(source.profile_versions || 0),
    reusable_preferences: Number(source.reusable_preferences || 0),
  };
}

function normalizeReviewCandidate(value) {
  const source = asObject(value);
  return {
    candidate_id: String(source.candidate_id || ""),
    card_id: String(source.card_id || ""),
    stage: String(source.stage || ""),
    label: String(source.label || "Candidate"),
    title: String(source.title || "Candidate"),
    status: String(source.status || "not_started"),
    summary: String(source.summary || ""),
    artifact_id: String(source.artifact_id || ""),
    artifact_type: String(source.artifact_type || ""),
    compare_points: asArray(source.compare_points).map(String),
    latest_decision: String(source.latest_decision || ""),
    latest_decision_note: String(source.latest_decision_note || ""),
  };
}

function normalizeReviewDecision(value) {
  const source = asObject(value);
  return {
    review_id: String(source.review_id || ""),
    card_id: String(source.card_id || ""),
    candidate_id: String(source.candidate_id || ""),
    artifact_id: String(source.artifact_id || ""),
    decision: String(source.decision || ""),
    note: String(source.note || ""),
    generated_at: String(source.generated_at || ""),
  };
}

function normalizeDecisionCounts(value) {
  const source = asObject(value);
  return {
    keep: Number(source.keep || 0),
    revise: Number(source.revise || 0),
    reject: Number(source.reject || 0),
  };
}

function normalizeControls(value) {
  const source = asObject(value);
  return {
    primary_action: String(source.primary_action || ""),
    primary_label: String(source.primary_label || "Continue"),
    ui_action: String(source.ui_action || ""),
    enabled: source.enabled === true,
    handoff_view: String(source.handoff_view || "Review"),
    summary: String(source.summary || ""),
    blocked_reason: String(source.blocked_reason || ""),
    requires_input: asArray(source.requires_input).map(String),
  };
}
