import { createNode, connect } from "./nodes.js";
import { buildKeyframeGenerationRequest } from "./optimizer-contract.js";
import { isRemoteImageModel } from "./presets/models.js";
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

// 发送（Ctrl+Enter / 发送按钮）：图片节点可走远程 keyframe，其他节点保持本地安全预览。
export async function startNodeGeneration(store, runtime, node, resultText) {
  const fresh = store.get().nodes[node.id] || node;
  if (fresh.type === "image" && isRemoteImageModel(fresh.params?.model) && runtime?.generateKeyframe) {
    await startRemoteKeyframeGeneration(store, runtime, fresh);
    return;
  }
  startLocalPreview(store, fresh, resultText);
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
    return `MiniMax 关键帧生成被阻止\nGate: ${gate}\n原因: ${blocker}`;
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

export function startLocalPreview(store, node, resultText) {
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
  });
  setTimeout(() => {
    store.set((s) => {
      const n = s.nodes[node.id];
      if (!n) return;
      n.status = "complete";
      n.result = resultText || buildPreviewResult(n);
      const asset = visibleAssetForNode(store, n);
      s.assets.unshift({
        ...asset,
        created_at: new Date().toISOString(),
      });
    });
  }, 1200);
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

function buildPreviewResult(node) {
  const prompt = (node.prompt || "").trim();
  const head = {
    text: "文本结果（本地预览）",
    image: "图片结果占位（本地预览）",
    video: "视频结果占位（本地预览）",
    audio: "音频结果占位（本地预览）",
    script: "分镜脚本占位（本地预览）",
    video_merge: "合成结果占位（本地预览）",
  }[node.type] || "结果占位（本地预览）";
  return `${head}\n${prompt ? `提示词：${prompt}` : "（未输入提示词）"}`;
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
  return prompt.slice(0, 90) || "本地预览生成的安全摘要，可作为后续节点参考。";
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
