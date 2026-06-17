import { mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { safeError, setNodeError } from "./node-action-utils.js";

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
