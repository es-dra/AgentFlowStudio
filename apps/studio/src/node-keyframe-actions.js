import { buildKeyframeGenerationRequest } from "./optimizer-contract.js";
import { mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { safeError, setNodeError } from "./node-action-utils.js";
import { visibleAssetForNode } from "./node-visible-assets.js";
import { setSubmittingGenerationState, updateNodeGenerationState } from "./node-generation-progress.js";
import { isKeyframeInProgress, keyframeResultText } from "./node-generation-results.js";
import { clearOneRunOverrides, prepareGenerationRequest } from "./node-generation-guards.js";
import { reconcileVisualAssetBadges } from "./node-generation-context.js";
import { generationRestoreSnapshot, restoreCancelledGeneration, sleep } from "./node-generation-restore.js";

export async function pollNodeKeyframeGeneration(store, runtime, node) {
  const jobId = node.params?.lastKeyframeJobId;
  if (!jobId || !runtime?.pollKeyframe) {
    setNodeError(store, node.id, "没有可继续轮询的图像生成任务。");
    return;
  }
  try {
    await pollKeyframeUntilTerminal(store, runtime, node.id, jobId, { aspect_ratio: node.params?.spec?.ratio || "9:16" });
  } catch (error) {
    setNodeError(store, node.id, `图像生成轮询失败: ${safeError(error)}`);
    await store.flushRuntimeSave?.();
  }
}

export async function startRemoteKeyframeGeneration(store, runtime, node) {
  const previousNodeState = generationRestoreSnapshot(node);
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    n.result = null;
    n.previewUrl = null;
    setSubmittingGenerationState(n, "keyframe", { label: "正在提交图片生成", percent: 8 });
  });
  let submitAttempted = false;
  try {
    let request = buildKeyframeGenerationRequest(store.get(), node);
    request = await prepareGenerationRequest(store, runtime, node, request, "keyframe");
    if (!request) {
      restoreCancelledGeneration(store, node.id, previousNodeState);
      await store.flushRuntimeSave?.();
      return;
    }
    submitAttempted = true;
    const response = await runtime.generateKeyframe(request);
    applyKeyframeResponse(store, node.id, response, request);
    clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
    if (isKeyframeInProgress(response) && response?.job?.job_id && runtime?.pollKeyframe) {
      await pollKeyframeUntilTerminal(store, runtime, node.id, response.job.job_id, request);
    }
  } catch (error) {
    setNodeError(store, node.id, `图像生成请求失败: ${safeError(error)}`);
    if (submitAttempted) clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
  }
}

async function pollKeyframeUntilTerminal(store, runtime, nodeId, jobId, request) {
  let lastResponse = null;
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (attempt > 0) await sleep(2000);
    const response = await runtime.pollKeyframe(jobId);
    lastResponse = response;
    applyKeyframeResponse(store, nodeId, response, request);
    await store.flushRuntimeSave?.();
    if (!isKeyframeInProgress(response)) return response;
  }
  throw new Error(`图像生成仍在处理中，请稍后重试刷新。任务编号：${lastResponse?.job?.job_id || jobId}`);
}

function applyKeyframeResponse(store, nodeId, response, request) {
  const status = response?.job?.status || "blocked";
  const succeeded = status === "succeeded";
  const inProgress = isKeyframeInProgress(response);
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const preview = response?.candidate_previews?.[0] || null;
    const reusableAsset = response?.reusable_image_assets?.[0] || null;
    const jobId = response?.job?.job_id || null;
    const shouldRecordAsset = succeeded && jobId && n.params.lastKeyframeCompletedJobId !== jobId;
    updateNodeGenerationState(n, response, { kind: "keyframe" });
    n.params.lastKeyframeJobId = jobId || n.params.lastKeyframeJobId || null;
    n.status = succeeded ? "complete" : inProgress ? "generating" : "error";
    if (preview?.preview_url) {
      n.previewUrl = preview.preview_url;
      resizeNodeForImagePreview(n, preview, request.aspect_ratio);
    }
    if (succeeded && reusableAsset?.asset_id) {
      n.params.uploads = mergeImageAssets(n.params.uploads || [], reusableAsset).slice(-4);
    }
    n.params.lastContextBundle = response?.context_bundle || n.params.lastContextBundle || null;
    reconcileVisualAssetBadges(n, response?.context_bundle || null);
    n.result = keyframeResultText(response, request, succeeded);
    if (shouldRecordAsset) {
      n.params.lastKeyframeCompletedJobId = jobId;
      const asset = visibleAssetForNode(store, n);
      s.assets.unshift({
        ...asset,
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
