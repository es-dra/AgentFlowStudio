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
  return createKeyframeNodesForStoryboard(store, fresh);
}
