import { agentChatContextSnapshot } from "./agent-chat-lifecycle.js";

const ACTION_MODES = {
  script_revision: "professional_expansion",
  shot_breakdown: "dynamic_shot_breakdown",
};

export function canUseEmbeddedCreativeAction(node, actionType = "script_revision") {
  if (!node) return false;
  if (actionType === "shot_breakdown") return ["text", "script", "sequence", "scene"].includes(node.type);
  return ["text", "script"].includes(node.type) || Boolean(node.params?.assetCardDraft);
}

export async function startEmbeddedCreativeAction(store, runtime, node, actionType = "script_revision", options = {}) {
  if (!canUseEmbeddedCreativeAction(node, actionType)) return null;
  const sourceText = sourceTextForNode(node);
  const actionId = `embedded_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const mode = options.mode || ACTION_MODES[actionType] || "professional_expansion";
  store.set((state) => {
    const target = state.nodes[node.id];
    if (!target) return;
    target.params.embeddedCreativeAction = {
      action_id: actionId,
      action_type: actionType,
      mode,
      status: sourceText.trim() ? "running" : "needs_input",
      source_text: sourceText,
      message: sourceText.trim()
        ? "AI 正在为当前节点生成可审查预览；确认前不会改动画布。"
        : "请先在当前节点输入想法、剧本或制作说明。",
      requested_at: new Date().toISOString(),
      preview: null,
      error: "",
    };
    state.selection = { nodeIds: [node.id], edgeId: null };
  }, { history: false });
  if (!sourceText.trim()) return null;
  if (!runtime?.previewEmbeddedCreativeAction) {
    markEmbeddedCreativeUnavailable(store, node.id, actionId, "运行服务没有可用的节点内 AI 预览接口；不会使用本地模板冒充改写。");
    return null;
  }
  try {
    const response = await runtime.previewEmbeddedCreativeAction({
      action_type: actionType,
      node_id: node.id,
      node_type: node.type,
      source_text: sourceText,
      mode,
      context_summary: safeNodeContext(store.get(), node),
      constraints: embeddedConstraints(actionType),
      provider_service_id: "server_codex",
      generated_at: new Date().toISOString(),
    });
    store.set((state) => {
      const target = state.nodes[node.id];
      if (!target || target.params?.embeddedCreativeAction?.action_id !== actionId) return;
      target.params.embeddedCreativeAction = {
        ...target.params.embeddedCreativeAction,
        status: response?.mode === "llm" && response?.provider_calls_started === true ? "preview" : "unavailable",
        message: response?.mode === "llm"
          ? "已生成节点内预览。请比较后应用、编辑或取消。"
          : response?.preview?.rationale || "AI 模型当前不可用；不会使用本地模板冒充改写。",
        preview: response?.preview || null,
        provider_lineage: safeProviderLineage(response?.provider_lineage),
        graph_mutation: response?.graph_mutation || null,
        latency_ms: response?.latency_ms || 0,
        cost_usd: Number(response?.cost_usd || 0),
        completed_at: new Date().toISOString(),
      };
    }, { history: false });
    await store.flushRuntimeSave?.();
    return response;
  } catch (error) {
    markEmbeddedCreativeUnavailable(store, node.id, actionId, safeError(error));
    return null;
  }
}

export function cancelEmbeddedCreativeAction(store, nodeId) {
  store.set((state) => {
    const node = state.nodes[nodeId];
    if (!node?.params?.embeddedCreativeAction) return;
    node.params.embeddedCreativeAction = {
      ...node.params.embeddedCreativeAction,
      status: "cancelled",
      message: "预览已取消，当前节点没有改变。",
      cancelled_at: new Date().toISOString(),
    };
  }, { history: false });
}

export function clearEmbeddedCreativeAction(store, nodeId) {
  store.set((state) => {
    const node = state.nodes[nodeId];
    if (node?.params) delete node.params.embeddedCreativeAction;
  }, { history: false });
}

export function applyEmbeddedCreativeAction(store, nodeId) {
  store.set((state) => {
    const node = state.nodes[nodeId];
    const action = node?.params?.embeddedCreativeAction;
    const preview = action?.preview || {};
    const revisedText = String(preview.revised_text || "").trim();
    if (!node || action?.status !== "preview" || !revisedText) return;
    const revisions = Array.isArray(node.params.revisions) ? node.params.revisions : [];
    const revisionId = `node_revision_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    revisions.push({
      revision_id: revisionId,
      action_type: action.action_type,
      mode: action.mode,
      before_text: action.source_text || node.content || node.prompt || "",
      after_text: revisedText,
      change_summary: preview.change_summary || [],
      rationale: preview.rationale || "",
      provider_lineage: action.provider_lineage || {},
      graph_mutation: action.graph_mutation || null,
      applied_at: new Date().toISOString(),
      same_node_identity: true,
    });
    node.params.revisions = revisions;
    node.params.currentRevisionId = revisionId;
    node.params.lastEmbeddedCreativeActionSummary = {
      action_type: action.action_type,
      mode: action.mode,
      revision_id: revisionId,
      provider_calls_started: action.provider_lineage?.provider_calls_started === true,
      cost_usd: Number(action.cost_usd || 0),
    };
    if (action.action_type === "shot_breakdown" && preview.shot_plan) {
      node.params.shotPlanDraft = {
        ...preview.shot_plan,
        source_revision_id: revisionId,
        confirmed_at: new Date().toISOString(),
      };
    }
    node.content = revisedText;
    node.prompt = revisedText;
    node.status = "draft";
    node.params.embeddedCreativeAction = {
      ...action,
      status: "applied",
      message: action.action_type === "shot_breakdown"
        ? "分镜草案已记录在当前节点，可继续编辑或显式派生镜头节点。"
        : "修订已应用到当前节点；没有创建新的剧本版本节点。",
      applied_revision_id: revisionId,
      applied_at: new Date().toISOString(),
    };
    state.selection = { nodeIds: [node.id], edgeId: null };
  });
}

export function editEmbeddedCreativePreview(store, nodeId, text) {
  store.set((state) => {
    const action = state.nodes[nodeId]?.params?.embeddedCreativeAction;
    if (!action?.preview) return;
    action.preview.revised_text = String(text || "");
  }, { history: false, renderScope: "canvas-local-edit" });
}

function markEmbeddedCreativeUnavailable(store, nodeId, actionId, message) {
  store.set((state) => {
    const action = state.nodes[nodeId]?.params?.embeddedCreativeAction;
    if (!action || action.action_id !== actionId) return;
    action.status = "unavailable";
    action.message = message;
    action.error = message;
    action.provider_lineage = { provider_calls_started: false };
    action.completed_at = new Date().toISOString();
  }, { history: false });
}

function sourceTextForNode(node) {
  return String(node?.content || node?.prompt || node?.result || "").trim();
}

function safeNodeContext(state, node) {
  const snapshot = agentChatContextSnapshot({
    project: { project_id: state.meta?.projectId || "", name: state.meta?.projectName || "" },
    studioState: state,
    section: "canvas",
    selectedNode: node,
  });
  return {
    project_name: snapshot.project_name,
    selected_node_title: snapshot.selected_node_title,
    selected_node_type: snapshot.selected_node_type,
    selected_node_status: snapshot.selected_node_status,
    selected_edge_relation_type: snapshot.selected_edge_relation_type,
    counts: snapshot.counts,
    section: snapshot.section,
  };
}

function embeddedConstraints(actionType) {
  if (actionType === "shot_breakdown") {
    return [
      "镜头数量和时长由内容决定，禁止固定模板。",
      "每个镜头需要景别、机位、运动、调度、声音、转场和叙事目的。",
      "确认前不创建镜头节点、不写入制作图。",
    ];
  }
  return [
    "普通优化必须保持同一节点身份。",
    "专业扩写需要补足角色目标、冲突、关系、动作、对白、节奏和视觉表达。",
    "确认前不改动画布；不要输出空泛标题模板。",
  ];
}

function safeProviderLineage(value) {
  if (!value || typeof value !== "object") return { provider_calls_started: false };
  return {
    service_id: String(value.service_id || ""),
    provider: String(value.provider || ""),
    model_surface: String(value.model_surface || ""),
    request_id: String(value.request_id || ""),
    structured_output_contract_id: String(value.structured_output_contract_id || ""),
    structured_output_schema_digest: String(value.structured_output_schema_digest || ""),
    provider_calls_started: value.provider_calls_started === true,
    external_paid_cost_usd: Number(value.external_paid_cost_usd || 0),
  };
}

function safeError(error) {
  return String(error?.message || error || "节点内 AI 动作失败；当前节点未改变。")
    .replace(/\bBearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/\/(?:home|Users|mnt|var|tmp|opt)\/[^\s"'<>]+/g, "<local-path-redacted>")
    .slice(0, 220);
}
