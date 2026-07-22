import { openVisualAssetPanel } from "./panels/visual-asset-panel.js";
import { imageAssetFromVisualAsset, lastImageAsset } from "./node-image-assets.js";
import { safeError } from "./node-action-utils.js";
import { canStartGenerationForNode, startNodeGeneration as runNodeGeneration } from "./node-generation-actions.js";
import { importScriptFileIntoTextNode } from "./script-breakdown.js";
import { createStoryboardKeyframeLayer, identifyScriptAssets } from "./storyboard-node-actions.js";
import {
  createKeyframeLocalEditDraft as createStudioLocalKeyframeLocalEditDraft,
  recordKeyframeLocalEditRuntimePreflight,
  recordKeyframeLocalEditRuntimePreflightError,
} from "./keyframe-local-edit-contract.js";

export { uploadNodeImage } from "./node-upload-actions.js";
export { visibleAssetForNode } from "./node-visible-assets.js";
export { createStoryboardKeyframeLayer, identifyScriptAssets } from "./storyboard-node-actions.js";
export { pollNodeKeyframeGeneration } from "./node-keyframe-actions.js";
export { cancelNodeVideoGeneration, enableVideoRevisionDraft, pollNodeVideoGeneration, setNodeVideoFrame } from "./node-video-actions.js";

export function canRunNodeGeneration(node) {
  return canStartGenerationForNode(node);
}

// Empty-state intents only select a real input path; story planning and text rewrites go through AI 创作搭档.
export function handleNodeIntent(store, node, intent) {
  if (node.type === "text" && intent === "上传完整剧本") {
    importScriptFileIntoTextNode(store, node);
    return;
  }
  if (node.type === "script" && intent === "识别资产") {
    identifyScriptAssets(store, null, node);
    return;
  }
  if (node.type === "script" && intent === "生成关键帧层") {
    createStoryboardKeyframeLayer(store, node);
    return;
  }
  store.set((s) => {
    const target = s.nodes[node.id];
    if (target) target.params.intent = intent;
    s.selection = { nodeIds: [node.id], edgeId: null };
  });
}

export function fixNodeVisualAsset(store, runtime, node) {
  const existingAsset = lastFixedVisualAsset(node);
  const imageAsset = lastImageAsset(node) || imageAssetFromVisualAsset(existingAsset);
  const initialAssetType = existingAsset?.asset_type || node.params?.assetCardDraft?.asset_type || "character";
  openVisualAssetPanel({
    store,
    runtime,
    node,
    imageAsset,
    initialAssetType,
    existingAsset,
  });
}

export function lastFixedVisualAsset(node) {
  const assets = Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : [];
  return [...assets].reverse().find((asset) => ["fixed", "ready", ""].includes(String(asset?.status || ""))) || null;
}

export async function createKeyframeLocalEditDraft(store, runtime, node, options = {}) {
  const draft = createStudioLocalKeyframeLocalEditDraft(store, node, options);
  if (!draft) return null;
  if (!runtime?.preflightKeyframeLocalEdit) {
    await store.flushRuntimeSave?.();
    return draft;
  }
  try {
    const runtimePreflight = await runtime.preflightKeyframeLocalEdit(draft.request);
    const updated = recordKeyframeLocalEditRuntimePreflight(store, node.id, runtimePreflight);
    await store.flushRuntimeSave?.();
    return updated || draft;
  } catch (error) {
    const updated = recordKeyframeLocalEditRuntimePreflightError(store, node.id, safeError(error));
    await store.flushRuntimeSave?.();
    return updated || draft;
  }
}

// 发送（Ctrl+Enter / 发送按钮）：图片/视频生成调度实现位于 node-generation-actions.js。
export async function startNodeGeneration(store, runtime, node, resultText) {
  return runNodeGeneration(store, runtime, node, resultText);
}
