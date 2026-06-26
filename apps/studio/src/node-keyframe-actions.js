import { buildKeyframeGenerationRequest } from "./optimizer-contract.js";
import { safeError, setNodeError } from "./node-action-utils.js";
import { setSubmittingGenerationState } from "./node-generation-progress.js";
import { isKeyframeInProgress } from "./node-generation-results.js";
import { clearOneRunOverrides, prepareGenerationRequest } from "./node-generation-guards.js";
import { generationRestoreSnapshot, restoreCancelledGeneration, sleep } from "./node-generation-restore.js";
import { applyKeyframeResponse, fallbackRequest, nodeGenerationKind, submitLabel } from "./node-keyframe-response.js";
import {
  isRecoverableSubmitError,
  markKeyframeRecovering,
  markKeyframeStillProcessing,
  recoverTimedOutKeyframeFromAssets,
} from "./node-keyframe-recovery.js";
const MAX_KEYFRAME_POLL_ATTEMPTS = 540;
const MAX_BOOTSTRAP_KEYFRAME_REFRESH = 4;
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
    setSubmittingGenerationState(n, generationKind, { label: submitLabel(generationKind), percent: 8 });
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
