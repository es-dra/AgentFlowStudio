import { lastImageAsset, mergeImageAssets } from "./node-image-assets.js";

const VIDEO_AUTO_POLL_INTERVAL_MS = 12000;
const VIDEO_AUTO_POLL_MAX_ATTEMPTS = 80;
const videoAutoPollTimers = new Map();

export function ensureVideoFirstFrameAsset(store, node) {
  const explicit = String(node?.params?.firstFrameImageAssetId || "").trim();
  if (explicit) return { asset_id: explicit };
  const inferred = inferConnectedFirstFrameAsset(store, node);
  if (!inferred?.asset_id) return null;
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.params.firstFrameImageAssetId = inferred.asset_id;
    if (inferred.preview_url) n.params.firstFramePreviewUrl = inferred.preview_url;
    n.params.uploads = mergeImageAssets(n.params.uploads || [], {
      ...inferred,
      role: inferred.role || "first_frame",
    }).slice(-4);
    n.result = `已自动使用上游关键帧作为首帧: ${inferred.asset_id}`;
  });
  return inferred;
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
    if (asset?.asset_id) return normalizeImageAssetRef(asset, "generated_keyframe_reference");
  }
  for (const edge of incoming) {
    const asset = latestReadyImageAssetFromNode(state, edge.from);
    if (asset?.asset_id) return normalizeImageAssetRef(asset, asset.kind === "keyframe" ? "generated_keyframe_reference" : "reference_image");
  }
  return null;
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

function normalizeImageAssetRef(asset, fallbackRole) {
  const assetId = String(asset?.asset_id || asset?.assetId || "").trim();
  if (!assetId) return null;
  return {
    ...asset,
    asset_id: assetId,
    filename: asset.filename || asset.title || `${assetId}.png`,
    preview_url: asset.preview_url || asset.previewUrl || null,
    role: asset.role || fallbackRole,
  };
}
