import { mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { safeError, setNodeError } from "./node-action-utils.js";

const IMAGE_UPLOAD_ACCEPT = "image/png,image/jpeg";
const ACCEPTED_IMAGE_MIME_TYPES = new Set(["image/png", "image/jpeg", "image/jpg"]);
const IMAGE_UPLOAD_NODE_TYPES = new Set(["image", "video", "ref", "character", "location", "prop", "shot"]);

export function uploadNodeImage(store, runtime, node) {
  if (!runtime?.uploadImageAsset) {
    setNodeError(store, node.id, "Runtime image upload API is not available.");
    return;
  }
  const input = document.createElement("input");
  input.type = "file";
  input.accept = IMAGE_UPLOAD_ACCEPT;
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

export async function uploadSelectedImage(store, runtime, nodeId, file) {
  const initialNode = store.get().nodes?.[nodeId];
  const targetError = unsupportedUploadTargetMessage(initialNode);
  if (targetError) {
    setNodeError(store, nodeId, targetError);
    return;
  }
  const fileError = unsupportedImageFileMessage(file);
  if (fileError) {
    setNodeError(store, nodeId, `图片上传失败: ${fileError}`);
    return;
  }
  const policy = referenceUploadPolicyForNode(initialNode);
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    n.status = "generating";
    n.result = policy.uploadingText;
  });
  try {
    const dataBase64 = await readFileAsBase64(file);
    const response = await runtime.uploadImageAsset({
      node_id: nodeId,
      filename: file.name || "reference.png",
      mime_type: file.type || "application/octet-stream",
      data_base64: dataBase64,
      role: policy.role,
      reference_target: policy.referenceTarget,
      user_intent: policy.userIntent,
      generated_at: new Date().toISOString(),
    });
    const asset = response?.asset;
    if (!asset?.asset_id || !asset?.preview_url) throw new Error("Runtime did not return an image asset");
    store.set((s) => {
      const n = s.nodes[nodeId];
      if (!n) return;
      if (!n.params || typeof n.params !== "object") n.params = {};
      const latestPolicy = referenceUploadPolicyForNode(n);
      const uploadRef = imageUploadRef(asset, file, latestPolicy);
      n.status = "complete";
      n.previewUrl = asset.preview_url;
      n.result = uploadResultText(uploadRef);
      n.params.uploads = mergeImageAssets(n.params.uploads || [], uploadRef).slice(-4);
      if (n.type === "video" && latestPolicy.role === "first_frame") {
        n.params.firstFrameImageAssetId = uploadRef.asset_id;
        n.params.firstFramePreviewUrl = uploadRef.preview_url;
        n.params.videoInputSource = {
          source_mode: "uploaded_image",
          source_asset_id: uploadRef.asset_id,
          source_node_id: n.id,
          source_job_id: null,
          visual_asset_id: null,
          role: "first_frame",
          user_intent: uploadRef.user_intent,
        };
      }
      resizeNodeForImagePreview(n, uploadRef, n.params?.spec?.ratio);
      s.assets.unshift({
        id: store.nextId("asset"),
        kind: "image_reference",
        title: n.title,
        safe_summary: uploadRef.user_intent || file.name || asset.asset_id,
        thumbnail_ref: "keyframe",
        source_node_id: n.id,
        status: "ready",
        asset_id: asset.asset_id,
        preview_url: asset.preview_url,
        role: uploadRef.role,
        reference_target: uploadRef.reference_target,
        user_intent: uploadRef.user_intent,
        created_at: new Date().toISOString(),
      });
    });
    await store.flushRuntimeSave?.();
  } catch (error) {
    setNodeError(store, nodeId, `图片上传失败: ${safeError(error)}`);
  }
}

function unsupportedUploadTargetMessage(node) {
  if (!node) return "没有找到要绑定参考图的节点，请先选择或创建一个参考、角色、场景、道具、镜头、图片或视频节点。";
  if (!IMAGE_UPLOAD_NODE_TYPES.has(node.type)) return "当前节点不支持直接绑定参考图，请选择参考、资产、镜头、图片或视频节点。";
  return "";
}

function unsupportedImageFileMessage(file) {
  const mimeType = String(file?.type || "").trim().toLowerCase();
  const filename = String(file?.name || "").trim().toLowerCase();
  if (mimeType && !ACCEPTED_IMAGE_MIME_TYPES.has(mimeType)) {
    return "仅支持 PNG 或 JPEG 图片，请重新选择参考图。";
  }
  if (!mimeType && /\.[a-z0-9]+$/i.test(filename) && !/\.(png|jpe?g)$/i.test(filename)) {
    return "仅支持 PNG 或 JPEG 图片，请重新选择参考图。";
  }
  return "";
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

export function referenceUploadPolicyForNode(node) {
  const userIntent = safeUserIntent(
    node?.params?.referenceIntent
    || node?.params?.intent
    || node?.prompt
    || node?.content
    || node?.title,
  );
  if (node?.type === "video") {
    return {
      role: "first_frame",
      referenceTarget: "video_first_frame",
      userIntent,
      uploadingText: "正在上传视频首帧参考图...",
    };
  }
  if (node?.type === "character") {
    return {
      role: "asset_reference",
      referenceTarget: "character_reference",
      userIntent,
      uploadingText: "正在上传角色参考图...",
    };
  }
  if (node?.type === "location") {
    return {
      role: "asset_reference",
      referenceTarget: "location_reference",
      userIntent,
      uploadingText: "正在上传场景空间参考图...",
    };
  }
  if (node?.type === "prop") {
    return {
      role: "asset_reference",
      referenceTarget: "prop_reference",
      userIntent,
      uploadingText: "正在上传道具参考图...",
    };
  }
  if (node?.type === "ref") {
    return {
      role: "reference_set",
      referenceTarget: "reference_set",
      userIntent,
      uploadingText: "正在上传参考集图片...",
    };
  }
  if (node?.type === "shot") {
    return {
      role: "reference_image",
      referenceTarget: "shot_reference",
      userIntent,
      uploadingText: "正在上传镜头参考图...",
    };
  }
  if (node?.params?.assetCardDraft || node?.params?.nodeRole === "asset_card_draft") {
    return {
      role: "asset_reference",
      referenceTarget: "asset_card_draft",
      userIntent,
      uploadingText: "正在上传资产卡参考图...",
    };
  }
  if (node?.params?.nodeRole === "keyframe_generation" || node?.params?.keyframeLayer) {
    return {
      role: "reference_image",
      referenceTarget: "keyframe_generation",
      userIntent,
      uploadingText: "正在上传关键帧参考图...",
    };
  }
  return {
    role: "reference_image",
    referenceTarget: "image_reference",
    userIntent,
    uploadingText: "正在上传参考图...",
  };
}

function imageUploadRef(asset, file, policy) {
  return {
    ...asset,
    asset_id: String(asset.asset_id || ""),
    filename: file.name || asset.filename || `${asset.asset_id}.png`,
    preview_url: asset.preview_url || "",
    width: asset.width || null,
    height: asset.height || null,
    aspect_ratio: asset.aspect_ratio || null,
    mime_type: asset.mime_type || file.type || null,
    media_kind: "image",
    role: policy.role,
    reference_target: policy.referenceTarget,
    user_intent: policy.userIntent,
    source_mode: policy.role === "first_frame" ? "uploaded_image" : "node_upload",
  };
}

function uploadResultText(uploadRef) {
  const lines = [
    uploadRef.reference_target === "video_first_frame" ? "已上传视频首帧参考图" : "已上传参考图",
    `用途：${referenceTargetLabel(uploadRef.reference_target)}`,
    `尺寸：${uploadRef.width || "?"}x${uploadRef.height || "?"}`,
  ];
  if (uploadRef.user_intent) lines.push(`说明：${uploadRef.user_intent}`);
  return lines.join("\n");
}

function referenceTargetLabel(value) {
  return {
    video_first_frame: "视频首帧",
    character_reference: "角色参考",
    location_reference: "场景空间参考",
    prop_reference: "道具参考",
    reference_set: "参考集",
    shot_reference: "镜头参考",
    asset_card_draft: "资产设定卡",
    keyframe_generation: "关键帧参考",
    image_reference: "图片参考",
  }[String(value || "")] || "参考素材";
}

function safeUserIntent(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .replace(/[\\/]/g, "")
    .trim()
    .slice(0, 240);
}
