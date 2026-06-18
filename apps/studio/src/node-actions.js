import { createNode, connect } from "./nodes.js";
import { buildContextSubgraph, buildKeyframeGenerationRequest } from "./optimizer-contract.js";
import { isRemoteImageModel, isRemoteVideoModel, providerServiceForVideoModel } from "./presets/models.js";
import { SAMPLE_SCRIPT, SAMPLE_SCRIPT_TITLE } from "./presets/starters.js";
import { openVisualAssetPanel } from "./panels/visual-asset-panel.js";
import { lastImageAsset, mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { clearVideoAutoPoll, ensureVideoFirstFrameAsset, scheduleVideoAutoPoll } from "./video-node-flow.js";
import { safeError, setNodeError } from "./node-action-utils.js";
import { visibleAssetForNode } from "./node-visible-assets.js";
import { firstCandidatePreview, setSubmittingGenerationState, updateNodeGenerationState } from "./node-generation-progress.js";
import { isKeyframeInProgress, keyframeResultText, parseDuration, videoResultText, videoRevisionResultText } from "./node-generation-results.js";
import { clearOneRunOverrides, normalizeStringList, prepareGenerationRequest } from "./node-generation-guards.js";
import { reconcileVisualAssetBadges } from "./node-generation-context.js";
import { generationRestoreSnapshot, restoreCancelledGeneration, sleep } from "./node-generation-restore.js";

export { uploadNodeImage } from "./node-upload-actions.js";
export { visibleAssetForNode } from "./node-visible-assets.js";

// Empty-state intent: script starter lays out a safe local upstream example flow.
export function handleNodeIntent(store, node, intent) {
  if (node.type === "script" && intent === "剧本生成分镜脚本") {
    spawnSampleScriptFlow(store, node);
    return;
  }
  store.set((s) => {
    const target = s.nodes[node.id];
    if (target) target.params.intent = intent;
    s.selection = { nodeIds: [node.id], edgeId: null };
  });
}

export function spawnSampleScriptFlow(store, scriptNode) {
  const textNode = createNode(store, "text", scriptNode.x - 420, scriptNode.y + 140);
  const groupId = store.nextId("group");
  store.set((s) => {
    const t = s.nodes[textNode.id];
    t.title = "文本";
    t.content = SAMPLE_SCRIPT;
    t.h = 320;
    t.status = "complete";
    const sc = s.nodes[scriptNode.id];
    sc.params.attachments = [{ id: textNode.id, label: SAMPLE_SCRIPT_TITLE }];
    s.groups[groupId] = {
      id: groupId,
      title: `预设 - ${SAMPLE_SCRIPT_TITLE}`,
      nodeIds: [scriptNode.id, textNode.id],
    };
    t.groupId = groupId;
    sc.groupId = groupId;
    s.selection = { nodeIds: [scriptNode.id], edgeId: null };
  });
  connect(store, textNode.id, scriptNode.id);
}

export function fixNodeVisualAsset(store, runtime, node) {
  const imageAsset = lastImageAsset(node);
  openVisualAssetPanel({ store, runtime, node, imageAsset });
}

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

// 发送（Ctrl+Enter / 发送按钮）：当前 MVP 只允许图片节点触发真实 keyframe。
export async function startNodeGeneration(store, runtime, node, resultText) {
  const fresh = store.get().nodes[node.id] || node;
  if (fresh.type === "image" && isRemoteImageModel(fresh.params?.model) && runtime?.generateKeyframe) {
    await startRemoteKeyframeGeneration(store, runtime, fresh);
    return;
  }
  if (fresh.type === "video" && isRemoteVideoModel(fresh.params?.model) && runtime?.generateVideo) {
    if (fresh.params?.videoRevision?.enabled && runtime?.generateVideoRevision) {
      await startRemoteVideoRevision(store, runtime, fresh);
      return;
    }
    await startRemoteVideoGeneration(store, runtime, fresh);
    return;
  }
  setNodeError(
    store,
    fresh.id,
    resultText || "当前版本仅图片节点支持真实生成；视频、音频、脚本和合成通道仍在开发中。",
  );
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

async function startRemoteVideoGeneration(store, runtime, node) {
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
    let request = {
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
      context_subgraph: buildContextSubgraph(store.get(), node, "context_generate"),
      temporary_lock_overrides: node.params?.temporaryLockOverrides || [],
      temporary_asset_exclusions: node.params?.temporaryAssetExclusions || [],
      quota_override_confirmed: Boolean(node.params?.quotaOverrideConfirmed),
      generated_at: new Date().toISOString(),
    };
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

async function startRemoteVideoRevision(store, runtime, node) {
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
    let request = {
      node_id: node.id,
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
      provider_service_id: providerServiceForVideoModel(node.params?.model),
      first_frame_image_asset_id: firstFrame,
      last_frame_image_asset_id: node.params?.lastFrameImageAssetId || null,
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

async function startRemoteKeyframeGeneration(store, runtime, node) {
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
