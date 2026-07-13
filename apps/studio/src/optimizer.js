import { buildOptimizationRequest, normalizeOptimization } from "./optimizer-contract.js";
import { connect } from "./nodes.js";
import { humanWarning } from "./node-result-view.js";
import { buildAssetReferenceActions } from "./asset-reference-inspector.js";
import { assetCardUserAdjustmentText } from "./asset-card-image-prompts.js";
import { buildUserAssetCardRevisionState } from "./asset-revision-references.js";
import { formatRuntimeError } from "./runtime-error-utils.js";
import { flashTooltip } from "./prompt-bar-actions.js";

const CONNECT_NAMED_ASSET_ACTION = "connect-named-asset";
const TEMPORARY_UNLOCK_ACTION = "temporary-unlock";

// Prompt optimization is node-scoped. It keeps running even if selection moves.
export async function openOptimizer(store, runtime, nodeId, anchorEl = null, textarea = null) {
  syncTextareaPromptToNode(store, nodeId, textarea);
  const node = store.get().nodes[nodeId];
  if (!node || !runtime?.optimizePrompt) return;
  const request = buildOptimizationRequest(store.get(), node);
  const assetInstruction = assetCardUserAdjustmentText(node);
  if (node.params?.assetCardDraft && assetInstruction) request.prompt_text = assetInstruction;
  setPromptOptimizationState(store, nodeId, {
    status: "running",
    percent: 12,
    label: "提示词优化",
    started_at: new Date().toISOString(),
  });
  setOptimizerControlState(anchorEl, true);
  textarea?.classList?.add("prompt-shimmer");
  try {
    const result = await runtime.optimizePrompt(request);
    const outcome = normalizeOptimization(result, request);
    const before = assetCardUserAdjustmentText(node) || String(node.prompt || node.content || "").trim();
    applyPrompt(store, nodeId, outcome.optimized, outcome.plain || outcome.optimized, textarea);
    recordOptimizationEvidence(store, nodeId, outcome);
    setPromptOptimizationState(store, nodeId, {
      status: "complete",
      percent: 100,
      completed_at: new Date().toISOString(),
      summary: optimizationSummary(request, outcome),
      model_call_context_id: outcome.model_call_context_id || "",
      model_call_context_summary: outcome.model_call_context_summary || null,
      creative_runtime_contract_id: outcome.creative_runtime_contract_id || "",
      creative_runtime_contract_summary: outcome.creative_runtime_contract_summary || null,
    });
    const after = assetCardUserAdjustmentText(store.get().nodes[nodeId]) || outcome.optimized;
    showOptimizerFeedback(anchorEl, normalizeComparablePrompt(after) === normalizeComparablePrompt(before)
      ? "已是当前可用版本"
      : "优化完成");
  } catch (error) {
    const message = safeError(error);
    setPromptOptimizationState(store, nodeId, {
      status: "error",
      percent: 100,
      completed_at: new Date().toISOString(),
      message,
    });
    showOptimizerFeedback(anchorEl, message);
  } finally {
    textarea?.classList?.remove("prompt-shimmer");
    setOptimizerControlState(anchorEl, false);
  }
}

function applyPrompt(store, nodeId, text, plainText, textarea) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.params = node.params || {};
    node.prompt = text;
    if (node.params?.assetCardDraft) {
      node.params.assetCardDraft.user_edited_text = text;
      node.params.assetCardDraft.updated_by_user = Boolean(String(text || "").trim());
      node.params.assetCardRevision = buildUserAssetCardRevisionState(
        node,
        node.params.assetCardDraft,
        text,
        node.params.assetReferenceMode,
      );
    }
    if (isTextContentNode(node)) {
      node.content = text;
      node.status = node.status === "empty" ? "complete" : node.status;
    }
    node.params.lastOptimizedPromptPlain = plainText || stripSectionHeaders(text);
  });
  if (textarea && store.get().nodes[nodeId]) textarea.value = text;
}

function syncTextareaPromptToNode(store, nodeId, textarea) {
  const value = String(textarea?.value || "");
  if (!textarea || !value.trim()) return;
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.params = node.params || {};
    node.prompt = value;
    if (node.params?.assetCardDraft) {
      node.params.assetCardDraft.user_edited_text = value;
      node.params.assetCardDraft.updated_by_user = true;
      node.params.assetCardRevision = buildUserAssetCardRevisionState(
        node,
        node.params.assetCardDraft,
        value,
        node.params.assetReferenceMode,
      );
    } else if (isTextContentNode(node)) {
      node.content = value;
    }
    delete node.params.lastOptimizedPromptPlain;
  }, { history: false });
}

function recordOptimizationEvidence(store, nodeId, outcome) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.params = node.params || {};
    if (outcome.context_bundle) node.params.lastContextBundle = outcome.context_bundle;
    if (outcome.model_call_context_id) node.params.lastModelCallContextId = outcome.model_call_context_id;
    if (outcome.model_call_context_summary) node.params.lastModelCallContextSummary = outcome.model_call_context_summary;
    if (outcome.creative_runtime_contract_id) {
      node.params.lastCreativeRuntimeContractId = outcome.creative_runtime_contract_id;
    }
    if (outcome.creative_runtime_contract_summary) {
      node.params.lastCreativeRuntimeContractSummary = outcome.creative_runtime_contract_summary;
    }
  }, { history: false, persist: true });
}

function isTextContentNode(node) {
  return node.type === "text" || node.type === "script";
}

function setPromptOptimizationState(store, nodeId, patch) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.params.promptOptimizationState = {
      ...(node.params.promptOptimizationState || {}),
      ...patch,
    };
  }, { history: false, persist: patch.status !== "running" });
}

function optimizationSummary(request, outcome) {
  const warnings = outcome?.context_bundle?.warnings || [];
  return {
    sources: optimizationSources(request, outcome),
    action_ids: {
      connect_named_asset: CONNECT_NAMED_ASSET_ACTION,
      temporary_unlock: TEMPORARY_UNLOCK_ACTION,
      temporary_overrides_field: "temporaryLockOverrides",
      available_asset_hint: "未引用 · 可连线",
    },
    asset_actions: buildAssetReferenceActions({ warnings }).map((action) => action.warning || action),
    lock_warnings: uniqueLockWarnings(warnings).map(humanWarning),
  };
}

function optimizationSources(request, outcome = null) {
  const labels = [optimizationModeLabel(outcome?.optimization_mode), "影视结构"].filter(Boolean);
  if (request.style) labels.push("项目风格");
  if (request.director_setup) labels.push("导演台布置");
  if (request.asset_refs?.length) labels.push("角色/场景设定");
  return labels;
}

function optimizationModeLabel(mode) {
  if (mode === "t2i") return "文生图扩写";
  if (mode === "i2i") return "图生图编辑";
  if (mode === "text") return "文本结构化";
  return "";
}

function uniqueLockWarnings(warnings) {
  const seen = new Set();
  const result = [];
  for (const warning of warnings.filter((item) => item.warning_id === "best_effort_lock_conflict")) {
    const key = `${warning.asset_id || ""}::${warning.lock_text || ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(warning);
  }
  return result;
}

function connectNamedAssetToTarget(store, nodeId, assetId) {
  const state = store.get();
  const source = Object.values(state.nodes).find((item) => item.id !== nodeId && hasVisualAsset(item, assetId));
  if (!source || !state.nodes[nodeId]) return false;
  connect(store, source.id, nodeId);
  return true;
}

function hasVisualAsset(node, assetId) {
  const values = [
    ...(Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : []),
    ...(Array.isArray(node?.params?.visual_asset_ids) ? node.params.visual_asset_ids : []),
  ];
  return values.some((item) => String(item?.asset_id || item?.assetId || item || "") === String(assetId || ""));
}

function stripSectionHeaders(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*(意图|角色|角色\/主体|人物|人物\/主体|主体|场景|场景\/美术|镜头|镜头\/构图|灯光|运动|运动\/时间推进|连续性|负面|负面约束)\s*[：:]\s*/, "").trim())
    .filter(Boolean)
    .join("\n");
}

function setOptimizerControlState(anchorEl, running) {
  if (!anchorEl) return;
  anchorEl.classList?.toggle?.("busy", running);
  if ("disabled" in anchorEl) anchorEl.disabled = running;
  const label = anchorEl.querySelector?.("span");
  if (label) label.textContent = running ? "优化中..." : "优化";
}

function showOptimizerFeedback(anchorEl, message) {
  if (!anchorEl || !message) return;
  try {
    if (typeof document === "undefined" || !document.getElementById("overlay-root")) return;
    if (!anchorEl.getBoundingClientRect) return;
    flashTooltip(anchorEl, message);
  } catch {
    // Feedback is best-effort; node promptOptimizationState still records the result.
  }
}

function normalizeComparablePrompt(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function safeError(error) {
  return formatRuntimeError(error, "提示词优化失败，请稍后重试。");
}
