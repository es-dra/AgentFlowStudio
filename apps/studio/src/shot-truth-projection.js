import { normalizedDurationSeconds, shotPlanSummary } from "./creative-task-contract.js";

export function legacyAppliedStoryboardProjection(studioState = {}) {
  const nodes = normalizeNodeMap(studioState.nodes);
  const edges = normalizeEdgeList(studioState.edges);
  const source = latestAppliedShotSource(nodes);
  if (!source) return emptyProjection();
  const { node: sourceNode, action } = source;
  const candidateId = safeToken(
    action.applied_subgraph?.candidate_id
    || sourceNode.params?.shotPlanDraft?.candidate_id
    || action.preview?.shot_plan?.candidate_id,
  );
  if (!candidateId) return emptyProjection();
  const revisionId = safeToken(action.applied_revision_id || sourceNode.params?.currentRevisionId || sourceNode.params?.shotPlanDraft?.source_revision_id);
  const sequenceNode = findAppliedSequenceNode(nodes, edges, sourceNode.id, candidateId, revisionId);
  if (!sequenceNode) return emptyProjection();
  const sceneNodes = findAppliedSceneNodes(nodes, edges, sequenceNode.id, candidateId, revisionId);
  const scenes = [];
  const shots = [];
  const seenShots = new Set();
  for (const sceneNode of sceneNodes) {
    const sceneShots = findAppliedShotNodes(nodes, edges, sceneNode.id, candidateId, revisionId)
      .filter((shotNode) => {
        if (seenShots.has(shotNode.id)) return false;
        seenShots.add(shotNode.id);
        return true;
      })
      .map((shotNode, index) => storyboardShotFromNode(shotNode, index, sceneNode.id));
    if (!sceneShots.length) continue;
    const sceneDuration = sceneShots.reduce((sum, shot) => sum + shot.durationSeconds, 0);
    shots.push(...sceneShots);
    scenes.push({
      name: cleanTitle(sceneNode.title || sceneNode.label || `场景 ${scenes.length + 1}`),
      sceneId: sceneNode.id,
      nodeId: sceneNode.id,
      shots: sceneShots,
      duration: `${sceneDuration.toFixed(1)}s`,
      blocked: sceneShots.some((shot) => shot.state === "blocked"),
      candidate_id: candidateId,
      source_revision_id: revisionId,
    });
  }
  if (!shots.length) return emptyProjection();
  const summary = shotPlanSummary(action.applied_subgraph?.shot_plan || sourceNode.params?.shotPlanDraft || action.preview?.shot_plan || {});
  const durationSec = summary.duration_source === "per_shot_sum"
    ? summary.estimated_duration_sec
    : shots.reduce((sum, shot) => sum + shot.durationSeconds, 0);
  return {
    status: "ready",
    source: "legacy_applied_candidate_subgraph",
    candidate_id: candidateId,
    source_node_id: sourceNode.id,
    source_revision_id: revisionId,
    scene_count: scenes.length,
    shot_count: shots.length,
    duration_sec: durationSec,
    scenes,
    shots,
  };
}

export function emptyProjection() {
  return {
    status: "empty",
    source: "",
    candidate_id: "",
    source_node_id: "",
    source_revision_id: "",
    scene_count: 0,
    shot_count: 0,
    duration_sec: 0,
    scenes: [],
    shots: [],
  };
}

function normalizeNodeMap(value) {
  if (Array.isArray(value)) return Object.fromEntries(value.filter(Boolean).map((node) => [node.id, node]));
  return value && typeof value === "object" ? value : {};
}

function normalizeEdgeList(value) {
  if (Array.isArray(value)) return value.filter(Boolean);
  if (value && typeof value === "object") return Object.values(value).filter(Boolean);
  return [];
}

function latestAppliedShotSource(nodes) {
  return Object.values(nodes)
    .map((node) => ({ node, action: node?.params?.embeddedCreativeAction || null }))
    .filter(({ node, action }) => (
      node
      && action?.action_type === "shot_breakdown"
      && action.status === "applied"
      && (action.applied_subgraph?.candidate_id || node.params?.shotPlanDraft?.candidate_id || action.preview?.shot_plan?.candidate_id)
    ))
    .sort((left, right) => timestamp(right.action.applied_at || right.action.completed_at || right.action.requested_at)
      - timestamp(left.action.applied_at || left.action.completed_at || left.action.requested_at))[0] || null;
}

function findAppliedSequenceNode(nodes, edges, sourceNodeId, candidateId, revisionId) {
  return Object.values(nodes)
    .filter((node) => node?.type === "sequence" && candidateMatches(node, candidateId, revisionId))
    .find((node) => edgeExists(edges, sourceNodeId, node.id, "proposed")) || null;
}

function findAppliedSceneNodes(nodes, edges, sequenceNodeId, candidateId, revisionId) {
  return Object.values(nodes)
    .filter((node) => node?.type === "scene" && candidateMatches(node, candidateId, revisionId))
    .filter((node) => node.params?.source_sequence_node_id === sequenceNodeId || edgeExists(edges, sequenceNodeId, node.id, "sequence"))
    .sort((left, right) => Number(left.params?.scene_index ?? 0) - Number(right.params?.scene_index ?? 0));
}

function findAppliedShotNodes(nodes, edges, sceneNodeId, candidateId, revisionId) {
  return Object.values(nodes)
    .filter((node) => node?.type === "shot" && candidateMatches(node, candidateId, revisionId))
    .filter((node) => node.params?.source_scene_node_id === sceneNodeId || edgeExists(edges, sceneNodeId, node.id, "sequence"))
    .sort((left, right) => Number(left.params?.shot_index ?? 0) - Number(right.params?.shot_index ?? 0));
}

function candidateMatches(node, candidateId, revisionId) {
  const params = node?.params || {};
  const candidate = safeToken(params.candidate_id || node.groupId);
  if (candidate !== candidateId) return false;
  if (revisionId && safeToken(params.source_revision_id) !== revisionId) return false;
  return [
    "m6_6_shot_sequence_candidate",
    "m6_6_scene_candidate",
    "m6_6_shot_candidate",
  ].includes(String(params.nodeRole || ""));
}

function edgeExists(edges, fromId, toId, relationType) {
  return edges.some((edge) => edge?.from === fromId && edge?.to === toId && String(edge.relation_type || edge.relationType || "") === relationType);
}

function storyboardShotFromNode(node, index, sceneId) {
  const params = node.params || {};
  const durationSeconds = normalizedDurationSeconds(params.duration_sec) ?? 0;
  return {
    nodeId: node.id,
    title: cleanTitle(node.title || node.label || `镜头 ${index + 1}`),
    description: cleanDescription(params.narrative_purpose || params.blocking || node.content || node.prompt || "等待补充镜头说明"),
    duration: `${durationSeconds.toFixed(1)}s`,
    durationSeconds,
    preview: "",
    state: node.status === "failed" ? "blocked" : "draft",
    sceneId,
    candidate_id: safeToken(params.candidate_id || node.groupId),
    source_revision_id: safeToken(params.source_revision_id),
  };
}

function cleanTitle(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 80) || "镜头";
}

function cleanDescription(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 240) || "等待补充镜头说明";
}

function safeToken(value) {
  return String(value || "").replace(/[^A-Za-z0-9_.:-]/g, "_").trim();
}

function timestamp(value) {
  const parsed = Date.parse(value || "");
  return Number.isFinite(parsed) ? parsed : 0;
}
