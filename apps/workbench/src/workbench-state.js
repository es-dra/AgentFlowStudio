import { normalizeActivityTimeline } from "./activity-state.js";
import { normalizeCommandHub } from "./command-hub-state.js";
import { normalizeCreationWorkspace } from "./creation-workspace-state.js";
import { normalizeProductionBoard } from "./production-board-state.js";
import { normalizeProjectHub } from "./project-hub-state.js";
import { normalizeProjectReadiness } from "./readiness-state.js";
export const EMPTY_WORKBENCH_STATE = {
  artifact_type: "agentflow_runtime_workbench_state",
  project_id: "",
  navigation: [],
  canvas_cards: [],
  project_readiness: null,
  asset_library: null,
  filmstrip: [],
  review_room: null,
  style_memory: null,
  job_center: null,
  activity_timeline: null,
  production_board: null,
  command_hub: null,
  project_hub: null,
  creation_workspace: null,
  events: [],
  provider_gate: null,
  advanced_evidence: {
    visible_by_default: false,
    non_claims: [],
    safe_ref_policy: "",
  },
};
function asArray(value) {
  return Array.isArray(value) ? value : [];
}
function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
export function normalizeWorkbenchState(payload) {
  const source = asObject(payload);
  const evidence = asObject(source.advanced_evidence);
  const cards = asArray(source.canvas_cards).length ? source.canvas_cards : source.cards;
  return {
    ...EMPTY_WORKBENCH_STATE,
    ...source,
    navigation: asArray(source.navigation),
    canvas_cards: asArray(cards).map(normalizeCard),
    project_readiness: normalizeProjectReadiness(source.project_readiness),
    asset_library: normalizeAssetLibrary(source.asset_library),
    filmstrip: asArray(source.filmstrip).map(normalizeFilmstripItem),
    review_room: normalizeReviewRoom(source.review_room),
    style_memory: normalizeStyleMemory(source.style_memory),
    job_center: normalizeJobCenter(source.job_center),
    activity_timeline: normalizeActivityTimeline(source.activity_timeline),
    production_board: normalizeProductionBoard(source.production_board),
    command_hub: normalizeCommandHub(source.command_hub),
    project_hub: normalizeProjectHub(source.project_hub),
    creation_workspace: normalizeCreationWorkspace(source.creation_workspace),
    events: asArray(source.events).map(normalizeEvent),
    provider_gate: source.provider_gate ? normalizeCard(source.provider_gate) : null,
    advanced_evidence: {
      visible_by_default: evidence.visible_by_default === true,
      non_claims: asArray(evidence.non_claims),
      safe_ref_policy: String(evidence.safe_ref_policy || ""),
    },
  };
}

export function normalizeAssetLibrary(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "needs_assets"),
    title: String(source.title || "Reference library"),
    summary: String(source.summary || ""),
    counts: normalizeAssetCounts(source.counts),
    items: asArray(source.items).map(normalizeAssetItem),
    next_actions: asArray(source.next_actions).map(String),
    safe_ref_policy: String(source.safe_ref_policy || ""),
  };
}

export function normalizeAssetCounts(value) {
  const source = asObject(value);
  return {
    total: Number(source.total || 0),
    brief: Number(source.brief || 0),
    reference: Number(source.reference || 0),
    script: Number(source.script || 0),
    other: Number(source.other || 0),
  };
}

export function normalizeAssetItem(value) {
  const source = asObject(value);
  return {
    asset_id: String(source.asset_id || ""),
    asset_type: String(source.asset_type || "reference"),
    label: String(source.label || "Asset"),
    summary: String(source.summary || ""),
    usage: String(source.usage || "Supporting context"),
    safety: String(source.safety || "safe_summary"),
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

export function normalizeReviewCandidate(value) {
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

export function normalizeReviewDecision(value) {
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

export function normalizeDecisionCounts(value) {
  const source = asObject(value);
  return {
    keep: Number(source.keep || 0),
    revise: Number(source.revise || 0),
    reject: Number(source.reject || 0),
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

export function normalizeJobCenter(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Job center"),
    summary: String(source.summary || ""),
    counts: normalizeJobCounts(source.counts),
    items: asArray(source.items).map(normalizeJobItem),
    polling: {
      enabled: asObject(source.polling).enabled === true,
      manual_refresh_action: String(asObject(source.polling).manual_refresh_action || "refresh"),
      suggested_interval_ms: Number(asObject(source.polling).suggested_interval_ms || 5000),
    },
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

export function normalizeCard(card) {
  const source = asObject(card);
  const primaryArtifactId = String(source.primary_artifact_id || "");
  const evidence = asObject(source.evidence);
  const evidenceArtifactIds = asArray(evidence.artifact_ids).map(String).filter(Boolean);
  const refs = asArray(source.refs).length
    ? asArray(source.refs)
    : [primaryArtifactId, ...evidenceArtifactIds.filter((item) => item !== primaryArtifactId)].filter(Boolean).map((artifactId) => ({
        label: artifactId === primaryArtifactId ? "primary" : "evidence",
        artifact_id: artifactId,
        artifact_type: "",
      }));
  return {
    id: String(source.id || source.card_id || "unknown"),
    kind: String(source.kind || ""),
    title: String(source.title || "Untitled"),
    status: String(source.status || "not_started"),
    summary: String(source.summary || ""),
    primary_artifact_id: primaryArtifactId,
    blockers: asArray(source.blockers).map(normalizeBlocker),
    actions: asArray(source.actions).map(String),
    refs: refs.map((ref) => ({
      label: String(asObject(ref).label || "ref"),
      artifact_id: String(asObject(ref).artifact_id || ""),
      artifact_type: String(asObject(ref).artifact_type || ""),
      summary: String(asObject(ref).summary || ""),
    })),
    inspector: normalizeInspector(source.inspector),
  };
}

export function normalizeInspector(value) {
  const source = asObject(value);
  return {
    prompt: String(source.prompt || ""),
    reference_summary: String(source.reference_summary || ""),
    style_direction: String(source.style_direction || ""),
    retry_intent: String(source.retry_intent || ""),
  };
}

export function normalizeFilmstripItem(item) {
  const source = asObject(item);
  return {
    card_id: String(source.card_id || ""),
    title: String(source.title || "Scene"),
    status: String(source.status || "ready_not_run"),
    summary: String(source.summary || ""),
  };
}

export function normalizeEvent(event) {
  const source = asObject(event);
  const artifactIds = asArray(source.artifact_ids).map(String).filter(Boolean);
  return {
    id: String(source.id || source.event_id || "event"),
    title: String(source.title || "Event"),
    action: String(source.action || ""),
    status: String(source.status || "not_started"),
    summary: String(source.summary || ""),
    job_id: String(source.job_id || ""),
    artifact_id: String(source.artifact_id || artifactIds[0] || ""),
    artifact_ids: artifactIds,
  };
}

export function normalizeBlocker(blocker) {
  const source = asObject(blocker);
  if (!Object.keys(source).length) {
    return { blocker_id: String(blocker || "blocked"), message: String(blocker || "blocked") };
  }
  return {
    blocker_id: String(source.blocker_id || source.block_id || source.reason || "blocked"),
    message: String(source.message || source.summary || source.reason || source.blocker_id || "blocked"),
    user_action: String(source.user_action || ""),
  };
}

export function statusTone(status) {
  if (status === "succeeded" || status === "ready_for_next_round") return "good";
  if (status === "blocked" || status === "failed") return "blocked";
  if (status === "running" || status === "needs_review") return "active";
  if (status === "ready_not_run") return "ready";
  return "quiet";
}
