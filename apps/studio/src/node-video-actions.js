import { buildContextSubgraph } from "./optimizer-contract.js";
import { providerServiceForVideoModel } from "./presets/models.js";
import { lastImageAsset } from "./node-image-assets.js";
import { clearVideoAutoPoll, ensureVideoFirstFrameAsset, scheduleVideoAutoPoll, videoInputSourceForRequest } from "./video-node-flow.js";
import { safeError, setNodeError } from "./node-action-utils.js";
import { setSubmittingGenerationState, updateNodeGenerationState } from "./node-generation-progress.js";
import { parseDuration } from "./node-generation-results.js";
import { clearOneRunOverrides, normalizeStringList, prepareGenerationRequest } from "./node-generation-guards.js";
import { appendPreservedOutput, retryFailedItemsPlan, retryResultText, retrySubmittingOptions } from "./node-generation-retry.js";
import { generationRestoreSnapshot, restoreCancelledGeneration } from "./node-generation-restore.js";
import { applyVideoResponse, applyVideoRevisionResponse } from "./node-video-response.js";

const VIDEO_LOCAL_EDIT_UNAVAILABLE = {
  status: "unavailable",
  required_capability: "video_edit_or_masked_temporal_edit",
  reason: "current_video_revision_is_global_regeneration_attempt",
  user_message: "局部视频编辑未开放；当前草稿只会按提示词和首帧提交整段重生成尝试。",
};

export function setNodeVideoFrame(store, node, slot = "first") {
  const imageAsset = lastImageAsset(node);
  if (!imageAsset?.asset_id) {
    setNodeError(store, node.id, "请先上传图片，再设为首帧或尾帧。");
    return;
  }
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    if (slot === "last") n.params.lastFrameImageAssetId = imageAsset.asset_id;
    else n.params.firstFrameImageAssetId = imageAsset.asset_id;
    n.result = slot === "last" ? `已设为尾帧: ${imageAsset.asset_id}` : `已设为首帧: ${imageAsset.asset_id}`;
  });
}

export function enableVideoRevisionDraft(store, node) {
  const baseVideoJobId = node.params?.lastVideoJobId;
  if (!baseVideoJobId) {
    setNodeError(store, node.id, "No accepted base video job is available for an experimental revision.");
    return;
  }
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    const previous = n.params.videoRevision || {};
    n.params.videoRevision = {
      enabled: true,
      experimental: true,
      base_video_job_id: previous.base_video_job_id || baseVideoJobId,
      base_lineage_root_job_id: previous.base_lineage_root_job_id || previous.base_video_job_id || baseVideoJobId,
      parent_revision_job_id: previous.parent_revision_job_id || null,
      preserve_policy: "best_effort",
      provider_capability_mode: "i2v_revision_attempt",
      editable_targets: previous.editable_targets || ["other"],
      locked_aspects: previous.locked_aspects || ["character_identity", "scene_layout", "camera_path", "duration"],
      temporal_scope: previous.temporal_scope || { kind: "whole_clip" },
      feature_flag_env: "AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION",
      local_edit_availability: { ...VIDEO_LOCAL_EDIT_UNAVAILABLE },
    };
    n.result = [
      "视频重生成草稿已启用。",
      "这不是局部编辑：当前只会基于提示词、首帧和基础视频信息提交整段重生成尝试。",
      "局部/蒙版/逐帧编辑未开放；需要 video-edit/mask/temporal 能力。",
      "可以描述目标变化，但未点名的画面、运动或身份仍可能漂移。",
      "提交仍需要 AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION。",
    ].join("\n");
  });
}

export async function pollNodeVideoGeneration(store, runtime, node) {
  const jobId = node.params?.lastVideoJobId;
  if (!jobId || !runtime?.pollVideo) {
    setNodeError(store, node.id, "没有可继续轮询的视频任务。");
    return;
  }
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    updateNodeGenerationState(n, { job: { job_id: jobId, status: "running" } }, {
      kind: "video",
      label: "正在刷新视频进度",
      percent: n.params?.progressPercent || 62,
    });
    n.result = `正在刷新视频生成进度...\n任务编号：${jobId}`;
  });
  try {
    const response = await runtime.pollVideo(jobId);
    applyVideoResponse(store, node.id, response);
    await store.flushRuntimeSave?.();
    scheduleVideoAutoPoll({ store, runtime, nodeId: node.id, response, applyVideoResponse, setNodeError, safeError });
  } catch (error) {
    setNodeError(store, node.id, `视频进度刷新失败：${safeError(error)}`);
    await store.flushRuntimeSave?.();
  }
}

export async function cancelNodeVideoGeneration(store, runtime, node) {
  const jobId = node.params?.lastVideoJobId;
  if (!jobId || !runtime?.cancelVideo) {
    setNodeError(store, node.id, "没有可本地取消轮询的视频任务。");
    return;
  }
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "cancelled";
    n.result = `本地取消请求已发送。\n任务编号：${jobId}\n注意：本地取消只停止页面继续刷新，不代表生成平台侧任务已经取消，也不保证停止计费。`;
  });
  try {
    const response = await runtime.cancelVideo(jobId);
    clearVideoAutoPoll(node.id);
    applyVideoResponse(store, node.id, response);
    await store.flushRuntimeSave?.();
  } catch (error) {
    setNodeError(store, node.id, `本地取消视频进度刷新失败：${safeError(error)}`);
    await store.flushRuntimeSave?.();
  }
}

export async function startRemoteVideoGeneration(store, runtime, node) {
  const frameAsset = ensureVideoFirstFrameAsset(store, node);
  const firstFrame = frameAsset?.asset_id;
  if (!firstFrame) {
    setNodeError(store, node.id, "请先在节点菜单中上传图片并设为首帧，再生成图生视频。");
    return;
  }
  if (!String(node.prompt || node.params?.lastOptimizedPromptPlain || "").trim()) {
    setNodeError(store, node.id, "请先填写视频提示词，再提交图生视频。");
    return;
  }
  node = store.get().nodes[node.id] || node;
  const previousNodeState = generationRestoreSnapshot(node);
  const retryPlan = retryFailedItemsPlan(node);
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    if (retryPlan.retrying) appendPreservedOutput(n, retryPlan.preserved);
    setSubmittingGenerationState(n, "video", retryPlan.retrying
      ? retrySubmittingOptions("正在提交视频任务")
      : { label: "正在提交视频任务", percent: 8 });
    n.result = retryPlan.retrying
      ? retryResultText()
      : "视频任务提交中...\n提交后如本地取消，只会停止 Studio 轮询；厂商侧任务仍可能继续执行并计费。";
  });
  let submitAttempted = false;
  try {
    let request = buildVideoGenerationRequest(store, node, firstFrame);
    request = await prepareGenerationRequest(store, runtime, node, request, "video");
    if (!request) {
      restoreCancelledGeneration(store, node.id, previousNodeState);
      await store.flushRuntimeSave?.();
      return;
    }
    submitAttempted = true;
    const response = await runtime.generateVideo(request);
    applyVideoResponse(store, node.id, response);
    clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
    scheduleVideoAutoPoll({ store, runtime, nodeId: node.id, response, applyVideoResponse, setNodeError, safeError });
  } catch (error) {
    setNodeError(store, node.id, `视频生成请求失败：${safeError(error)}`);
    if (submitAttempted) clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
  }
}

export async function startRemoteVideoRevision(store, runtime, node) {
  const frameAsset = ensureVideoFirstFrameAsset(store, node);
  const firstFrame = frameAsset?.asset_id;
  const revision = node.params?.videoRevision || {};
  const baseVideoJobId = revision.base_video_job_id || node.params?.lastVideoJobId;
  if (!baseVideoJobId) {
    setNodeError(store, node.id, "No accepted base video job is available for an experimental revision.");
    return;
  }
  if (!firstFrame) {
    setNodeError(store, node.id, "Upload or select a first frame before starting an experimental video revision.");
    return;
  }
  node = store.get().nodes[node.id] || node;
  const previousNodeState = generationRestoreSnapshot(node);
  const retryPlan = retryFailedItemsPlan(node);
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    if (retryPlan.retrying) appendPreservedOutput(n, retryPlan.preserved);
    setSubmittingGenerationState(n, "video_revision", retryPlan.retrying
      ? retrySubmittingOptions("正在提交视频重生成尝试")
      : { label: "正在提交视频重生成尝试", percent: 8 });
    n.result = retryPlan.retrying
      ? retryResultText()
      : "正在准备视频重生成尝试；这不是局部编辑，未点名内容也可能变化。";
  });
  let submitAttempted = false;
  try {
    let request = buildVideoRevisionRequest(store, node, revision, baseVideoJobId, firstFrame);
    request = await prepareGenerationRequest(store, runtime, node, request, "video_revision");
    if (!request) {
      restoreCancelledGeneration(store, node.id, previousNodeState);
      await store.flushRuntimeSave?.();
      return;
    }
    submitAttempted = true;
    const response = await runtime.generateVideoRevision(request);
    applyVideoRevisionResponse(store, node.id, response);
    clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
  } catch (error) {
    setNodeError(store, node.id, `视频重生成尝试请求失败：${safeError(error)}`);
    if (submitAttempted) clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
  }
}

function buildVideoGenerationRequest(store, node, firstFrame) {
  return {
    node_id: node.id,
    prompt_text: node.prompt || node.params?.lastOptimizedPromptPlain || "",
    optimized_prompt: node.params?.lastOptimizedPromptPlain || null,
    provider_service_id: providerServiceForVideoModel(node.params?.model),
    first_frame_image_asset_id: firstFrame,
    last_frame_image_asset_id: node.params?.lastFrameImageAssetId || null,
    input_source: videoInputSourceForRequest(node, firstFrame),
    duration_sec: parseDuration(node.params?.spec?.duration),
    resolution: String(node.params?.spec?.resolution || "720P").toLowerCase(),
    aspect_ratio: node.params?.spec?.ratio || "9:16",
    motion: node.params?.motion || "",
    candidate_count: 1,
    context_subgraph: buildContextSubgraph(store.get(), node, "context_generate"),
    temporary_lock_overrides: node.params?.temporaryLockOverrides || [],
    temporary_asset_exclusions: node.params?.temporaryAssetExclusions || [],
    quota_override_confirmed: Boolean(node.params?.quotaOverrideConfirmed),
    generated_at: new Date().toISOString(),
  };
}

function buildVideoRevisionRequest(store, node, revision, baseVideoJobId, firstFrame) {
  return {
    ...buildVideoGenerationRequest(store, node, firstFrame),
    base_video_job_id: baseVideoJobId,
    base_video_artifact_id: revision.base_video_artifact_id || null,
    base_lineage_root_job_id: revision.base_lineage_root_job_id || baseVideoJobId,
    parent_revision_job_id: revision.parent_revision_job_id || null,
    revision_intent: node.prompt || revision.revision_intent || "Adjust the requested detail while keeping unrelated aspects stable.",
    editable_targets: normalizeStringList(revision.editable_targets || ["other"]),
    locked_aspects: normalizeStringList(revision.locked_aspects || ["character_identity", "scene_layout", "camera_path", "duration"]),
    temporal_scope: revision.temporal_scope || { kind: "whole_clip" },
    preserve_policy: "best_effort",
    provider_capability_mode: "i2v_revision_attempt",
  };
}
