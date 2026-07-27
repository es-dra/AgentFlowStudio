import { applyProductionPlanProjection } from "./production-plan-projection.js";
import { applyScriptCoreTruthProjection } from "./script-core-truth-projection.js";
import { fitVisibleCanvasViewport } from "./canvas-safe-area.js";
import { conversationalReply } from "./agent-chat-conversation.js";
import { NODE_TYPES, defaultParams } from "./nodes.js";

const SCHEMA_VERSION = "afs_agent_chat_lifecycle.v0.1";
const CORE_ASSET_COMMAND_SCHEMA_VERSION = "afs.core_asset_command.v0.1";
const STORY_PLAN_CANDIDATE_SCHEMA_VERSION = "afs.story_plan_candidate.v0.1";
const PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION = "afs.production_plan_command.v0.1";
const M3_CONTEXT_COMMAND_SCHEMA_VERSION = "afs.m3_context_command.v0.1";
const MESSAGE_LIMIT = 28;
const RECEIPT_LIMIT = 12;
export const AGENT_COMMAND_PREVIEW_PLACEHOLDER_ID = "agent_command_preview_default_v1";
export const EMBEDDED_CREATIVE_TASK_OPEN_PLACEHOLDER_ID = "embedded_creative_task_open_v1";

export function createAgentChatContextStore() {
  const contexts = new Map();
  return {
    get(key) {
      const safeKey = cleanToken(key, 180) || "unknown";
      if (!contexts.has(safeKey)) contexts.set(safeKey, emptySession(safeKey));
      return contexts.get(safeKey);
    },
    clear() {
      contexts.clear();
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

export function agentChatContextFingerprint(context = {}) {
  const parts = [
    cleanToken(context.project_id, 120),
    cleanToken(context.section, 80),
    cleanToken(context.object_kind, 40),
    cleanToken(context.object_id, 160),
    cleanToken(context.script_revision_id, 160),
    cleanToken(context.production_plan_id, 160),
    cleanToken(context.production_plan_digest, 80),
    String(Number(context.production_graph_version || 0)),
    cleanToken(context.production_graph_digest, 80),
    cleanToken(context.asset_bible_revision_id, 160),
  ];
  let hash = 2166136261;
  for (const character of parts.join("\u001f")) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return `agent-context-${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

export function agentChatContextSnapshot({
  project = null,
  studioState = null,
  section = "canvas",
  selectedNode = null,
  currentShot = null,
  selectedAsset = null,
  assetBible = null,
  copilot = null,
} = {}) {
  const state = studioState && typeof studioState === "object" ? studioState : {};
  const meta = state.meta && typeof state.meta === "object" ? state.meta : {};
  const nodes = state.nodes && typeof state.nodes === "object" ? state.nodes : {};
  const nodeValues = Object.values(nodes).filter(Boolean);
  const sceneNodes = nodeValues.filter((node) => isSceneContextNode(node));
  const shotNodes = nodeValues.filter((node) => isShotContextNode(node));
  const activeNode = selectedNode || null;
  const scriptTruth = state.production?.script_core_truth_projection || {};
  const productionPlan = state.production?.dynamic_production_plan_projection || {};
  const productionGraph = state.production?.production_graph_projection || {};
  const selectedCoreAsset = activeNode?.params?.coreAssetTruth || null;
  const selectedPlanEntity = activeNode?.params?.productionPlanTruth || null;
  const selectedScreenplaySummary = screenplaySummaryForNode(activeNode)
    || latestScreenplaySummary(nodeValues);
  const selectedEdgeId = cleanToken(state.selection?.edgeId, 140);
  const selectedEdge = selectedEdgeId ? state.edges?.[selectedEdgeId] : null;
  const selectedEdgeFrom = selectedEdge?.from ? nodes[selectedEdge.from] : null;
  const selectedEdgeTo = selectedEdge?.to ? nodes[selectedEdge.to] : null;
  const scriptRevisionId = cleanToken(
    scriptTruth.current_revision_id
    || selectedScreenplaySummary?.revision_id
    || latestAppliedScriptRevisionId(nodeValues),
    140,
  );
  const scriptSourceDigest = cleanToken(scriptTruth.source_digest, 80);
  const planShotCount = Number(productionPlan.shot_count || 0);
  const normalizedSection = section === "storyboard" ? "storyboard_read_only" : section === "asset_bible" ? "asset_bible" : "canvas";
  const objectKind = normalizedSection === "asset_bible" && selectedAsset?.stable_id
    ? "asset"
    : normalizedSection === "storyboard_read_only" && currentShot?.nodeId
      ? "shot"
      : activeNode?.id
        ? "node"
        : "project";
  const objectId = objectKind === "asset"
    ? cleanToken(selectedAsset?.stable_id, 160)
    : objectKind === "shot"
      ? cleanToken(currentShot?.nodeId, 160)
      : objectKind === "node"
        ? cleanToken(activeNode?.id, 160)
        : cleanToken(project?.project_id || meta.projectId, 120);
  const snapshot = {
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
    project_name: cleanText(preferredProjectName(project?.name, meta.projectName), 80),
    section: normalizedSection,
    object_kind: objectKind,
    object_id: objectId,
    selected_node_id: cleanToken(activeNode?.id, 120),
    selected_node_type: cleanToken(activeNode?.type, 40),
    selected_node_status: cleanToken(activeNode?.status, 40),
    selected_node_title: cleanText(activeNode?.title || activeNode?.label || "", 80),
    selected_node_text: cleanSourceText(
      activeNode?.params?.scriptRevision?.source_text
      || activeNode?.content
      || activeNode?.prompt
      || "",
      12000,
    ),
    selected_core_asset_id: cleanToken(selectedCoreAsset?.asset_id, 140),
    selected_core_asset_type: cleanToken(selectedCoreAsset?.asset_type, 60),
    selected_core_asset_status: cleanToken(selectedCoreAsset?.status, 80),
    selected_plan_entity_type: cleanToken(selectedPlanEntity?.entity_type, 80),
    selected_plan_shot_id: cleanToken(selectedPlanEntity?.shot_id, 140),
    selected_plan_chunk_id: cleanToken(selectedPlanEntity?.chunk_id, 160),
    selected_plan_entity_plan_id: cleanToken(selectedPlanEntity?.plan_id, 140),
    selected_plan_entity_plan_digest: cleanToken(selectedPlanEntity?.plan_digest, 80),
    selected_screenplay_summary: selectedScreenplaySummary,
    selected_edge_id: selectedEdgeId,
    selected_edge_relation_type: cleanToken(selectedEdge?.relation_type || selectedEdge?.relationType || "", 80),
    selected_edge_from_node_id: cleanToken(selectedEdge?.from, 120),
    selected_edge_to_node_id: cleanToken(selectedEdge?.to, 120),
    selected_edge_from_title: cleanText(selectedEdgeFrom?.title || selectedEdgeFrom?.label || "", 80),
    selected_edge_to_title: cleanText(selectedEdgeTo?.title || selectedEdgeTo?.label || "", 80),
    current_shot_node_id: cleanToken(currentShot?.nodeId, 120),
    current_shot_title: cleanText(currentShot?.title || "", 80),
    selected_asset_id: cleanToken(selectedAsset?.stable_id, 160),
    selected_asset_type: cleanToken(selectedAsset?.asset_type, 40),
    selected_asset_title: cleanText(selectedAsset?.display_name || "", 120),
    selected_asset_review_state: cleanToken(selectedAsset?.review_state, 40),
    asset_bible_revision_id: cleanToken(assetBible?.current_revision_id, 160),
    asset_bible_status: cleanToken(assetBible?.status, 40),
    asset_candidate_set_id: cleanToken(assetBible?.candidate_set?.candidate_set_id, 160),
    production_copilot: copilot || {},
    counts: {
      nodes: nodeValues.length,
      scenes: Number(productionGraph.scene_count || 0) || sceneNodes.length || inferSceneCount(shotNodes),
      shots: Number(productionGraph.shot_count || 0) || planShotCount || shotNodes.length,
      assets: Array.isArray(state.assets) ? state.assets.length : 0,
      asset_candidates: Number(assetBible?.counts?.total || 0),
      asset_candidates_pending: Number(assetBible?.counts?.candidate || 0),
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
      "m6_script_plan_asset_bible_contract",
      "m6_professional_review_roles",
    ],
    storyboard_mode: "read_only_deferred",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
  snapshot.context_fingerprint = agentChatContextFingerprint(snapshot);
  return snapshot;
}

function preferredProjectName(primary, fallback) {
  const values = [primary, fallback].map((item) => String(item || "").trim());
  return values.find((item) => item && !["未命名项目", "项目"].includes(item))
    || values.find(Boolean)
    || "未命名项目";
}

function screenplaySummaryForNode(node) {
  const params = node?.params && typeof node.params === "object" ? node.params : {};
  const revisions = Array.isArray(params.revisions) ? params.revisions : [];
  const currentRevisionId = cleanToken(params.currentRevisionId, 160);
  const currentRevision = revisions.find((revision) => cleanToken(revision?.revision_id, 160) === currentRevisionId)
    || revisions.slice().reverse().find((revision) => revision?.screenplay_candidate);
  const candidate = currentRevision?.screenplay_candidate || params.embeddedCreativeAction?.preview?.screenplay_candidate || null;
  const scenes = Array.isArray(candidate?.scenes) ? candidate.scenes : [];
  const characters = Array.isArray(candidate?.characters) ? candidate.characters : [];
  if (!scenes.length && !characters.length && !currentRevisionId) return null;
  return {
    revision_id: currentRevisionId || cleanToken(currentRevision?.revision_id, 160),
    title: cleanText(candidate?.title || "剧本候选", 120),
    scene_count: scenes.length,
    character_count: characters.length,
    dialogue_blocks: scenes.reduce((sum, scene) => {
      const blocks = Array.isArray(scene?.blocks) ? scene.blocks : [];
      return sum + blocks.filter((block) => cleanToken(block?.type, 40) === "dialogue").length;
    }, 0),
  };
}

function latestScreenplaySummary(nodes) {
  return nodes
    .map((node) => screenplaySummaryForNode(node))
    .filter(Boolean)
    .sort((left, right) => String(right.revision_id || "").localeCompare(String(left.revision_id || "")))[0] || {};
}

function latestAppliedScriptRevisionId(nodes) {
  const applied = nodes
    .map((node) => node?.params?.embeddedCreativeAction)
    .filter((action) => action?.status === "applied" && action?.applied_revision_id);
  return cleanToken(applied.slice(-1)[0]?.applied_revision_id, 140);
}

function isSceneContextNode(node) {
  const role = cleanToken(node?.params?.nodeRole, 80);
  return node?.type === "scene" || role === "storyboard_scene" || role === "m6_6_scene_candidate";
}

function isShotContextNode(node) {
  const role = cleanToken(node?.params?.nodeRole, 80);
  return Boolean(node?.params?.structuredShot) || node?.type === "shot" || role === "storyboard_shot" || role === "m6_6_shot_candidate";
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
  appendMessage(session, { role: "assistant", text: "更改内容已准备好；请先查看影响，确认前项目不会改变。" });
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

export function stageM6ScriptPlanCandidateCommand(session, context, preview) {
  const previewPayload = preview?.preview || preview || {};
  const candidate = previewPayload?.candidate || {};
  const validation = previewPayload?.validation || {};
  const runId = cleanToken(preview?.run_id, 120);
  const candidateDigest = cleanToken(preview?.candidate_digest || previewPayload?.candidate_digest, 80);
  const characters = Array.isArray(candidate.characters) ? candidate.characters.length : 0;
  const scenes = Array.isArray(candidate.scenes) ? candidate.scenes.length : 0;
  const shots = Array.isArray(candidate.shots) ? candidate.shots.length : 0;
  const roles = Array.isArray(validation.review_roles) ? validation.review_roles.length : 0;
  const scopeImpact = m6ScopeImpact(candidate);
  if (!session || candidate.m6_schema_version !== "afs.m6.script_plan_asset_bible.v0.1" || !characters || !scenes || !shots || roles < 6) {
    throw new Error("制作方案缺少完整的剧本、动态分镜、资产清单或审核结果");
  }
  const command = {
    schema_version: SCHEMA_VERSION,
    command_id: `command_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "m6_script_plan_asset_bible",
    graph_action: "confirm_m6_script_plan_asset_bible",
    title: "确认制作方案",
    summary: `现在仅供预览。确认后会保存 ${characters} 个角色、${scenes} 个场景和 ${shots} 个动态镜头；所有新建、改名、补充、用途和关联都会逐项列出。`,
    status: "preview",
    execution_mode: "runtime",
    context_key: context?.context_key || agentChatContextKey(context),
    project_id: context?.project_id || "",
    graph_version: Number(context?.production_graph_version || 0),
    graph_digest: context?.production_graph_digest || "",
    run_id: runId,
    candidate_digest: candidateDigest,
    candidate,
    m6_validation: validation,
    scope_impact: scopeImpact,
    storyboard_write: false,
    provider_dispatch_count: Number(preview?.dispatch_count || previewPayload?.provider_dispatch_count || 0),
  };
  if (runId) {
    appendM6RunMessage(session, runId, "user", "生成制作方案", "submitted");
  } else {
    appendMessage(session, { role: "user", text: "生成制作方案" });
  }
  session.pendingCommand = command;
  if (runId) {
    syncM6PreviewRunSession(session, context, preview);
  } else {
    appendMessage(session, { role: "assistant", text: "制作方案已生成。现在仅供预览；请核对全部内容，确认后才会保存到项目。" });
  }
  return command;
}

function m6ScopeImpact(candidate = {}) {
  const review = candidate?.m6_scope_review && typeof candidate.m6_scope_review === "object" ? candidate.m6_scope_review : {};
  const impact = {
    schema_version: cleanToken(review.schema_version, 80) || "afs.m6.canonical_scope_review.v0.1",
    source_authority: cleanToken(review.source_authority, 80) || "user_supplied_canonical_scope",
    canonical: safeRecordOfLists(review.canonical),
    production_aids: arrayOfRecords(review.production_aids).map((item) => ({
      name: cleanText(item.name, 120),
      kind: cleanToken(item.kind, 40),
      classification: cleanToken(item.classification, 60),
      production_aid_type: cleanToken(item.production_aid_type, 60),
    })),
    proposed_additions: arrayOfRecords(review.proposed_additions).map(m6ScopeImpactItem),
    proposed_renames: arrayOfRecords(review.proposed_renames).map(m6ScopeImpactItem),
    proposed_expansions: arrayOfRecords(review.proposed_expansions).map(m6ScopeImpactItem),
    proposed_classifications: arrayOfRecords(review.proposed_classifications).map(m6ScopeImpactItem),
    affected_associations: arrayOfRecords(review.affected_associations).map(m6ScopeImpactItem),
  };
  impact.summary = {
    additions: impact.proposed_additions.length,
    renames: impact.proposed_renames.length,
    expansions: impact.proposed_expansions.length,
    classifications: impact.proposed_classifications.length,
    affected_associations: impact.affected_associations.length,
  };
  return impact;
}

function m6ScopeImpactItem(item = {}) {
  return {
    item_type: cleanToken(item.item_type, 40),
    association_type: cleanToken(item.association_type, 80),
    id: cleanToken(item.id, 180),
    name: cleanText(item.name, 160),
    before: cleanText(item.before, 160),
    after: cleanText(item.after, 160),
    kind: cleanToken(item.kind, 40),
    classification: cleanToken(item.classification, 80),
    canonical_asset_type: cleanToken(item.canonical_asset_type, 60),
    production_aid_type: cleanToken(item.production_aid_type, 60),
    authority: cleanToken(item.authority, 80),
    fields: Array.isArray(item.fields) ? item.fields.map((field) => cleanToken(field, 80)).filter(Boolean).slice(0, 16) : [],
    names: Array.isArray(item.names) ? item.names.map((name) => cleanText(name, 120)).filter(Boolean).slice(0, 24) : [],
    scene: cleanText(item.scene, 120),
    characters: Array.isArray(item.characters) ? item.characters.map((name) => cleanText(name, 120)).filter(Boolean).slice(0, 12) : [],
    canonical_props: Array.isArray(item.canonical_props) ? item.canonical_props.map((name) => cleanText(name, 120)).filter(Boolean).slice(0, 12) : [],
    production_aids: Array.isArray(item.production_aids) ? item.production_aids.map((name) => cleanText(name, 120)).filter(Boolean).slice(0, 12) : [],
    duration_seconds: Number(item.duration_seconds || 0),
  };
}

function safeRecordOfLists(value = {}) {
  const source = value && typeof value === "object" ? value : {};
  return Object.fromEntries(
    Object.entries(source).map(([key, list]) => [
      cleanToken(key, 40),
      Array.isArray(list) ? list.map((item) => cleanText(item, 120)).filter(Boolean).slice(0, 24) : [],
    ]),
  );
}

function arrayOfRecords(value) {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") : [];
}

export function syncM6PreviewRunSession(session, context, run) {
  const runId = cleanToken(run?.run_id, 120);
  if (!session || !runId) return null;
  const phase = cleanToken(run?.phase, 40) || "queued";
  const errorMessage = cleanText(run?.error?.message, 300);
  const copy = {
    queued: "制作方案已提交；确认前不会改变制作事实。",
    running: "制作方案处理中。即使浏览器连接中断，也会恢复同一任务，不会重复提交。",
    running_cancel_requested: "已记录停止后续处理的请求；当前同步文本任务可能仍在完成，不会虚假显示已取消。",
    succeeded: "制作方案预览已恢复；请先审阅，确认前不会保存到项目。",
    failed: errorMessage || "制作方案任务失败；已保留原项目事实，可查看同一任务的失败状态。",
    unknown: errorMessage || "文本任务状态需要人工核对；系统不会自动再次提交。",
    cancelled: "制作方案预览已取消；项目内容没有改变。",
    confirmed: "制作方案已确认并保存；刷新后仍可恢复本次确认记录。",
  }[phase] || "制作方案状态正在恢复；不会重复提交。";
  return appendM6RunMessage(session, runId, "assistant", copy, phase, context);
}

function appendM6RunMessage(session, runId, role, text, phase, context = null) {
  const messages = (Array.isArray(session.messages) ? [...session.messages] : []).filter((message) => (
    role !== "assistant"
    || message?.placeholder_id !== AGENT_COMMAND_PREVIEW_PLACEHOLDER_ID
    || (context?.context_key && message?.context_key && message.context_key !== context.context_key)
  ));
  const markerRole = role === "user" ? "user" : "assistant";
  const matching = [];
  for (let index = 0; index < messages.length; index += 1) {
    if (messages[index]?.m6_preview_run_id === runId && messages[index]?.role === markerRole) matching.push(index);
  }
  const message = {
    role: markerRole,
    text: cleanText(text, 900),
    tone: phase === "failed" ? "error" : phase === "cancelled" ? "warning" : "",
    created_at: new Date().toISOString(),
    m6_preview_run_id: runId,
    m6_preview_phase: cleanToken(phase, 40),
    context_key: cleanToken(context?.context_key, 180),
  };
  if (matching.length) {
    messages[matching.at(-1)] = { ...messages[matching.at(-1)], ...message };
    for (const index of matching.slice(0, -1).reverse()) messages.splice(index, 1);
  } else {
    messages.push(message);
  }
  session.messages = messages.slice(-MESSAGE_LIMIT);
  return message;
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
        : "更改内容已准备好；确认前画布不会改变。",
    });
    return { status: command.status, command };
  }
  appendMessage(session, { role: "user", text: displayText || commandText });
  const answer = conversationalReply(commandText, context);
  appendMessage(session, {
    role: "assistant",
    text: answer?.text || "我可以继续讨论创作方向；需要改动画布时会先给出可确认的预览。",
  });
  return { status: answer?.status || "answered", conversation: answer };
}

export async function submitAgentChatMessageWithRuntime(session, rawText, context, runtime = null) {
  const commandText = cleanSourceText(rawText, 12000);
  const displayText = cleanText(rawText, 900);
  if (!commandText) return { status: "empty" };
  const command = previewAgentCommand(commandText, context);
  if (command.command_type !== "none") {
    return submitAgentChatMessage(session, rawText, context);
  }
  appendMessage(session, { role: "user", text: displayText || commandText });
  if (!runtime?.agentChatConversation) {
    const unavailable = unavailableConversation("runtime_unavailable");
    session.conversationRequest = {
      status: "unavailable",
      message: unavailable.text,
      lastMessage: commandText,
    };
    appendMessage(session, { role: "assistant", text: unavailable.text, tone: "warning" });
    return { status: "unavailable", conversation: unavailable };
  }
  const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
  session.conversationRequest = {
    status: "loading",
    message: "AI 创作搭档正在通过运行服务结合当前画布回答；这不会改动画布。",
    lastMessage: commandText,
    cancel: () => controller?.abort(),
  };
  try {
    const response = await runtime.agentChatConversation({
      message: commandText,
      node_id: context?.selected_node_id || "",
      canvas_summary: agentChatRuntimeSummary(context),
      provider_service_id: "server_codex",
      generated_at: new Date().toISOString(),
    }, { signal: controller?.signal || null });
    if (response?.mode !== "llm" || response?.provider_calls_started !== true) {
      const unavailable = unavailableConversation(response?.safe_manifest?.fallback_reason || response?.mode || "llm_unavailable");
      session.conversationRequest = {
        status: "unavailable",
        message: unavailable.text,
        lastMessage: commandText,
      };
      appendMessage(session, { role: "assistant", text: unavailable.text, tone: "warning" });
      return { status: "unavailable", conversation: unavailable, response };
    }
    const answer = runtimeConversationAnswer(response);
    session.conversationRequest = null;
    session.lastConversation = answer;
    appendMessage(session, { role: "assistant", text: answer.text });
    return { status: answer.status, conversation: answer, response };
  } catch (error) {
    const aborted = error?.name === "AbortError";
    const failure = unavailableConversation(aborted ? "cancelled" : "runtime_request_failed");
    session.conversationRequest = {
      status: aborted ? "cancelled" : "failed",
      message: failure.text,
      lastMessage: commandText,
    };
    appendMessage(session, { role: "assistant", text: failure.text, tone: aborted ? "warning" : "error" });
    return { status: session.conversationRequest.status, conversation: failure, error };
  }
}

export function cancelAgentCommand(session) {
  if (!session?.pendingCommand) return null;
  const command = session.pendingCommand;
  session.pendingCommand = null;
  appendMessage(session, { role: "assistant", text: "本次更改已取消，画布没有改变。" });
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

function dispatchM6PreviewRunUpdate(run) {
  try {
    window.dispatchEvent(new CustomEvent("afs:m6-preview-run-updated", { detail: { run } }));
  } catch {
    // Lifecycle contracts can execute in Node without a browser event target.
  }
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
  if (command.command_type === "m6_script_plan_asset_bible") {
    response = await runtime.confirmM6ScriptPlanAssetBible({
      expected_graph_version: command.graph_version,
      run_id: command.run_id,
      candidate_digest: command.candidate_digest,
    });
    const graph = response?.graph || {};
    runtimeReceipt = { graph_version: graph.version, graph_digest: graph.graph_digest, recovery: "refresh_and_retry_on_version_conflict" };
    projectionDomain = "production_graph";
  } else if (command.command_type === "m5_graph_candidate") {
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
  if (command.command_type === "m6_script_plan_asset_bible" && command.run_id) {
    syncM6PreviewRunSession(session, { context_key: command.context_key }, {
      run_id: command.run_id,
      phase: "confirmed",
    });
    dispatchM6PreviewRunUpdate({
      run_id: command.run_id,
      project_id: command.project_id,
      phase: "confirmed",
      confirmation: runtimeReceipt,
    });
  } else {
    appendMessage(session, { role: "assistant", text: receipt.summary });
  }
  return receipt;
}

function productionGraphAgentReceipt(command, runtimeReceipt = {}) {
  const actionSummaries = {
    confirm_candidate: "可信制作方案已建立为唯一制作图版本；画布与故事板将同步刷新。",
    confirm_m6_script_plan_asset_bible: "剧本、动态分镜和资产清单已保存；画布、故事板、资产 Bible 与 AI 创作搭档会同步显示。",
    mutate: "局部修改已确认；仅证据关联的下游对象进入待处理，未关联产物继续保留。",
    select_candidate: "候选版本已选定并保存。",
    review_decision: command.payload?.state === "approved" ? "专业审核已通过并保存。" : "专业审核已退回，原候选与证据仍保留。",
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
    provider_dispatch_count: Number(command.provider_dispatch_count || 0),
    remote_dispatch_count: command.command_type === "m6_script_plan_asset_bible"
      ? Number(command.provider_dispatch_count || 0)
      : 0,
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
        text: "我会先展示本次更改的内容和影响；确认前画布不会改变。",
        placeholder_id: AGENT_COMMAND_PREVIEW_PLACEHOLDER_ID,
        context_key: contextKey,
      },
    ],
    pendingCommand: null,
    receipts: [],
    draftMessage: "",
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

  if (/^\/screenplay-selected$/i.test(message) || /^把当前节点剧本化$/i.test(message) || /^剧本化当前节点$/i.test(message)) {
    return embeddedCreativeActionCommand({
      context,
      actionType: "script_revision",
      mode: "professional_screenplay",
      title: "剧本化扩写当前节点",
      summary: "确认后在当前节点打开真实 LLM 剧本化任务；预览、diff、应用和取消都绑定同一节点，不创建新节点。",
    });
  }

  if (/^\/optimize-selected-default$/i.test(message) || /^默认优化(?:当前)?文本$/i.test(message) || /^优化当前文本$/i.test(message)) {
    return scriptOptimizationCommand({
      context,
      mode: "default",
      instruction: "保留原有创作目标，改善结构、表达、节奏和可生产性。",
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

  const forkInstruction = matchCommand(message, [
    /^\/fork-selected(?:\s+(.+))?$/i,
    /^创建分支版本(?:[:：]\s*(.+))?$/i,
    /^派生为新节点(?:[:：]\s*(.+))?$/i,
  ]);
  if (/^\/fork-selected$/i.test(message) || /^创建分支版本$/i.test(message) || /^派生为新节点$/i.test(message) || forkInstruction) {
    return forkSelectedNodeCommand(context, forkInstruction || "从当前节点显式派生一个分支版本。");
  }

  const createNodeIntent = nodeCreationIntent(message);
  if (createNodeIntent) return createCanvasNodeCommand(context, createNodeIntent);

  const relationIntent = edgeRelationIntent(message);
  if (relationIntent) return edgeRelationCommand(context, relationIntent);

  if (/^\/delete-selected-edge$/i.test(message) || /^删除(?:当前|选中)?连线$/i.test(message)) {
    return deleteSelectedEdgeCommand(context);
  }

  const generationIntent = generationPreviewIntent(message);
  if (generationIntent) return generationPreviewCommand(context, generationIntent);

  if (/^\/refresh-script-truth$/i.test(message) || /^刷新(?:剧本)?事实$/i.test(message)) {
    return runtimeCommand({
      context,
      commandType: "refresh_script_truth",
      title: "刷新剧本与资产事实",
      summary: "从运行服务事实重新投影剧本版本、角色、主要场景与手动道具。",
      requiresScriptRevision: false,
    });
  }

  if (/^\/plan-selected-script-shots$/i.test(message) || /^拆分分镜$/i.test(message) || /^自动分镜$/i.test(message)) {
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

function scriptOptimizationCommand({ context, mode }) {
  return embeddedCreativeActionCommand({
    context,
    actionType: "script_revision",
    mode: mode === "default" ? "professional_expansion" : "instructed_revision",
    title: mode === "default" ? "优化当前节点" : "按要求优化当前节点",
    summary: "确认后在当前节点打开真实 LLM 修订任务；结果先审阅，应用后只更新同一节点修订历史。",
  });
}

function embeddedCreativeActionCommand({ context, actionType, mode, title, summary }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("start_embedded_creative_action", title, "故事板是只读投影。请切回画布后再启动节点内 AI 动作。", context);
  }
  const allowedTypes = actionType === "shot_breakdown" ? ["text", "script", "sequence", "scene"] : ["text", "script"];
  if (!allowedTypes.includes(context.selected_node_type)) {
    return blockedCommand("start_embedded_creative_action", title, "请先选择一个可写的文本、剧本、场景或镜头相关节点。", context);
  }
  const sourceText = cleanSourceText(context.selected_node_text, 12000);
  if (!sourceText) {
    return blockedCommand("start_embedded_creative_action", title, "当前节点在制作图中的正文为空；请先输入内容。", context);
  }
  const commandId = `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  return {
    schema_version: SCHEMA_VERSION,
    command_id: commandId,
    command_type: "start_embedded_creative_action",
    execution_mode: "embedded_creative_action",
    status: "preview",
    title,
    summary,
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    node_id: cleanToken(context.selected_node_id, 120),
    action_type: actionType,
    mode,
    source_digest: cleanToken(context.studio_state_revision_id, 80),
    impact: {
      node_ids: context.selected_node_id ? [context.selected_node_id] : [],
      relation: actionType === "shot_breakdown" ? "visible_candidate_storyboard_subgraph" : "same_node_revision_preview",
      storyboard_write: actionType === "shot_breakdown",
    },
    requires_confirmation: true,
    provider_label: "server_codex 文本模型",
    tool_label: "节点内 AI 动作",
    cost_label: "外部付费 $0；确认后才调用文本模型",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function createCanvasNodeCommand(context, intent) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("create_canvas_node", "创建画布节点", "故事板是只读投影。请切回画布后再创建节点。", context);
  }
  const def = NODE_TYPES[intent.type] || NODE_TYPES.text;
  const title = cleanText(intent.title || `${def.label}节点`, 80);
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "create_canvas_node",
    execution_mode: "local",
    status: "preview",
    title: `创建${def.label}`,
    summary: context.selected_node_id
      ? `确认后在当前节点${intent.direction === "upstream" ? "前面" : "后面"}创建「${title}」，并建立一条${relationTypeLabel(intent.relation_type)}连线。`
      : `确认后在当前画布创建「${title}」，不会补造上游剧本或分镜。`,
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    node_id: cleanToken(context.selected_node_id, 120),
    create_node: {
      type: intent.type,
      title,
      prompt: cleanText(intent.prompt || "", 500),
      relation_type: intent.relation_type,
      direction: intent.direction || "downstream",
    },
    impact: {
      node_ids: context.selected_node_id ? [context.selected_node_id] : [],
      relation: intent.relation_type || "generation",
      storyboard_write: false,
    },
    requires_confirmation: true,
    tool_label: "画布本地操作",
    cost_label: "不产生费用",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function forkSelectedNodeCommand(context, instruction) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("fork_selected_node", "创建分支版本", "故事板是只读投影。请切回画布后再创建分支。", context);
  }
  if (!context.selected_node_id) return blockedCommand("fork_selected_node", "创建分支版本", "请先选择要派生的节点。", context);
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "fork_selected_node",
    execution_mode: "local",
    status: "preview",
    title: "创建分支版本",
    summary: "确认后才会从当前节点派生一个新节点；普通优化仍保留在原节点修订历史中。",
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    node_id: cleanToken(context.selected_node_id, 120),
    fork_instruction: cleanText(instruction, 500),
    impact: {
      node_ids: [context.selected_node_id],
      relation: "fork",
      storyboard_write: false,
    },
    requires_confirmation: true,
    tool_label: "画布本地操作",
    cost_label: "不产生费用",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function edgeRelationCommand(context, intent) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("change_edge_relation", "调整连线关系", "故事板是只读投影。请切回画布后再调整连线。", context);
  }
  const edgeId = cleanToken(context.selected_edge_id, 140);
  if (!edgeId) return blockedCommand("change_edge_relation", "调整连线关系", "请先点选一条连线。", context);
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "change_edge_relation",
    execution_mode: "local",
    status: "preview",
    title: "调整连线关系",
    summary: `确认后把当前连线标记为${relationTypeLabel(intent.relation_type)}；节点内容不变。`,
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    edge_id: edgeId,
    relation_type: intent.relation_type,
    impact: {
      node_ids: [context.selected_edge_from_node_id, context.selected_edge_to_node_id].filter(Boolean),
      relation: "edge_relation_update",
      storyboard_write: false,
    },
    requires_confirmation: true,
    tool_label: "画布本地操作",
    cost_label: "不产生费用",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function deleteSelectedEdgeCommand(context) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("delete_selected_edge", "删除当前连线", "故事板是只读投影。请切回画布后再删除连线。", context);
  }
  const edgeId = cleanToken(context.selected_edge_id, 140);
  if (!edgeId) return blockedCommand("delete_selected_edge", "删除当前连线", "请先点选一条连线。", context);
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "delete_selected_edge",
    execution_mode: "local",
    status: "preview",
    title: "删除当前连线",
    summary: "确认后只删除这条关系，两个节点都会保留；可以撤销。",
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    edge_id: edgeId,
    impact: {
      node_ids: [context.selected_edge_from_node_id, context.selected_edge_to_node_id].filter(Boolean),
      relation: "edge_delete",
      storyboard_write: false,
    },
    requires_confirmation: true,
    tool_label: "画布本地操作",
    cost_label: "不产生费用",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function generationPreviewCommand(context, intent) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand("preview_generation_from_selected", "预览生成命令", "故事板是只读投影。请回到画布后再预览生成命令。", context);
  }
  if (!context.selected_node_id) return blockedCommand("preview_generation_from_selected", "预览生成命令", "请先选择一个镜头、图片、关键帧或视频节点。", context);
  return {
    schema_version: SCHEMA_VERSION,
    command_id: `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    command_type: "preview_generation_from_selected",
    execution_mode: "local",
    status: "preview",
    title: intent.kind === "video" ? "预览视频生成" : "预览图片生成",
    summary: intent.kind === "video"
      ? "确认后只记录当前节点的视频生成意图预览；外部视频能力关闭时不会提交任务。"
      : "确认后只记录当前节点的图片生成意图预览；外部图片能力关闭时不会提交任务。",
    context_key: agentChatContextKey(context),
    project_id: cleanToken(context.project_id, 120),
    node_id: cleanToken(context.selected_node_id, 120),
    generation_kind: intent.kind,
    generation_instruction: cleanText(intent.instruction, 500),
    impact: {
      node_ids: [context.selected_node_id],
      relation: "generation_intent_preview",
      storyboard_write: false,
    },
    requires_confirmation: true,
    provider_label: intent.kind === "video" ? "外部视频能力当前未启用" : "外部图片能力当前未启用",
    tool_label: "生成命令预览",
    cost_label: "本次不扣费；真实生成前需单独确认",
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function trimSentence(value, limit) {
  const text = cleanSourceText(value, limit + 80).replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function nodeCreationIntent(message) {
  const direct = message.match(/^\/create-node\s+([a-z_]+)(?:\s+(.+))?$/i);
  if (direct) return nodeIntentFromType(direct[1], direct[2]);
  const createMatch = message.match(/^(?:创建|新增|添加)(.+?)(?:节点|卡|对象)?(?:[:：]\s*(.+))?$/);
  if (!createMatch) return null;
  const raw = createMatch[1] || "";
  const title = createMatch[2] || "";
  if (/角色/.test(raw)) return nodeIntentFromType("character", title || "角色设定");
  if (/场景空间|地点|空间|location/i.test(raw)) return nodeIntentFromType("location", title || "场景空间");
  if (/道具|prop/i.test(raw)) return nodeIntentFromType("prop", title || "道具设定");
  if (/参考|ReferenceSet|参考图|素材/.test(raw)) return nodeIntentFromType("ref", title || "参考集");
  if (/图片|关键帧|image|keyframe/i.test(raw)) return nodeIntentFromType("image", title || "图片 / 关键帧");
  if (/视频|video/i.test(raw)) return nodeIntentFromType("video", title || "视频片段");
  if (/音频|audio/i.test(raw)) return nodeIntentFromType("audio", title || "音频");
  if (/镜头|shot/i.test(raw)) return nodeIntentFromType("shot", title || "镜头");
  if (/场景|场|scene/i.test(raw)) return nodeIntentFromType("scene", title || "场景");
  if (/序列|段落|sequence/i.test(raw)) return nodeIntentFromType("sequence", title || "段落");
  if (/剧本|脚本|script/i.test(raw)) return nodeIntentFromType("script", title || "剧本");
  if (/想法|idea|文本|text/i.test(raw)) return nodeIntentFromType("text", title || "文本");
  return null;
}

function nodeIntentFromType(type, title = "") {
  const normalized = ({
    keyframe: "image",
    reference: "ref",
    referenceset: "ref",
    location: "location",
    scene_location: "location",
  })[String(type || "").toLowerCase()] || String(type || "text").toLowerCase();
  const safeType = NODE_TYPES[normalized] ? normalized : "text";
  return {
    type: safeType,
    title: cleanText(title, 80) || (NODE_TYPES[safeType]?.label || "节点"),
    prompt: "",
    direction: "downstream",
    relation_type: ["ref", "character", "location", "prop"].includes(safeType) ? "reference" : "generation",
  };
}

function edgeRelationIntent(message) {
  const match = message.match(/(?:把|将)?(?:这条|当前|选中)?(?:连线|关系|边).*(?:改成|改为|设为|设置为)\s*(参考|生成|派生|分支|导演|顺序|待确认|reference|generation|fork|director|sequence|proposed)/i);
  if (!match) return null;
  return { relation_type: relationTypeFromText(match[1]) };
}

function generationPreviewIntent(message) {
  const image = message.match(/^(?:预览)?(?:生成|制作)(?:一张)?(?:图片|关键帧|image|keyframe)(?:[:：]\s*(.+))?$/i);
  if (image) return { kind: "image", instruction: image[1] || "基于当前节点上下文生成图片" };
  const video = message.match(/^(?:预览)?(?:生成|制作)(?:一段)?(?:视频|video)(?:[:：]\s*(.+))?$/i);
  if (video) return { kind: "video", instruction: video[1] || "基于当前节点上下文生成视频" };
  return null;
}

function relationTypeFromText(text) {
  const value = String(text || "").trim().toLowerCase();
  if (/参考|reference/.test(value)) return "reference";
  if (/分支|派生|fork/.test(value)) return "fork";
  if (/导演|director/.test(value)) return "director";
  if (/顺序|sequence/.test(value)) return "sequence";
  if (/待确认|建议|proposed/.test(value)) return "proposed";
  return "generation";
}

function relationTypeLabel(value) {
  return {
    generation: "生成/派生",
    reference: "参考",
    director: "导演控制",
    fork: "分支",
    sequence: "叙事顺序",
    proposed: "待确认建议",
  }[value] || cleanText(value, 40);
}

function runtimeCommand({ context, commandType, title, summary, requiresScriptRevision = true }) {
  if (context?.section === "storyboard_read_only") {
    return blockedCommand(commandType, title, "请切回画布后再保存这项更改。", context);
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
  return embeddedCreativeActionCommand({
    context,
    actionType: "shot_breakdown",
    mode: "dynamic_shot_breakdown",
    title: "拆分分镜",
    summary: "确认后在当前节点打开真实 LLM 分镜任务；预览完成后可见候选分镜子图，应用前不写最终制作事实。",
  });
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
    return blockedCommand(commandType, title, "请切回画布查看并确认这项更改。", context);
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
  if (command.command_type === "create_canvas_node") return executeCreateCanvasNode(command, state);
  if (command.command_type === "change_edge_relation") return executeChangeEdgeRelation(command, state);
  if (command.command_type === "delete_selected_edge") return executeDeleteSelectedEdge(command, state);
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
  } else if (command.command_type === "revise_selected_node") {
    applySameNodeRevision(node, command);
  } else if (command.command_type === "fork_selected_node") {
    return executeForkSelectedNode(command, state, node, before);
  } else if (command.command_type === "preview_generation_from_selected") {
    node.params = node.params || {};
    node.params.generationIntentPreview = {
      schema_version: "afs.generation_intent_preview.v0.1",
      kind: command.generation_kind,
      instruction: command.generation_instruction,
      provider_state: "provider_gate_closed_preview_only",
      cost_label: command.cost_label,
      command_id: command.command_id,
      updated_at: new Date().toISOString(),
    };
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
    summary: localNodeReceiptSummary(command),
    before,
    after,
    undo_available: true,
    storyboard_write: false,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
}

function localNodeReceiptSummary(command) {
  if (command.command_type === "revise_selected_node") return "当前节点已新增一个可撤销修订；没有创建新节点。";
  if (command.command_type === "preview_generation_from_selected") return "生成意图预览已记录；未调用外部能力，也没有产生费用。";
  return `${command.title}已执行，影响范围：当前节点。`;
}

function executeCreateCanvasNode(command, state) {
  const spec = command.create_node || {};
  const def = NODE_TYPES[spec.type] || NODE_TYPES.text;
  const id = nextStateId(state, "node");
  const anchor = state.nodes?.[command.node_id] || null;
  const position = nodePositionForCreate(state, anchor, def, spec.direction);
  const created = {
    id,
    type: spec.type || "text",
    title: cleanText(spec.title || `${def.label}节点`, 80),
    x: position.x,
    y: position.y,
    w: def.size.w,
    h: def.size.h,
    prompt: cleanText(spec.prompt || "", 1000),
    params: defaultParams(spec.type || "text"),
    content: "",
    status: "empty",
    result: null,
    groupId: null,
    collapsed: false,
  };
  state.nodes[id] = created;
  state.order = [...(state.order || []), id];
  const createdEdgeIds = [];
  if (anchor?.id) {
    const from = spec.direction === "upstream" ? id : anchor.id;
    const to = spec.direction === "upstream" ? anchor.id : id;
    const edgeId = uniqueEdgeId(state, from, to);
    state.edges[edgeId] = { id: edgeId, from, to, relation_type: spec.relation_type || "generation" };
    createdEdgeIds.push(edgeId);
    state.ui = state.ui || {};
    state.ui.lastConnectedEdgeId = edgeId;
  }
  state.selection = { nodeIds: [id], edgeId: null };
  return commandReceipt(command, {
    node_id: id,
    summary: `已创建「${created.title}」；${createdEdgeIds.length ? "已建立声明关系，" : ""}未补造上游事实。`,
    created_node_id: id,
    created_edge_ids: createdEdgeIds,
    after: snapshotNode(created),
  });
}

function executeForkSelectedNode(command, state, source, before) {
  const id = nextStateId(state, "node");
  const clone = safeJsonClone(source);
  clone.id = id;
  clone.title = `${cleanText(source.title, 70) || "节点"} 分支`;
  clone.x = Math.round(Number(source.x || 0) + Math.max(Number(source.w || 280) + 160, 380));
  clone.y = Math.round(Number(source.y || 0) + 28);
  clone.status = source.status === "empty" ? "draft" : source.status;
  clone.params = {
    ...(clone.params || {}),
    forkedFromNodeId: source.id,
    forkInstruction: cleanText(command.fork_instruction, 500),
    forkedAt: new Date().toISOString(),
  };
  state.nodes[id] = clone;
  state.order = [...(state.order || []), id];
  const edgeId = uniqueEdgeId(state, source.id, id);
  state.edges[edgeId] = { id: edgeId, from: source.id, to: id, relation_type: "fork" };
  state.selection = { nodeIds: [id], edgeId: null };
  return commandReceipt(command, {
    node_id: id,
    before,
    after: snapshotNode(clone),
    summary: `已显式派生「${clone.title}」；原节点保持不变。`,
    created_node_id: id,
    created_edge_ids: [edgeId],
  });
}

function executeChangeEdgeRelation(command, state) {
  const edge = state?.edges?.[command.edge_id];
  if (!edge) throw new Error("selected edge no longer exists");
  const before = safeJsonClone(edge);
  edge.relation_type = relationTypeFromText(command.relation_type);
  state.selection = { nodeIds: [], edgeId: edge.id };
  return commandReceipt(command, {
    edge_id: edge.id,
    edge_before: before,
    edge_after: safeJsonClone(edge),
    summary: `当前连线已改为${relationTypeLabel(edge.relation_type)}关系。`,
  });
}

function executeDeleteSelectedEdge(command, state) {
  const edge = state?.edges?.[command.edge_id];
  if (!edge) throw new Error("selected edge no longer exists");
  const before = safeJsonClone(edge);
  delete state.edges[command.edge_id];
  state.selection = { nodeIds: [], edgeId: null };
  return commandReceipt(command, {
    edge_id: command.edge_id,
    edge_before: before,
    edge_after: null,
    summary: "当前连线已删除；两个节点仍保留。",
  });
}

function applySameNodeRevision(node, command) {
  const beforeText = cleanSourceText(command.before_text || node.content || node.prompt || "", 12000);
  const afterText = cleanSourceText(command.after_text || command.source_text || "", 12000);
  node.params = node.params || {};
  const revisions = Array.isArray(node.params.revisions) ? node.params.revisions : [];
  const revisionId = `node_revision_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  node.params.revisions = [...revisions, {
    schema_version: "afs.node_revision.v0.1",
    revision_id: revisionId,
    source: "ai_creation_partner_preview",
    instruction: cleanText(command.optimization_instruction, 500),
    mode: cleanToken(command.optimization_mode, 80),
    before_text: beforeText,
    after_text: afterText,
    created_at: new Date().toISOString(),
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  }].slice(-12);
  node.params.currentRevisionId = revisionId;
  node.params.pendingRevisionPreview = null;
  node.content = afterText;
  node.prompt = afterText;
  node.status = afterText ? "draft" : "empty";
}

function commandReceipt(command, patch = {}) {
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
    summary: patch.summary || `${command.title}已执行。`,
    before: patch.before,
    after: patch.after,
    undo_available: true,
    storyboard_write: false,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
    ...patch,
  };
}

function nextStateId(state, prefix) {
  state.meta = state.meta || {};
  state.meta.seq = Number(state.meta.seq || 1) + 1;
  return `${prefix}_${state.meta.seq}`;
}

function nodePositionForCreate(state, anchor, def, direction = "downstream") {
  const base = anchor
    ? {
        x: Number(anchor.x || 0) + (direction === "upstream" ? -(def.size.w + 160) : Number(anchor.w || 280) + 160),
        y: Number(anchor.y || 0),
      }
    : {
        x: Math.round((260 - Number(state.viewport?.x || 0)) / Number(state.viewport?.scale || 1)),
        y: Math.round((190 - Number(state.viewport?.y || 0)) / Number(state.viewport?.scale || 1)),
      };
  return openPositionForState(state, { ...base, w: def.size.w, h: def.size.h });
}

function openPositionForState(state, base) {
  const existing = Object.values(state.nodes || {}).map((node) => ({
    x: Number(node.x || 0) - 28,
    y: Number(node.y || 0) - 28,
    w: Number(node.w || 280) + 56,
    h: Number(node.h || 240) + 56,
  }));
  const stepX = Math.max(Number(base.w || 280) + 80, 360);
  const stepY = Math.max(Number(base.h || 240) + 80, 320);
  for (const [dx, dy] of [[0, 0], [stepX, 0], [0, stepY], [stepX, stepY], [0, -stepY], [-stepX, 0]]) {
    const candidate = { ...base, x: Math.round(base.x + dx), y: Math.round(base.y + dy) };
    if (!existing.some((rect) => rectsIntersectLocal(candidate, rect))) return { x: candidate.x, y: candidate.y };
  }
  return { x: Math.round(base.x + stepX * (existing.length + 1)), y: Math.round(base.y) };
}

function rectsIntersectLocal(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function uniqueEdgeId(state, fromId, toId) {
  const base = `edge_${fromId}__${toId}`;
  if (!state.edges?.[base]) return base;
  return `${base}_${Date.now().toString(36)}`;
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
    summary: `创作上下文已准备；采用 ${Number(contextPack.relevant_knowledge_refs?.length || 0)} 条相关参考，草案确认前不会保存。`,
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
    request_story_plan_candidate: "拆分分镜",
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
  if (type === "revise_selected_node") {
    return command.optimization_mode === "instructed_local_structure"
      ? `按要求优化当前文本：${cleanText(command.optimization_instruction, 140)}`
      : "默认优化当前文本";
  }
  if (type === "fork_selected_node") return "创建分支版本";
  if (type === "create_canvas_node") return command.title || "创建画布节点";
  if (type === "change_edge_relation") return "调整连线关系";
  if (type === "delete_selected_edge") return "删除当前连线";
  if (type === "preview_generation_from_selected") return command.title || "预览生成命令";
  if (type === "start_embedded_creative_action") return command.title || "启动节点内 AI 动作";
  if (type === "submit_story_plan_candidate") return "提交动态制作计划候选";
  if (type === "request_story_plan_candidate") return "拆分分镜";
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
  if (receipt?.created_node_id) {
    delete state.nodes?.[receipt.created_node_id];
    state.order = (state.order || []).filter((id) => id !== receipt.created_node_id);
    for (const edgeId of receipt.created_edge_ids || []) delete state.edges?.[edgeId];
    state.selection = receipt.node_id && state.nodes?.[receipt.node_id]
      ? { nodeIds: [receipt.node_id], edgeId: null }
      : { nodeIds: [], edgeId: null };
    return undoReceipt(receipt, "已撤销新节点，画布回到创建前。");
  }
  if (receipt?.edge_before || receipt?.edge_id) {
    if (receipt.edge_before) state.edges[receipt.edge_before.id] = safeJsonClone(receipt.edge_before);
    else if (receipt.edge_id) delete state.edges[receipt.edge_id];
    state.selection = receipt.edge_before ? { nodeIds: [], edgeId: receipt.edge_before.id } : { nodeIds: [], edgeId: null };
    return undoReceipt(receipt, "已撤销连线变更。");
  }
  const node = state?.nodes?.[receipt.node_id];
  if (!node) throw new Error("selected node no longer exists");
  restoreNode(node, receipt.before || {});
  return undoReceipt(receipt, "上一条 AI 创作搭档命令已撤销，画布回到执行前状态。");
}

function snapshotNode(node) {
  return {
    id: cleanToken(node?.id, 120),
    type: cleanToken(node?.type, 40),
    title: cleanText(node?.title, 120),
    status: cleanToken(node?.status, 40),
    content: cleanSourceText(node?.content || "", 200000),
    prompt: cleanSourceText(node?.prompt || "", 200000),
    result: cleanSourceText(node?.result || "", 200000),
    previewUrl: cleanText(node?.previewUrl || "", 500),
    x: Number(node?.x || 0),
    y: Number(node?.y || 0),
    w: Number(node?.w || 0),
    h: Number(node?.h || 0),
    collapsed: Boolean(node?.collapsed),
    params: safeJsonClone(node?.params || {}),
  };
}

function restoreNode(node, snapshot) {
  if (snapshot.type) node.type = cleanToken(snapshot.type, 40);
  node.title = cleanText(snapshot.title, 120);
  node.status = cleanToken(snapshot.status, 40) || "draft";
  node.content = cleanSourceText(snapshot.content || "", 200000);
  node.prompt = cleanSourceText(snapshot.prompt || "", 200000);
  node.result = cleanSourceText(snapshot.result || "", 200000) || null;
  if (snapshot.previewUrl) node.previewUrl = cleanText(snapshot.previewUrl, 500);
  else delete node.previewUrl;
  if (Number(snapshot.w)) node.w = Number(snapshot.w);
  if (Number(snapshot.h)) node.h = Number(snapshot.h);
  node.collapsed = Boolean(snapshot.collapsed);
  node.params = safeJsonClone(snapshot.params || {});
}

function undoReceipt(receipt, summary) {
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
    edge_id: receipt.edge_id,
    summary,
    before: receipt.after,
    after: receipt.before,
    undo_available: false,
    storyboard_write: false,
    remote_dispatch_count: 0,
    provider_dispatch_count: 0,
  };
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

function runtimeConversationAnswer(response) {
  return {
    status: "answered",
    text: cleanText(response?.reply || "我已结合当前画布回答。", 900),
    source: "runtime_llm",
    provider_dispatch_count: 1,
    remote_dispatch_count: 1,
    request_id: cleanToken(response?.provider_lineage?.request_id, 180),
    latency_ms: Number(response?.latency_ms || 0),
    cost_usd: Number(response?.cost_usd || 0),
    graph_mutation: {
      mutated: response?.graph_mutation?.mutated === true,
      before_digest: cleanToken(response?.graph_mutation?.before_digest, 80),
      after_digest: cleanToken(response?.graph_mutation?.after_digest, 80),
    },
  };
}

function unavailableConversation(reason) {
  return {
    status: "unavailable",
    text: reason === "cancelled"
      ? "已取消这次回答；画布事实没有改变。"
      : "AI 模型当前不可用，我不会用本地固定回答冒充理解；请稍后重试，或先用画布按钮创建节点和预览命令。",
    source: "runtime_llm_unavailable",
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
    reason: cleanToken(reason, 80),
  };
}

function agentChatRuntimeSummary(context = {}) {
  const counts = context?.counts || {};
  return {
    nodes: Number(counts.nodes || 0),
    edges: Number(counts.edges || 0),
    assets: Number(counts.assets || 0),
    selected_node_type: cleanToken(context?.selected_node_type, 40),
    selected_node_status: cleanToken(context?.selected_node_status, 40),
    selected_node_title: cleanText(context?.selected_node_title, 120),
    selected_edge_relation_type: cleanToken(context?.selected_edge_relation_type, 80),
    selected_edge_from_title: cleanText(context?.selected_edge_from_title, 120),
    selected_edge_to_title: cleanText(context?.selected_edge_to_title, 120),
    section: cleanToken(context?.section, 80),
    video_readiness_status: cleanToken(context?.video_readiness_status, 40),
    video_selected_shot_ready: context?.video_selected_shot_ready === true ? 1 : 0,
    video_shot_label: cleanText(context?.video_shot_label, 80),
    video_keyframe_label: cleanText(context?.video_keyframe_label, 120),
    video_reference_count: Number(context?.video_reference_count || 0),
    video_model: cleanToken(context?.video_model, 80),
    video_resolution: cleanToken(context?.video_resolution, 20),
    video_duration_sec: Number(context?.video_duration_sec || 0),
  };
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
