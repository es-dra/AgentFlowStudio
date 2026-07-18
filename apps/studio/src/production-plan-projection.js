const PROJECTION_FLAG = "dynamic_production_plan_projection";

export function applyProductionPlanProjection(state, projection) {
  const safeProjection = projection && typeof projection === "object" ? projection : {};
  const projectId = cleanToken(safeProjection.project_id || state?.meta?.projectId, 128);
  if (!projectId || projectId !== cleanToken(state?.meta?.projectId, 128)) {
    throw new Error("production plan project does not match the active canvas");
  }
  removePreviousProjection(state);
  const plan = safeProjection.current_plan || null;
  state.production = state.production || {};
  state.production.dynamic_production_plan_projection = projectionSummary(projectId, safeProjection, plan);
  if (!plan?.plan_id) {
    state.selection = { nodeIds: [], edgeId: null };
    return state.production.dynamic_production_plan_projection;
  }

  const planNode = planNodeFor(projectId, plan, safeProjection);
  state.nodes[planNode.id] = planNode;
  pushOrder(state, planNode.id);

  const scriptNodeId = `script_truth_revision_${cleanToken(plan.script_revision_id, 140)}`;
  if (state.nodes?.[scriptNodeId]) {
    addEdge(state, scriptNodeId, planNode.id, "production_plan_source_revision");
  }

  const beatNodes = new Map();
  const beats = Array.isArray(safeProjection.beats) ? safeProjection.beats : [];
  beats.forEach((beat, index) => {
    const node = beatNodeFor(projectId, plan, beat, index);
    state.nodes[node.id] = node;
    pushOrder(state, node.id);
    beatNodes.set(cleanToken(beat.beat_id, 120), node.id);
    addEdge(state, planNode.id, node.id, "production_plan_beat");
  });

  const shotNodes = new Map();
  const shots = Array.isArray(safeProjection.shots) ? safeProjection.shots : [];
  shots.forEach((shot, index) => {
    const node = shotNodeFor(projectId, plan, shot, index);
    state.nodes[node.id] = node;
    pushOrder(state, node.id);
    shotNodes.set(cleanToken(shot.shot_id, 120), node.id);
    const beatNodeId = beatNodes.get(cleanToken(shot.beat_id, 120));
    addEdge(state, beatNodeId || planNode.id, node.id, "production_plan_shot");
  });

  const chunks = Array.isArray(safeProjection.chunks) ? safeProjection.chunks : [];
  chunks.forEach((chunk, index) => {
    const node = chunkNodeFor(projectId, plan, chunk, index);
    state.nodes[node.id] = node;
    pushOrder(state, node.id);
    const shotNodeId = shotNodes.get(cleanToken(chunk.shot_id, 120));
    addEdge(state, shotNodeId || planNode.id, node.id, "production_plan_chunk");
  });

  if (safeProjection.concat_plan) {
    const concatNode = concatNodeFor(projectId, plan, safeProjection.concat_plan);
    state.nodes[concatNode.id] = concatNode;
    pushOrder(state, concatNode.id);
    addEdge(state, planNode.id, concatNode.id, "production_plan_concat");
    shots.forEach((shot) => {
      const shotNodeId = shotNodes.get(cleanToken(shot.shot_id, 120));
      if (shotNodeId) addEdge(state, shotNodeId, concatNode.id, "production_plan_concat_order");
    });
  }

  state.selection = state.selection?.nodeIds?.some((id) => state.nodes[id])
    ? state.selection
    : { nodeIds: [planNode.id], edgeId: null };
  return state.production.dynamic_production_plan_projection;
}

export function selectedProductionPlanEntityFromState(state) {
  const selectedId = state?.selection?.nodeIds?.[0] || "";
  const node = selectedId ? state?.nodes?.[selectedId] : null;
  return node?.params?.productionPlanTruth || null;
}

function projectionSummary(projectId, projection, plan) {
  const shots = Array.isArray(projection.shots) ? projection.shots : [];
  const chunks = Array.isArray(projection.chunks) ? projection.chunks : [];
  return {
    schema_version: String(projection.schema_version || ""),
    project_id: projectId,
    planning_state: cleanToken(projection.planning_state || "planning_required", 80),
    plan_id: cleanToken(plan?.plan_id, 140),
    plan_digest: cleanDigest(plan?.plan_digest || ""),
    plan_version: Number(plan?.plan_version || 0),
    script_revision_id: cleanToken(plan?.script_revision_id, 140),
    source_digest: cleanDigest(plan?.source_digest || ""),
    candidate_digest: cleanDigest(plan?.candidate_digest || ""),
    shot_count: shots.length,
    chunk_count: chunks.length,
    total_duration_seconds: round2(shots.reduce((sum, shot) => sum + Number(shot?.duration_seconds || 0), 0)),
    storyboard_mode: "read_only_consumer",
    projection_source: "runtime_dynamic_production_plan",
    storyboard_shots: shots
      .slice()
      .sort((left, right) => Number(left?.order || 0) - Number(right?.order || 0))
      .map((shot) => ({
        shot_id: cleanToken(shot.shot_id, 120),
        beat_id: cleanToken(shot.beat_id, 120),
        order: Number(shot.order || 0),
        title: `Shot ${Number(shot.order || 0) || ""}`.trim(),
        intent: cleanText(shot.intent || "", 240),
        duration_seconds: round2(Number(shot.duration_seconds || 0)),
        strategy: cleanToken(shot.media_strategy?.strategy || "", 20),
        strategy_reason: cleanText(shot.media_strategy?.strategy_reason || "", 240),
        status: cleanToken(shot.status || "", 40),
        media_input_state: cleanToken(shot.media_input_state || "", 80),
        character_refs: safeStringList(shot.character_refs, 16),
        scene_refs: safeStringList(shot.scene_refs, 16),
      })),
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}

function planNodeFor(projectId, plan, projection) {
  const planId = cleanToken(plan.plan_id, 140);
  const planningState = cleanToken(projection.planning_state || "planned", 80);
  return {
    id: `production_plan_${planId}`,
    type: "text",
    title: `Production Plan v${Number(plan.plan_version || 1)}`,
    x: 80,
    y: 410,
    w: 320,
    h: 210,
    prompt: "",
    params: baseParams(projectId, plan, {
      entity_type: "plan",
      plan_id: planId,
      plan_digest: cleanDigest(plan.plan_digest || ""),
      planning_state: planningState,
    }),
    content: [
      `state: ${planningState}`,
      `shots: ${Array.isArray(projection.shots) ? projection.shots.length : 0}`,
      `chunks: ${Array.isArray(projection.chunks) ? projection.chunks.length : 0}`,
      `storyboard: read_only_consumer`,
    ].join("\n"),
    status: planningState === "planned" ? "complete" : "draft",
    result: null,
    groupId: null,
    collapsed: false,
  };
}

function beatNodeFor(projectId, plan, beat, index) {
  const beatId = cleanToken(beat.beat_id, 120);
  return {
    id: `production_plan_beat_${beatId}`,
    type: "text",
    title: `Beat ${Number(beat.order || index + 1)}`,
    x: 470,
    y: 380 + index * 170,
    w: 300,
    h: 150,
    prompt: "",
    params: baseParams(projectId, plan, {
      entity_type: "beat",
      beat_id: beatId,
      order: Number(beat.order || index + 1),
    }),
    content: [
      cleanText(beat.summary || "", 160),
      `purpose: ${cleanText(beat.narrative_purpose || "", 120)}`,
    ].filter(Boolean).join("\n"),
    status: "complete",
    result: null,
    groupId: null,
    collapsed: false,
  };
}

function shotNodeFor(projectId, plan, shot, index) {
  const shotId = cleanToken(shot.shot_id, 120);
  const strategy = cleanToken(shot.media_strategy?.strategy || "", 20);
  const status = cleanToken(shot.status || "planned", 40);
  return {
    id: `production_plan_shot_${shotId}`,
    type: "video",
    title: `Shot ${Number(shot.order || index + 1)}`,
    x: 850,
    y: 350 + index * 185,
    w: 330,
    h: 170,
    prompt: "",
    params: baseParams(projectId, plan, {
      entity_type: "shot",
      shot_id: shotId,
      beat_id: cleanToken(shot.beat_id, 120),
      order: Number(shot.order || index + 1),
      duration_seconds: round2(Number(shot.duration_seconds || 0)),
      strategy,
      media_input_state: cleanToken(shot.media_input_state || "", 80),
      character_refs: safeStringList(shot.character_refs, 24),
      scene_refs: safeStringList(shot.scene_refs, 24),
    }),
    content: [
      `${round2(Number(shot.duration_seconds || 0))}s ${strategy.toUpperCase()}`,
      cleanText(shot.intent || "", 160),
      `reason: ${cleanText(shot.media_strategy?.strategy_reason || "", 120)}`,
    ].filter(Boolean).join("\n"),
    status: status === "planned" ? "complete" : "draft",
    result: null,
    groupId: null,
    collapsed: false,
  };
}

function chunkNodeFor(projectId, plan, chunk, index) {
  const chunkId = cleanToken(chunk.chunk_id, 160);
  const state = cleanToken(chunk.state || "planned", 40);
  return {
    id: `production_plan_chunk_${chunkId}`,
    type: "render",
    title: `Chunk ${Number(chunk.sequence || index + 1)}`,
    x: 1240,
    y: 340 + index * 130,
    w: 300,
    h: 135,
    prompt: "",
    params: baseParams(projectId, plan, {
      entity_type: "chunk",
      chunk_id: chunkId,
      shot_id: cleanToken(chunk.shot_id, 120),
      sequence: Number(chunk.sequence || index + 1),
      target_duration_seconds: round2(Number(chunk.target_duration_seconds || 0)),
      state,
      remainder_strategy: cleanToken(chunk.remainder_strategy || "", 80),
    }),
    content: [
      `${round2(Number(chunk.target_duration_seconds || 0))}s`,
      `state: ${state}`,
      chunk.depends_on ? `depends_on: ${cleanToken(chunk.depends_on, 120)}` : "",
      chunk.remainder_strategy ? `remainder: ${cleanToken(chunk.remainder_strategy, 80)}` : "",
    ].filter(Boolean).join("\n"),
    status: state === "ready" ? "complete" : "draft",
    result: null,
    groupId: null,
    collapsed: false,
  };
}

function concatNodeFor(projectId, plan, concatPlan) {
  return {
    id: `production_plan_concat_${cleanToken(concatPlan.concat_plan_id || plan.plan_id, 140)}`,
    type: "render",
    title: "Concat Plan",
    x: 1620,
    y: 410,
    w: 300,
    h: 160,
    prompt: "",
    params: baseParams(projectId, plan, {
      entity_type: "concat_plan",
      concat_plan_id: cleanToken(concatPlan.concat_plan_id || "", 140),
      state: cleanToken(concatPlan.state || "planned_not_executed", 80),
      executes_media: false,
    }),
    content: [
      `state: ${cleanToken(concatPlan.state || "planned_not_executed", 80)}`,
      `shots: ${Array.isArray(concatPlan.shot_order) ? concatPlan.shot_order.length : 0}`,
      "executes_media: false",
    ].join("\n"),
    status: "draft",
    result: null,
    groupId: null,
    collapsed: false,
  };
}

function baseParams(projectId, plan, entity) {
  return {
    model: null,
    attachments: [],
    styleRef: null,
    isReference: false,
    productionPlanProjection: PROJECTION_FLAG,
    productionPlanTruth: {
      project_id: projectId,
      script_revision_id: cleanToken(plan.script_revision_id, 140),
      source_digest: cleanDigest(plan.source_digest || ""),
      plan_id: cleanToken(plan.plan_id, 140),
      plan_digest: cleanDigest(plan.plan_digest || ""),
      plan_version: Number(plan.plan_version || 1),
      storyboard_write: false,
      ...entity,
    },
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}

function addEdge(state, from, to, relationType) {
  if (!from || !to) return;
  const edgeId = `edge_${from}__${to}`;
  state.edges[edgeId] = {
    id: edgeId,
    from,
    to,
    relation_type: relationType,
  };
}

function removePreviousProjection(state) {
  const remove = new Set();
  for (const [id, node] of Object.entries(state.nodes || {})) {
    if (node?.params?.productionPlanProjection === PROJECTION_FLAG) remove.add(id);
  }
  for (const id of remove) delete state.nodes[id];
  state.order = (state.order || []).filter((id) => !remove.has(id));
  for (const [edgeId, edge] of Object.entries(state.edges || {})) {
    if (remove.has(edge.from) || remove.has(edge.to) || String(edge.relation_type || "").startsWith("production_plan_")) {
      delete state.edges[edgeId];
    }
  }
  if ((state.selection?.nodeIds || []).some((id) => remove.has(id))) {
    state.selection = { nodeIds: [], edgeId: null };
  }
}

function pushOrder(state, nodeId) {
  state.order = (state.order || []).filter((id) => id !== nodeId);
  state.order.push(nodeId);
}

function safeStringList(value, limit) {
  return (Array.isArray(value) ? value : [])
    .map((item) => cleanToken(item, 140))
    .filter(Boolean)
    .slice(0, limit);
}

function cleanToken(value, limit = 120) {
  return String(value || "").replace(/[^A-Za-z0-9_.:-]/g, "").slice(0, limit);
}

function cleanDigest(value) {
  const text = String(value || "").trim().toLowerCase();
  return /^[a-f0-9]{64}$/.test(text) ? text : "";
}

function cleanText(value, limit) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function round2(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.round(value * 100) / 100;
}
