import { isRemoteImageModel, isRemoteVideoModel } from "./presets/models.js";
import { setNodeError } from "./node-action-utils.js";
import { startRemoteKeyframeGeneration } from "./node-keyframe-actions.js";
import { startRemoteVideoGeneration, startRemoteVideoRevision } from "./node-video-actions.js";

export function canStartGenerationForNode(node) {
  return ["image", "video"].includes(node?.type);
}

// Ctrl+Enter / send button: only image and video nodes can trigger real generation.
export async function startNodeGeneration(store, runtime, node, resultText) {
  const fresh = store.get().nodes[node.id] || node;
  if (!canStartGenerationForNode(fresh)) {
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
