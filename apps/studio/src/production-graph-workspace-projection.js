const READY = "ready";

export function productionGraphWorkspaceProjection(workspace = null) {
  if (!workspace || workspace.status !== READY) {
    return {
      status: workspace?.status || "unavailable",
      planningRequired: workspace?.status === "planning_required",
      graphVersion: Number(workspace?.graph_version || 0),
      graphDigest: String(workspace?.graph_digest || ""),
      scenes: [],
      shots: [],
      summary: emptySummary(),
    };
  }

  const graphVersion = Number(workspace.graph_version || 0);
  const graphDigest = String(workspace.graph_digest || "");
  if (
    Number(workspace.storyboard?.graph_version || 0) !== graphVersion
    || String(workspace.storyboard?.graph_digest || "") !== graphDigest
  ) {
    return { status: "projection_conflict", planningRequired: false, graphVersion, graphDigest, scenes: [], shots: [], summary: emptySummary() };
  }

  const sequence = workspace.sequence || {};
  const relations = array(sequence.dependencies);
  const shots = array(sequence.shots).map((shot) => ({
    nodeId: canvasNodeId(shot.node_id),
    graphNodeId: String(shot.node_id || ""),
    sceneNodeId: sceneForShot(relations, shot.node_id),
    title: String(shot.metadata?.title || shot.metadata?.intent || ""),
    description: String(shot.metadata?.intent || ""),
    durationSeconds: Number(shot.metadata?.duration_seconds || 0),
    state: shot.state === "invalidated" ? "blocked" : shot.metadata?.review_state === "approved" ? "ready" : "draft",
  }));
  const scenes = array(sequence.scenes).map((scene) => ({
    nodeId: canvasNodeId(scene.node_id),
    graphNodeId: String(scene.node_id || ""),
    name: String(scene.metadata?.name || ""),
    shots: shots.filter((shot) => shot.sceneNodeId === scene.node_id),
  }));

  return {
    status: READY,
    planningRequired: false,
    graphVersion,
    graphDigest,
    scenes,
    shots,
    summary: {
      scriptRevisions: array(sequence.script_revisions).filter(
        (item) => item?.state !== "invalidated",
      ).length,
      sequences: array(sequence.sequences).length,
      characters: array(sequence.characters).length,
      locations: array(sequence.scenes).length,
      props: array(sequence.props).length,
      referenceSets: array(sequence.reference_sets).length,
      productionAids: array(sequence.production_aids).length,
      tasks: array(sequence.tasks).length,
      candidates: array(sequence.candidates).length,
      selections: array(sequence.selections).length,
      reviews: array(sequence.reviews).length,
      pendingReviews: array(sequence.reviews).filter((item) => item.state === "pending").length,
      rejectedReviews: array(sequence.reviews).filter((item) => item.state === "rejected").length,
      deliveries: array(sequence.delivery_plan).length,
      versionHistory: array(sequence.version_history),
    },
    lifecycle: {
      tasks: array(sequence.tasks),
      candidates: array(sequence.candidates),
      selections: array(sequence.selections),
      reviews: array(sequence.reviews),
      deliveries: array(sequence.delivery_plan),
    },
  };
}

export function applyProductionGraphCanvasProjection(state, workspace) {
  const projection = productionGraphWorkspaceProjection(workspace);
  removeCanvasProjection(state);
  state.production = state.production || {};
  if (projection.status !== READY) {
    delete state.production.production_graph_projection;
    return projection;
  }
  for (const node of Object.values(state.nodes || {})) {
    node.params = { ...(node.params || {}), productionGraphLegacyProjection: "read_only_legacy_projection" };
  }
  state.production.production_graph_projection = {
    graph_version: projection.graphVersion,
    graph_digest: projection.graphDigest,
    scene_count: projection.scenes.length,
    shot_count: projection.shots.length,
    task_count: projection.summary.tasks,
    pending_review_count: projection.summary.pendingReviews,
    migration_state: "read_only_projection",
    provider_dispatch_count: 0,
  };

  const sequence = workspace.sequence || {};
  const groups = [
    [array(sequence.script_revisions), "script", "剧本版本"],
    [array(sequence.sequences), "text", "制作序列"],
    [array(sequence.characters), "character", "角色"],
    [array(sequence.scenes), "scene", "场景"],
    [array(sequence.props), "asset", "道具"],
    [array(sequence.reference_sets), "asset", "参考集"],
    [array(sequence.shots), "shot", "镜头"],
  ];
  const nodeMap = new Map();
  const legacyBottom = Object.values(state.nodes || {}).reduce(
    (bottom, node) => Math.max(bottom, Number(node?.y || 0) + Number(node?.h || 0)),
    0,
  );
  const originY = legacyBottom > 0 ? legacyBottom + 80 : 80;
  let slot = 0;
  for (const [records, type, fallbackTitle] of groups) {
    if (!records.length) continue;
    records.forEach((record) => {
      const graphNodeId = String(record.node_id || "");
      const id = canvasNodeId(graphNodeId);
      nodeMap.set(graphNodeId, id);
      state.nodes[id] = canvasNode(record, id, graphNodeId, type, fallbackTitle, slot, originY, projection);
      pushOrder(state, id);
      slot += 1;
    });
  }
  for (const relation of array(sequence.dependencies)) {
    const from = nodeMap.get(String(relation.from_id || ""));
    const to = nodeMap.get(String(relation.to_id || ""));
    if (!from || !to) continue;
    const edgeId = `production_graph_edge_${from}__${to}`;
    state.edges[edgeId] = { id: edgeId, from, to, relation_type: `production_graph_${String(relation.relation_type || "dependency")}` };
  }
  return projection;
}

export function productionGraphAgentContext(studioState, workspace) {
  const projection = productionGraphWorkspaceProjection(workspace);
  if (projection.status !== READY) return studioState;
  return {
    ...(studioState || {}),
    production: {
      ...(studioState?.production || {}),
      production_graph_projection: {
        graph_version: projection.graphVersion,
        graph_digest: projection.graphDigest,
        scene_count: projection.scenes.length,
        shot_count: projection.shots.length,
        task_count: projection.summary.tasks,
        pending_review_count: projection.summary.pendingReviews,
        migration_state: "read_only_projection",
      },
    },
  };
}

function sceneForShot(relations, shotId) {
  return String(relations.find((item) => item.to_id === shotId && item.relation_type === "contains")?.from_id || "");
}

function emptySummary() {
  return { scriptRevisions: 0, sequences: 0, characters: 0, locations: 0, props: 0, referenceSets: 0, tasks: 0, candidates: 0,
    productionAids: 0, selections: 0, reviews: 0, pendingReviews: 0, rejectedReviews: 0, deliveries: 0, versionHistory: [] };
}

function canvasNode(record, id, graphNodeId, type, fallbackTitle, slot, originY, projection) {
  const metadata = record.metadata || {};
  const title = String(metadata.display_name || metadata.name || metadata.title || metadata.intent || fallbackTitle).trim() || fallbackTitle;
  const details = [];
  if (metadata.intent) details.push(String(metadata.intent));
  if (Number(metadata.duration_seconds || 0) > 0) details.push(`时长：${Number(metadata.duration_seconds).toFixed(1)} 秒`);
  if (record.state === "invalidated") details.push("需要更新");
  return {
    id,
    type,
    title: title.slice(0, 80),
    x: 80 + (slot % 4) * 330,
    y: originY + Math.floor(slot / 4) * 240,
    w: 280,
    h: 190,
    content: details.join("\n") || "已加入当前制作方案。",
    prompt: "",
    status: record.state === "invalidated" ? "blocked" : "accepted",
    result: null,
    groupId: null,
    collapsed: false,
    params: {
      productionGraphProjection: "canonical_production_graph_projection",
      productionGraphTruth: { graph_node_id: graphNodeId, graph_version: projection.graphVersion, graph_digest: projection.graphDigest },
      provider_dispatch_count: 0,
    },
  };
}

function removeCanvasProjection(state) {
  const remove = new Set();
  for (const [id, item] of Object.entries(state.nodes || {})) {
    if (item?.params?.productionGraphProjection === "canonical_production_graph_projection") remove.add(id);
  }
  for (const id of remove) delete state.nodes[id];
  state.order = array(state.order).filter((id) => !remove.has(id));
  for (const [edgeId, edge] of Object.entries(state.edges || {})) {
    if (remove.has(edge.from) || remove.has(edge.to) || String(edge.relation_type || "").startsWith("production_graph_")) delete state.edges[edgeId];
  }
  if (array(state.selection?.nodeIds).some((id) => remove.has(id))) state.selection = { nodeIds: [], edgeId: null };
}

function pushOrder(state, nodeId) {
  state.order = array(state.order).filter((id) => id !== nodeId);
  state.order.push(nodeId);
}

function canvasNodeId(value) {
  return `production_graph_${String(value || "").replace(/[^A-Za-z0-9_.:-]/g, "_").slice(0, 160)}`;
}

function array(value) {
  return Array.isArray(value) ? value : [];
}
