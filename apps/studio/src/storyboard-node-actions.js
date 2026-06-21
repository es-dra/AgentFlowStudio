import { setNodeError } from "./node-action-utils.js";
import { ensureShotAssetPrepNodesForScriptNode } from "./shot-asset-nodes.js";
import { createKeyframeNodesForStoryboard } from "./storyboard-keyframes.js";

export function identifyScriptAssets(store, node) {
  const created = ensureShotAssetPrepNodesForScriptNode(store, node);
  if (!created.length) {
    setNodeError(store, node.id, "当前分镜没有识别到可拆出的角色、场景或道具资产。");
  }
  return created;
}

export function createStoryboardKeyframeLayer(store, node) {
  const fresh = store.get().nodes[node.id] || node;
  const assetIds = ensureShotAssetPrepNodesForScriptNode(store, fresh);
  if (!assetIds.length) {
    setNodeError(store, fresh.id, "请先识别资产，再生成关键帧层。");
    return [];
  }
  return createKeyframeNodesForStoryboard(store, fresh);
}
