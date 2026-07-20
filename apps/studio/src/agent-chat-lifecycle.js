import { applyProductionPlanProjection } from "./production-plan-projection.js";
import { applyScriptCoreTruthProjection } from "./script-core-truth-projection.js";
import { fitVisibleCanvasViewport } from "./canvas-safe-area.js";

const SCHEMA_VERSION = "afs_agent_chat_lifecycle.v0.1";
const CORE_ASSET_COMMAND_SCHEMA_VERSION = "afs.core_asset_command.v0.1";
const STORY_PLAN_CANDIDATE_SCHEMA_VERSION = "afs.story_plan_candidate.v0.1";
const PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION = "afs.production_plan_command.v0.1";
const M3_CONTEXT_COMMAND_SCHEMA_VERSION = "afs.m3_context_command.v0.1";
const MESSAGE_LIMIT = 28;
const RECEIPT_LIMIT = 12;

export function createAgentChatContextStore() {
  const contexts = new Map();
  return {
    get(key) {
      const safeKey = cleanToken(key, 180) || "unknown";
      if (!contexts.has(safeKey)) contexts.set(safeKey, emptySession(safeKey));
      return contexts.get(safeKey);
    },
  };
}

export function agentChatContextKey(context = {}) {
  return [
    cleanToken(context.project_id, 120) || "local-project",
    cleanToken(context.section, 80) || "canvas",
    "agent-chat",
  ].join(":");
}

export function agentChatContextSnapshot({
  project = null,
  studioState = null,
  section = "canvas",
  selectedNode = null,
  currentShot = null,
} = {}) {
  const state = studioState && typeof studioState === "object" ? studioState : {};
  const meta = state.meta && typeof state.meta === "object" ? state.meta : {};
  const nodes = state.nodes && typeof state.nodes === "object" ? state.nodes : {};
  const nodeValues = Object.values(nodes).filter(Boolean);
  const shotNodes = nodeValues.filter((node) => node?.params?.structuredShot || node?.params?.nodeRole === "storyboard_shot");
  const activeNode = selectedNode || null;
  const scriptTruth = state.production?.script_core_truth_projection || {};
  const productionPlan = state.production?.dynamic_production_plan_projection || {};
  const productionGraph = state.production?.production_graph_projection || {};
  const selectedCoreAsset = activeNode?.params?.coreAssetTruth || null;
  const selectedPlanEntity = activeNode?.params?.productionPlanTruth || null;
  const scriptRevisionId = cleanToken(scriptTruth.current_revision_id, 140);
  const scriptSourceDigest = cleanToken(scriptTruth.source_digest, 80);
  const planShotCount = Number(productionPlan.shot_count || 0);
  return {
    schema_version: SCHEMA_VERSION,
    project_id: cleanToken(project?.project_id || meta.projectId, 120),
    revision_id: scriptRevisionId || cleanToken(meta.seq ? `studio-state-${meta.seq}` : "", 80),
    studio_state_revision_id: cleanToken(meta.seq ? `studio-state-${meta.seq}` : "", 80),
    script_revision_id: scriptRevisionId,
    script_source_digest: scriptSourceDigest,
    script_analysis_state: cleanToken(scriptTruth.analysis_state || "", 80),
    production_plan_id: cleanToken(productionPlan.plan_id, 140),
    production_plan_digest: cleanToken(productionPlan.plan_digest, 80),
    production_plan_state: cleanToken(productionPlan.planning_state || "", 80),
    production_plan_version: Number(productionPlan.plan_version || 0),
    production_graph_version: Number(productionGraph.graph_version || 0),
    production_graph_digest: cleanToken(productionGraph.graph_digest, 80),
    canvas_name: cleanText(meta.canvasName || "画布", 40),
    project_name: cleanText(project?.name || meta.projectName || "未命名项目", 80),
    section: section === "storyboard" ? "storyboard_read_only" : "canvas",
    selected_node_id: cleanToken(activeNode?.id, 120),
    selected_node_type: cleanToken(activeNode?.type, 40),
    selected_node_status: cleanToken(activeNode?.status, 40),
    selected_node_title: cleanText(activeNode?.title || activeNode?.label || "", 80),
    selected_node_text: cleanSourceText(activeNode?.content || activeNode?.prompt || "", 12000),
    selected_core_asset_id: cleanToken(selectedCoreAsset?.asset_id, 140),
    selected_core_asset_type: cleanToken(selectedCoreAsset?.asset_type, 60),
    selected_core_asset_status: cleanToken(selectedCoreAsset?.status, 80),
    selected_plan_entity_type: cleanToken(selectedPlanEntity?.entity_type, 80),
    selected_plan_shot_id: cleanToken(selectedPlanEntity?.shot_id, 140),
    selected_plan_chunk_id: cleanToken(selectedPlanEntity?.chunk_id, 160),
    selected_plan_entity_plan_id: cleanToken(selectedPlanEntity?.plan_id, 140),
    selected_plan_entity_plan_digest: cleanToken(selectedPlanEntity?.plan_digest, 80),
    current_shot_node_id: cleanToken(currentShot?.nodeId, 120),
    current_shot_title: cleanText(currentShot?.title || "", 80),
    counts: {
      nodes: nodeValues.length,
      scenes: Number(productionGraph.scene_count || 0) || inferSceneCount(shotNodes),
      shots: Number(productionGraph.shot_count || 0) || planShotCount || shotNodes.length,
      assets: Array.isArray(state.assets) ? state.assets.length : 0,
      graph_tasks: Number(productionGraph.task_count || 0),
      graph_pending_reviews: Number(productionGraph.pending_review_count || 0),
      production_plan_shots: planShotCount,
      production_plan_chunks: Number(productionPlan.chunk_count || 0),
    },
    capabilities: [
      "multi_turn_history",
      "context_snapshot",
      "typed_command_preview",
      "confirm_before_mutation",
      "execution_receipt",
      "safe_error_recovery",
      "undo_receipt",
      "storyboard_read_only_projection",
      "script_revision_truth_contract",
      "core_asset_truth_runtime_commands",
      "dynamic_story_plan_candidate_contract",
      "media_strategy_preview_confirm",
      "chunk_continuity_plan_contract",
      "production_plan_undo",
      "m3_zero_cost_context_pack",
      "feedback_not_memory_contract",
      "knowledge_pack_scoped_retrieval",
    ],
    storyboard_mode: "read_only_deferred",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

export function stageProductionGraphCommand(session, context, { action, title, summary, targetNodeId = "", changedNodeIds = [], patch = {}, payload = {}, impact = null } = {}) {
  if (!session || !action) throw new Error("production graph command requires a session and action");
  const command = {
    schema_version: SCHEMA_VERSION,
    command_id: `command_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: action === "mutate" ? "m5_graph_mutation" : "m5_graph_action",
    graph_action: action,
    title: cleanText(title || "更新制作序列", 100),
    summary: cleanText(summary || "确认后更新同一制作图版本。", 320),
    status: "preview",
    execution_mode: "runtime",
    context_key: context?.context_key || agentChatContextKey(context),
    project_id: context?.project_id || "",
    graph_version: Number(context?.production_graph_version || 0),
    graph_digest: context?.production_graph_digest || "",
    target_node_id: cleanToken(targetNodeId, 160),
    changed_node_ids: changedNodeIds.map((item) => cleanToken(item, 160)).filter(Boolean),
    patch: { ...patch },
    payload: { ...payload },
    impact: impact ? { node_ids: [...(impact.invalidated_node_ids || [])], storyboard_write: false } : { node_ids: [], storyboard_write: false },
    storyboard_write: false,
    provider_dispatch_count: 0,
  };
  appendMessage(session, { role: "user", text: command.title });
  session.pendingCommand = command;
  appendMessage(session, { role: "assistant", text: "已生成制作图命令预览；确认前不会改变制作事实。" });
  return command;
}

export function stageProductionGraphCandidateCommand(session, context, candidate) {
  const characters = Array.isArray(candidate?.characters) ? candidate.characters.length : 0;
  const scenes = Array.isArray(candidate?.scenes) ? candidate.scenes.length : 0;
  const shots = Array.isArray(candidate?.shots) ? candidate.shots.length : 0;
  if (!session || candidate?.trusted_candidate !== true || !characters || !scenes || !shots) {
    throw new Error("可信制作方案需要明确的角色、场景和镜头结构");
  }
  const command = {
    schema_version: SCHEMA_VERSION,
    command_id: `command_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "m5_graph_candidate",
    graph_action: "confirm_candidate",
    title: "确认导入制作方案",
    summary: `确认后建立 ${characters} 个角色、${scenes} 个场景和 ${shots} 个镜头，并生成同一制作图版本。`,
    status: "preview",
    execution_mode: "runtime",
    context_key: context?.context_key || agentChatContextKey(context),
    project_id: context?.project_id || "",
    graph_version: Number(context?.production_graph_version || 0),
    candidate,
    storyboard_write: false,
    provider_dispatch_count: 0,
  };
  appendMessage(session, { role: "user", text: "导入可信制作方案" });
  session.pendingCommand = command;
  appendMessage(session, { role: "assistant", text: "已核对结构范围；确认前不会建立制作图或改变画布事实。" });
  return command;
}

export function submitAgentChatMessage(session, rawText, context) {
  const commandText = cleanSourceText(rawText, 12000);
  const displayText = cleanText(rawText, 900);
  if (!commandText) return { status: "empty" };
  const command = previewAgentCommand(commandText, context);
  if (command.command_type !== "none") {
    command.raw_command_text = commandText;
    appendMessage(session, { role: "user", text: userCommandDisplayText(command, displayText || commandText) });
    session.pendingCommand = command;
    appendMessage(session, {
      role: command.status === "blocked" ? "assistant" : "assistant",
      text: command.status === "blocked"
        ? command.error_message
        : "已生成命令预览；确认前不会改变画布事实。",
    });
    return { status: command.status, command };
  }
  appendMessage(session, { role: "user", text: displayText || commandText });
  appendMessage(session, {
    role: "assistant",
    text: "已记录到当前上下文。需要改动画布时，请发送可预览命令。",
  });
  return { status: "recorded" };
}

export function cancelAgentCommand(session) {
  if (!session?.pendingCommand) return null;
  const command = session.pendingCommand;
  session.pendingCommand = null;
  appendMessage(session, { role: "assistant", text: "命令预览已取消，画布未改变。" });
  return command;
}

export function executePendingAgentCommand(session, state) {
  const command = session?.pendingCommand;
  if (!command) throw new Error("agent command preview is empty");
  if (command.status === "blocked") throw new Error(command.error_message || "agent command is blocked");
  const receipt = executeAgentCommand(command, state);
  session.pendingCommand = null;
  recordReceipt(session, receipt);
  appendMessage(session, { role: "assistant", text: receipt.summary });
  return receipt;
}

export async function executePendingAgentCommandWithRuntime(session, store, runtime) {
  const command = session?.pendingCommand;
  if (!command) throw new Error("agent command preview is empty");
  if (command.status === "blocked") throw new Error(command.error_message || "agent command is blocked");
  if (command.execution_mode !== "runtime") {
    let receipt = null;
    store.set((state) => {
      receipt = executePendingAgentCommand(session, state);
    });
    return receipt;
  }
  if (!runtime) throw new Error("运行服务连接不可用");
  let response = null;
  let runtimeReceipt = null;
  let projectionDomain = "script_core";
  if (command.command_type === "m5_graph_candidate") {
    response = await runtime.confirmFilmCandidate({
      expected_graph_version: command.graph_version,
      idempotency_key: command.command_id,
      candidate: command.candidate,
    });
    const graph = response?.graph || {};
    runtimeReceipt = { graph_version: graph.version, graph_digest: graph.graph_digest, recovery: "refresh_and_retry_on_version_conflict" };
    projectionDomain = "production_graph";
  } else if (command.command_type === "m5_graph_mutation") {
    await runtime.previewSequenceImpact({ changed_node_ids: command.changed_node_ids });
    response = await runtime.confirmSequenceMutation({
      expected_graph_version: command.graph_version,
      idempotency_key: command.command_id,
      node_id: command.target_node_id,
      changed_node_ids: command.changed_node_ids,
      patch: command.patch,
    });
    runtimeReceipt = response?.receipt || null;
    projectionDomain = "production_graph";
  } else if (command.command_type === "m5_graph_action") {
    response = await runtime.confirmSequenceAction({
      expected_graph_version: command.graph_version,
      idempotency_key: command.command_id,
      action: command.graph_action,
      payload: command.payload,
    });
    runtimeReceipt = response?.receipt || null;
    projectionDomain = "production_graph";
  } else if (command.command_type === "create_script_revision" || command.command_type === "optimize_script_revision") {
    response = await runtime.createScriptRevision({
      source_kind: command.source_kind || "script",
      source_text: command.source_text || "",
      parent_revision_id: command.parent_revision_id || null,
      provenance: {
        source: command.command_type === "optimize_script_revision" ? "agent_chat_script_optimization" : "agent_chat",
        command_id: command.command_id,
        context_key: command.context_key,
        optimization_mode: command.optimization_mode || "",
        optimization_instruction: command.optimization_instruction || "",
      },
      created_at: new Date().toISOString(),
    });
  } else if (command.command_type === "refresh_script_truth") {
    response = await runtime.loadScriptTruth();
  } else if (command.command_type === "submit_story_plan_candidate") {
    const submitResponse = await runtime.submitStoryPlanCandidate(command.candidate);
    const candidateDigest = submitResponse?.candidate?.candidate_digest || command.candidate?.candidate_digest || "";
    response = await runtime.confirmStoryPlanCandidate(candidateDigest, {
      project_id: command.project_id,
      script_revision_id: command.script_revision_id,
      source_digest: command.source_digest,
      candidate_digest: candidateDigest,
      schema_version: STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
    });
    runtimeReceipt = response?.receipt || null;
    projectionDomain = "production_plan";
  } else if (command.command_type === "request_story_plan_candidate") {
    response = await runtime.loadProductionPlanTruth();
    projectionDomain = "production_plan";
  } else if (command.command_type === "refresh_production_plan") {
    response = await runtime.loadProductionPlanTruth();
    projectionDomain = "production_plan";
  } else if (isProductionPlanRuntimeCommand(command.command_type)) {
    const payload = runtimeProductionPlanCommandPayload(command);
    await runtime.previewProductionPlanCommand(payload);
    response = await runtime.confirmProductionPlanCommand(payload);
    runtimeReceipt = response?.receipt || null;
    projectionDomain = "production_plan";
  } else if (command.command_type === "build_m3_context_pack") {
    const payload = runtimeM3ContextPackPayload(command);
    await runtime.previewM3ContextPack(payload);
    response = await runtime.confirmM3ContextPack(payload);
    runtimeReceipt = response?.receipt || null;
    projectionDomain = "m3_context";
  } else {
    const payload = runtimeCoreAssetCommandPayload(command);
    await runtime.previewCoreAssetCommand(payload);
    response = await runtime.confirmCoreAssetCommand(payload);
    runtimeReceipt = response?.receipt || null;
  }
  const projection = response?.projection;
  let projectionSummary = null;
  if (projection && projectionDomain !== "production_graph") {
    store.set((state) => {
      projectionSummary = projectionDomain === "production_plan"
        ? applyProductionPlanProjection(state, projection)
        : applyScriptCoreTruthProjection(state, projection);
      fitCanvasProjection(state);
    });
  }
  const receipt = projectionDomain === "production_graph"
    ? productionGraphAgentReceipt(command, runtimeReceipt)
    : projectionDomain === "production_plan"
    ? productionPlanAgentReceipt(command, response, runtimeReceipt, projectionSummary)
    : projectionDomain === "m3_context"
      ? m3ContextAgentReceipt(command, response, runtimeReceipt)
      : runtimeAgentReceipt(command, response, runtimeReceipt, projectionSummary);
  session.pendingCommand = null;
  recordReceipt(session, receipt);
  appendMessage(session, { role: "assistant", text: receipt.summary });
  return receipt;
}

function productionGraphAgentReceipt(command, runtimeReceipt = {}) {
  const actionSummaries = {
    confirm_candidate: "可信制作方案已建立为唯一制作图版本；画布与故事板将同步刷新。",
    mutate: "局部修改已确认；仅证据关联的下游对象进入待处理，未关联产物继续保留。",
    select_candidate: "候选版本已选定并写入制作图版本记录。",
    review_decision: command.payload?.state === "approved" ? "专业审核已通过并写入制作图。" : "专业审核已退回，原候选与证据仍保留。",
    redo_rejected: "返工任务已创建；原候选、审核记录与版本历史均保留。",
    delivery_state: "交付清单状态已更新，媒体、权利与来源仍需逐项核验。",
  };
  return {
    schema_version: SCHEMA_VERSION,
    receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_id: command.command_id,
    command_type: command.command_type,
    status: "confirmed",
    executed_at: new Date().toISOString(),
    context_key: command.context_key,
    project_id: command.project_id,
    graph_version: Number(runtimeReceipt.graph_version || 0),
    graph_digest: runtimeReceipt.graph_digest || "",
    summary: actionSummaries[command.graph_action] || "制作图动作已确认。",
    undo_available: false,
    recovery_available: true,
    storyboard_write: false,
    execution_mode: "runtime",
    runtime_domain: "production_graph",
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}

export async function undoAgentReceiptWithRuntime(session, receipt, store, runtime) {
  if (receipt?.execution_mode !== "runtime") {
    let undo = null;
    store.set((state) => {
      undo = undoAgentReceipt(session, receipt, state);
    });
    return undo;
  }
  if (!receipt?.undo_available) throw new Error("agent receipt is not undoable");
  const isProductionPlan = receipt.runtime_domain === "production_plan";
  const isScriptRevision = receipt.runtime_domain === "script_revision";
  const isM3Context = receipt.runtime_domain === "m3_context";
  if (isScriptRevision) {
    if (!receipt.previous_revision_id || !runtime?.selectScriptRevision) throw new Error("script revision undo is unavailable");
    const response = await runtime.selectScriptRevision(receipt.previous_revision_id);
    let projectionSummary = null;
    if (response?.projection) {
      store.set((state) => {
        projectionSummary = applyScriptCoreTruthProjection(state, response.projection);
        fitCanvasProjection(state);
      });
    }
    const undoReceipt = {
      schema_version: SCHEMA_VERSION,
      receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      command_id: receipt.command_id,
      command_type: `${receipt.command_type}.undo`,
      status: "undone",
      executed_at: new Date().toISOString(),
      context_key: receipt.context_key,
      project_id: receipt.project_id,
      revision_id: receipt.previous_revision_id,
      script_revision_id: receipt.previous_revision_id,
      source_digest: response?.projection?.source_digest || "",
      summary: "已恢复上一个剧本版本，画布投影已同步更新。",
      undo_available: false,
      storyboard_write: false,
      execution_mode: "runtime",
      runtime_domain: "script_revision",
      projection_summary: projectionSummary,
      remote_dispatch_count: 0,
      provider_dispatch_count: 0,
    };
    receipt.undo_available = false;
    recordReceipt(session, undoReceipt);
    appendMessage(session, { role: "assistant", text: undoReceipt.summary });
    return undoReceipt;
  }
  if (isM3Context) {
    if (!runtime?.undoM3ContextPack || !receipt.context_pack_id || !receipt.runtime_receipt_id) throw new Error("上下文包撤销不可用");
    const response = await runtime.undoM3ContextPack({
      project_id: receipt.project_id,
      context_pack_id: receipt.context_pack_id,
      receipt_id: receipt.runtime_receipt_id,
      script_revision_id: receipt.script_revision_id || receipt.revision_id,
      source_digest: receipt.source_digest,
      schema_version: M3_CONTEXT_COMMAND_SCHEMA_VERSION,
    });
    const undoReceipt = {
      schema_version: SCHEMA_VERSION,
      receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      command_id: receipt.command_id,
      command_type: `${receipt.command_type}.undo`,
      status: "undone",
      executed_at: new Date().toISOString(),
      context_key: receipt.context_key,
      project_id: receipt.project_id,
      revision_id: receipt.revision_id,
      script_revision_id: receipt.script_revision_id || receipt.revision_id,
      source_digest: receipt.source_digest,
      context_pack_id: receipt.context_pack_id,
      summary: response?.receipt?.summary || "已撤销上下文包选择；剧本、分镜、资产事实未改变。",
      undo_available: false,
      storyboard_write: false,
      execution_mode: "runtime",
      runtime_domain: "m3_context",
      remote_dispatch_count: 0,
      provider_dispatch_count: 0,
    };
    receipt.undo_available = false;
    recordReceipt(session, undoReceipt);
    appendMessage(session, { role: "assistant", text: undoReceipt.summary });
    return undoReceipt;
  }
  if (!receipt?.runtime_receipt_id) throw new Error("agent receipt is not undoable");
  if (isProductionPlan && !runtime?.undoProductionPlanCommand) throw new Error("制作计划撤销不可用");
  if (!isProductionPlan && !runtime?.undoCoreAssetCommand) throw new Error("运行服务撤销不可用");
  const response = isProductionPlan
    ? await runtime.undoProductionPlanCommand({
      project_id: receipt.project_id,
      receipt_id: receipt.runtime_receipt_id,
      script_revision_id: receipt.script_revision_id || receipt.revision_id,
      source_digest: receipt.source_digest,
      plan_digest: receipt.plan_digest || receipt.after_plan_digest,
      schema_version: PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION,
    })
    : await runtime.undoCoreAssetCommand({
      project_id: receipt.project_id,
      receipt_id: receipt.runtime_receipt_id,
      revision_id: receipt.revision_id,
      source_digest: receipt.source_digest,
      schema_version: CORE_ASSET_COMMAND_SCHEMA_VERSION,
    });
  let projectionSummary = null;
  if (response?.projection) {
    store.set((state) => {
      projectionSummary = isProductionPlan
        ? applyProductionPlanProjection(state, response.projection)
        : applyScriptCoreTruthProjection(state, response.projection);
      fitCanvasProjection(state);
    });
  }
  const undoReceipt = {
    schema_version: SCHEMA_VERSION,
    receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_id: receipt.command_id,
    command_type: `${receipt.command_type}.undo`,
    status: "undone",
    executed_at: new Date().toISOString(),
    context_key: receipt.context_key,
    project_id: receipt.project_id,
    revision_id: receipt.revision_id,
    script_revision_id: receipt.script_revision_id || receipt.revision_id,
    source_digest: receipt.source_digest,
    plan_digest: response?.receipt?.after_plan_digest || "",
    summary: isProductionPlan ? productionPlanUndoSummary(receipt) : coreAssetUndoSummary(receipt),
    undo_available: false,
    storyboard_write: false,
    execution_mode: "runtime",
    runtime_domain: receipt.runtime_domain || "script_core",
    projection_summary: projectionSummary,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
  receipt.undo_available = false;
  recordReceipt(session, undoReceipt);
  appendMessage(session, { role: "assistant", text: undoReceipt.summary });
  return undoReceipt;
}

export function undoAgentReceipt(session, receipt, state) {
  if (!receipt?.undo_available) throw new Error("agent receipt is not undoable");
  const undoReceipt = applyUndo(receipt, state);
  recordReceipt(session, undoReceipt);
  appendMessage(session, { role: "assistant", text: undoReceipt.summary });
  return undoReceipt;
}

export function recordAgentCommandError(session, error) {
  const message = safeAgentErrorMessage(error);
  appendMessage(session, { role: "assistant", text: message, tone: "error" });
  return message;
}

export function safeAgentErrorMessage(error) {
  const text = cleanText(error?.message || error || "命令执行失败", 160);
  return `执行失败：${text}。可以修改命令后重试，或取消当前预览。`;
}

function emptySession(contextKey) {
  return {
    schema_version: SCHEMA_VERSION,
    context_key: contextKey,
    messages: [
      {
        role: "assistant",
        text: "我会基于当前画布上下文生成命令预览；确认前不改变事实。",
      },
    ],
    pendingCommand: null,
    receipts: [],
  };
}

function previewAgentCommand(message, context = {}) {
  const scriptText = matchCommand(message, [
    /^\/script-revision\s+(.+)$/i,
    /^创建(?:剧本)?修订[:：]\s*(.+)$/i,
  ]);
  if (scriptText) {
    return scriptRevisionCommand({
      context,
      sourceKind: "script",
      sourceText: scriptText,
      title: "创建剧本版本",
      summary: "把输入文本保存为新的剧本版本，并把同一事实投到画布。",
    });
  }

  const ideaText = matchCommand(message, [
    /^\/idea\s+(.+)$/i,
    /^创意[:：]\s*(.+)$/i,
  ]);
  if (ideaText) {
    return scriptRevisionCommand({
      context,
      sourceKind: "idea",
      sourceText: ideaText,
      title: "创建想法版本",
      summary: "把想法保存为新的剧本版本；没有可信分析前保持待分析状态。",
    });
  }

  if (/^\/optimize-selected-default$/i.test(message) || /^默认优化(?:当前)?文本$/i.test(message) || /^优化当前文本$/i.test(message)) {
    return scriptOptimizationCommand({
      context,
      mode: "default",
      instruction: "保留核心意图，改善结构、表达、节奏和可生产性。",
    });
  }

  const optimizeInstruction = matchCommand(message, [
    /^\/optimize-selected\s+(.+)$/i,
    /^按照(?:我的)?要求优化[:：]\s*(.+)$/i,
    /^按要求优化[:：]\s*(.+)$/i,
  ]);
  if (optimizeInstruction) {
    return scriptOptimizationCommand({
      context,
      mode: "instructed",
      instruction: optimizeInstruction,
    });
  }

  if (/^\/refresh-script-truth$/i.test(message) || /^刷新(?:剧本)?事实$/i.test(message)) {
    return runtimeCommand({
      context,
      commandType: "refresh_script_truth",
      title: "刷新剧本与资产事实",
      summary: "从运行服务事实重新投影剧本版本、角色、主要场景与手动道具。",
      requiresScriptRevision: false,
    });
  }

  if (/^\/plan-selected-script-shots$/i.test(message) || /^自动拆分分镜$/i.test(message) || /^自动分镜$/i.test(message)) {
    return storyPlanRequestCommand(context);
  }

  const m3Instruction = matchCommand(message, [
    /^\/m3-context-pack(?:\s+(.+))?$/i,
    /^构建精准上下文包(?:[:：]\s*(.+))?$/i,
    /^零付费审计上下文(?:[:：]\s*(.+))?$/i,
  ]);
  if (/^\/m3-context-pack$/i.test(message) || /^构建精准上下文包$/i.test(message) || /^零付费审计上下文$/i.test(message) || m3Instruction) {
    return m3ContextPackCommand(context, m3Instruction || "零付费审计当前剧本、动态计划、资产 Bible 和上下文边界。");
  }

  const storyPlanCandidate = jsonPayloadCommand(message, [
    /^\/submit-story-plan\s+/i,
    /^\/story-plan\s+/i,
    /^提交动态制作计划[:：]\s*/i,
  ]);
  if (storyPlanCandidate.matched) {
    if (!storyPlanCandidate.value) {
      return blockedCommand("submit_story_plan_candidate", "提交动态制作计划候选", storyPlanCandidate.error || "动态制作计划候选无法解析。", context);
    }
    return storyPlanCandidateCommand({
      context,
      candidate: storyPlanCandidate.value,
    });
  }

  if (/^\/refresh-production-plan$/i.test(message) || /^刷新(?:制作)?计划事实$/i.test(message)) {
    return productionPlanRefreshCommand(context);
  }

  const durationText = matchCommand(message, [
    /^\/edit-shot-duration\s+([0-9]+(?:\.[0-9]+)?)$/i,
    /^修改镜头时长[:：]\s*([0-9]+(?:\.[0-9]+)?)$/i,
  ]);
  if (durationText) {
    return productionPlanCommand({
      context,
      commandType: "edit_shot_duration",
      title: "编辑镜头时长",
      summary: `把当前镜头时长改为 ${Number(durationText).toFixed(2)} 秒，并重算该镜头的分段计划。`,
      patch: { duration_seconds: Number(durationText) },
    });
  }

  const intentText = matchCommand(message, [
    /^\/edit-shot-intent\s+(.+)$/i,
    /^修改镜头意图[:：]\s*(.+)$/i,
  ]);
  if (intentText) {
    return productionPlanCommand({
      context,
      commandType: "edit_shot_intent",
      title: "编辑镜头意图",
      summary: "更新当前镜头意图，并保留制作计划历史。",
      patch: { intent: cleanText(intentText, 900) },
    });
  }

  const strategyPatch = strategyCommandPatch(message);
  if (strategyPatch.matched) {
    if (!strategyPatch.patch) {
      return blockedCommand("set_shot_strategy", "设置镜头媒体策略", strategyPatch.error || "媒体策略必须是 t2v 或 i2v，并包含 reason。", context);
    }
    return productionPlanCommand({
      context,
      commandType: "set_shot_strategy",
      title: "设置镜头媒体策略",
      summary: `把当前镜头策略设为 ${strategyPatch.patch.strategy.toUpperCase()}，并重算输入状态和分段计划。`,
      patch: strategyPatch.patch,
    });
  }

  const splitPatch = splitCommandPatch(message);
  if (splitPatch.matched) {
    if (!splitPatch.patch) {
      return blockedCommand("split_shot", "拆分当前镜头", splitPatch.error || "拆分镜头需要两个正数时长。", context);
    }
    return productionPlanCommand({
      context,
      commandType: "split_shot",
      title: "拆分当前镜头",
      summary: "把当前镜头拆为两个新镜头，并只重算受影响分段。",
      patch: splitPatch.patch,
    });
  }

  if (/^\/merge-shot-next$/i.test(message) || /^合并下一镜头$/i.test(message)) {
    return productionPlanCommand({
      context,
      commandType: "merge_shot_next",
      title: "合并下一镜头",
      summary: "将当前镜头与后续镜头合并，并重算合并后的分段计划。",
      patch: {},
    });
  }

  if (/^\/replan-affected$/i.test(message) || /^重算受影响计划$/i.test(message)) {
    return productionPlanCommand({
      context,
      commandType: "replan_affected",
      title: "重算受影响计划",
      summary: "只重算当前或受阻镜头的分段计划，保留可证明未受影响项。",
      patch: {},
      allowMissingTarget: true,
    });
  }

  if (/^\/mark-failed$/i.test(message) || /^标记失败$/i.test(message)) {
    return productionPlanCommand({
      context,
      commandType: "mark_failed",
      title: "标记失败",
      summary: "将当前镜头或分段标记为失败，并记录失败尝试。",
      patch: { reason: "agent_chat_mark_failed" },
    });
  }

  if (/^\/retry-failed$/i.test(message) || /^重试失败项$/i.test(message)) {
    return productionPlanCommand({
      context,
      commandType: "retry_failed",
      title: "重试失败项",
      summary: "只把失败分段恢复为可重试状态，不覆盖已成功的产物脉络。",
      patch: {},
      allowMissingTarget: true,
    });
  }

  const manualProp = matchCommand(message, [
    /^\/manual-prop\s+(.+)$/i,
    /^\/add-prop\s+(.+)$/i,
    /^手动道具[:：]\s*(.+)$/i,
  ]);
  if (manualProp) {
    return coreAssetCommand({
      context,
      commandType: "create_manual_prop",
      title: "创建手动 Prop",
      summary: `创建绑定当前剧本版本的手动道具「${cleanText(manualProp, 60)}」`,
      patch: { display_name: cleanText(manualProp, 120) },
      allowMissingTarget: true,
    });
  }

  const editAsset = matchCommand(message, [
    /^\/edit-selected-asset\s+(.+)$/i,
    /^编辑当前资产[:：]\s*(.+)$/i,
  ]);
  if (editAsset) {
    return coreAssetCommand({
      context,
      commandType: "edit_asset",
      title: "编辑当前核心资产",
      summary: `把当前核心资产名称改为「${cleanText(editAsset, 60)}」`,
      patch: { display_name: cleanText(editAsset, 120) },
    });
  }

  const aliasText = matchCommand(message, [
    /^\/merge-alias\s+(.+)$/i,
    /^合并别名[:：]\s*(.+)$/i,
  ]);
  if (aliasText) {
    return coreAssetCommand({
      context,
      commandType: "merge_alias",
      title: "合并角色别名",
      summary: `把「${cleanText(aliasText, 60)}」合并为当前角色别名`,
      patch: { alias: cleanText(aliasText, 120) },
    });
  }

  if (/^\/retire-selected-asset$/i.test(message) || /^停用当前资产$/i.test(message)) {
    return coreAssetCommand({
      context,
      commandType: context.selected_core_asset_type === "prop" ? "retire_manual_prop" : "retire_asset",
      title: "停用当前核心资产",
      summary: "将当前核心资产标记为停用，并保留审计历史和撤销入口。",
      patch: {},
    });
  }

  if (/^\/restore-selected-asset$/i.test(message) || /^恢复当前资产$/i.test(message)) {
    return coreAssetCommand({
      context,
      commandType: "restore_asset",
      title: "恢复当前核心资产",
      summary: "将当前已停用核心资产恢复为可用状态。",
      patch: {},
    });
  }

  const renameText = matchCommand(message, [
    /^\/rename-selected\s+(.+)$/i,
    /^\/rename-node\s+(.+)$/i,
    /^重命名(?:当前)?节点[:：]\s*(.+)$/i,
  ]);
  if (renameText) {
    return commandForSelectedNode({
      context,
      commandType: "rename_selected_node",
      title: "重命名当前节点",
      summary: `把当前节点重命名为「${cleanText(renameText, 60)}」`,
      after: { title: cleanText(renameText, 80) },
    });
  }

  const noteText = matchCommand(message, [
    /^\/add-note\s+(.+)$/i,
    /^\/note\s+(.+)$/i,
    /^添加(?:当前)?节点备注[:：]\s*(.+)$/i,
  ]);
  if (noteText) {
    return commandForSelectedNode({
      context,
      commandType: "add_selected_node_note",
      title: "添加节点备注",
      summary: "为当前节点追加一条备注",
      after: { note: cleanText(noteText, 240) },
    });
  }

  if (/^\/recover-selected$/i.test(message) || /^恢复(?:当前)?节点$/i.test(message)) {
    return commandForSelectedNode({
      context,
      commandType: "recover_selected_node_error",
      title: "恢复当前节点",
      summary: "将当前节点从错误状态恢复为草稿，并保留错误文本供继续处理",
      after: { status: "draft" },
      allowEmptyTitle: true,
    });
  }

  return { command_type: "none", status: "none" };
}

function scriptRevisionCommand({ context, sourceKind, sourceText, title, summary }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("create_script_revision", title, "故事板是只读投影。请切回画布后再创建剧本版本。", context);
  }
  const text = cleanSourceText(sourceText, 200000);
  if (!text) return blockedCommand("create_script_revision", title, "剧本文本为空，无法创建版本。", context);
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "create_script_revision",
    execution_mode: "runtime",
    status: "preview",
    title,
    summary,
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    revision_id: cleanToken(context.script_revision_id, 140),
    source_kind: sourceKind,
    source_text: text,
    parent_revision_id: cleanToken(context.script_revision_id, 140) || null,
    impact: {
      node_ids: [],
      relation: "script_revision_canonical_projection",
      storyboard_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function scriptOptimizationCommand({ context, mode, instruction }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("optimize_script_revision", "优化文本为剧本版本", "故事板是只读投影。请切回画布后再优化文本。", context);
  }
  if (!["text", "script"].includes(context.selected_node_type)) {
    return blockedCommand("optimize_script_revision", "优化文本为剧本版本", "请先选择一个文本或脚本节点。", context);
  }
  const sourceText = cleanSourceText(context.selected_node_text, 12000);
  if (!sourceText) {
    return blockedCommand("optimize_script_revision", "优化文本为剧本版本", "当前文本节点还没有内容。", context);
  }
  const optimized = optimizedScriptDraft(sourceText, instruction);
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "optimize_script_revision",
    execution_mode: "runtime",
    status: "preview",
    title: mode === "default" ? "默认优化文本" : "按要求优化文本",
    summary: "生成可审阅的剧本修订草案；确认后写入同一事实源，故事板不反写。",
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    revision_id: cleanToken(context.script_revision_id, 140),
    source_kind: "script",
    source_text: optimized,
    before_text: sourceText,
    parent_revision_id: cleanToken(context.script_revision_id, 140) || null,
    optimization_mode: mode === "default" ? "default_local_structure" : "instructed_local_structure",
    optimization_instruction: cleanText(instruction, 500),
    preview_diff: scriptDiffSummary(sourceText, optimized),
    impact: {
      node_ids: context.selected_node_id ? [context.selected_node_id] : [],
      relation: "script_revision_canonical_projection",
      storyboard_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function optimizedScriptDraft(sourceText, instruction) {
  const paragraphs = sourceText
    .split(/\n{2,}/)
    .map((part) => part.replace(/[ \t]+/g, " ").trim())
    .filter(Boolean);
  const lines = paragraphs.length ? paragraphs : sourceText.split(/\r?\n/).map((part) => part.trim()).filter(Boolean);
  const lead = lines[0] || sourceText.trim();
  const body = lines.slice(1);
  const beats = body.length ? body : [lead];
  return [
    "核心意图",
    trimSentence(lead, 360),
    "",
    "叙事推进",
    ...beats.slice(0, 8).map((line, index) => `${index + 1}. ${trimSentence(line, 420)}`),
    "",
    "制作优化",
    `- 优化方向：${cleanText(instruction, 260)}`,
    "- 保留原始人物、地点、因果和关键情绪，不引入未确认角色或场景。",
    "- 让下一步角色、主要场景、动态镜头和媒体计划更容易从同一版本追溯。",
  ].join("\n").trim();
}

function scriptDiffSummary(before, after) {
  return {
    before_chars: before.length,
    after_chars: after.length,
    before_excerpt: cleanText(before, 220),
    after_excerpt: cleanText(after, 260),
  };
}

function trimSentence(value, limit) {
  const text = cleanSourceText(value, limit + 80).replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function runtimeCommand({ context, commandType, title, summary, requiresScriptRevision = true }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand(commandType, title, "故事板是只读投影。请切回画布后再执行写入命令。", context);
  }
  if (requiresScriptRevision && (!context.script_revision_id || !context.script_source_digest)) {
    return blockedCommand(commandType, title, "请先创建或刷新剧本版本，再执行核心资产命令。", context);
  }
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: commandType,
    execution_mode: "runtime",
    status: "preview",
    title,
    summary,
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    revision_id: cleanToken(context.script_revision_id, 140),
    source_digest: cleanToken(context.script_source_digest, 80),
    impact: {
      node_ids: [],
      relation: "runtime_script_core_truth_projection",
      storyboard_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function storyPlanCandidateCommand({ context, candidate }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("submit_story_plan_candidate", "提交动态制作计划候选", "故事板是只读投影。请切回画布后再确认动态制作计划。", context);
  }
  if (!context.script_revision_id || !context.script_source_digest) {
    return blockedCommand("submit_story_plan_candidate", "提交动态制作计划候选", "请先创建或刷新剧本版本，再提交动态制作计划候选。", context);
  }
  const safeCandidate = safeJsonClone(candidate);
  if (
    safeCandidate.project_id !== context.project_id
    || safeCandidate.script_revision_id !== context.script_revision_id
    || safeCandidate.source_digest !== context.script_source_digest
    || safeCandidate.schema_version !== STORY_PLAN_CANDIDATE_SCHEMA_VERSION
  ) {
    return blockedCommand("submit_story_plan_candidate", "提交动态制作计划候选", "动态制作计划候选必须绑定当前项目、剧本版本、文本摘要和合同版本。", context);
  }
  if (!safeCandidate.candidate_digest || !Array.isArray(safeCandidate.beats) || !Array.isArray(safeCandidate.shots)) {
    return blockedCommand("submit_story_plan_candidate", "提交动态制作计划候选", "动态制作计划候选需要候选摘要、叙事段落和镜头清单。", context);
  }
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "submit_story_plan_candidate",
    execution_mode: "runtime",
    status: "preview",
    title: "提交动态制作计划候选",
    summary: `提交并确认 ${safeCandidate.beats.length} 个叙事段落、${safeCandidate.shots.length} 个动态镜头；确认后生成制作计划。`,
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    script_revision_id: cleanToken(context.script_revision_id, 140),
    revision_id: cleanToken(context.script_revision_id, 140),
    source_digest: cleanToken(context.script_source_digest, 80),
    candidate: safeCandidate,
    impact: {
      node_ids: [],
      relation: "runtime_dynamic_production_plan_truth",
      storyboard_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function storyPlanRequestCommand(context) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("request_story_plan_candidate", "自动拆分分镜", "故事板是只读投影。请切回画布后再请求动态分镜。", context);
  }
  if (!["text", "script"].includes(context.selected_node_type)) {
    return blockedCommand("request_story_plan_candidate", "自动拆分分镜", "请先选择一个文本或脚本节点。", context);
  }
  if (!context.script_revision_id || !context.script_source_digest) {
    return blockedCommand("request_story_plan_candidate", "自动拆分分镜", "请先把当前文本创建为剧本版本；动态分镜必须绑定可追溯的剧本版本。", context);
  }
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "request_story_plan_candidate",
    execution_mode: "runtime",
    status: "preview",
    title: "自动拆分分镜",
    summary: "检查当前剧本版本是否已有可信动态分镜候选；没有可信候选时返回待规划，需要智能规划器生成候选。",
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    revision_id: cleanToken(context.script_revision_id, 140),
    script_revision_id: cleanToken(context.script_revision_id, 140),
    source_digest: cleanToken(context.script_source_digest, 80),
    planning_state: "planning_required",
    impact: {
      node_ids: context.selected_node_id ? [context.selected_node_id] : [],
      relation: "script_revision_to_story_plan_candidate_request",
      storyboard_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function m3ContextPackCommand(context, instruction) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("build_m3_context_pack", "构建精准上下文包", "故事板是只读投影。请切回画布后再构建执行上下文。", context);
  }
  if (!context.script_revision_id || !context.script_source_digest) {
    return blockedCommand("build_m3_context_pack", "构建精准上下文包", "请先创建或刷新剧本版本；上下文包必须绑定可追溯的 ScriptRevision。", context);
  }
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "build_m3_context_pack",
    execution_mode: "runtime",
    status: "preview",
    title: "构建精准上下文包",
    summary: "按当前剧本版本、选中节点、制作计划摘要和任务域检索少量相关知识；确认后只锁定上下文包，不改剧本或分镜事实。",
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    revision_id: cleanToken(context.script_revision_id, 140),
    script_revision_id: cleanToken(context.script_revision_id, 140),
    source_digest: cleanToken(context.script_source_digest, 80),
    plan_id: cleanToken(context.production_plan_id, 140) || null,
    plan_digest: cleanToken(context.production_plan_digest, 80) || null,
    selected_node_id: cleanToken(context.selected_node_id, 120),
    selected_node_type: cleanToken(context.selected_node_type, 40),
    instruction: cleanText(instruction, 900),
    requested_domains: ["story_plan", "asset_bible", "context", "safety", "evaluation"],
    upstream_refs: [
      cleanToken(context.script_revision_id, 140),
      cleanToken(context.production_plan_id, 140),
    ].filter(Boolean),
    downstream_refs: ["professional_script_candidate", "script_understanding", "story_plan_candidate", "asset_bible_candidate", "evaluation_report"],
    constraints: {
      storyboard_mode: "read_only_deferred",
      draft_is_not_truth: true,
      feedback_is_not_memory: true,
      provider_disabled: true,
    },
    preferences: {},
    exclusions: ["private_user_data", "prompt_injection", "full_chat_history"],
    token_budget: 760,
    impact: {
      node_ids: context.selected_node_id ? [context.selected_node_id] : [],
      relation: "m3_zero_cost_context_pack_only",
      storyboard_write: false,
      canonical_truth_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function productionPlanRefreshCommand(context) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("refresh_production_plan", "刷新制作计划事实", "故事板是只读投影。请切回画布后再刷新计划投影。", context);
  }
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "refresh_production_plan",
    execution_mode: "runtime",
    status: "preview",
    title: "刷新制作计划事实",
    summary: "从运行服务事实重新投影叙事段落、镜头、分段与拼接计划。",
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    revision_id: cleanToken(context.script_revision_id, 140),
    script_revision_id: cleanToken(context.script_revision_id, 140),
    source_digest: cleanToken(context.script_source_digest, 80),
    impact: {
      node_ids: [],
      relation: "runtime_dynamic_production_plan_projection",
      storyboard_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function productionPlanCommand({ context, commandType, title, summary, patch, allowMissingTarget = false }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand(commandType, title, "故事板是只读投影。请切回画布后再预览和确认制作计划命令。", context);
  }
  if (!context.production_plan_id || !context.production_plan_digest) {
    return blockedCommand(commandType, title, "请先提交或刷新制作计划，再执行镜头或分段命令。", context);
  }
  if (
    context.selected_plan_entity_plan_id
    && (context.selected_plan_entity_plan_id !== context.production_plan_id || context.selected_plan_entity_plan_digest !== context.production_plan_digest)
  ) {
    return blockedCommand(commandType, title, "当前选中节点不属于最新制作计划，请刷新计划投影后重试。", context);
  }
  const targetShotId = cleanToken(context.selected_plan_shot_id, 140);
  const targetChunkId = cleanToken(context.selected_plan_chunk_id, 160);
  if (!allowMissingTarget && !targetShotId && !targetChunkId) {
    return blockedCommand(commandType, title, "请先选择一个镜头或分段投影节点。", context);
  }
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: commandType,
    execution_mode: "runtime",
    status: "preview",
    title,
    summary,
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    revision_id: cleanToken(context.script_revision_id, 140),
    script_revision_id: cleanToken(context.script_revision_id, 140),
    source_digest: cleanToken(context.script_source_digest, 80),
    plan_id: cleanToken(context.production_plan_id, 140),
    plan_digest: cleanToken(context.production_plan_digest, 80),
    target_shot_id: targetShotId || null,
    target_chunk_id: targetChunkId || null,
    patch: safeJsonClone(patch || {}),
    reason: "agent_chat_confirmed",
    impact: {
      node_ids: context.selected_node_id ? [context.selected_node_id] : [],
      relation: "runtime_dynamic_production_plan_truth",
      storyboard_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function coreAssetCommand({ context, commandType, title, summary, patch, allowMissingTarget = false }) {
  const base = runtimeCommand({ context, commandType, title, summary });
  if (base.status === "blocked") return base;
  const targetAssetId = cleanToken(context.selected_core_asset_id, 140);
  if (!allowMissingTarget && !targetAssetId) {
    return blockedCommand(commandType, title, "请先选择一个角色、主要场景或手动道具投影节点。", context);
  }
  return {
    ...base,
    target_asset_id: targetAssetId || null,
    patch: safeJsonClone(patch || {}),
    impact: {
      node_ids: context.selected_node_id ? [context.selected_node_id] : [],
      relation: "runtime_core_asset_truth",
      storyboard_write: false,
    },
  };
}

function commandForSelectedNode({ context, commandType, title, summary, after, allowEmptyTitle = false }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand(commandType, title, "故事板是只读投影。请切回画布后再预览和确认写入命令。", context);
  }
  const nodeId = cleanToken(context.selected_node_id, 120);
  if (!nodeId) {
    return blockedCommand(commandType, title, "请先在画布选择一个节点，再发送这条命令。", context);
  }
  if (!allowEmptyTitle && after?.title && !cleanText(after.title, 80)) {
    return blockedCommand(commandType, title, "目标标题为空，无法生成可执行预览。", context);
  }
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: commandType,
    status: "preview",
    title,
    summary,
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    revision_id: cleanToken(context.revision_id, 80),
    node_id: nodeId,
    before: {
      title: cleanText(context.selected_node_title, 120),
      status: cleanToken(context.selected_node_status, 40),
    },
    after,
    impact: {
      node_ids: [nodeId],
      relation: "selected_canvas_node_only",
      storyboard_write: false,
    },
    requires_confirmation: true,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function blockedCommand(commandType, title, errorMessage, context) {
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_blocked_${Date.now()}`,
    command_type: commandType,
    status: "blocked",
    title,
    context_key: agentChatContextKey(context),
    error_message: errorMessage,
    requires_confirmation: false,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function executeAgentCommand(command, state) {
  const node = state?.nodes?.[command.node_id];
  if (!node) throw new Error("selected node no longer exists");
  const before = snapshotNode(node);
  if (command.command_type === "rename_selected_node") {
    node.title = command.after.title;
  } else if (command.command_type === "add_selected_node_note") {
    node.params = node.params || {};
    const notes = Array.isArray(node.params.agentNotes) ? node.params.agentNotes : [];
    node.params.agentNotes = [
      ...notes,
      { text: command.after.note, created_at: new Date().toISOString(), source: "agent_chat_command" },
    ].slice(-8);
  } else if (command.command_type === "recover_selected_node_error") {
    node.params = node.params || {};
    node.params.agentRecoveredFrom = before.status || "unknown";
    node.status = "draft";
  } else {
    throw new Error("unsupported agent command");
  }
  const after = snapshotNode(node);
  return {
    schema_version: SCHEMA_VERSION,
    receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_id: command.command_id,
    command_type: command.command_type,
    status: "executed",
    executed_at: new Date().toISOString(),
    context_key: command.context_key,
    project_id: command.project_id,
    revision_id: command.revision_id,
    node_id: command.node_id,
    summary: `${command.title}已执行，影响范围：当前节点。`,
    before,
    after,
    undo_available: true,
    storyboard_write: false,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function runtimeCoreAssetCommandPayload(command) {
  return {
    project_id: command.project_id,
    revision_id: command.revision_id,
    source_digest: command.source_digest,
    schema_version: CORE_ASSET_COMMAND_SCHEMA_VERSION,
    command_type: command.command_type,
    target_asset_id: command.target_asset_id || null,
    patch: command.patch || {},
    reason: "agent_chat_confirmed",
    generated_at: new Date().toISOString(),
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}

function runtimeProductionPlanCommandPayload(command) {
  return {
    project_id: command.project_id,
    script_revision_id: command.script_revision_id || command.revision_id,
    source_digest: command.source_digest,
    plan_id: command.plan_id,
    plan_digest: command.plan_digest,
    schema_version: PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION,
    command_type: command.command_type,
    target_shot_id: command.target_shot_id || null,
    target_chunk_id: command.target_chunk_id || null,
    patch: command.patch || {},
    reason: command.reason || "agent_chat_confirmed",
    generated_at: new Date().toISOString(),
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}

function runtimeM3ContextPackPayload(command) {
  return {
    project_id: command.project_id,
    script_revision_id: command.script_revision_id || command.revision_id,
    source_digest: command.source_digest,
    schema_version: M3_CONTEXT_COMMAND_SCHEMA_VERSION,
    instruction: command.instruction || "",
    selected_node_id: command.selected_node_id || null,
    selected_node_type: command.selected_node_type || null,
    plan_id: command.plan_id || null,
    plan_digest: command.plan_digest || null,
    requested_domains: command.requested_domains || [],
    constraints: command.constraints || {},
    preferences: command.preferences || {},
    upstream_refs: command.upstream_refs || [],
    downstream_refs: command.downstream_refs || [],
    exclusions: command.exclusions || [],
    token_budget: command.token_budget || 760,
    provider_gates: {
      llm: false,
      image: false,
      video: false,
      audio: false,
      asr: false,
      vision: false,
      external_download: false,
    },
    tool_gates: {
      model_call: false,
      external_download: false,
      media_generation: false,
    },
    trace_id: command.command_id,
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}

function productionPlanAgentReceipt(command, response, runtimeReceipt, projectionSummary) {
  const projection = response?.projection || {};
  const plan = projection.current_plan || {};
  const receipt = {
    schema_version: SCHEMA_VERSION,
    receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_id: command.command_id,
    command_type: command.command_type,
    status: "executed",
    executed_at: new Date().toISOString(),
    context_key: command.context_key,
    project_id: command.project_id || response?.project_id || projection.project_id || "",
    revision_id: runtimeReceipt?.script_revision_id || plan.script_revision_id || command.script_revision_id || command.revision_id || "",
    script_revision_id: runtimeReceipt?.script_revision_id || plan.script_revision_id || command.script_revision_id || command.revision_id || "",
    source_digest: runtimeReceipt?.source_digest || plan.source_digest || command.source_digest || "",
    plan_id: runtimeReceipt?.after_plan_id || plan.plan_id || command.plan_id || "",
    plan_digest: runtimeReceipt?.after_plan_digest || plan.plan_digest || command.plan_digest || "",
    before_plan_id: runtimeReceipt?.before_plan_id || "",
    after_plan_id: runtimeReceipt?.after_plan_id || plan.plan_id || "",
    before_plan_digest: runtimeReceipt?.before_plan_digest || "",
    after_plan_digest: runtimeReceipt?.after_plan_digest || plan.plan_digest || "",
    summary: productionPlanReceiptSummary(command, response),
    undo_available: Boolean(runtimeReceipt?.undo_available),
    runtime_receipt_id: runtimeReceipt?.receipt_id || "",
    storyboard_write: false,
    execution_mode: "runtime",
    runtime_domain: "production_plan",
    projection_summary: projectionSummary,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
  return receipt;
}

function runtimeAgentReceipt(command, response, runtimeReceipt, projectionSummary) {
  const revision = response?.revision || response?.projection?.current_revision || {};
  const projection = response?.projection || {};
  const scriptRevisionCommand = command.command_type === "create_script_revision" || command.command_type === "optimize_script_revision";
  const receipt = {
    schema_version: SCHEMA_VERSION,
    receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_id: command.command_id,
    command_type: command.command_type,
    status: "executed",
    executed_at: new Date().toISOString(),
    context_key: command.context_key,
    project_id: command.project_id || response?.project_id || projection.project_id || "",
    revision_id: runtimeReceipt?.revision_id || revision.revision_id || projection.current_revision_id || command.revision_id || "",
    source_digest: runtimeReceipt?.source_digest || revision.source_digest || projection.current_revision?.source_digest || command.source_digest || "",
    summary: runtimeReceiptSummary(command, response),
    undo_available: Boolean(runtimeReceipt?.undo_available) || Boolean(command.command_type === "optimize_script_revision" && command.parent_revision_id),
    runtime_receipt_id: runtimeReceipt?.receipt_id || "",
    storyboard_write: false,
    execution_mode: "runtime",
    runtime_domain: scriptRevisionCommand ? "script_revision" : "script_core",
    previous_revision_id: command.parent_revision_id || "",
    created_revision_id: revision.revision_id || projection.current_revision_id || "",
    projection_summary: projectionSummary,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
  return receipt;
}

function m3ContextAgentReceipt(command, response, runtimeReceipt) {
  const contextPack = response?.context_pack || {};
  return {
    schema_version: SCHEMA_VERSION,
    receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_id: command.command_id,
    command_type: command.command_type,
    status: "executed",
    executed_at: new Date().toISOString(),
    context_key: command.context_key,
    project_id: command.project_id || response?.project_id || contextPack.project_id || "",
    revision_id: contextPack.script_revision_id || command.revision_id || "",
    script_revision_id: contextPack.script_revision_id || command.script_revision_id || command.revision_id || "",
    source_digest: contextPack.source_digest || command.source_digest || "",
    context_pack_id: contextPack.context_pack_id || runtimeReceipt?.context_pack_id || "",
    canonical_truth_digest: contextPack.canonical_truth_digest || "",
    summary: `精准上下文包已锁定；知识引用 ${Number(contextPack.relevant_knowledge_refs?.length || 0)} 条，Provider 保持关闭，草案不会写入事实。`,
    undo_available: Boolean(runtimeReceipt?.undo_available),
    runtime_receipt_id: runtimeReceipt?.receipt_id || "",
    storyboard_write: false,
    execution_mode: "runtime",
    runtime_domain: "m3_context",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function productionPlanReceiptSummary(command, response) {
  if (command.command_type === "request_story_plan_candidate") {
    const state = response?.projection?.planning_state || "planning_required";
    if (!response?.projection?.current_plan?.plan_id) {
      return `当前剧本版本还没有可信动态分镜候选；规划状态：${productionPlanStateLabel(state)}。需要智能规划器提交结构化候选后再确认生成镜头。`;
    }
    return `已找到当前剧本版本的动态分镜计划；规划状态：${productionPlanStateLabel(state)}。`;
  }
  if (command.command_type === "refresh_production_plan") {
    const state = response?.projection?.planning_state || "planning_required";
    return `制作计划事实已刷新；当前规划状态：${productionPlanStateLabel(state)}。`;
  }
  if (command.command_type === "submit_story_plan_candidate") {
    const plan = response?.projection?.current_plan || {};
    return `动态制作计划已确认；镜头数：${Number(response?.projection?.shots?.length || 0)}，计划版本：${Number(plan.plan_version || 1)}。`;
  }
  return `${productionPlanCommandLabel(command.command_type)}已执行，画布和故事板投影已同步。`;
}

function runtimeReceiptSummary(command, response) {
  if (command.command_type === "optimize_script_revision") {
    const state = response?.analysis_state || response?.projection?.analysis_state || "analysis_required";
    return `优化后的剧本版本已创建；当前分析状态：${scriptAnalysisStateLabel(state)}。`;
  }
  if (command.command_type === "create_script_revision") {
    const state = response?.analysis_state || response?.projection?.analysis_state || "analysis_required";
    return `剧本版本已创建；当前分析状态：${scriptAnalysisStateLabel(state)}。`;
  }
  if (command.command_type === "refresh_script_truth") {
    const state = response?.projection?.analysis_state || "analysis_required";
    return `剧本与核心资产事实已刷新；当前分析状态：${scriptAnalysisStateLabel(state)}。`;
  }
  return `${coreAssetCommandLabel(command.command_type) || command.title || "命令"}已执行，画布投影已同步。`;
}

function productionPlanUndoSummary(receipt) {
  return `${productionPlanCommandLabel(receipt?.command_type)}已撤销，制作计划回到上一个可追溯版本。`;
}

function coreAssetUndoSummary(receipt) {
  return `${coreAssetCommandLabel(receipt?.command_type) || "上一条核心资产命令"}已撤销，画布投影已同步更新。`;
}

function productionPlanCommandLabel(commandType) {
  return ({
    request_story_plan_candidate: "自动拆分分镜",
    submit_story_plan_candidate: "确认动态制作计划",
    refresh_production_plan: "刷新制作计划事实",
    edit_shot_duration: "镜头时长调整",
    edit_shot_intent: "镜头意图调整",
    set_shot_strategy: "镜头媒体策略调整",
    split_shot: "镜头拆分",
    merge_shot_next: "镜头合并",
    replan_affected: "受影响计划重算",
    mark_failed: "失败状态标记",
    retry_failed: "失败项重试准备",
  })[String(commandType || "").replace(/\.undo$/, "")] || "制作计划命令";
}

function coreAssetCommandLabel(commandType) {
  return ({
    refresh_script_truth: "刷新剧本与资产事实",
    create_manual_prop: "手动道具创建",
    edit_asset: "核心资产编辑",
    merge_alias: "角色别名合并",
    retire_asset: "核心资产停用",
    retire_manual_prop: "手动道具停用",
    restore_asset: "核心资产恢复",
  })[String(commandType || "").replace(/\.undo$/, "")] || "";
}

function userCommandDisplayText(command, fallbackText) {
  const type = command?.command_type || "";
  if (type === "create_script_revision") {
    return command.source_kind === "idea" ? "提交创作想法" : "提交剧本文本";
  }
  if (type === "optimize_script_revision") {
    return command.optimization_mode === "instructed_local_structure"
      ? `按要求优化当前文本：${cleanText(command.optimization_instruction, 140)}`
      : "默认优化当前文本";
  }
  if (type === "submit_story_plan_candidate") return "提交动态制作计划候选";
  if (type === "request_story_plan_candidate") return "自动拆分分镜";
  if (type === "build_m3_context_pack") return "构建精准上下文包";
  if (type === "refresh_script_truth") return "刷新剧本与资产事实";
  if (type === "refresh_production_plan") return "刷新制作计划事实";
  if (isProductionPlanRuntimeCommand(type)) return productionPlanCommandLabel(type);
  const coreAsset = coreAssetCommandLabel(type);
  if (coreAsset) return coreAsset;
  return fallbackText;
}

function productionPlanStateLabel(value) {
  const state = String(value || "").trim();
  if (!state || state === "planning_required") return "待规划";
  if (state === "pending_capability") return "等待能力确认";
  if (state === "planned") return "已规划";
  if (state === "blocked") return "有阻断";
  return state.replace(/_/g, " ");
}

function scriptAnalysisStateLabel(value) {
  const state = String(value || "").trim();
  if (!state || state === "analysis_required") return "待分析";
  if (state === "low_confidence_pending") return "待确认";
  if (state === "pending_confirmation") return "待确认";
  if (state === "confirmed") return "已确认";
  return state.replace(/_/g, " ");
}

function applyUndo(receipt, state) {
  const node = state?.nodes?.[receipt.node_id];
  if (!node) throw new Error("selected node no longer exists");
  restoreNode(node, receipt.before || {});
  return {
    schema_version: SCHEMA_VERSION,
    receipt_id: `receipt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_id: receipt.command_id,
    command_type: `${receipt.command_type}.undo`,
    status: "undone",
    executed_at: new Date().toISOString(),
    context_key: receipt.context_key,
    project_id: receipt.project_id,
    revision_id: receipt.revision_id,
    node_id: receipt.node_id,
    summary: "上一条 Agent 命令已撤销，画布回到执行前状态。",
    before: receipt.after,
    after: receipt.before,
    undo_available: false,
    storyboard_write: false,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function snapshotNode(node) {
  return {
    title: cleanText(node?.title, 120),
    status: cleanToken(node?.status, 40),
    params: safeJsonClone(node?.params || {}),
  };
}

function restoreNode(node, snapshot) {
  node.title = cleanText(snapshot.title, 120);
  node.status = cleanToken(snapshot.status, 40) || "draft";
  node.params = safeJsonClone(snapshot.params || {});
}

function recordReceipt(session, receipt) {
  session.receipts = [...(session.receipts || []), receipt].slice(-RECEIPT_LIMIT);
}

function appendMessage(session, message) {
  session.messages = [...(session.messages || []), {
    role: message.role === "user" ? "user" : "assistant",
    text: cleanText(message.text, 900),
    tone: cleanToken(message.tone, 24),
    created_at: new Date().toISOString(),
  }].slice(-MESSAGE_LIMIT);
}

function isProductionPlanRuntimeCommand(commandType) {
  return [
    "edit_shot_duration",
    "edit_shot_intent",
    "set_shot_strategy",
    "split_shot",
    "merge_shot_next",
    "replan_affected",
    "mark_failed",
    "retry_failed",
  ].includes(commandType);
}

function jsonPayloadCommand(text, prefixes) {
  for (const prefix of prefixes) {
    const match = String(text || "").match(prefix);
    if (!match) continue;
    const jsonText = String(text || "").slice(match[0].length).trim();
    try {
      const value = JSON.parse(jsonText);
      if (!value || typeof value !== "object" || Array.isArray(value)) {
        return { matched: true, value: null, error: "动态制作计划候选必须是结构化对象。" };
      }
      return { matched: true, value, error: "" };
    } catch {
      return { matched: true, value: null, error: "动态制作计划候选无法解析。" };
    }
  }
  return { matched: false, value: null, error: "" };
}

function strategyCommandPatch(message) {
  const match = String(message || "").match(/^\/set-shot-strategy\s+(t2v|i2v)(?:\s+reason=|\s+)(.+)$/i)
    || String(message || "").match(/^设置镜头策略[:：]\s*(t2v|i2v)(?:\s+reason=|\s+)(.+)$/i);
  if (!match) return { matched: false, patch: null, error: "" };
  const strategy = cleanToken(match[1], 20).toLowerCase();
  const reason = cleanText(match[2], 600);
  if (!["t2v", "i2v"].includes(strategy) || !reason) {
    return { matched: true, patch: null, error: "媒体策略必须是 t2v 或 i2v，并包含策略依据。" };
  }
  const patch = {
    strategy,
    strategy_reason: reason,
    input_requirements: strategy === "i2v" ? ["reference_asset_or_locked_keyframe"] : ["text_prompt_contract"],
  };
  if (strategy === "i2v") patch.reference_asset_refs = [];
  return { matched: true, patch, error: "" };
}

function splitCommandPatch(message) {
  const match = String(message || "").match(/^\/split-shot\s+([0-9]+(?:\.[0-9]+)?)[,\s]+([0-9]+(?:\.[0-9]+)?)$/i)
    || String(message || "").match(/^拆分镜头[:：]\s*([0-9]+(?:\.[0-9]+)?)[,\s]+([0-9]+(?:\.[0-9]+)?)$/i);
  if (!match) return { matched: false, patch: null, error: "" };
  const left = Number(match[1]);
  const right = Number(match[2]);
  if (!Number.isFinite(left) || !Number.isFinite(right) || left <= 0 || right <= 0) {
    return { matched: true, patch: null, error: "拆分镜头需要两个正数时长。" };
  }
  return {
    matched: true,
    patch: {
      durations: [left, right],
      first_intent: "拆分后的前半镜头",
      second_intent: "拆分后的后半镜头",
    },
    error: "",
  };
}

function matchCommand(text, patterns) {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match?.[1]) return match[1];
  }
  return "";
}

function inferSceneCount(shotNodes) {
  const sceneIds = new Set();
  for (const node of shotNodes) {
    const value = node?.params?.structuredShot?.scene_id || node?.params?.sceneId || "";
    if (value) sceneIds.add(String(value));
  }
  return sceneIds.size;
}

function cleanToken(value, limit) {
  return String(value || "").replace(/[^A-Za-z0-9_.:-]/g, "").slice(0, limit);
}

function cleanText(value, limit) {
  return String(value || "")
    .replace(/\b(Bearer|sk-[A-Za-z0-9_-]+|token=|secret=|authorization=)\S*/gi, "[redacted]")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

function cleanSourceText(value, limit) {
  return String(value || "")
    .replace(/\b(Bearer|sk-[A-Za-z0-9_-]+|token=|secret=|authorization=)\S*/gi, "[redacted]")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .trim()
    .slice(0, limit);
}

function safeJsonClone(value) {
  try {
    return JSON.parse(JSON.stringify(value || {}));
  } catch {
    return {};
  }
}

function fitCanvasProjection(state) {
  if (typeof document === "undefined" || !document.getElementById("canvas-root")) return;
  const nodes = state?.nodes || {};
  if (!Object.keys(nodes).length) return;
  const viewport = fitVisibleCanvasViewport(nodes);
  if (viewport) state.viewport = viewport;
}
