import { normalizeActivityTimeline } from "./activity-state.js";
import { normalizeCommandHub } from "./command-hub-state.js";
import { normalizeCreationWorkspace } from "./creation-workspace-state.js";
import { normalizeMemoryWorkspace, normalizeReviewRoom, normalizeStyleMemory } from "./memory-workspace-state.js";
import { normalizeJobCenter, normalizeOperationsWorkspace } from "./operations-workspace-state.js";
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
  memory_workspace: null,
  operations_workspace: null,
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
    memory_workspace: normalizeMemoryWorkspace(source.memory_workspace),
    operations_workspace: normalizeOperationsWorkspace(source.operations_workspace),
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
