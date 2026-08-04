const PROJECTION_FLAG = "script_core_truth_projection";

export function applyScriptCoreTruthProjection(state, projection) {
  const safeProjection = projection && typeof projection === "object" ? projection : {};
  const projectId = cleanToken(safeProjection.project_id || state?.meta?.projectId, 128);
  if (!projectId || projectId !== cleanToken(state?.meta?.projectId, 128)) {
    throw new Error("script truth project does not match the active canvas");
  }
  const revision = safeProjection.current_revision || null;
  if (revision?.project_id && cleanToken(revision.project_id, 128) !== projectId) {
    throw new Error("script revision project does not match the active canvas");
  }
  for (const asset of Array.isArray(safeProjection.assets) ? safeProjection.assets : []) {
    if (asset?.project_id && cleanToken(asset.project_id, 128) !== projectId) {
      throw new Error("script asset project does not match the active canvas");
    }
  }
  const revisionId = cleanToken(safeProjection.current_revision_id || revision?.revision_id, 140);
  const previousRevisionNode = state.nodes?.[`script_truth_revision_${revisionId}`] || null;
  const previousSelectedNodeIds = Array.isArray(state.selection?.nodeIds)
    ? [...state.selection.nodeIds]
    : [];
  removePreviousProjection(state);
  const sourceDigest = cleanDigest(revision?.source_digest || "");
  state.production = state.production || {};
  state.production.script_core_truth_projection = {
    schema_version: String(safeProjection.schema_version || ""),
    project_id: projectId,
    current_revision_id: revisionId,
    source_digest: sourceDigest,
    source_text: cleanSourceText(revision?.source_text),
    source_kind: cleanToken(revision?.source_kind || "", 40),
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
  const revisionNode = revisionNodeFor(projectId, revision, safeProjection, previousRevisionNode);
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
  const restoredNodeIds = previousSelectedNodeIds.filter((id) => state.nodes[id]);
  state.selection = restoredNodeIds.length
    ? { nodeIds: restoredNodeIds, edgeId: null }
    : state.selection?.nodeIds?.some((id) => state.nodes[id])
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

function revisionNodeFor(projectId, revision, projection, previousNode = null) {
  const revisionId = cleanToken(revision.revision_id, 140);
  const analysisState = cleanToken(projection.analysis_state || revision.analysis_state || "analysis_required", 80);
  const sourceKind = cleanToken(revision.source_kind || "script", 40);
  const sourceDigest = cleanDigest(revision.source_digest || "");
  const counts = safeCounts(projection.asset_counts);
  const sourceText = cleanSourceText(revision.source_text);
  const previousParams = previousNode?.params && typeof previousNode.params === "object" ? previousNode.params : {};
  return {
    id: `script_truth_revision_${revisionId}`,
    type: "script",
    title: "剧本版本",
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
        source_text: sourceText,
        analysis_state: analysisState,
      },
      coreAssetCounts: counts,
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
      ...(previousParams.embeddedCreativeAction
        ? { embeddedCreativeAction: safeProjectedCreativeAction(previousParams.embeddedCreativeAction) }
        : {}),
      ...(Array.isArray(previousParams.revisions) ? { revisions: previousParams.revisions } : {}),
      ...(previousParams.currentRevisionId ? { currentRevisionId: previousParams.currentRevisionId } : {}),
    },
    content: [
      sourceText ? `${sourceKind === "idea" ? "创作想法" : "剧本文本"}：${sourceExcerpt(sourceText)}` : "创作内容：待补充",
      `来源：${sourceKindLabel(sourceKind)}`,
      `分析：${analysisStateLabel(analysisState)}`,
      `角色：${counts.characters || 0}`,
      `主要场景：${counts.main_scenes || 0}`,
      `手动道具：${counts.manual_props || 0}`,
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
        candidate_id: cleanToken(asset.candidate_id || "", 160),
        version: Math.max(1, Number(asset.version || 1)),
        version_id: cleanToken(asset.version_id || "", 160),
        parent_version_id: cleanToken(asset.parent_version_id || "", 160),
        review_decision_id: cleanToken(asset.review_decision_id || "", 160),
        display_name: label,
        evidence_spans: safeEvidenceSpans(asset.evidence_spans),
      },
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
    content: [
      `类型：${assetTypeLabel(assetType)}`,
      `状态：${assetStatusLabel(status)}`,
      sourceMode ? `来源：${sourceModeLabel(sourceMode)}` : "",
      Array.isArray(asset.aliases) && asset.aliases.length ? `别名：${asset.aliases.join(", ")}` : "",
      Number(asset.confidence || 0) ? `置信度：${Number(asset.confidence).toFixed(2)}` : "",
      safeEvidenceSpans(asset.evidence_spans).length
        ? `依据：${safeEvidenceSpans(asset.evidence_spans).map((item) => item.quote).join(" / ")}`
        : "",
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

function cleanSourceText(value) {
  return String(value || "").replace(/\r\n?/g, "\n").trim().slice(0, 200000);
}

function safeEvidenceSpans(value) {
  return (Array.isArray(value) ? value : []).slice(0, 12).map((item) => ({
    start: Math.max(0, Number(item?.start || 0)),
    end: Math.max(0, Number(item?.end || 0)),
    quote: String(item?.quote || "").replace(/\s+/g, " ").trim().slice(0, 1200),
  })).filter((item) => item.quote && item.end > item.start);
}

function sourceExcerpt(value, limit = 520) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function safeProjectedCreativeAction(value) {
  if (!value || typeof value !== "object") return null;
  if (value.action_type !== "script_revision" || value.status !== "unavailable") return value;
  return {
    ...value,
    message: "文本优化未完成；原始想法已保留。",
    error: "文本优化未完成；原始想法已保留。",
    error_category: value.error_category === "timeout" ? "timeout" : "task_failed",
    error_owner: "runtime",
    error_detail: "",
    preserved_state: "原文已保留并可继续编辑；制作内容没有改变。",
    next_action: "检查后可重新运行文本优化。",
  };
}

function sourceKindLabel(value) {
  const kind = String(value || "").trim();
  if (kind === "idea") return "想法";
  if (kind === "script") return "剧本";
  if (kind === "uploaded_text") return "上传文本";
  return kind.replace(/_/g, " ") || "文本";
}

function analysisStateLabel(value) {
  const state = String(value || "").trim();
  if (!state || state === "analysis_required") return "待分析";
  if (state === "low_confidence_pending") return "低置信待确认";
  if (state === "pending_confirmation") return "待确认";
  if (state === "confirmed") return "已确认";
  if (state === "rejected") return "已拒绝";
  if (state === "expired") return "已过期";
  return state.replace(/_/g, " ");
}

function assetTypeLabel(value) {
  const type = String(value || "").trim();
  if (type === "character") return "角色";
  if (type === "main_scene") return "主要场景";
  if (type === "prop") return "手动道具";
  return type.replace(/_/g, " ") || "资产";
}

function assetStatusLabel(value) {
  const status = String(value || "").trim();
  if (status === "confirmed") return "已确认";
  if (status === "candidate") return "待审阅";
  if (status === "modified") return "已修改，待审阅";
  if (status === "rejected") return "已拒绝";
  if (status === "expired") return "已过期";
  if (status === "pending_confirmation") return "待确认";
  if (status === "retired") return "已停用";
  if (status === "low_confidence_pending") return "低置信待确认";
  return status.replace(/_/g, " ") || "待确认";
}

function sourceModeLabel(value) {
  const mode = String(value || "").trim();
  if (mode === "analysis_candidate") return "结构化候选";
  if (mode === "manual") return "手动";
  return mode.replace(/_/g, " ");
}
