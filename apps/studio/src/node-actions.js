import { createNode, connect } from "./nodes.js";
import { buildContextSubgraph, buildKeyframeGenerationRequest } from "./optimizer-contract.js";
import { isRemoteImageModel, isRemoteVideoModel, providerServiceForVideoModel } from "./presets/models.js";
import { SAMPLE_SCRIPT, SAMPLE_SCRIPT_TITLE } from "./presets/starters.js";
import { openVisualAssetPanel } from "./panels/visual-asset-panel.js";
import { lastImageAsset, mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { el, showModal } from "./overlay.js";
import { buildAssetReferenceActions } from "./asset-reference-inspector.js";

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

export function uploadNodeImage(store, runtime, node) {
  if (!runtime?.uploadImageAsset) {
    setNodeError(store, node.id, "Runtime image upload API is not available.");
    return;
  }
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/png,image/jpeg";
  input.style.display = "none";
  document.body.appendChild(input);
  input.addEventListener("change", async () => {
    const file = input.files?.[0];
    input.remove();
    if (!file) return;
    await uploadSelectedImage(store, runtime, node.id, file);
  }, { once: true });
  input.click();
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

async function uploadSelectedImage(store, runtime, nodeId, file) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    n.status = "generating";
    n.result = "正在上传参考图...";
  });
  try {
    const dataBase64 = await readFileAsBase64(file);
    const response = await runtime.uploadImageAsset({
      node_id: nodeId,
      filename: file.name || "reference.png",
      mime_type: file.type || "application/octet-stream",
      data_base64: dataBase64,
      role: "reference_image",
      generated_at: new Date().toISOString(),
    });
    const asset = response?.asset;
    if (!asset?.asset_id || !asset?.preview_url) throw new Error("Runtime did not return an image asset");
    store.set((s) => {
      const n = s.nodes[nodeId];
      if (!n) return;
      n.status = "complete";
      n.previewUrl = asset.preview_url;
      n.result = `已上传参考图\nAsset: ${asset.asset_id}\nSize: ${asset.width || "?"}x${asset.height || "?"}`;
      n.params.uploads = mergeImageAssets(n.params.uploads || [], asset).slice(-4);
      resizeNodeForImagePreview(n, asset, n.params?.spec?.ratio);
      s.assets.unshift({
        id: store.nextId("asset"),
        kind: "image_reference",
        title: n.title,
        safe_summary: file.name || asset.asset_id,
        thumbnail_ref: "keyframe",
        source_node_id: n.id,
        status: "ready",
        asset_id: asset.asset_id,
        preview_url: asset.preview_url,
        created_at: new Date().toISOString(),
      });
    });
    await store.flushRuntimeSave?.();
  } catch (error) {
    setNodeError(store, nodeId, `图片上传失败: ${safeError(error)}`);
  }
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("image file read failed"));
    reader.onload = () => {
      const text = String(reader.result || "");
      const marker = ";base64,";
      const index = text.indexOf(marker);
      resolve(index >= 0 ? text.slice(index + marker.length) : text);
    };
    reader.readAsDataURL(file);
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
    n.result = `正在轮询 Kling 视频任务...\nJob: ${jobId}`;
  });
  try {
    const response = await runtime.pollVideo(jobId);
    applyVideoResponse(store, node.id, response);
    await store.flushRuntimeSave?.();
  } catch (error) {
    setNodeError(store, node.id, `Kling video poll failed: ${safeError(error)}`);
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
    n.result = `本地取消请求已发送。\nJob: ${jobId}\n注意：本地取消只停止 Studio 继续轮询，不代表厂商侧任务已经取消，也不保证停止计费。`;
  });
  try {
    const response = await runtime.cancelVideo(jobId);
    applyVideoResponse(store, node.id, response);
    await store.flushRuntimeSave?.();
  } catch (error) {
    setNodeError(store, node.id, `Kling video local cancel failed: ${safeError(error)}`);
    await store.flushRuntimeSave?.();
  }
}

async function startRemoteVideoGeneration(store, runtime, node) {
  const firstFrame = node.params?.firstFrameImageAssetId;
  if (!firstFrame) {
    setNodeError(store, node.id, "请先在节点菜单中上传图片并设为首帧，再生成图生视频。");
    return;
  }
  const previousNodeState = generationRestoreSnapshot(node);
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
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
  } catch (error) {
    setNodeError(store, node.id, `Kling video request failed: ${safeError(error)}`);
    if (submitAttempted) clearOneRunOverrides(store, node.id);
    await store.flushRuntimeSave?.();
  }
}

async function startRemoteVideoRevision(store, runtime, node) {
  const firstFrame = node.params?.firstFrameImageAssetId;
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
  const previousNodeState = generationRestoreSnapshot(node);
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
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
    const previewUrl = response?.candidate_previews?.[0]?.preview_url || null;
    if (previewUrl) n.previewUrl = previewUrl;
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

function videoRevisionResultText(response) {
  const status = response?.job?.status || "blocked";
  const manifest = response?.safe_manifest || {};
  const block = manifest.blocks?.[0] || {};
  if (status === "succeeded") return "Experimental video revision completed through Runtime safe preview.";
  return [
    "Experimental video revision did not start.",
    `Status: ${status}`,
    `Reason: ${block.reason || "video revision provider path is not enabled"}`,
    "Goal: change requested effects while keeping unrelated aspects as stable as possible.",
  ].join("\n");
}

function applyVideoResponse(store, nodeId, response) {
  const status = response?.job?.status || "blocked";
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const previewUrl = response?.candidate_previews?.[0]?.preview_url || null;
    n.params.lastVideoJobId = response?.job?.job_id || null;
    n.params.lastVideoPreviewUrl = previewUrl;
    n.params.lastContextBundle = response?.context_bundle || n.params.lastContextBundle || null;
    reconcileVisualAssetBadges(n, response?.context_bundle || null);
    if (previewUrl) n.previewUrl = previewUrl;
    n.status = status === "succeeded" ? "complete" : status === "cancelled_local_only" ? "cancelled" : ["submitted", "running"].includes(status) ? "generating" : "error";
    n.result = videoResultText(response);
  });
}

function videoResultText(response) {
  const status = response?.job?.status || "blocked";
  if (status === "succeeded") return "Kling 视频已完成，预览已通过 Runtime 安全端点加载。";
  if (status === "submitted") return `Kling 视频已提交，可继续轮询。\nJob: ${response?.job?.job_id || "unknown"}\n本地取消只会停止 Studio 继续轮询，不代表厂商侧任务已经取消，也不保证停止计费。`;
  if (status === "running") return `Kling video task is still running.\nJob: ${response?.job?.job_id || "unknown"}\n本地取消只会停止 Studio 继续轮询，不代表厂商侧任务已经取消，也不保证停止计费。`;
  if (status === "cancelled_local_only") {
    return `本地已取消继续轮询（cancelled_local_only）。\nJob: ${response?.job?.job_id || "unknown"}\n这只更新 Runtime/Studio 状态，不代表厂商侧任务已经取消，也不保证停止计费。`;
  }
  const reason = response?.safe_manifest?.blocks?.[0]?.reason || "video provider is not ready";
  return `视频生成未开始或未完成。\n状态: ${status}\n原因: ${reason}`;
}

function parseDuration(value) {
  const match = String(value || "5").match(/\d+/);
  return match ? Number(match[0]) : 5;
}

async function startRemoteKeyframeGeneration(store, runtime, node) {
  const previousNodeState = generationRestoreSnapshot(node);
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    n.result = null;
    n.previewUrl = null;
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
  throw new Error(`图像生成仍在处理中，请稍后重试轮询。Job: ${lastResponse?.job?.job_id || jobId}`);
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

function isKeyframeInProgress(response) {
  return ["submitted", "running", "pending"].includes(String(response?.job?.status || ""));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function prepareGenerationRequest(store, runtime, node, request, kind) {
  const preflight = kind === "video_revision"
    ? runtime?.preflightVideoRevision
    : kind === "video"
      ? runtime?.preflightVideo
      : runtime?.preflightKeyframe;
  if (!preflight) return request;
  let working = {
    ...request,
    temporary_asset_exclusions: normalizeAssetExclusions(request.temporary_asset_exclusions),
  };
  while (true) {
    let outcome;
    try {
      outcome = await preflight(working);
    } catch (error) {
      if (missingPreflightRouteError(error)) {
        throw new Error(staleRuntimePreflightMessage(kind));
      }
      throw error;
    }
    const unconnectedNamed = unconnectedLabelMatchedAssets(outcome);
    if (unconnectedNamed.length) {
      const labels = unconnectedNamed.map((asset) => asset.label || asset.asset_id).join(", ");
      throw new Error(
        `named_asset_not_connected_fail_closed: prompt mentions fixed asset(s) that are not connected to this node: ${labels}. Connect them first or exclude them for this run.`,
      );
    }
    const included = Array.isArray(outcome?.included_assets) ? outcome.included_assets : [];
    if (!included.length) return { ...working, preflight_token: outcome?.preflight_token || null };
    const decision = await showCarryConfirmModal(outcome, node, kind);
    if (decision.action === "cancel") return null;
    if (decision.action === "continue") return { ...working, preflight_token: outcome?.preflight_token || null };
    const nextExclusions = mergeAssetExclusions(working.temporary_asset_exclusions, decision.assetIds);
    if (nextExclusions.length === working.temporary_asset_exclusions.length) continue;
    store.set((s) => {
      const n = s.nodes[node.id];
      if (n) n.params.temporaryAssetExclusions = nextExclusions;
    }, { history: false });
    working = { ...working, temporary_asset_exclusions: nextExclusions, preflight_token: null };
  }
}

function unconnectedLabelMatchedAssets(preflight) {
  return buildAssetReferenceActions(preflight).filter((action) => action.blocking);
}

function missingPreflightRouteError(error) {
  return Number(error?.status) === 404 && String(error?.route || "").endsWith("/preflight");
}

function staleRuntimePreflightMessage(kind) {
  const label = kind === "video_revision" ? "video revision" : kind === "video" ? "video" : "keyframe";
  return `Runtime Service version is stale or not started from this branch: missing ${label} preflight route. Restart the 8790 Runtime Service and retry.`;
}

function showCarryConfirmModal(preflight, node, kind) {
  return new Promise((resolve) => {
    const included = Array.isArray(preflight?.included_assets) ? preflight.included_assets : [];
    const excluded = Array.isArray(preflight?.excluded_assets) ? preflight.excluded_assets : [];
    const conflicts = Array.isArray(preflight?.asset_conflicts) ? preflight.asset_conflicts : [];
    const overrides = Array.isArray(preflight?.context_bundle?.temporary_lock_overrides)
      ? preflight.context_bundle.temporary_lock_overrides
      : [];
    const tempExcluded = excluded.filter((item) => item.reason === "temporary_asset_excluded_by_user");
    const subjectId = preflight?.subject_reference_asset_id || "";
    const modal = el("div", "modal compact generation-carry-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "生成前确认"));
    head.appendChild(el("span", "head-spacer"));
    const closeBtn = el("button", "modal-close");
    closeBtn.textContent = "×";
    head.appendChild(closeBtn);

    const body = el("div", "modal-body generation-carry-body");
    body.appendChild(el("p", "carry-note", `${kind === "video" ? "视频" : "图片"}生成将携带以下固定资产。固定资产会约束结果，即使未检测到冲突也会生效。`));
    const list = el("div", "carry-asset-list");
    const checks = new Map();
    for (const asset of included) {
      const row = el("label", "carry-asset-row");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = asset.asset_id;
      checks.set(asset.asset_id, input);
      const text = el("span", "carry-asset-text");
      text.textContent = `${asset.asset_type === "scene" ? "场景" : "人物"} · ${asset.label || asset.asset_id}${asset.asset_id === subjectId ? " · 主体参考图" : ""}`;
      const sig = el("small", "", asset.signature || asset.detail_level || "");
      row.append(input, text, sig);
      list.appendChild(row);
    }
    body.appendChild(list);
    const warningBox = el("div", conflicts.length ? "carry-warning" : "carry-muted");
    warningBox.textContent = conflicts.length
      ? `检测到 ${conflicts.length} 条疑似冲突；未排除资产或解除锁定时，固定资产约束优先生效。`
      : "未检测到明显冲突，但固定资产仍会约束结果。";
    body.appendChild(warningBox);
    if (overrides.length) {
      body.appendChild(el("div", "carry-muted", `本次已解除 ${overrides.length} 条锁定。`));
    }
    if (tempExcluded.length) {
      body.appendChild(el("div", "carry-muted", `本次已排除 ${tempExcluded.length} 项资产。`));
    }

    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const exclude = el("button", "ghost-btn", "本次不携带选中项");
    const submit = el("button", "primary-btn", "继续生成");
    exclude.disabled = true;
    actions.append(cancel, exclude, submit);
    modal.append(head, body, actions);

    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve({ action: "cancel" }); } });
    const finish = (decision) => {
      if (settled) return;
      settled = true;
      close();
      resolve(decision);
    };
    const selectedIds = () => [...checks.entries()].filter(([, input]) => input.checked).map(([assetId]) => assetId);
    list.addEventListener("change", () => {
      exclude.disabled = selectedIds().length === 0;
    });
    closeBtn.addEventListener("click", () => finish({ action: "cancel" }));
    cancel.addEventListener("click", () => finish({ action: "cancel" }));
    submit.addEventListener("click", () => finish({ action: "continue" }));
    exclude.addEventListener("click", () => finish({ action: "exclude", assetIds: selectedIds() }));
  });
}

function normalizeStringList(values) {
  const seen = new Set();
  const result = [];
  for (const value of Array.isArray(values) ? values : []) {
    const item = String(value || "").trim().slice(0, 80);
    if (!item || seen.has(item)) continue;
    seen.add(item);
    result.push(item);
  }
  return result;
}

function normalizeAssetExclusions(values) {
  const seen = new Set();
  const result = [];
  for (const item of Array.isArray(values) ? values : []) {
    const assetId = String(item?.asset_id || item?.assetId || item || "").trim();
    if (!assetId || seen.has(assetId)) continue;
    seen.add(assetId);
    result.push({ asset_id: assetId, reason: String(item?.reason || "one_run_asset_exclusion").slice(0, 120) });
  }
  return result;
}

function mergeAssetExclusions(existing, assetIds) {
  const result = normalizeAssetExclusions(existing);
  const seen = new Set(result.map((item) => item.asset_id));
  for (const assetId of assetIds || []) {
    const id = String(assetId || "").trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    result.push({ asset_id: id, reason: "user_excluded_from_preflight_confirmation" });
  }
  return result;
}

function clearOneRunOverrides(store, nodeId, options = {}) {
  const clearLocks = options.locks !== false;
  const clearAssets = options.assets !== false;
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    if (clearLocks) n.params.temporaryLockOverrides = [];
    if (clearAssets) n.params.temporaryAssetExclusions = [];
  }, { history: false });
}

function generationRestoreSnapshot(node) {
  return {
    status: node.status,
    result: node.result,
    previewUrl: node.previewUrl,
  };
}

function restoreCancelledGeneration(store, nodeId, previous = null) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    if (previous) {
      n.status = previous.status || ((previous.previewUrl || previous.result) ? "complete" : "empty");
      n.result = previous.result || "";
      n.previewUrl = previous.previewUrl || null;
      return;
    }
    n.status = (n.previewUrl || n.result) ? "complete" : "empty";
    n.result = n.result || "";
  }, { history: false });
}

function keyframeResultText(response, request, succeeded) {
  {
    const jobId = response?.job?.job_id || "not_available";
    const status = response?.job?.status || "blocked";
    const outputCount = response?.safe_manifest?.output_count ?? 0;
    if (["submitted", "running", "pending"].includes(status)) {
      return [
        "图像生成中，预览完成后会自动更新到节点。",
        `Job: ${jobId}`,
      ].join("\n");
    }
    if (!succeeded) {
      const reason = response?.safe_manifest?.blocks?.[0]?.reason || "image generation service is not ready";
      return [
        "图像生成未完成，本次没有可用预览。",
        `状态: ${status}`,
        `原因: ${reason}`,
      ].join("\n");
    }
    return [
      "关键帧已生成",
      `Job: ${jobId}`,
      `请求比例: ${request.aspect_ratio}`,
      `候选数量: ${outputCount}`,
      response?.reusable_image_assets?.[0]?.asset_id ? `Reference Asset: ${response.reusable_image_assets[0].asset_id}` : null,
      response?.candidate_previews?.[0]?.preview_url ? "预览已从 Runtime 安全端点加载。" : "未返回预览地址。",
    ].filter(Boolean).join("\n");
  }
  const jobId = response?.job?.job_id || "not_available";
  const outputCount = response?.safe_manifest?.output_count ?? 0;
  if (!succeeded) {
    return [
      "图像生成服务未就绪，本次没有发起有效生成。",
      "处理：请检查本机图像 provider 配置与 Runtime 启动环境，然后在节点菜单重试。",
      "技术细节已写入本次 safe manifest 与 run trace。",
    ].join("\n");
  }
  return [
    "关键帧已生成",
    `Job: ${jobId}`,
    `请求比例: ${request.aspect_ratio}`,
    `候选数量: ${outputCount}`,
    response?.reusable_image_assets?.[0]?.asset_id ? `Reference Asset: ${response.reusable_image_assets[0].asset_id}` : null,
    response?.candidate_previews?.[0]?.preview_url ? "预览已从 Runtime 安全 artifact 端点加载。" : "未返回预览地址。",
  ].filter(Boolean).join("\n");
}

function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  const clean = message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>");
  if (/AFS_ALLOW_REMOTE_|provider service not found|provider gate is closed|Remote .* calls are disabled/i.test(clean)) {
    return "provider 服务未就绪，请检查本机配置与 Runtime 启动环境后重试。";
  }
  return clean.slice(0, 160);
}

function setNodeError(store, nodeId, message) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    n.status = "error";
    n.result = message;
  });
}

export function visibleAssetForNode(store, node) {
  const kind = assetKind(node.type);
  return {
    id: store.nextId("asset"),
    kind,
    title: assetTitle(node),
    safe_summary: assetSummary(node),
    thumbnail_ref: thumbnailForKind(kind),
    source_node_id: node.id,
    status: "ready",
  };
}

function reconcileVisualAssetBadges(node, bundle) {
  const current = Array.isArray(node.params?.visualAssets) ? node.params.visualAssets : [];
  if (!current.length || !bundle) return;
  const included = new Set((bundle.included_assets || []).map((item) => String(item.asset_id || "")));
  const excluded = new Map((bundle.excluded_assets || []).map((item) => [String(item.asset_id || ""), item]));
  node.params.visualAssets = current.map((asset) => {
    const assetId = String(asset?.asset_id || asset?.assetId || asset || "");
    if (included.has(assetId)) return { ...asset, runtime_status: "included", disabled_reason: "" };
    const miss = excluded.get(assetId);
    if (!miss) return asset;
    if (["retired_or_missing_visual_asset", "superseded_by_newer_label_version"].includes(miss.reason)) {
      return {
        ...asset,
        status: asset.status || "fixed",
        runtime_status: "excluded",
        disabled_reason: "已失效，本次未携带",
        excluded_reason: miss.reason,
      };
    }
    return asset;
  });
}

function assetKind(type) {
  return {
    text: "text_brief",
    image: "keyframe",
    video: "video_clip",
    audio: "audio_clip",
    script: "storyboard",
    director: "director_setup",
    video_merge: "video_comp",
  }[type] || "reference";
}

function assetTitle(node) {
  const fallback = {
    text: "文本创作摘要",
    image: "关键帧预览",
    video: "5s 视频片段预览",
    audio: "音频预览",
    script: "分镜脚本预览",
    director: "导演台布置",
    video_merge: "合成预览",
  }[node.type] || "显性资产";
  return node.title || fallback;
}

function assetSummary(node) {
  if (node.type === "director" && node.params?.directorSummary) return node.params.directorSummary;
  const prompt = (node.prompt || node.result || node.content || "").replace(/\s+/g, " ").trim();
  return prompt.slice(0, 90) || "生成后的安全摘要会在这里显示。";
}

function thumbnailForKind(kind) {
  return {
    text_brief: "text",
    keyframe: "keyframe",
    video_clip: "video",
    audio_clip: "audio",
    storyboard: "storyboard",
    director_setup: "director-board",
    video_comp: "video",
  }[kind] || "reference";
}
