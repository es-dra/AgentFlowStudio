import { createNode, connect } from "./nodes.js";
import { buildKeyframeGenerationRequest } from "./optimizer-contract.js";
import { isRemoteImageModel, isRemoteVideoModel, providerServiceForVideoModel } from "./presets/models.js";
import { SAMPLE_SCRIPT, SAMPLE_SCRIPT_TITLE } from "./presets/starters.js";
import { openVisualAssetPanel } from "./panels/visual-asset-panel.js";
import { lastImageAsset, mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";

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
    await startRemoteVideoGeneration(store, runtime, fresh);
    return;
  }
  setNodeError(
    store,
    fresh.id,
    resultText || "当前版本仅图片节点支持真实生成；视频、音频、脚本和合成通道仍在开发中。",
  );
}

async function startRemoteVideoGeneration(store, runtime, node) {
  const firstFrame = node.params?.firstFrameImageAssetId;
  if (!firstFrame) {
    setNodeError(store, node.id, "请先在节点菜单中上传图片并设为首帧，再生成图生视频。");
    return;
  }
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    n.result = "视频任务提交中...";
  });
  try {
    const response = await runtime.generateVideo({
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
      context_subgraph: null,
      temporary_lock_overrides: node.params?.temporaryLockOverrides || [],
      quota_override_confirmed: Boolean(node.params?.quotaOverrideConfirmed),
      generated_at: new Date().toISOString(),
    });
    applyVideoResponse(store, node.id, response);
  } catch (error) {
    setNodeError(store, node.id, `Kling video request failed: ${safeError(error)}`);
  }
}

function applyVideoResponse(store, nodeId, response) {
  const status = response?.job?.status || "blocked";
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    n.params.lastVideoJobId = response?.job?.job_id || null;
    n.params.lastVideoPreviewUrl = response?.candidate_previews?.[0]?.preview_url || null;
    n.status = status === "succeeded" ? "complete" : status === "submitted" ? "generating" : "error";
    n.result = videoResultText(response);
  });
}

function videoResultText(response) {
  const status = response?.job?.status || "blocked";
  if (status === "succeeded") return "Kling 视频已完成，预览已通过 Runtime 安全端点加载。";
  if (status === "submitted") return `Kling 视频已提交，可继续轮询。\nJob: ${response?.job?.job_id || "unknown"}`;
  const reason = response?.safe_manifest?.blocks?.[0]?.reason || "video provider is not ready";
  return `视频生成未开始或未完成。\n状态: ${status}\n原因: ${reason}`;
}

function parseDuration(value) {
  const match = String(value || "5").match(/\d+/);
  return match ? Number(match[0]) : 5;
}

async function startRemoteKeyframeGeneration(store, runtime, node) {
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
    n.result = null;
    n.previewUrl = null;
  });
  try {
    const request = buildKeyframeGenerationRequest(store.get(), node);
    const response = await runtime.generateKeyframe(request);
    const succeeded = response?.job?.status === "succeeded";
    store.set((s) => {
      const n = s.nodes[node.id];
      if (!n) return;
      n.status = succeeded ? "complete" : "error";
      const preview = response?.candidate_previews?.[0] || null;
      const reusableAsset = response?.reusable_image_assets?.[0] || null;
      n.previewUrl = preview?.preview_url || null;
      if (n.previewUrl) resizeNodeForImagePreview(n, preview, request.aspect_ratio);
      if (succeeded && reusableAsset?.asset_id) {
        n.params.uploads = mergeImageAssets(n.params.uploads || [], reusableAsset).slice(-4);
      }
      n.params.lastContextBundle = response?.context_bundle || null;
      reconcileVisualAssetBadges(n, response?.context_bundle || null);
      // “本次解除”语义:锁定解除只随单次请求生效,请求发出后即清空,避免静默延续到下一次生成。
      n.params.temporaryLockOverrides = [];
      n.result = keyframeResultText(response, request, succeeded);
      const asset = visibleAssetForNode(store, n);
      s.assets.unshift({
        ...asset,
        safe_summary: (n.prompt || "").slice(0, 90),
        job_id: response?.job?.job_id || null,
        artifact_id: response?.artifacts?.keyframe_generation_safe_manifest?.artifact_id || null,
        asset_id: reusableAsset?.asset_id || null,
        preview_url: n.previewUrl,
        created_at: new Date().toISOString(),
      });
    });
  } catch (error) {
    setNodeError(store, node.id, `MiniMax keyframe request failed: ${safeError(error)}`);
  }
}

function keyframeResultText(response, request, succeeded) {
  const gate = response?.provider_gate?.status || "unknown";
  const jobId = response?.job?.job_id || "not_available";
  const outputCount = response?.safe_manifest?.output_count ?? 0;
  if (!succeeded) {
    const blocker = response?.safe_manifest?.blocks?.[0]?.reason || "remote image provider is not ready";
    return [
      "生成未开始，当前图像 provider gate 未开启或 provider 不可用。",
      `Gate: ${gate}`,
      `原因: ${blocker}`,
      "处理：确认本机已设置 AFS_ALLOW_REMOTE_IMAGE=true，并重启 Runtime Service 后重试。",
    ].join("\n");
  }
  return [
    "MiniMax 关键帧已生成",
    `Job: ${jobId}`,
    `请求比例: ${request.aspect_ratio}`,
    `候选数量: ${outputCount}`,
    response?.reusable_image_assets?.[0]?.asset_id ? `Reference Asset: ${response.reusable_image_assets[0].asset_id}` : null,
    response?.candidate_previews?.[0]?.preview_url ? "预览已从 Runtime 安全 artifact 端点加载。" : "未返回预览地址。",
  ].filter(Boolean).join("\n");
}

function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  return message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 160);
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
