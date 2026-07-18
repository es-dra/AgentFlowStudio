import { applyScriptCoreTruthProjection } from "./script-core-truth-projection.js";

const SCHEMA_VERSION = "afs_agent_chat_lifecycle.v0.1";
const CORE_ASSET_COMMAND_SCHEMA_VERSION = "afs.core_asset_command.v0.1";
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
  const selectedCoreAsset = activeNode?.params?.coreAssetTruth || null;
  const scriptRevisionId = cleanToken(scriptTruth.current_revision_id, 140);
  const scriptSourceDigest = cleanToken(scriptTruth.source_digest, 80);
  return {
    schema_version: SCHEMA_VERSION,
    project_id: cleanToken(project?.project_id || meta.projectId, 120),
    revision_id: scriptRevisionId || cleanToken(meta.seq ? `studio-state-${meta.seq}` : "", 80),
    studio_state_revision_id: cleanToken(meta.seq ? `studio-state-${meta.seq}` : "", 80),
    script_revision_id: scriptRevisionId,
    script_source_digest: scriptSourceDigest,
    script_analysis_state: cleanToken(scriptTruth.analysis_state || "", 80),
    canvas_name: cleanText(meta.canvasName || "画布", 40),
    project_name: cleanText(project?.name || meta.projectName || "未命名项目", 80),
    section: section === "storyboard" ? "storyboard_read_only" : "canvas",
    selected_node_id: cleanToken(activeNode?.id, 120),
    selected_node_type: cleanToken(activeNode?.type, 40),
    selected_node_status: cleanToken(activeNode?.status, 40),
    selected_node_title: cleanText(activeNode?.title || activeNode?.label || "", 80),
    selected_core_asset_id: cleanToken(selectedCoreAsset?.asset_id, 140),
    selected_core_asset_type: cleanToken(selectedCoreAsset?.asset_type, 60),
    selected_core_asset_status: cleanToken(selectedCoreAsset?.status, 80),
    current_shot_node_id: cleanToken(currentShot?.nodeId, 120),
    current_shot_title: cleanText(currentShot?.title || "", 80),
    counts: {
      nodes: nodeValues.length,
      scenes: inferSceneCount(shotNodes),
      shots: shotNodes.length,
      assets: Array.isArray(state.assets) ? state.assets.length : 0,
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
    ],
    storyboard_mode: "read_only_deferred",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

export function submitAgentChatMessage(session, rawText, context) {
  const text = cleanText(rawText, 900);
  if (!text) return { status: "empty" };
  appendMessage(session, { role: "user", text });
  const command = previewAgentCommand(text, context);
  if (command.command_type !== "none") {
    session.pendingCommand = command;
    appendMessage(session, {
      role: command.status === "blocked" ? "assistant" : "assistant",
      text: command.status === "blocked"
        ? command.error_message
        : "已生成命令预览；确认前不会改变画布事实。",
    });
    return { status: command.status, command };
  }
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
  if (!runtime) throw new Error("runtime client is unavailable");
  let response = null;
  let runtimeReceipt = null;
  if (command.command_type === "create_script_revision") {
    response = await runtime.createScriptRevision({
      source_kind: command.source_kind || "script",
      source_text: command.source_text || "",
      parent_revision_id: command.parent_revision_id || null,
      provenance: {
        source: "agent_chat",
        command_id: command.command_id,
        context_key: command.context_key,
      },
      created_at: new Date().toISOString(),
    });
  } else if (command.command_type === "refresh_script_truth") {
    response = await runtime.loadScriptTruth();
  } else {
    const payload = runtimeCoreAssetCommandPayload(command);
    await runtime.previewCoreAssetCommand(payload);
    response = await runtime.confirmCoreAssetCommand(payload);
    runtimeReceipt = response?.receipt || null;
  }
  const projection = response?.projection;
  let projectionSummary = null;
  if (projection) {
    store.set((state) => {
      projectionSummary = applyScriptCoreTruthProjection(state, projection);
    });
  }
  const receipt = runtimeAgentReceipt(command, response, runtimeReceipt, projectionSummary);
  session.pendingCommand = null;
  recordReceipt(session, receipt);
  appendMessage(session, { role: "assistant", text: receipt.summary });
  return receipt;
}

export async function undoAgentReceiptWithRuntime(session, receipt, store, runtime) {
  if (receipt?.execution_mode !== "runtime") {
    let undo = null;
    store.set((state) => {
      undo = undoAgentReceipt(session, receipt, state);
    });
    return undo;
  }
  if (!receipt?.runtime_receipt_id || !receipt?.undo_available) throw new Error("agent receipt is not undoable");
  if (!runtime?.undoCoreAssetCommand) throw new Error("runtime undo is unavailable");
  const response = await runtime.undoCoreAssetCommand({
    project_id: receipt.project_id,
    receipt_id: receipt.runtime_receipt_id,
    revision_id: receipt.revision_id,
    source_digest: receipt.source_digest,
    schema_version: CORE_ASSET_COMMAND_SCHEMA_VERSION,
  });
  let projectionSummary = null;
  if (response?.projection) {
    store.set((state) => {
      projectionSummary = applyScriptCoreTruthProjection(state, response.projection);
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
    source_digest: receipt.source_digest,
    summary: response?.receipt?.summary || "上一条 Core Asset 命令已撤销，画布投影已从 runtime truth 刷新。",
    undo_available: false,
    storyboard_write: false,
    execution_mode: "runtime",
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
      title: "创建 ScriptRevision",
      summary: "把输入文本写入 runtime ScriptRevision，并将 canonical projection 投到画布。",
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
      title: "创建 Idea Revision",
      summary: "把想法写入 runtime ScriptRevision；没有 structured analysis 前只标记 analysis_required。",
    });
  }

  if (/^\/refresh-script-truth$/i.test(message) || /^刷新(?:剧本)?事实$/i.test(message)) {
    return runtimeCommand({
      context,
      commandType: "refresh_script_truth",
      title: "刷新 Script/Core Asset Truth",
      summary: "从 runtime canonical truth 重新投影 ScriptRevision、Character、Main Scene 与手动 Prop。",
      requiresScriptRevision: false,
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
      summary: `创建绑定当前 ScriptRevision 的手动 Prop「${cleanText(manualProp, 60)}」`,
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
      title: "编辑当前 Core Asset",
      summary: `把当前 Core Asset 名称改为「${cleanText(editAsset, 60)}」`,
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
      title: "停用当前 Core Asset",
      summary: "将当前 Core Asset 标记为 retired，并保留审计历史和撤销入口。",
      patch: {},
    });
  }

  if (/^\/restore-selected-asset$/i.test(message) || /^恢复当前资产$/i.test(message)) {
    return coreAssetCommand({
      context,
      commandType: "restore_asset",
      title: "恢复当前 Core Asset",
      summary: "将当前 retired Core Asset 恢复为可用状态。",
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
    return blockedCommand("create_script_revision", title, "故事板是只读投影。请切回画布后再创建 ScriptRevision。", context);
  }
  const text = cleanSourceText(sourceText, 200000);
  if (!text) return blockedCommand("create_script_revision", title, "ScriptRevision source text is empty.", context);
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

function runtimeCommand({ context, commandType, title, summary, requiresScriptRevision = true }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand(commandType, title, "故事板是只读投影。请切回画布后再执行写入命令。", context);
  }
  if (requiresScriptRevision && (!context.script_revision_id || !context.script_source_digest)) {
    return blockedCommand(commandType, title, "请先创建或刷新 ScriptRevision，再执行 Core Asset 命令。", context);
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

function coreAssetCommand({ context, commandType, title, summary, patch, allowMissingTarget = false }) {
  const base = runtimeCommand({ context, commandType, title, summary });
  if (base.status === "blocked") return base;
  const targetAssetId = cleanToken(context.selected_core_asset_id, 140);
  if (!allowMissingTarget && !targetAssetId) {
    return blockedCommand(commandType, title, "请先选择一个 Character、Main Scene 或手动 Prop 投影节点。", context);
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

function runtimeAgentReceipt(command, response, runtimeReceipt, projectionSummary) {
  const revision = response?.revision || response?.projection?.current_revision || {};
  const projection = response?.projection || {};
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
    summary: runtimeReceipt?.summary || runtimeReceiptSummary(command, response),
    undo_available: Boolean(runtimeReceipt?.undo_available),
    runtime_receipt_id: runtimeReceipt?.receipt_id || "",
    storyboard_write: false,
    execution_mode: "runtime",
    projection_summary: projectionSummary,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
  return receipt;
}

function runtimeReceiptSummary(command, response) {
  if (command.command_type === "create_script_revision") {
    const state = response?.analysis_state || response?.projection?.analysis_state || "analysis_required";
    return `ScriptRevision 已创建；当前分析状态：${state}。`;
  }
  if (command.command_type === "refresh_script_truth") {
    const state = response?.projection?.analysis_state || "analysis_required";
    return `Script/Core Asset Truth 已刷新；当前分析状态：${state}。`;
  }
  return `${command.title || "Runtime 命令"}已执行。`;
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
