export function mergeImageAssets(existing, asset) {
  const items = Array.isArray(existing) ? [...existing] : [];
  const assetId = String(asset?.asset_id || asset?.assetId || "").trim();
  if (!assetId) return items;
  return [...items.filter((item) => String(item?.asset_id || item?.assetId || "") !== assetId), asset];
}

export function lastImageAsset(node) {
  const uploads = Array.isArray(node?.params?.uploads) ? node.params.uploads : [];
  return uploads[uploads.length - 1] || null;
}

export function resizeNodeForImagePreview(node, preview, fallbackAspectRatio) {
  const [wRatio, hRatio] = previewRatio(preview, fallbackAspectRatio);
  const portrait = hRatio >= wRatio;
  const width = portrait ? 340 : 420;
  const imageWidth = width - 56;
  const imageHeight = Math.round(imageWidth * (hRatio / wRatio));
  node.w = width;
  node.h = Math.max(260, Math.min(720, imageHeight + 92));
  node.params.previewAspectRatio = `${wRatio}:${hRatio}`;
}

function previewRatio(preview, fallbackAspectRatio) {
  const width = Number(preview?.width || 0);
  const height = Number(preview?.height || 0);
  if (width > 0 && height > 0) return [width, height];
  return parseRatio(preview?.aspect_ratio || fallbackAspectRatio);
}

function parseRatio(value) {
  const match = String(value || "").match(/^(\d+):(\d+)$/);
  if (!match) return [9, 16];
  const w = Math.max(1, Number(match[1]));
  const h = Math.max(1, Number(match[2]));
  return [w, h];
}
