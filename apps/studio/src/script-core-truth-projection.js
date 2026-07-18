const PROJECTION_FLAG = "script_core_truth_projection";

export function applyScriptCoreTruthProjection(state, projection) {
  const safeProjection = projection && typeof projection === "object" ? projection : {};
  const projectId = cleanToken(safeProjection.project_id || state?.meta?.projectId, 128);
  if (!projectId || projectId !== cleanToken(state?.meta?.projectId, 128)) {
    throw new Error("script truth project does not match the active canvas");
  }
  removePreviousProjection(state);
  const revision = safeProjection.current_revision || null;
  const revisionId = cleanToken(safeProjection.current_revision_id || revision?.revision_id, 140);
  const sourceDigest = cleanDigest(revision?.source_digest || "");
  state.production = state.production || {};
  state.production.script_core_truth_projection = {
    schema_version: String(safeProjection.schema_version || ""),
    project_id: projectId,
    current_revision_id: revisionId,
    source_digest: sourceDigest,
    analysis_state: cleanToken(safeProjection.analysis_state || "analysis_required", 80),
    asset_counts: safeCounts(safeProjection.asset_counts),
    projection_source: "runtime_script_core_truth",
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
  if (!revisionId || !revision) {
    state.selection = { nodeIds: [], edgeId: null };
    return state.production.script_core_truth_projection;
  }
  const revisionNode = revisionNodeFor(projectId, revision, safeProjection);
  state.nodes[revisionNode.id] = revisionNode;
  pushOrder(state, revisionNode.id);
  const assets = Array.isArray(safeProjection.assets) ? safeProjection.assets : [];
  assets.forEach((asset, index) => {
    const node = assetNodeFor(projectId, revisionNode, asset, index);
    state.nodes[node.id] = node;
    pushOrder(state, node.id);
    const edgeId = `edge_${revisionNode.id}__${node.id}`;
    state.edges[edgeId] = {
      id: edgeId,
      from: revisionNode.id,
      to: node.id,
      relation_type: "script_core_truth",
    };
  });
  state.selection = state.selection?.nodeIds?.some((id) => state.nodes[id])
    ? state.selection
    : { nodeIds: [revisionNode.id], edgeId: null };
  return state.production.script_core_truth_projection;
}

export function selectedCoreAssetFromState(state) {
  const selectedId = state?.selection?.nodeIds?.[0] || "";
  const node = selectedId ? state?.nodes?.[selectedId] : null;
  return node?.params?.coreAssetTruth || null;
}

function removePreviousProjection(state) {
  const remove = new Set();
  for (const [id, node] of Object.entries(state.nodes || {})) {
    if (node?.params?.scriptCoreProjection === PROJECTION_FLAG) remove.add(id);
  }
  for (const id of remove) delete state.nodes[id];
  state.order = (state.order || []).filter((id) => !remove.has(id));
  for (const [edgeId, edge] of Object.entries(state.edges || {})) {
    if (remove.has(edge.from) || remove.has(edge.to) || edge.relation_type === "script_core_truth") delete state.edges[edgeId];
  }
  if ((state.selection?.nodeIds || []).some((id) => remove.has(id))) {
    state.selection = { nodeIds: [], edgeId: null };
  }
}

function revisionNodeFor(projectId, revision, projection) {
  const revisionId = cleanToken(revision.revision_id, 140);
  const analysisState = cleanToken(projection.analysis_state || revision.analysis_state || "analysis_required", 80);
  const sourceKind = cleanToken(revision.source_kind || "script", 40);
  const sourceDigest = cleanDigest(revision.source_digest || "");
  const counts = safeCounts(projection.asset_counts);
  return {
    id: `script_truth_revision_${revisionId}`,
    type: "script",
    title: `ScriptRevision ${revisionId.slice(-6)}`,
    x: 80,
    y: 80,
    w: 300,
    h: 280,
    prompt: "",
    params: {
      model: null,
      attachments: [],
      styleRef: null,
      isReference: false,
      scriptCoreProjection: PROJECTION_FLAG,
      scriptRevision: {
        project_id: projectId,
        revision_id: revisionId,
        source_kind: sourceKind,
        source_digest: sourceDigest,
        source_length: Number(revision.source_length || 0),
        analysis_state: analysisState,
      },
      coreAssetCounts: counts,
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
    content: [
      `source_kind: ${sourceKind}`,
      `analysis_state: ${analysisState}`,
      `characters: ${counts.characters || 0}`,
      `main_scenes: ${counts.main_scenes || 0}`,
      `manual_props: ${counts.manual_props || 0}`,
    ].join("\n"),
    status: analysisState === "confirmed" ? "complete" : "draft",
    result: null,
    groupId: null,
    collapsed: false,
  };
}

function assetNodeFor(projectId, revisionNode, asset, index) {
  const assetId = cleanToken(asset.asset_id, 160);
  const assetType = cleanToken(asset.asset_type, 60);
  const status = cleanToken(asset.status || "pending_confirmation", 80);
  const sourceMode = cleanToken(asset.source_mode || "", 80);
  const label = cleanLabel(asset.display_name || asset.name || assetId);
  const column = assetType === "main_scene" ? 720 : assetType === "prop" ? 420 : 420;
  const row = assetType === "main_scene" ? index : index;
  return {
    id: `script_truth_asset_${assetId}`,
    type: assetType === "main_scene" ? "text" : assetType === "prop" ? "library" : "text",
    title: label,
    x: column,
    y: 80 + row * 150,
    w: 300,
    h: 180,
    prompt: "",
    params: {
      model: null,
      attachments: [],
      styleRef: null,
      isReference: false,
      scriptCoreProjection: PROJECTION_FLAG,
      coreAssetTruth: {
        project_id: projectId,
        revision_id: cleanToken(asset.revision_id || revisionNode.params.scriptRevision.revision_id, 140),
        source_digest: cleanDigest(asset.source_digest || revisionNode.params.scriptRevision.source_digest),
        asset_id: assetId,
        asset_type: assetType,
        source_mode: sourceMode,
        status,
      },
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
    content: [
      `${assetType}: ${label}`,
      `status: ${status}`,
      `source_mode: ${sourceMode}`,
      Array.isArray(asset.aliases) && asset.aliases.length ? `aliases: ${asset.aliases.join(", ")}` : "",
      Number(asset.confidence || 0) ? `confidence: ${Number(asset.confidence).toFixed(2)}` : "",
    ].filter(Boolean).join("\n"),
    status: status === "confirmed" ? "complete" : "draft",
    result: null,
    groupId: null,
    collapsed: false,
  };
}

function pushOrder(state, nodeId) {
  state.order = (state.order || []).filter((id) => id !== nodeId);
  state.order.push(nodeId);
}

function safeCounts(value) {
  const counts = value && typeof value === "object" ? value : {};
  return {
    characters: Number(counts.characters || 0),
    main_scenes: Number(counts.main_scenes || 0),
    manual_props: Number(counts.manual_props || 0),
    auto_props: 0,
    style_assets: 0,
    action_event_assets: 0,
  };
}

function cleanToken(value, limit) {
  return String(value || "").replace(/[^A-Za-z0-9_.:-]/g, "").slice(0, limit);
}

function cleanDigest(value) {
  const text = String(value || "").trim().toLowerCase();
  return /^[a-f0-9]{64}$/.test(text) ? text : "";
}

function cleanLabel(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 120) || "Core Asset";
}
