import { mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { visibleAssetForNode } from "./node-visible-assets.js";
import { updateNodeGenerationState } from "./node-generation-progress.js";
import { isKeyframeInProgress, keyframeResultText } from "./node-generation-results.js";
import { reconcileVisualAssetBadges } from "./node-generation-context.js";
import { keyframeSourceEvidenceTrace } from "./keyframe-source-evidence-trace.js";
export function applyKeyframeResponse(store, nodeId, response, request, options = {}) {
  const status = response?.job?.status || "blocked";
  const inProgress = isKeyframeInProgress(response);
  const kind = options.kind || "keyframe";
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const reusableAsset = response?.reusable_image_assets?.[0] || null;
    const preview = response?.candidate_previews?.[0] || previewFromReusableAsset(reusableAsset);
    const outputCount = Number(response?.safe_manifest?.output_count || 0);
    const succeeded = status === "succeeded";
    const partial = !succeeded && !inProgress && Boolean(preview?.preview_url || reusableAsset?.preview_url || outputCount > 0);
    const jobId = response?.job?.job_id || null;
    const shouldRecordAsset = (succeeded || partial) && jobId && n.params.lastKeyframeCompletedJobId !== jobId;
    updateNodeGenerationState(n, response, { kind, retrying: Boolean(options.retrying) });
    n.params.lastKeyframeJobId = jobId || n.params.lastKeyframeJobId || null;
    n.status = succeeded ? "complete" : inProgress ? "generating" : partial ? "partial" : "error";
    if (preview?.preview_url) {
      n.previewUrl = preview.preview_url;
      resizeNodeForImagePreview(n, preview, request.aspect_ratio);
    }
    if (succeeded && reusableAsset?.asset_id) {
      n.params.uploads = mergeImageAssets(n.params.uploads || [], reusableAssetForNode(n, reusableAsset, kind)).slice(-4);
    }
    n.params.lastContextBundle = response?.context_bundle || n.params.lastContextBundle || null;
    n.params.lastGenerationBridge = response?.generation_bridge || n.params.lastGenerationBridge || null;
    n.params.lastGenerationBridgeArtifactId = response?.artifacts?.keyframe_generation_bridge?.artifact_id || n.params.lastGenerationBridgeArtifactId || "";
    n.params.lastKeyframeSourceEvidenceTrace = keyframeSourceEvidenceTrace(n) || n.params.lastKeyframeSourceEvidenceTrace || null;
    reconcileVisualAssetBadges(n, response?.context_bundle || null);
    n.result = keyframeResultText(response, request, succeeded, { kind, partial });
    if (shouldRecordAsset) {
      n.params.lastKeyframeCompletedJobId = jobId;
      const asset = visibleAssetForNode(store, n);
      s.assets.unshift({
        ...asset,
        status: partial ? "partially_complete" : asset.status,
        safe_summary: (n.prompt || "").slice(0, 90),
        job_id: jobId,
        artifact_id: response?.artifacts?.keyframe_generation_safe_manifest?.artifact_id || null,
        asset_id: reusableAsset?.asset_id || null,
        preview_url: n.previewUrl,
        created_at: new Date().toISOString(),
      });
    }
  });
}
export function nodeGenerationKind(node) {
  return node?.params?.nodeRole === "asset_card_draft" ? "asset" : "keyframe";
}
export function submitLabel(kind) {
  return kind === "asset" ? "正在提交资产图生成" : "正在提交图片生成";
}
export function fallbackRequest(node) {
  return { aspect_ratio: node.params?.spec?.ratio || "9:16" };
}
function reusableAssetForNode(node, reusableAsset, kind) {
  if (kind !== "asset") return reusableAsset;
  const assetType = String(node?.params?.assetCardDraft?.asset_type || "");
  const role = { character: "character_reference", scene: "scene_reference", prop: "prop_reference" }[assetType] || "asset_reference";
  return { ...reusableAsset, role };
}
function previewFromReusableAsset(asset) {
  if (!asset?.preview_url) return null;
  return {
    preview_url: asset.preview_url,
    width: asset.width || null,
    height: asset.height || null,
    aspect_ratio: asset.aspect_ratio || null,
  };
}
