import { buildOptimizationRequest, normalizeOptimization } from "./optimizer-contract.js";
import { connect } from "./nodes.js";
import { humanWarning } from "./node-result-view.js";
import { buildAssetReferenceActions } from "./asset-reference-inspector.js";

const CONNECT_NAMED_ASSET_ACTION = "connect-named-asset";
const TEMPORARY_UNLOCK_ACTION = "temporary-unlock";

// Prompt optimization is node-scoped. It keeps running even if selection moves.
export async function openOptimizer(store, runtime, nodeId, _anchorEl = null, textarea = null) {
  const node = store.get().nodes[nodeId];
  if (!node || !runtime?.optimizePrompt) return;
  const request = buildOptimizationRequest(store.get(), node);
  setPromptOptimizationState(store, nodeId, { status: "running", started_at: new Date().toISOString() });
  textarea?.classList?.add("prompt-shimmer");
  try {
    const result = await runtime.optimizePrompt(request);
    const outcome = normalizeOptimization(result, request);
    applyPrompt(store, nodeId, outcome.optimized, outcome.plain || outcome.optimized, textarea);
    setPromptOptimizationState(store, nodeId, {
      status: "complete",
      completed_at: new Date().toISOString(),
      summary: optimizationSummary(request, outcome),
    });
  } catch (error) {
    setPromptOptimizationState(store, nodeId, {
      status: "error",
      completed_at: new Date().toISOString(),
      message: safeError(error),
    });
  } finally {
    textarea?.classList?.remove("prompt-shimmer");
  }
}

function applyPrompt(store, nodeId, text, plainText, textarea) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.prompt = text;
    node.params.lastOptimizedPromptPlain = plainText || stripSectionHeaders(text);
  });
  if (textarea && store.get().nodes[nodeId]) textarea.value = text;
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

function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  const clean = message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>");
  if (/provider service not found|remote LLM prompt optimization unavailable|AFS_ALLOW_REMOTE_LLM/i.test(clean)) {
    return "提示词优化服务未就绪，请检查 LLM provider 配置与 Runtime 启动环境后重试。";
  }
  return clean.slice(0, 180);
}
