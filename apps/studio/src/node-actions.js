import { createNode, connect } from "./nodes.js";
import { isRemoteImageModel, isRemoteVideoModel } from "./presets/models.js";
import { SAMPLE_SCRIPT, SAMPLE_SCRIPT_TITLE } from "./presets/starters.js";
import { openVisualAssetPanel } from "./panels/visual-asset-panel.js";
import { lastImageAsset } from "./node-image-assets.js";
import { setNodeError } from "./node-action-utils.js";
import { startRemoteKeyframeGeneration } from "./node-keyframe-actions.js";
import { startRemoteVideoGeneration, startRemoteVideoRevision } from "./node-video-actions.js";

export { uploadNodeImage } from "./node-upload-actions.js";
export { visibleAssetForNode } from "./node-visible-assets.js";
export { pollNodeKeyframeGeneration } from "./node-keyframe-actions.js";
export {
  cancelNodeVideoGeneration,
  enableVideoRevisionDraft,
  pollNodeVideoGeneration,
  setNodeVideoFrame,
} from "./node-video-actions.js";

// Empty-state intent: script starter lays out a safe local upstream example flow.
export function handleNodeIntent(store, node, intent) {
  if (node.type === "script" && intent === "剧本生成分镜脚本") {
    spawnSampleScriptFlow(store, node);
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
  const imageAsset = lastImageAsset(node);
  openVisualAssetPanel({ store, runtime, node, imageAsset });
}

// 发送（Ctrl+Enter / 发送按钮）：当前 MVP 只允许图片节点触发真实 keyframe。
export async function startNodeGeneration(store, runtime, node, resultText) {
  const fresh = store.get().nodes[node.id] || node;
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
    resultText || "当前版本仅图片节点支持真实生成；视频、音频、脚本和合成通道仍在开发中。",
  );
}
