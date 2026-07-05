import { createNode, connect } from "./nodes.js";
import { isRemoteImageModel, isRemoteVideoModel } from "./presets/models.js";
import { SAMPLE_SCRIPT, SAMPLE_SCRIPT_TITLE } from "./presets/starters.js";
import { openVisualAssetPanel } from "./panels/visual-asset-panel.js";
import { imageAssetFromVisualAsset, lastImageAsset } from "./node-image-assets.js";
import { setNodeError } from "./node-action-utils.js";
import { startRemoteKeyframeGeneration } from "./node-keyframe-actions.js";
import { startRemoteVideoGeneration, startRemoteVideoRevision } from "./node-video-actions.js";
import { importScriptFileIntoTextNode, splitTextNodeToStoryboardNodes } from "./script-breakdown.js";
import { createStoryboardKeyframeLayer, identifyScriptAssets } from "./storyboard-node-actions.js";

export { uploadNodeImage } from "./node-upload-actions.js";
export { visibleAssetForNode } from "./node-visible-assets.js";
export { createStoryboardKeyframeLayer, identifyScriptAssets } from "./storyboard-node-actions.js";
export { createKeyframeLocalEditDraft } from "./keyframe-local-edit-contract.js";
export { pollNodeKeyframeGeneration } from "./node-keyframe-actions.js";
export { cancelNodeVideoGeneration, enableVideoRevisionDraft, pollNodeVideoGeneration, setNodeVideoFrame } from "./node-video-actions.js";

export function canRunNodeGeneration(node) {
  return ["image", "video"].includes(node?.type);
}

// Empty-state intent: script starter lays out a safe local upstream example flow.
export function handleNodeIntent(store, node, intent) {
  if (node.type === "text" && intent === "上传完整剧本") {
    importScriptFileIntoTextNode(store, node);
    return;
  }
  if (node.type === "text" && intent === "想法扩写剧本") {
    setNodeError(store, node.id, "请先在底部输入想法，再点击扩写剧本。");
    return;
  }
  if (node.type === "text" && intent === "剧本拆分分镜") {
    splitTextNodeToStoryboardNodes(store, node).then((created) => {
      if (!created.length) setNodeError(store, node.id, "请先输入或导入完整剧本，再拆分分镜。");
    });
    return;
  }
  if (node.type === "script" && intent === "剧本生成分镜脚本") {
    spawnSampleScriptFlow(store, node);
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

export function spawnSampleScriptFlow(store, scriptNode) {
  const textNode = createNode(store, "text", scriptNode.x - 420, scriptNode.y + 140);
  const groupId = store.nextId("group");
  store.set((s) => {
    const t = s.nodes[textNode.id];
    t.title = "文本";
    t.content = SAMPLE_SCRIPT;
    t.h = 320;
    t.status = "complete";
    const sc = s.nodes[scriptNode.id];
    sc.params.attachments = [{ id: textNode.id, label: SAMPLE_SCRIPT_TITLE }];
    s.groups[groupId] = {
      id: groupId,
      title: `预设 - ${SAMPLE_SCRIPT_TITLE}`,
      nodeIds: [scriptNode.id, textNode.id],
    };
    t.groupId = groupId;
    sc.groupId = groupId;
    s.selection = { nodeIds: [scriptNode.id], edgeId: null };
  });
  connect(store, textNode.id, scriptNode.id);
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

// 发送（Ctrl+Enter / 发送按钮）：当前只允许图片/视频节点触发真实生成。
export async function startNodeGeneration(store, runtime, node, resultText) {
  const fresh = store.get().nodes[node.id] || node;
  if (!canRunNodeGeneration(fresh)) {
    setNodeError(
      store,
      fresh.id,
      resultText || "当前节点不支持直接生成。请使用该节点菜单里的专用操作，或连接到图片/视频节点后生成。",
    );
    return;
  }
  if (fresh.type === "image" && isRemoteImageModel(fresh.params?.model) && runtime?.generateKeyframe) {
    await startRemoteKeyframeGeneration(store, runtime, fresh);
    return;
  }
  if (fresh.type === "video" && isRemoteVideoModel(fresh.params?.model) && runtime?.generateVideo) {
    if (fresh.params?.videoRevision?.enabled && runtime?.generateVideoRevision) {
      await startRemoteVideoRevision(store, runtime, fresh);
      return;
    }
    await startRemoteVideoGeneration(store, runtime, fresh);
    return;
  }
  setNodeError(
    store,
    fresh.id,
    resultText || "当前节点不支持直接生成，请使用该节点的专用操作。",
  );
}
