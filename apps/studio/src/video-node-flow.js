import { imageAssetFromVisualAsset, lastImageAsset, mergeImageAssets } from "./node-image-assets.js";

const VIDEO_AUTO_POLL_INTERVAL_MS = 12000;
const VIDEO_AUTO_POLL_MAX_ATTEMPTS = 80;
const videoAutoPollTimers = new Map();

export function ensureVideoFirstFrameAsset(store, node) {
  const explicit = String(node?.params?.firstFrameImageAssetId || "").trim();
  if (explicit) {
    const selected = explicitFirstFrameSource(node, explicit);
    persistVideoInputSource(store, node, selected);
    return selected;
  }
  const directUpload = directUploadedFirstFrameAsset(node);
  if (directUpload?.asset_id) {
    persistInferredFirstFrame(store, node, directUpload, `已自动使用本节点上传图片作为首帧: ${directUpload.asset_id}`);
    return directUpload;
  }
  const directVisual = firstFrameAssetFromVisualAssets(node);
  if (directVisual?.asset_id) {
    persistInferredFirstFrame(store, node, directVisual, `已自动使用参考资产作为首帧: ${directVisual.asset_id}`);
    return directVisual;
  }
  const inferred = inferConnectedFirstFrameAsset(store, node);
  if (!inferred?.asset_id) return null;
  persistInferredFirstFrame(store, node, inferred, `已自动使用上游关键帧作为首帧: ${inferred.asset_id}`);
  return inferred;
}

function persistInferredFirstFrame(store, node, inferred, result) {
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.params.firstFrameImageAssetId = inferred.asset_id;
    if (inferred.preview_url) n.params.firstFramePreviewUrl = inferred.preview_url;
    n.params.videoInputSource = videoInputSourceFromAsset(inferred, node);
    n.params.uploads = mergeImageAssets(n.params.uploads || [], {
      ...inferred,
      role: "first_frame",
    }).slice(-4);
    n.result = result;
  });
}

function persistVideoInputSource(store, node, inferred) {
  if (!inferred?.asset_id) return;
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.params.videoInputSource = videoInputSourceFromAsset(inferred, n);
  });
}

export function scheduleVideoAutoPoll({
  store,
  runtime,
  nodeId,
  response,
  applyVideoResponse,
  setNodeError,
  safeError,
  attempts = 0,
}) {
  const status = response?.job?.status || "blocked";
  if (!["submitted", "running"].includes(status)) {
    clearVideoAutoPoll(nodeId);
    return;
  }
  if (!runtime?.pollVideo || attempts >= VIDEO_AUTO_POLL_MAX_ATTEMPTS) return;
  const fresh = store.get().nodes[nodeId];
  const jobId = response?.job?.job_id || fresh?.params?.lastVideoJobId;
  if (!jobId) return;
  const existing = videoAutoPollTimers.get(nodeId);
  if (existing?.jobId === jobId && existing?.timer) return;
  clearVideoAutoPoll(nodeId);
  const timer = globalThis.setTimeout(async () => {
    videoAutoPollTimers.delete(nodeId);
    const current = store.get().nodes[nodeId];
    if (!current || current.status !== "generating" || current.params?.lastVideoJobId !== jobId) return;
    try {
      const next = await runtime.pollVideo(jobId);
      applyVideoResponse(store, nodeId, next);
      await store.flushRuntimeSave?.();
      scheduleVideoAutoPoll({ store, runtime, nodeId, response: next, applyVideoResponse, setNodeError, safeError, attempts: attempts + 1 });
    } catch (error) {
      setNodeError(store, nodeId, `视频进度刷新失败：${safeError(error)}`);
      await store.flushRuntimeSave?.();
    }
  }, VIDEO_AUTO_POLL_INTERVAL_MS);
  videoAutoPollTimers.set(nodeId, { jobId, timer });
}

export function clearVideoAutoPoll(nodeId) {
  const existing = videoAutoPollTimers.get(nodeId);
  if (existing?.timer) globalThis.clearTimeout(existing.timer);
  videoAutoPollTimers.delete(nodeId);
}

function inferConnectedFirstFrameAsset(store, node) {
  const state = store.get();
  const incoming = Object.values(state.edges || {})
    .filter((edge) => edge?.to === node?.id)
    .reverse();
  for (const edge of incoming) {
    const upstream = state.nodes?.[edge.from];
    const asset = lastImageAsset(upstream);
    if (asset?.asset_id) return normalizeImageAssetRef(asset, sourceModeForUpstreamNode(upstream), upstream);
  }
  for (const edge of incoming) {
    const upstream = state.nodes?.[edge.from];
    const asset = firstFrameAssetFromVisualAssets(upstream);
    if (asset?.asset_id) return normalizeImageAssetRef(asset, "visual_asset_reference");
  }
  for (const edge of incoming) {
    const asset = latestReadyImageAssetFromNode(state, edge.from);
    if (asset?.asset_id) return normalizeImageAssetRef(asset, asset.kind === "keyframe" ? "upstream_generated_image" : "upstream_uploaded_image", state.nodes?.[edge.from]);
  }
  return null;
}

function firstFrameAssetFromVisualAssets(node) {
  const assets = Array.isArray(node?.params?.visualAssets) ? [...node.params.visualAssets].reverse() : [];
  for (const visualAsset of assets) {
    const imageAsset = imageAssetFromVisualAsset(visualAsset);
    if (imageAsset?.asset_id) return normalizeImageAssetRef({
      ...imageAsset,
      visual_asset_id: visualAsset.visual_asset_id || visualAsset.asset_id || null,
    }, "visual_asset_reference", node);
  }
  return null;
}

function directUploadedFirstFrameAsset(node) {
  const upload = lastImageAsset(node);
  if (!upload?.asset_id) return null;
  return normalizeImageAssetRef(upload, "uploaded_image", node);
}

function explicitFirstFrameSource(node, assetId) {
  const existing = node?.params?.videoInputSource || {};
  const upload = (Array.isArray(node?.params?.uploads) ? node.params.uploads : [])
    .find((item) => String(item?.asset_id || item?.assetId || "") === assetId);
  return normalizeImageAssetRef({
    ...(upload || {}),
    asset_id: assetId,
    source_mode: existing.source_mode || "explicit_first_frame_selection",
    source_node_id: existing.source_node_id || node?.id || null,
    source_job_id: existing.source_job_id || null,
    visual_asset_id: existing.visual_asset_id || null,
  }, existing.source_mode || "explicit_first_frame_selection", node);
}

function latestReadyImageAssetFromNode(state, sourceNodeId) {
  const assets = Array.isArray(state.assets) ? state.assets : [];
  return assets.find((asset) =>
    asset?.source_node_id === sourceNodeId
    && asset?.asset_id
    && ["keyframe", "image_reference"].includes(asset?.kind)
    && (!asset.status || asset.status === "ready")
  ) || null;
}

function normalizeImageAssetRef(asset, fallbackRole, sourceNode = null) {
  const assetId = String(asset?.asset_id || asset?.assetId || "").trim();
  if (!assetId) return null;
  const sourceMode = videoSourceMode(asset?.source_mode || fallbackRole);
  return {
    ...asset,
    asset_id: assetId,
    filename: asset.filename || asset.title || `${assetId}.png`,
    preview_url: asset.preview_url || asset.previewUrl || null,
    role: asset.role || "first_frame",
    source_mode: sourceMode,
    source_asset_id: assetId,
    source_node_id: asset.source_node_id || sourceNode?.id || null,
    source_job_id: asset.source_job_id || sourceNode?.params?.lastKeyframeJobId || null,
    visual_asset_id: asset.visual_asset_id || null,
  };
}

function sourceModeForUpstreamNode(node) {
  const role = String(lastImageAsset(node)?.role || "").toLowerCase();
  if (role === "generated_keyframe_reference" || node?.params?.nodeRole === "keyframe_generation" || node?.params?.lastKeyframeJobId) {
    return "upstream_generated_image";
  }
  return "upstream_uploaded_image";
}

function videoSourceMode(value) {
  const mode = String(value || "").trim();
  if ([
    "uploaded_image",
    "upstream_uploaded_image",
    "upstream_generated_image",
    "visual_asset_reference",
    "explicit_first_frame_selection",
  ].includes(mode)) return mode;
  if (mode === "generated_keyframe_reference") return "upstream_generated_image";
  if (mode === "reference_image") return "upstream_uploaded_image";
  return "explicit_first_frame_selection";
}

function videoInputSourceFromAsset(asset, node) {
  return {
    source_mode: videoSourceMode(asset?.source_mode),
    source_asset_id: asset?.source_asset_id || asset?.asset_id || "",
    source_node_id: asset?.source_node_id || node?.id || null,
    source_job_id: asset?.source_job_id || null,
    visual_asset_id: asset?.visual_asset_id || null,
    role: "first_frame",
  };
}

export function videoInputSourceForRequest(node, firstFrameAssetId) {
  const source = node?.params?.videoInputSource || {};
  const assetId = String(firstFrameAssetId || source.source_asset_id || node?.params?.firstFrameImageAssetId || "").trim();
  return {
    source_mode: videoSourceMode(source.source_mode),
    source_asset_id: assetId,
    source_node_id: source.source_node_id || node?.id || null,
    source_job_id: source.source_job_id || null,
    visual_asset_id: source.visual_asset_id || null,
    role: source.role || "first_frame",
  };
}
