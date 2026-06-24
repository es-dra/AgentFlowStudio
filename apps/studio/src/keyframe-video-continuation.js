import { createNode, connect } from "./nodes.js";
import { lastImageAsset, mergeImageAssets } from "./node-image-assets.js";
import { VIDEO_RATIOS } from "./presets/specs.js";

export function canContinueKeyframeToVideo(node) {
  return Boolean(isKeyframeLikeNode(node));
}

export function createVideoNodeFromKeyframe(store, keyframeNode) {
  const state = store.get();
  const source = state.nodes?.[keyframeNode?.id] || keyframeNode;
  if (!source || !isKeyframeLikeNode(source)) return null;
  const frameAsset = keyframeFirstFrameAsset(state, source);
  if (!frameAsset?.asset_id) {
    markMissingFirstFrame(store, source.id);
    return null;
  }

  const video = createNode(
    store,
    "video",
    Number(source.x || 0) + Number(source.w || 280) + 180,
    Number(source.y || 0),
  );
  store.set((s) => {
    const node = s.nodes[video.id];
    if (!node) return;
    node.title = videoTitle(source);
    node.prompt = videoPrompt(source);
    node.status = "empty";
    node.previewUrl = null;
    node.result = "已从上游关键帧创建图生视频节点。关键帧图片已设为首帧。";
    node.params = {
      ...node.params,
      nodeRole: "video_generation",
      sourceKeyframeNodeId: source.id,
      sourceKeyframeJobId: source.params?.lastKeyframeJobId || null,
      sourceKeyframeAssetId: frameAsset.asset_id,
      firstFrameImageAssetId: frameAsset.asset_id,
      firstFramePreviewUrl: frameAsset.preview_url || source.previewUrl || "",
      motion: node.params?.motion || "轻微推进，保留对峙张力和呼吸感镜头。",
      spec: {
        ...(node.params?.spec || {}),
        ratio: supportedVideoRatio(source.params?.spec?.ratio || node.params?.spec?.ratio),
        resolution: node.params?.spec?.resolution || "720P",
        duration: node.params?.spec?.duration || "5s",
        count: 1,
        mode: "图生视频",
      },
      uploads: mergeImageAssets(node.params?.uploads || [], {
        ...frameAsset,
        role: "first_frame",
        source_role: frameAsset.role || frameAsset.source_role || null,
      }).slice(-4),
      videoAssetRecognition: {
        status: "pending_video_generation",
        source: "generated_video",
        source_keyframe_node_id: source.id,
        source_first_frame_image_asset_id: frameAsset.asset_id,
      },
    };
  });
  connect(store, source.id, video.id);
  return store.get().nodes[video.id] || video;
}

export function keyframeFirstFrameAsset(state, node) {
  return normalizeImageAssetRef(lastImageAsset(node), node)
    || latestReadyImageAssetFromNode(state, node?.id)
    || null;
}

function isKeyframeLikeNode(node) {
  return node?.type === "image" && (
    node.params?.nodeRole === "keyframe_generation"
    || Boolean(node.params?.keyframeLayer)
    || Boolean(node.params?.lastKeyframeJobId)
  );
}

function latestReadyImageAssetFromNode(state, sourceNodeId) {
  if (!sourceNodeId) return null;
  const assets = (Array.isArray(state.assets) ? state.assets : [])
    .filter((asset) =>
      asset?.source_node_id === sourceNodeId
      && asset?.asset_id
      && (!asset.status || asset.status === "ready")
      && ["keyframe", "image_reference"].includes(asset.kind),
    )
    .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
  return normalizeImageAssetRef(assets[0], state.nodes?.[sourceNodeId]);
}

function normalizeImageAssetRef(asset, node) {
  const assetId = String(asset?.asset_id || asset?.assetId || "").trim();
  if (!assetId) return null;
  return {
    ...asset,
    asset_id: assetId,
    filename: asset.filename || asset.title || `${assetId}.png`,
    preview_url: asset.preview_url || asset.previewUrl || node?.previewUrl || "",
    width: asset.width || null,
    height: asset.height || null,
    aspect_ratio: asset.aspect_ratio || asset.aspectRatio || node?.params?.previewAspectRatio || null,
  };
}

function supportedVideoRatio(ratio) {
  const value = String(ratio || "16:9").trim();
  return VIDEO_RATIOS.includes(value) ? value : "16:9";
}

function videoTitle(source) {
  const suffix = String(source.title || source.id || "关键帧")
    .replace(/^关键帧\s*[·.-]\s*/u, "")
    .slice(0, 36);
  return `视频 · ${suffix}`;
}

function videoPrompt(source) {
  const sourcePrompt = String(source.prompt || source.result || "").trim();
  const excerpt = sourcePrompt.length > 520 ? `${sourcePrompt.slice(0, 520)}...` : sourcePrompt;
  return [
    "基于上游关键帧生成 5 秒图生视频，保持关键帧画面连续。",
    "Maintain exact character identity, wardrobe, prop geometry, scene layout, camera composition, and lighting.",
    "Do not introduce new characters, extra props, text, watermark, UI, or borders.",
    "动作：延续当前对峙或动作关系，轻微推进或呼吸感镜头，避免大幅改变构图。",
    excerpt ? `上游关键帧提示：${excerpt}` : "",
  ].filter(Boolean).join("\n");
}

function markMissingFirstFrame(store, nodeId) {
  store.set((s) => {
    const node = s.nodes?.[nodeId];
    if (!node) return;
    node.result = [
      node.result || "",
      "无法接续视频节点：当前关键帧缺少可作为首帧的图像资产。请先重新生成关键帧，或上传/替换一张可用参考图。",
    ].filter(Boolean).join("\n");
  });
}
