import { buildKeyframeGenerationRequest } from "./optimizer-contract.js";
import { mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { safeError, setNodeError } from "./node-action-utils.js";
import { visibleAssetForNode } from "./node-visible-assets.js";
import { setSubmittingGenerationState, updateNodeGenerationState } from "./node-generation-progress.js";
import { isKeyframeInProgress, keyframeResultText } from "./node-generation-results.js";
import { clearOneRunOverrides, prepareGenerationRequest } from "./node-generation-guards.js";
import { reconcileVisualAssetBadges } from "./node-generation-context.js";
import { generationRestoreSnapshot, restoreCancelledGeneration, sleep } from "./node-generation-restore.js";
const MAX_KEYFRAME_POLL_ATTEMPTS = 540;
const MAX_BOOTSTRAP_KEYFRAME_REFRESH = 4;
const MAX_ASSET_RECOVERY_ATTEMPTS = 18;
const activeKeyframePolls = new Map();
export async function pollNodeKeyframeGeneration(store, runtime, node) {
  const jobId = node.params?.lastKeyframeJobId;
  if (!jobId || !runtime?.pollKeyframe) {
    setNodeError(store, node.id, "没有可继续轮询的图像生成任务。");
    return;
  }
  try {
    await startBackgroundKeyframePolling(store, runtime, node.id, jobId, { aspect_ratio: node.params?.spec?.ratio || "9:16" });
  } catch (error) {
    setNodeError(store, node.id, `图像生成轮询失败: ${safeError(error)}`);
    await store.flushRuntimeSave?.();
  }
}
export async function startRemoteKeyframeGeneration(store, runtime, node) {
  const previousNodeState = generationRestoreSnapshot(node);
  const generationKind = nodeGenerationKind(node);
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    n.result = null;
    n.previewUrl = null;
    setSubmittingGenerationState(n, generationKind, { label: submitLabel(generationKind), percent: null });
  });
  let submitAttempted = false;
  let submittedAtMs = 0;
  try {
    let request = buildKeyframeGenerationRequest(store.get(), node);
    request = await prepareGenerationRequest(store, runtime, node, request, "keyframe");
    if (!request) {
      restoreCancelledGeneration(store, node.id, previousNodeState);
      await store.flushRuntimeSave?.();
      return;
    }
    submitAttempted = true;
    submittedAtMs = Date.now();
    const response = await runtime.generateKeyframe(request);
    applyKeyframeResponse(store, node.id, response, request, { kind: generationKind });
    clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
    if (isKeyframeInProgress(response) && response?.job?.job_id && runtime?.pollKeyframe) {
      await startBackgroundKeyframePolling(store, runtime, node.id, response.job.job_id, request);
    }
  } catch (error) {
    if (submitAttempted) clearOneRunOverrides(store, node.id);
    if (submitAttempted && isRecoverableSubmitError(error)) {
      markKeyframeRecovering(store, node.id, nodeGenerationKind(node));
      await store.flushRuntimeSave?.();
      void recoverTimedOutKeyframeFromAssets(store, runtime, node.id, generationKind, submittedAtMs, error);
      return;
    }
    setNodeError(store, node.id, `图像生成请求失败: ${safeError(error)}`);
    await store.flushRuntimeSave?.();
  }
}
export async function refreshPendingKeyframeGenerations(store, runtime, options = {}) {
  if (!runtime?.pollKeyframe) return;
  const limit = Number(options.limit || MAX_BOOTSTRAP_KEYFRAME_REFRESH);
  const nodes = Object.values(store.get().nodes || {})
    .filter((node) => node?.type === "image" && node.status === "generating" && node.params?.lastKeyframeJobId)
    .slice(0, Math.max(0, limit));
  for (const node of nodes) {
    const jobId = node.params.lastKeyframeJobId;
    try {
      const response = await runtime.pollKeyframe(jobId);
      applyKeyframeResponse(store, node.id, response, fallbackRequest(node), { kind: nodeGenerationKind(node) });
      await store.flushRuntimeSave?.();
      if (isKeyframeInProgress(response)) {
        void startBackgroundKeyframePolling(store, runtime, node.id, jobId, fallbackRequest(node));
      }
    } catch {}
  }
}
function startBackgroundKeyframePolling(store, runtime, nodeId, jobId, request) {
  const key = String(jobId || "");
  if (!key || !runtime?.pollKeyframe) return Promise.resolve(null);
  if (activeKeyframePolls.has(key)) return activeKeyframePolls.get(key);
  const poll = pollKeyframeUntilTerminal(store, runtime, nodeId, key, request)
    .finally(() => activeKeyframePolls.delete(key));
  activeKeyframePolls.set(key, poll);
  return poll;
}
async function pollKeyframeUntilTerminal(store, runtime, nodeId, jobId, request) {
  let lastResponse = null;
  let lastSavedStatus = "";
  for (let attempt = 0; attempt < MAX_KEYFRAME_POLL_ATTEMPTS; attempt += 1) {
    if (attempt > 0) await sleep(pollDelayMs(attempt));
    const response = await runtime.pollKeyframe(jobId);
    lastResponse = response;
    const fresh = store.get().nodes[nodeId];
    applyKeyframeResponse(store, nodeId, response, request, { kind: nodeGenerationKind(fresh) });
    const status = response?.job?.status || "";
    if (shouldSavePollState(attempt, status, lastSavedStatus, response)) {
      await store.flushRuntimeSave?.();
      lastSavedStatus = status;
    }
    if (!isKeyframeInProgress(response)) {
      await store.flushRuntimeSave?.();
      return response;
    }
  }
  markKeyframeStillProcessing(store, nodeId, lastResponse?.job?.job_id || jobId);
  await store.flushRuntimeSave?.();
  return lastResponse;
}
function pollDelayMs(attempt) {
  return attempt < 3 ? 2000 : attempt < 24 ? 5000 : 10000;
}
function shouldSavePollState(attempt, status, lastSavedStatus, response) {
  return !isKeyframeInProgress(response) || (status && status !== lastSavedStatus) || (attempt > 0 && attempt % 6 === 0);
}
function applyKeyframeResponse(store, nodeId, response, request, options = {}) {
  const status = response?.job?.status || "blocked";
  const inProgress = isKeyframeInProgress(response);
  const kind = options.kind || "keyframe";
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const preview = response?.candidate_previews?.[0] || null;
    const reusableAsset = response?.reusable_image_assets?.[0] || null;
    const succeeded = status === "succeeded" || Boolean(preview?.preview_url && (response?.safe_manifest?.output_count ?? 0) > 0);
    const jobId = response?.job?.job_id || null;
    const shouldRecordAsset = succeeded && jobId && n.params.lastKeyframeCompletedJobId !== jobId;
    updateNodeGenerationState(n, response, { kind });
    n.params.lastKeyframeJobId = jobId || n.params.lastKeyframeJobId || null;
    n.status = succeeded ? "complete" : inProgress ? "generating" : "error";
    if (preview?.preview_url) {
      n.previewUrl = preview.preview_url;
      resizeNodeForImagePreview(n, preview, request.aspect_ratio);
    }
    if (succeeded && reusableAsset?.asset_id) {
      n.params.uploads = mergeImageAssets(n.params.uploads || [], reusableAssetForNode(n, reusableAsset, kind)).slice(-4);
    }
    n.params.lastContextBundle = response?.context_bundle || n.params.lastContextBundle || null;
    reconcileVisualAssetBadges(n, response?.context_bundle || null);
    n.result = keyframeResultText(response, request, succeeded, { kind });
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
function markKeyframeRecovering(store, nodeId, kind) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const label = kind === "asset" ? "正在找回资产图结果" : "正在找回图片结果";
    n.status = "generating";
    updateNodeGenerationState(n, { job: { status: "running", progress: { mode: "indeterminate" } } }, {
      kind,
      label,
      hint: "浏览器连接超时或中断，但 Runtime 可能仍在完成生成；正在从素材库补偿回填。",
    });
    n.result = `${kind === "asset" ? "资产图" : "图像"}请求连接中断，正在尝试找回已完成结果。`;
  }, { history: false });
}
async function recoverTimedOutKeyframeFromAssets(store, runtime, nodeId, kind, submittedAtMs, originalError) {
  for (let attempt = 0; attempt < MAX_ASSET_RECOVERY_ATTEMPTS; attempt += 1) {
    if (nodeAlreadyRecovered(store, nodeId)) return;
    if (attempt > 0) await sleep(attempt < 4 ? 3000 : 5000);
    const recovered = await recoverNodeFromGeneratedAssets(store, runtime, nodeId, kind, submittedAtMs);
    if (recovered) {
      await store.flushRuntimeSave?.();
      return;
    }
  }
  if (nodeAlreadyRecovered(store, nodeId)) return;
  setNodeError(store, nodeId, `图像生成请求失败: ${safeError(originalError)} 可稍后在素材库中查看是否已有候选图，或在节点菜单重试。`);
  await store.flushRuntimeSave?.();
}
async function recoverNodeFromGeneratedAssets(store, runtime, nodeId, kind, submittedAtMs) {
  if (!runtime?.listImageAssets) return false;
  let payload = null;
  try {
    payload = await runtime.listImageAssets();
  } catch {
    return false;
  }
  const assets = Array.isArray(payload?.assets) ? payload.assets : [];
  const matching = assets
    .filter((item) => String(item?.source_node_id || "") === String(nodeId) && item?.preview_url)
    .sort((a, b) => assetCreatedAtMs(b) - assetCreatedAtMs(a));
  const asset = matching.find((item) => assetCreatedAtMs(item) >= submittedAtMs - 1000) || matching.find((item) => !assetCreatedAtMs(item));
  if (!asset) return false;
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    n.status = "complete";
    n.previewUrl = asset.preview_url;
    n.params.uploads = mergeImageAssets(n.params.uploads || [], recoveredAssetForNode(asset, kind)).slice(-4);
    if (asset.source_job_id) {
      n.params.lastKeyframeJobId = asset.source_job_id;
      n.params.lastKeyframeCompletedJobId = asset.source_job_id;
    }
    resizeNodeForImagePreview(n, asset, n.params?.spec?.ratio || "16:9");
    n.result = [
      `${kind === "asset" ? "资产图" : "关键帧"}已从已落盘素材找回`,
      asset.source_job_id ? `任务编号：${asset.source_job_id}` : null,
      "预览已从安全素材地址加载。",
    ].filter(Boolean).join("\n");
  }, { history: false });
  return true;
}
function nodeAlreadyRecovered(store, nodeId) {
  const node = store.get().nodes?.[nodeId];
  return node?.status === "complete" && Boolean(node.previewUrl);
}
function assetCreatedAtMs(asset) {
  const parsed = Date.parse(String(asset?.created_at || ""));
  return Number.isFinite(parsed) ? parsed : 0;
}
function recoveredAssetForNode(asset, kind) {
  const role = kind === "asset" ? asset.role || "asset_reference" : asset.role || "generated_keyframe_reference";
  return {
    asset_id: asset.asset_id,
    role,
    filename: asset.filename || `${asset.asset_id}.png`,
    preview_url: asset.preview_url,
    width: asset.width || null,
    height: asset.height || null,
    aspect_ratio: asset.aspect_ratio || null,
  };
}
function isRecoverableSubmitError(error) {
  const message = error instanceof Error ? error.message : String(error || "");
  const status = Number(error?.status || 0);
  return status === 0 || status === 502 || status === 503 || status === 504
    || /Gateway timeout|network connection interrupted|Failed to fetch|timed out/i.test(message);
}
function markKeyframeStillProcessing(store, nodeId, jobId) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const kind = nodeGenerationKind(n);
    const label = kind === "asset" ? "资产图仍在生成" : "图片仍在生成";
    n.status = "generating";
    updateNodeGenerationState(n, { job: { job_id: jobId, status: "running", progress: { mode: "indeterminate" } } }, { kind, label, hint: `任务 ${jobId} 还在处理，稍后可继续刷新节点。` });
    n.result = `${kind === "asset" ? "资产图" : "图像"}生成仍在进行中。\n任务编号：${jobId}`;
    n.params.lastKeyframeJobId = jobId;
  }, { history: false });
}
function nodeGenerationKind(node) { return node?.params?.nodeRole === "asset_card_draft" ? "asset" : "keyframe"; }
function submitLabel(kind) { return kind === "asset" ? "正在提交资产图生成" : "正在提交图片生成"; }
function fallbackRequest(node) { return { aspect_ratio: node.params?.spec?.ratio || "9:16" }; }
function reusableAssetForNode(node, reusableAsset, kind) {
  if (kind !== "asset") return reusableAsset;
  const assetType = String(node?.params?.assetCardDraft?.asset_type || "");
  const role = { character: "character_reference", scene: "scene_reference", prop: "prop_reference" }[assetType] || "asset_reference";
  return { ...reusableAsset, role };
}
