import { agentChatContextSnapshot } from "./agent-chat-lifecycle.js";
import {
  appliedCreativeActionReceiptText,
  completeCreativeTask,
  createLocalCreativeTask,
  failCreativeTask,
  normalizeCreativeTask,
  nodeVersion,
  shotPlanSummary,
} from "./creative-task-contract.js";
import { visibleCanvasFrame } from "./canvas-safe-area.js";
import { clampScale, nodesBounds } from "./geometry.js";
import { defaultParams } from "./nodes.js";
import { applyScriptCoreTruthProjection } from "./script-core-truth-projection.js";

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
  const clientRequestId = options.clientRequestId
    || runtime?.newEmbeddedCreativeClientRequestId?.()
    || `cli_embedded_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const mode = options.mode || ACTION_MODES[actionType] || "professional_expansion";
  const localTask = createLocalCreativeTask(node, actionId, actionType, mode, sourceText);
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
      client_request_id: clientRequestId,
      source_node_version: nodeVersion(target, sourceText),
      creative_task: localTask,
      preview: null,
      error: "",
    };
    state.selection = { nodeIds: [node.id], edgeId: null };
  }, { history: false });
  dispatchBrowserEvent("afs:agent-chat-open-task", {
    detail: { node_id: node.id, action_type: actionType, task_id: actionId },
  });
  dispatchBrowserEvent("afs:embedded-creative-task-running", {
    detail: { node_id: node.id, action_type: actionType, task_id: actionId, phase: "dispatching" },
  });
  void store.flushRuntimeSave?.();
  if (!sourceText.trim()) return null;
  if (!runtime?.previewEmbeddedCreativeAction) {
    markEmbeddedCreativeUnavailable(store, node.id, actionId, {
      category: "runtime_unavailable",
      error_owner: "runtime",
      message: "运行服务没有可用的节点内 AI 预览接口；不会使用本地模板冒充改写。",
      detail: "embedded creative preview endpoint unavailable",
      next_action: "确认运行服务健康后重新预览。",
    });
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
    }, { clientRequestId });
    applyEmbeddedCreativeResponse(store, node.id, actionId, actionType, response, localTask);
    await store.flushRuntimeSave?.();
    return response;
  } catch (error) {
    const recoverableConflict = Number(error?.status || 0) === 409
      && error?.errorCode === "embedded_preview_in_progress";
    if (
      ([0, 504].includes(Number(error?.status || 0)) || recoverableConflict)
      && runtime?.recoverEmbeddedCreativeActionByClient
    ) {
      markEmbeddedCreativeRecovering(store, node.id, actionId, localTask);
      const recovered = await recoverEmbeddedCreativeResponse(runtime, clientRequestId);
      if (recovered) {
        applyEmbeddedCreativeResponse(store, node.id, actionId, actionType, recovered, localTask);
        await store.flushRuntimeSave?.();
        return recovered;
      }
    }
    markEmbeddedCreativeUnavailable(store, node.id, actionId, safeEmbeddedActionError(error, actionType), localTask);
    return null;
  }
}

export async function recoverPendingEmbeddedCreativeActions(store, runtime) {
  const pending = Object.values(store?.get?.()?.nodes || {})
    .map((node) => ({ node, action: node?.params?.embeddedCreativeAction }))
    .filter(({ action }) => ["running", "recovering"].includes(action?.status) && action?.client_request_id);
  await Promise.all(pending.map(async ({ node, action }) => {
    const recovered = await recoverEmbeddedCreativeResponse(runtime, action.client_request_id);
    if (!recovered) return;
    applyEmbeddedCreativeResponse(
      store,
      node.id,
      action.action_id,
      action.action_type || "script_revision",
      recovered,
      action.creative_task || {},
    );
    await store.flushRuntimeSave?.();
  }));
}

function applyEmbeddedCreativeResponse(store, nodeId, actionId, actionType, response, localTask) {
  store.set((state) => {
    const target = state.nodes[nodeId];
    const current = target?.params?.embeddedCreativeAction;
    if (!target || current?.action_id !== actionId || current?.status === "cancelled") return;
    const unavailable = response?.mode !== "llm" || response?.provider_calls_started !== true;
    const failure = unavailable ? failureFromPreviewResponse(response, actionType) : null;
    target.params.embeddedCreativeAction = {
      ...current,
      status: unavailable ? "unavailable" : "preview",
      message: unavailable ? failure.message : resultReadyMessage(actionType, response?.preview),
      error: unavailable ? failure.message : "",
      error_category: unavailable ? failure.category : "",
      error_owner: unavailable ? failure.error_owner : "",
      error_detail: unavailable ? failure.detail : "",
      preserved_state: unavailable ? failure.preserved_state : "",
      next_action: unavailable ? failure.next_action : "",
      creative_task: unavailable
        ? failCreativeTask(normalizeCreativeTask(response?.creative_task, localTask), failure.category, {
          error_owner: failure.error_owner,
          error_detail: failure.detail,
        })
        : normalizeCreativeTask(response?.creative_task, completeCreativeTask(localTask)),
      preview: response?.preview || null,
      provider_lineage: safeProviderLineage(response?.provider_lineage || { provider_calls_started: response?.provider_calls_started === true }),
      safe_manifest: safeEmbeddedManifest(response?.safe_manifest),
      graph_mutation: response?.graph_mutation || { mutated: false, scope: "preview_only", reason: unavailable ? "preview_unavailable" : "preview_ready" },
      latency_ms: response?.latency_ms || 0,
      cost_usd: Number(response?.cost_usd || 0),
      completed_at: new Date().toISOString(),
    };
  }, { history: false });
}

function markEmbeddedCreativeRecovering(store, nodeId, actionId, localTask) {
  store.set((state) => {
    const target = state.nodes[nodeId];
    const current = target?.params?.embeddedCreativeAction;
    if (!target || current?.action_id !== actionId || current?.status === "cancelled") return;
    target.params.embeddedCreativeAction = {
      ...current,
      status: "recovering",
      message: "连接已中断，正在恢复同一文本预览；不会再次提交。",
      creative_task: {
        ...normalizeCreativeTask(current.creative_task, localTask),
        state: "running",
        phase: "recovering",
      },
    };
  }, { history: false });
  void store.flushRuntimeSave?.();
}

async function recoverEmbeddedCreativeResponse(runtime, clientRequestId, attempts = 65) {
  if (!runtime?.recoverEmbeddedCreativeActionByClient || !clientRequestId) return null;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await runtime.recoverEmbeddedCreativeActionByClient(clientRequestId);
    } catch (error) {
      if (Number(error?.status || 0) !== 404) return null;
      if (attempt + 1 < attempts) await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  return null;
}

export function cancelEmbeddedCreativeAction(store, nodeId) {
  let cancelled = false;
  store.set((state) => {
    const node = state.nodes[nodeId];
    if (!node?.params?.embeddedCreativeAction) return;
    node.params.embeddedCreativeAction = {
      ...node.params.embeddedCreativeAction,
      status: "cancelled",
      message: "预览已取消，当前节点没有改变。",
      cancelled_at: new Date().toISOString(),
    };
    cancelled = true;
  }, { history: false });
  if (cancelled) {
    dispatchBrowserEvent("afs:embedded-creative-task-finished", {
      detail: { node_id: nodeId, status: "cancelled" },
    });
  }
}

export function clearEmbeddedCreativeAction(store, nodeId) {
  store.set((state) => {
    const node = state.nodes[nodeId];
    if (node?.params) delete node.params.embeddedCreativeAction;
  }, { history: false });
}

export async function applyEmbeddedCreativeAction(store, nodeId, runtime = null) {
  const projected = store.get()?.nodes?.[nodeId];
  const projectedAction = projected?.params?.embeddedCreativeAction;
  const revisedText = String(projectedAction?.preview?.revised_text || "").trim();
  const scriptRevisionId = String(projected?.params?.scriptRevision?.revision_id || "").trim();
  if (
    runtime?.applyEmbeddedCreativeShotPlan
    && projectedAction?.status === "preview"
    && projectedAction?.action_type === "shot_breakdown"
    && projectedAction?.preview?.shot_plan
    && projectedAction?.client_request_id
    && projectedAction?.safe_manifest?.request_digest
  ) {
    if (projectedAction.source_node_version && projectedAction.source_node_version !== nodeVersion(projected, projectedAction.source_text)) {
      markStaleEmbeddedCreativeAction(store, nodeId, projectedAction);
      return false;
    }
    store.set((state) => {
      const action = state.nodes[nodeId]?.params?.embeddedCreativeAction;
      if (action?.status !== "preview") return;
      action.status = "applying";
      action.message = "正在把已审阅分镜保存到当前制作版本。";
    }, { history: false });
    try {
      const response = await runtime.applyEmbeddedCreativeShotPlan(
        projectedAction.client_request_id,
        {
          expected_graph_version: Number(
            store.get()?.production?.production_graph_projection?.graph_version || 0,
          ),
          expected_request_digest: projectedAction.safe_manifest.request_digest,
        },
      );
      store.set((state) => {
        const action = state.nodes[nodeId]?.params?.embeddedCreativeAction;
        if (!action) return;
        action.status = "applied";
        action.message = "分镜已保存到当前制作版本。";
        action.creative_task = completeCreativeTask(action.creative_task, "applied", "applied");
        action.applied_graph_version = Number(response?.graph_version || 0);
        action.applied_graph_digest = String(response?.graph_digest || "");
        action.applied_at = new Date().toISOString();
      }, { history: false });
      await store.flushRuntimeSave?.();
      dispatchBrowserEvent("afs:production-graph-updated", {
        detail: {
          graph_version: Number(response?.graph_version || 0),
          graph_digest: String(response?.graph_digest || ""),
          workspace: response?.workspace || null,
        },
      });
      dispatchBrowserEvent("afs:embedded-creative-task-finished", {
        detail: { node_id: nodeId, status: "applied" },
      });
      return true;
    } catch (error) {
      markEmbeddedCreativeUnavailable(store, nodeId, projectedAction.action_id, {
        category: "shot_plan_apply_failed",
        error_owner: "runtime",
        message: "分镜暂时无法保存；原剧本和预览都已保留。",
        detail: safeFailureText(error?.message || ""),
        next_action: "刷新当前项目后再次应用同一预览，不会重新调用文本模型。",
      }, projectedAction.creative_task);
      await store.flushRuntimeSave?.();
      return false;
    }
  }
  if (
    runtime?.createScriptRevision
    && scriptRevisionId
    && projectedAction?.status === "preview"
    && projectedAction?.action_type === "script_revision"
    && revisedText
  ) {
    if (projectedAction.source_node_version && projectedAction.source_node_version !== nodeVersion(projected, projectedAction.source_text)) {
      markStaleEmbeddedCreativeAction(store, nodeId, projectedAction);
      return false;
    }
    store.set((state) => {
      const action = state.nodes[nodeId]?.params?.embeddedCreativeAction;
      if (action?.status !== "preview") return;
      action.status = "applying";
      action.message = "正在保存新的剧本版本；完成前当前内容不会改变。";
    }, { history: false });
    try {
      const response = await runtime.createScriptRevision({
        source_kind: "script",
        source_text: revisedText,
        parent_revision_id: scriptRevisionId,
        provenance: {
          source: "embedded_creative_action",
          action_id: projectedAction.action_id,
          mode: projectedAction.mode || "",
        },
        created_at: new Date().toISOString(),
      });
      const projection = response?.projection;
      const revisionId = String(response?.revision?.revision_id || projection?.current_revision_id || "").trim();
      if (!projection || !revisionId) throw new Error("新的剧本版本未返回可恢复投影");
      store.set((state) => {
        applyScriptCoreTruthProjection(state, projection);
        const appliedNode = state.nodes?.[`script_truth_revision_${revisionId}`];
        if (!appliedNode) return;
        appliedNode.params.embeddedCreativeAction = {
          ...projectedAction,
          status: "applied",
          message: "修订已保存为新的剧本版本；原始想法仍保留在版本记录中。",
          creative_task: completeCreativeTask(projectedAction.creative_task, "applied", "applied"),
          applied_revision_id: revisionId,
          applied_at: new Date().toISOString(),
        };
        state.selection = { nodeIds: [appliedNode.id], edgeId: null };
      });
      await store.flushRuntimeSave?.();
      dispatchBrowserEvent("afs:embedded-creative-task-finished", {
        detail: { node_id: `script_truth_revision_${revisionId}`, status: "applied" },
      });
      return true;
    } catch (error) {
      markEmbeddedCreativeUnavailable(store, nodeId, projectedAction.action_id, {
        category: "script_revision_save_failed",
        error_owner: "runtime",
        message: "修订暂时无法保存；原文和预览都已保留。",
        detail: safeFailureText(error?.message || ""),
        next_action: "检查连接后再次应用当前预览，不会重新调用文本模型。",
      }, projectedAction.creative_task);
      await store.flushRuntimeSave?.();
      return false;
    }
  }
  let applied = false;
  store.set((state) => {
    const node = state.nodes[nodeId];
    const action = node?.params?.embeddedCreativeAction;
    const preview = action?.preview || {};
    const revisedText = String(preview.revised_text || "").trim();
    if (!node || action?.status !== "preview" || !revisedText) return;
    if (action.source_node_version && action.source_node_version !== nodeVersion(node, action.source_text)) {
      markStaleEmbeddedCreativeActionInNode(node, action);
      return;
    }
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
      source_node_version: action.source_node_version || nodeVersion(node, action.source_text),
      provider_lineage: action.provider_lineage || {},
      graph_mutation: action.graph_mutation || null,
      screenplay_candidate: preview.screenplay_candidate || null,
      shot_plan: preview.shot_plan || null,
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
      const subgraph = materializeShotCandidateSubgraph(state, node, preview.shot_plan, revisionId, action);
      node.params.shotPlanDraft = subgraph.shot_plan;
      const appliedAction = {
        ...action,
        action_type: "shot_breakdown",
        applied_subgraph: subgraph,
      };
      node.params.embeddedCreativeAction = {
        ...appliedAction,
        status: "applied",
        message: appliedCreativeActionReceiptText(appliedAction),
        creative_task: completeCreativeTask(action.creative_task, "applied", "applied"),
        applied_revision_id: revisionId,
        applied_at: new Date().toISOString(),
      };
      const focusNodeId = isNarrowViewport() && subgraph.first_shot_node_id
        ? subgraph.first_shot_node_id
        : subgraph.sequence_node_id;
      state.selection = { nodeIds: [focusNodeId], edgeId: null };
      frameCandidateSubgraph(state, subgraph.created_node_ids, { focusNodeId });
      applied = true;
      return;
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
      creative_task: completeCreativeTask(action.creative_task, "applied", "applied"),
      applied_revision_id: revisionId,
      applied_at: new Date().toISOString(),
    };
    state.selection = { nodeIds: [node.id], edgeId: null };
    applied = true;
  });
  if (applied) {
    const finish = () => dispatchBrowserEvent("afs:embedded-creative-task-finished", {
      detail: { node_id: nodeId, status: "applied" },
    });
    const flush = store.flushRuntimeSave?.();
    if (flush && typeof flush.finally === "function") void flush.finally(finish);
    else finish();
  }
  return applied;
}

function markStaleEmbeddedCreativeAction(store, nodeId, action) {
  store.set((state) => {
    const node = state.nodes?.[nodeId];
    if (!node || node.params?.embeddedCreativeAction?.action_id !== action.action_id) return;
    markStaleEmbeddedCreativeActionInNode(node, action);
  }, { history: false });
}

function markStaleEmbeddedCreativeActionInNode(node, action) {
  const failure = {
    category: "stale_node_version",
    error_owner: "client_state",
    message: "当前节点已变化，请重新预览，避免把旧结果应用到新内容。",
    detail: "source node revision changed before apply",
    next_action: "保持当前节点内容，在 AI 创作搭档中重新预览。",
    preserved_state: "当前节点内容已保留；制作内容没有改变。",
  };
  node.params.embeddedCreativeAction = {
    ...action,
    status: "unavailable",
    message: failure.message,
    error: failure.message,
    error_category: failure.category,
    error_owner: failure.error_owner,
    error_detail: failure.detail,
    next_action: failure.next_action,
    preserved_state: failure.preserved_state,
    graph_mutation: { mutated: false, scope: "apply_guard", reason: "stale_node_version" },
    creative_task: failCreativeTask(action.creative_task, failure.category, {
      error_owner: failure.error_owner,
      error_detail: failure.detail,
    }),
  };
}

export function editEmbeddedCreativePreview(store, nodeId, text) {
  store.set((state) => {
    const action = state.nodes[nodeId]?.params?.embeddedCreativeAction;
    if (!action?.preview) return;
    action.preview.revised_text = String(text || "");
  }, { history: false, renderScope: "canvas-local-edit" });
}

function markEmbeddedCreativeUnavailable(store, nodeId, actionId, failureInput, task = null) {
  store.set((state) => {
    const action = state.nodes[nodeId]?.params?.embeddedCreativeAction;
    if (!action || action.action_id !== actionId || action.status === "cancelled") return;
    const failure = normalizeFailurePayload(failureInput, action.action_type);
    action.status = "unavailable";
    action.message = failure.message;
    action.error = failure.message;
    action.error_category = failure.category;
    action.error_owner = failure.error_owner;
    action.error_detail = failure.detail;
    action.next_action = failure.next_action;
    action.preserved_state = failure.preserved_state;
    action.creative_task = failCreativeTask(task || action.creative_task, failure.category, {
      error_owner: failure.error_owner,
      error_detail: failure.detail,
    });
    action.provider_lineage = failure.provider_lineage || safeProviderLineage(action.provider_lineage);
    action.graph_mutation = failure.graph_mutation || action.graph_mutation || {
      mutated: false,
      scope: "preview_only",
      reason: "task_failed_before_apply",
    };
    action.completed_at = new Date().toISOString();
  }, { history: false });
}

function failureFromPreviewResponse(response, actionType) {
  const task = response?.creative_task || {};
  const category = String(
    response?.validation_error_category
    || response?.fallback_reason
    || task.error_category
    || "task_failed",
  );
  const detail = response?.preview?.rationale || task.error_detail || response?.message || "";
  return normalizeFailurePayload({
    category,
    error_owner: task.error_owner || (category.includes("validation") ? "provider_output_validation" : "runtime"),
    message: actionType === "shot_breakdown"
      ? "动态分镜候选未生成可审预览。"
      : "节点内修订未生成可审预览。",
    detail,
    provider_lineage: safeProviderLineage(response?.provider_lineage || { provider_calls_started: response?.provider_calls_started === true }),
    graph_mutation: response?.graph_mutation || { mutated: false, scope: "preview_only", reason: "preview_unavailable" },
  }, actionType);
}

function normalizeFailurePayload(value, actionType) {
  const raw = value && typeof value === "object" ? value : { message: value };
  const category = safeCategory(raw.category || raw.error_category || "task_failed");
  const detail = safeFailureText(raw.detail || raw.error_detail || raw.message || "");
  const message = safeFailureText(raw.message || defaultFailureMessage(category, actionType));
  return {
    category,
    error_owner: safeCategory(raw.error_owner || "runtime"),
    message: message || defaultFailureMessage(category, actionType),
    detail,
    preserved_state: safeFailureText(raw.preserved_state)
      || (actionType === "shot_breakdown"
        ? "当前节点和已应用剧本已保留；制作内容没有改变。"
        : "原文已保留并可继续编辑；制作内容没有改变。"),
    next_action: safeFailureText(raw.next_action) || defaultNextAction(category, actionType),
    provider_lineage: raw.provider_lineage ? safeProviderLineage(raw.provider_lineage) : null,
    graph_mutation: raw.graph_mutation || null,
  };
}

function defaultFailureMessage(category, actionType) {
  if (category === "stale_node_version") return "当前节点版本已变化，旧预览不能应用。";
  if (category === "provider_output_validation" || category === "unsafe_or_invalid_llm_preview") {
    return actionType === "shot_breakdown" ? "AI 返回的分镜结构未通过校验。" : "AI 返回的剧本结构未通过校验。";
  }
  if (category === "timeout") return "文本优化等待超时；原文已保留。";
  return actionType === "shot_breakdown" ? "动态分镜任务失败；当前图未改变。" : "节点内修订任务失败；当前图未改变。";
}

function defaultNextAction(category, actionType) {
  if (category === "stale_node_version" || category === "studio_state_conflict") return "刷新项目状态后，从当前节点重新预览。";
  if (category === "provider_output_validation" || category === "unsafe_or_invalid_llm_preview") {
    return actionType === "shot_breakdown"
      ? "保留已扩写剧本，重新预览分镜；若再次失败，先检查场次边界。"
      : "保留原节点，重新预览剧本化修订。";
  }
  if (category === "timeout") return "可以重新运行文本优化；这次只处理文字内容。";
  return "使用 AI 创作搭档中的重新预览继续；确认前不会改动画布。";
}

function resultReadyMessage(actionType, preview) {
  if (actionType === "shot_breakdown") {
    const summary = shotPlanSummary(preview?.shot_plan);
    return `分镜候选已生成：${summary.scene_count} 场 · ${summary.shot_count} 镜头。请在右侧审阅后应用或取消。`;
  }
  const scenes = Array.isArray(preview?.screenplay_candidate?.scenes) ? preview.screenplay_candidate.scenes.length : 0;
  return scenes
    ? `剧本化预览已生成：${scenes} 场，含角色、动作与对白结构。请在右侧审阅后应用或取消。`
    : "已生成节点内预览。请在右侧比较后应用、编辑或取消。";
}

function materializeShotCandidateSubgraph(state, sourceNode, shotPlan, revisionId, action) {
  const summary = shotPlanSummary(shotPlan);
  const durationLabel = summary.provider_estimated_duration_sec
    && Math.round(summary.provider_estimated_duration_sec) !== Math.round(summary.estimated_duration_sec)
    ? `镜头合计 ${Math.round(summary.estimated_duration_sec)} 秒；计划估算 ${Math.round(summary.provider_estimated_duration_sec)} 秒`
    : `镜头合计 ${Math.round(summary.estimated_duration_sec)} 秒`;
  const candidateId = `shot_candidate_${Date.now().toString(36)}`;
  const layout = shotCandidateLayout(sourceNode, shotPlan);
  const sequenceNode = candidateNode(state, "sequence", {
    title: `分镜序列候选 · ${summary.shot_count} 镜头`,
    x: layout.sequence.x,
    y: layout.sequence.y,
    w: layout.sequence.w,
    h: layout.sequence.h,
    content: `动态分镜候选：${summary.scene_count} 场，${summary.shot_count} 镜头，${durationLabel}。`,
    status: "draft",
    params: {
      candidate_id: candidateId,
      nodeRole: "m6_6_shot_sequence_candidate",
      source_node_id: sourceNode.id,
      source_revision_id: revisionId,
      creative_task_id: action.creative_task?.task_id || action.action_id,
      shot_count: summary.shot_count,
      scene_count: summary.scene_count,
      estimated_duration_sec: summary.estimated_duration_sec,
      provider_estimated_duration_sec: summary.provider_estimated_duration_sec,
      duration_source: summary.duration_source,
      promotion_state: "candidate_preview",
      layout_role: "sequence_group_anchor",
    },
    groupId: candidateId,
  });
  const createdNodes = [sequenceNode.id];
  const createdEdges = [upsertEdge(state, sourceNode.id, sequenceNode.id, "proposed")].filter(Boolean);
  const visibleScenes = [];
  (shotPlan.scenes || []).forEach((scene, sceneIndex) => {
    const sceneLayout = layout.scene(sceneIndex, scene);
    const sceneNode = candidateNode(state, "scene", {
      title: scene.title || `场景 ${sceneIndex + 1}`,
      x: sceneLayout.x,
      y: sceneLayout.y,
      w: sceneLayout.w,
      h: sceneLayout.h,
      content: scene.purpose || "",
      status: "draft",
      params: {
        candidate_id: candidateId,
        nodeRole: "m6_6_scene_candidate",
        source_sequence_node_id: sequenceNode.id,
        source_revision_id: revisionId,
        scene_index: sceneIndex,
        purpose: scene.purpose || "",
        layout_role: "scene_lane",
      },
      groupId: candidateId,
    });
    createdNodes.push(sceneNode.id);
      createdEdges.push(upsertEdge(state, sequenceNode.id, sceneNode.id, "sequence"));
      const visibleShots = [];
      let firstShotNodeId = "";
      (scene.shots || []).forEach((shot, shotIndex) => {
        const shotLayout = layout.shot(sceneIndex, shotIndex, scene);
        const shotNode = candidateNode(state, "shot", {
        title: shot.title || `镜头 ${shotIndex + 1}`,
        x: shotLayout.x,
        y: shotLayout.y,
        w: shotLayout.w,
        h: shotLayout.h,
        content: shotContent(shot),
        status: "draft",
        params: {
          candidate_id: candidateId,
          nodeRole: "m6_6_shot_candidate",
          source_scene_node_id: sceneNode.id,
          source_revision_id: revisionId,
          scene_index: sceneIndex,
          shot_index: shotIndex,
          duration_sec: Number(shot.duration_sec || 0),
          shot_size: shot.shot_size || "",
          camera_angle: shot.camera_angle || "",
          movement: shot.movement || "",
          blocking: shot.blocking || "",
          sound: shot.sound || "",
          transition: shot.transition || "",
          narrative_purpose: shot.narrative_purpose || "",
          layout_role: "shot_grid_item",
          layout_column: shotLayout.column,
          layout_row: shotLayout.row,
          },
          groupId: candidateId,
        });
        if (!firstShotNodeId) firstShotNodeId = shotNode.id;
        createdNodes.push(shotNode.id);
        createdEdges.push(upsertEdge(state, sceneNode.id, shotNode.id, "sequence", { suppressLabel: true }));
        visibleShots.push({ ...shot, node_id: shotNode.id });
      });
    visibleScenes.push({ ...scene, node_id: sceneNode.id, shots: visibleShots, first_shot_node_id: firstShotNodeId });
  });
  const firstShotNodeId = visibleScenes.map((scene) => scene.first_shot_node_id).find(Boolean) || "";
  return {
    schema_version: "afs.m6_6.visible_shot_candidate_subgraph.v0.1",
    candidate_id: candidateId,
    source_node_id: sourceNode.id,
    source_revision_id: revisionId,
    sequence_node_id: sequenceNode.id,
    first_shot_node_id: firstShotNodeId,
    scene_count: summary.scene_count,
    shot_count: summary.shot_count,
    estimated_duration_sec: summary.estimated_duration_sec,
    created_node_ids: createdNodes,
    created_edge_ids: createdEdges.filter(Boolean),
    shot_plan: {
      ...shotPlan,
      estimated_duration_sec: summary.estimated_duration_sec,
      provider_estimated_duration_sec: summary.provider_estimated_duration_sec,
      duration_source: summary.duration_source,
      source_revision_id: revisionId,
      candidate_id: candidateId,
      scenes: visibleScenes,
      confirmed_at: new Date().toISOString(),
    },
  };
}

function shotCandidateLayout(sourceNode, shotPlan) {
  const narrow = isNarrowViewport();
  const sourceX = Number(sourceNode.x || 0);
  const sourceY = Number(sourceNode.y || 0);
  const sourceW = Number(sourceNode.w || 300);
  const sourceH = Number(sourceNode.h || 260);
  const sequenceW = narrow ? 278 : 260;
  const sequenceH = narrow ? 142 : 154;
  const sceneW = narrow ? 278 : 236;
  const sceneH = narrow ? 132 : 146;
  const sceneGap = narrow ? 82 : 88;
  const shotGridGap = narrow ? 0 : 108;
  const shotW = narrow ? 278 : 230;
  const shotH = narrow ? 148 : 146;
  const columns = narrow ? 1 : 3;
  const colGap = narrow ? 0 : 46;
  const rowGap = narrow ? 64 : 80;
  const sequence = narrow
    ? { x: sourceX + 18, y: sourceY + sourceH + 132, w: sequenceW, h: sequenceH }
    : { x: sourceX + sourceW + 150, y: sourceY, w: sequenceW, h: sequenceH };

  function rowsFor(scene) {
    return Math.max(1, Math.ceil((scene?.shots?.length || 1) / columns));
  }

  function laneHeight(scene) {
    const gridHeight = rowsFor(scene) * shotH + Math.max(0, rowsFor(scene) - 1) * rowGap;
    const sceneAndGrid = narrow ? sceneH + 58 + gridHeight : Math.max(sceneH, gridHeight);
    return Math.max(narrow ? 380 : 320, sceneAndGrid + (narrow ? 92 : 84));
  }

  function sceneOrigin(sceneIndex, scene) {
    if (narrow) {
      const previousHeight = (shotPlan.scenes || [])
        .slice(0, sceneIndex)
        .reduce((total, item) => total + laneHeight(item) + 72, 0);
      return {
        x: sequence.x + 36,
        y: sequence.y + sequence.h + sceneGap + previousHeight,
      };
    }
    const previousHeight = (shotPlan.scenes || [])
      .slice(0, sceneIndex)
      .reduce((total, item) => total + laneHeight(item) + 58, 0);
    return {
      x: sequence.x + sequence.w + sceneGap,
      y: sequence.y + previousHeight,
    };
  }

  return {
    sequence,
    scene(sceneIndex, scene) {
      const origin = sceneOrigin(sceneIndex, scene);
      return {
        x: origin.x,
        y: origin.y,
        w: sceneW,
        h: sceneH,
      };
    },
    shot(sceneIndex, shotIndex, scene) {
      const origin = sceneOrigin(sceneIndex, scene);
      const gridX = narrow ? sequence.x : origin.x + sceneW + shotGridGap;
      const gridY = origin.y + (narrow ? sceneH + 58 : 0);
      const column = shotIndex % columns;
      const row = Math.floor(shotIndex / columns);
      return {
        x: gridX + column * (shotW + colGap),
        y: gridY + row * (shotH + rowGap),
        w: shotW,
        h: shotH,
        column,
        row,
      };
    },
  };
}

function frameCandidateSubgraph(state, nodeIds, options = {}) {
  if (typeof document === "undefined") return;
  const nodes = {};
  for (const id of nodeIds || []) {
    if (state.nodes?.[id]) nodes[id] = state.nodes[id];
  }
  const bounds = nodesBounds(nodes);
  const frame = visibleCanvasFrame();
  if (!bounds || !frame.visible || frame.width < 160 || frame.height < 160) return;
  const narrow = isNarrowViewport();
  const focusNode = options.focusNodeId ? state.nodes?.[options.focusNodeId] : null;
  const floor = narrow ? 0.58 : 0.72;
  const preferred = narrow ? 0.68 : 0.78;
  const left = Math.max(0, Number(frame.safeArea?.left || 0));
  const right = Math.max(0, Number(frame.safeArea?.right || 0));
  const top = Math.max(0, Number(frame.safeArea?.top || 0));
  const bottom = Math.max(0, Number(frame.safeArea?.bottom || 0));
  const availableW = Math.max(160, frame.width - left - right);
  const availableH = Math.max(160, frame.height - top - bottom);
  if (narrow && focusNode) {
    const targetScale = clampScale(0.86);
    const focusX = Number(focusNode.x || 0) + Number(focusNode.w || 280) / 2;
    const focusY = Number(focusNode.y || 0) + Number(focusNode.h || 180) / 2;
    state.viewport = {
      scale: targetScale,
      x: left + availableW / 2 - focusX * targetScale,
      y: top + availableH * 0.48 - focusY * targetScale,
    };
    if (typeof window !== "undefined") window.__afsSuppressNextSafeAreaFit = true;
    return;
  }
  const boundsW = Math.max(1, bounds.maxX - bounds.minX);
  const boundsH = Math.max(1, bounds.maxY - bounds.minY);
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  const fitScale = clampScale(Math.min((availableW - 88) / boundsW, (availableH - 88) / boundsH, 1));
  const targetScale = clampScale(Math.min(preferred, Math.max(fitScale, floor)));
  const contentH = boundsH * targetScale;
  const y = narrow && contentH > availableH - 48
    ? top + 24 - bounds.minY * targetScale
    : top + availableH / 2 - centerY * targetScale;
  state.viewport = {
    scale: targetScale,
    x: left + availableW / 2 - centerX * targetScale,
    y,
  };
  if (typeof window !== "undefined") window.__afsSuppressNextSafeAreaFit = true;
}

function isNarrowViewport() {
  return typeof window !== "undefined" && Number(window.innerWidth || 0) <= 560;
}

function candidateNode(state, type, spec) {
  const id = nextStateId(state, "node");
  const defaults = defaultParams(type);
  const node = {
    id,
    type,
    title: spec.title,
    x: Math.round(Number(spec.x || 0)),
    y: Math.round(Number(spec.y || 0)),
    w: Math.round(Number(spec.w || 300)),
    h: Math.round(Number(spec.h || (type === "sequence" ? 230 : type === "shot" ? 250 : 240))),
    prompt: spec.content || "",
    content: spec.content || "",
    params: { ...defaults, ...(spec.params || {}) },
    status: spec.status || "draft",
    result: null,
    groupId: spec.groupId || null,
    collapsed: false,
  };
  state.nodes[id] = node;
  state.order = [...(state.order || []), id];
  return node;
}

function nextStateId(state, prefix) {
  state.meta = state.meta || {};
  state.meta.seq = Number(state.meta.seq || 1) + 1;
  return `${prefix}_${state.meta.seq}`;
}

function upsertEdge(state, fromId, toId, relationType, options = {}) {
  if (!fromId || !toId || fromId === toId) return "";
  const existing = Object.values(state.edges || {}).find((edge) => edge.from === fromId && edge.to === toId);
  if (existing) {
    existing.relation_type = relationType;
    existing.suppress_label = options.suppressLabel === true;
    return existing.id;
  }
  const id = uniqueEdgeId(state, fromId, toId);
  state.edges[id] = { id, from: fromId, to: toId, relation_type: relationType, suppress_label: options.suppressLabel === true };
  state.ui = state.ui || {};
  state.ui.lastConnectedEdgeId = id;
  return id;
}

function uniqueEdgeId(state, fromId, toId) {
  const base = `edge_${fromId}__${toId}`;
  if (!state.edges?.[base]) return base;
  let suffix = 2;
  while (state.edges?.[`${base}_${suffix}`]) suffix += 1;
  return `${base}_${suffix}`;
}

function shotContent(shot) {
  return [
    `${Number(shot.duration_sec || 0)} 秒 · ${shot.shot_size || "景别待定"} · ${shot.camera_angle || "机位待定"}`,
    `${shot.movement || "运动待定"} · ${shot.transition || "转场待定"}`,
    `目的：${compactShotText(shot.narrative_purpose || shot.blocking || "补足叙事目的")}`,
  ].join("\n");
}

function compactShotText(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > 34 ? `${text.slice(0, 34)}…` : text;
}

function sourceTextForNode(node) {
  return String(
    node?.params?.scriptRevision?.source_text
    || node?.content
    || node?.prompt
    || node?.result
    || "",
  ).trim();
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

function dispatchBrowserEvent(name, options) {
  if (typeof window === "undefined" || typeof window.dispatchEvent !== "function") return;
  if (typeof CustomEvent === "undefined") return;
  window.dispatchEvent(new CustomEvent(name, options));
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
    provider_dispatch_count: Number(value.provider_dispatch_count || 0),
    external_paid_cost_usd: Number(value.external_paid_cost_usd || 0),
  };
}

function safeEmbeddedManifest(value) {
  return {
    request_digest: String(value?.request_digest || "").slice(0, 64),
    source_digest: String(value?.source_digest || "").slice(0, 64),
    provider_dispatch_count: Number(value?.provider_dispatch_count || 0),
    image_video_generation_enabled: value?.image_video_generation_enabled === true,
  };
}

function safeEmbeddedActionError(error, actionType) {
  const text = String(error?.message || error || "");
  const category = /timeout|timed out|超时/i.test(text)
    ? "timeout"
    : /studio_state_conflict|version conflict|版本冲突/i.test(text)
    ? "studio_state_conflict"
    : /validation|schema|parse|invalid|校验|结构/i.test(text)
    ? "provider_output_validation"
    : "task_failed";
  return normalizeFailurePayload({
    category,
    error_owner: category === "provider_output_validation" ? "provider_output_validation" : "runtime",
    message: defaultFailureMessage(category, actionType),
    detail: text || "embedded creative action failed",
  }, actionType);
}

function safeFailureText(value) {
  return String(value || "")
    .replace(/\bBearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/\/(?:home|Users|mnt|var|tmp|opt)\/[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 420);
}

function safeCategory(value) {
  return String(value || "").replace(/[^A-Za-z0-9_.:-]/g, "_").trim().slice(0, 120) || "task_failed";
}
