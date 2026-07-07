import { buildContextSubgraph } from "./optimizer-contract.js";
import { providerServiceForVideoModel } from "./presets/models.js";
import { lastImageAsset, resizeNodeForImagePreview } from "./node-image-assets.js";
import { clearVideoAutoPoll, ensureVideoFirstFrameAsset, scheduleVideoAutoPoll } from "./video-node-flow.js";
import { safeError, setNodeError } from "./node-action-utils.js";
import { firstCandidatePreview, setSubmittingGenerationState, updateNodeGenerationState } from "./node-generation-progress.js";
import { parseDuration, videoResultText, videoRevisionResultText } from "./node-generation-results.js";
import { clearOneRunOverrides, normalizeStringList, prepareGenerationRequest } from "./node-generation-guards.js";
import { reconcileVisualAssetBadges } from "./node-generation-context.js";
import { generationRestoreSnapshot, restoreCancelledGeneration } from "./node-generation-restore.js";

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
    };
    n.result = [
      "Experimental video revision draft is enabled.",
      "Edit this node prompt to describe only the intended change.",
      "Preservation is best-effort, not pixel-identical.",
      "Requires AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION for submit.",
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
  node = store.get().nodes[node.id] || node;
  const previousNodeState = generationRestoreSnapshot(node);
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    setSubmittingGenerationState(n, "video", { label: "正在提交视频任务", percent: 8 });
    n.result = "视频任务提交中...\n提交后如本地取消，只会停止 Studio 轮询；厂商侧任务仍可能继续执行并计费。";
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
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    setSubmittingGenerationState(n, "video_revision", { label: "正在提交视频修订", percent: 8 });
    n.result = "Preparing experimental video revision...";
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
    setNodeError(store, node.id, `Experimental video revision request failed: ${safeError(error)}`);
    if (submitAttempted) clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
  }
}

function buildVideoGenerationRequest(store, node, firstFrame) {
  return {
    node_id: node.id,
    prompt_text: node.prompt || "保持首帧主体身份，生成自然克制的镜头运动。",
    optimized_prompt: node.params?.lastOptimizedPromptPlain || null,
    provider_service_id: providerServiceForVideoModel(node.params?.model),
    first_frame_image_asset_id: firstFrame,
    last_frame_image_asset_id: node.params?.lastFrameImageAssetId || null,
    duration_sec: parseDuration(node.params?.spec?.duration),
    resolution: String(node.params?.spec?.resolution || "720P").toLowerCase(),
    aspect_ratio: node.params?.spec?.ratio || "9:16",
    motion: node.params?.motion || "",
    candidate_count: 1,
    node_parameters: {
      reference_transform_mode: node.params?.assetReferenceMode || node.params?.referenceTransformMode || null,
    },
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

function applyVideoRevisionResponse(store, nodeId, response) {
  const status = response?.job?.status || "blocked";
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const preview = firstCandidatePreview(response);
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
    n.status = status === "succeeded" ? "complete" : ["submitted", "running"].includes(status) ? "generating" : "error";
    n.result = videoRevisionResultText(response);
  });
}

function applyVideoResponse(store, nodeId, response) {
  const status = response?.job?.status || "blocked";
  if (!["submitted", "running"].includes(status)) clearVideoAutoPoll(nodeId);
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const preview = firstCandidatePreview(response);
    const previewUrl = preview?.url || null;
    updateNodeGenerationState(n, response, { kind: "video" });
    n.params.lastVideoJobId = response?.job?.job_id || null;
    n.params.lastVideoPreviewUrl = previewUrl;
    n.params.lastContextBundle = response?.context_bundle || n.params.lastContextBundle || null;
    reconcileVisualAssetBadges(n, response?.context_bundle || null);
    if (previewUrl) {
      n.previewUrl = previewUrl;
      resizeNodeForImagePreview(n, preview, n.params?.spec?.ratio || "9:16");
    }
    n.status = status === "succeeded" ? "complete" : status === "cancelled_local_only" ? "cancelled" : ["submitted", "running"].includes(status) ? "generating" : "error";
    n.result = videoResultText(response);
  });
}
