import { clearVideoAutoPoll } from "./video-node-flow.js";
import { resizeNodeForImagePreview } from "./node-image-assets.js";
import { firstCandidatePreview, updateNodeGenerationState } from "./node-generation-progress.js";
import { videoResultText, videoRevisionResultText } from "./node-generation-results.js";
import { reconcileVisualAssetBadges } from "./node-generation-context.js";
import { isPartialTerminalResponse, nodeStatusFromTerminalResponse } from "./node-generation-retry.js";

const VIDEO_CANCELLED_LOCAL_ONLY_STATUS = "cancelled_local_only";

export function applyVideoRevisionResponse(store, nodeId, response) {
  const status = response?.job?.status || "blocked";
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const preview = firstCandidatePreview(response);
    const partial = isPartialTerminalResponse(response, preview);
    updateNodeGenerationState(n, response, { kind: "video_revision" });
    if (preview?.url) {
      n.previewUrl = preview.url;
      resizeNodeForImagePreview(n, preview, n.params?.spec?.ratio || "9:16");
    }
    n.params.videoRevision = {
      ...(n.params.videoRevision || {}),
      enabled: true,
      experimental: true,
      lastRevisionJobId: response?.job?.job_id || null,
      lastSafeManifest: response?.safe_manifest || null,
    };
    n.status = nodeStatusFromTerminalResponse(status, partial);
    n.result = videoRevisionResultText(response);
  });
}

export function applyVideoResponse(store, nodeId, response) {
  const status = response?.job?.status || "blocked";
  if (!["submitted", "pending", "running"].includes(status)) clearVideoAutoPoll(nodeId);
  if (status === VIDEO_CANCELLED_LOCAL_ONLY_STATUS) clearVideoAutoPoll(nodeId);
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const preview = firstCandidatePreview(response);
    const previewUrl = preview?.url || null;
    const partial = isPartialTerminalResponse(response, preview);
    updateNodeGenerationState(n, response, { kind: "video" });
    n.params.lastVideoJobId = response?.job?.job_id || null;
    n.params.lastVideoPreviewUrl = previewUrl;
    n.params.lastContextBundle = response?.context_bundle || n.params.lastContextBundle || null;
    reconcileVisualAssetBadges(n, response?.context_bundle || null);
    if (previewUrl) {
      n.previewUrl = previewUrl;
      resizeNodeForImagePreview(n, preview, n.params?.spec?.ratio || "9:16");
    }
    n.status = nodeStatusFromTerminalResponse(status, partial);
    n.result = videoResultText(response);
  });
}
