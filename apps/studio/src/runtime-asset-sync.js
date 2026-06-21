export async function syncRuntimeAssets(store, runtime) {
  const [imagePayload, visualPayload] = await Promise.allSettled([
    runtime.listImageAssets?.(),
    runtime.listVisualAssets?.("fixed"),
  ]);
  const imageAssets = imagePayload.status === "fulfilled" && Array.isArray(imagePayload.value?.assets)
    ? imagePayload.value.assets
    : [];
  const visualAssets = visualPayload.status === "fulfilled" && Array.isArray(visualPayload.value?.assets)
    ? visualPayload.value.assets
    : [];
  const imagePreviewById = new Map(
    imageAssets.map((asset) => [asset.asset_id, asset.preview_url]).filter(([assetId, previewUrl]) => assetId && previewUrl),
  );
  store.set((s) => {
    const existingByKey = new Map();
    for (const item of s.assets || []) {
      const key = assetStableKey(item);
      if (key && !existingByKey.has(key)) existingByKey.set(key, item);
    }
    const generated = [
      ...visualAssets.map((asset) => visualAssetProjection(asset, runtime, imagePreviewById)),
      ...imageAssets.map(imageAssetProjection),
    ].map((item) => mergeAsset(existingByKey.get(assetStableKey(item)), item));
    const generatedKeys = new Set(generated.map(assetStableKey).filter(Boolean));
    s.assets = [
      ...generated,
      ...s.assets.filter((item) => {
        const key = assetStableKey(item);
        return !key || !generatedKeys.has(key);
      }),
    ];
  }, { history: false });
}

function visualAssetProjection(asset, runtime, imagePreviewById) {
  return {
    id: `visual_${asset.asset_id}`,
    kind: asset.asset_type === "scene" ? "scene_asset" : asset.asset_type === "prop" ? "prop_asset" : "character_asset",
    title: asset.label || asset.asset_id,
    safe_summary: asset.signature || "",
    thumbnail_ref: asset.asset_type === "scene" ? "scene-board" : asset.asset_type === "prop" ? "prop-sheet" : "character-sheet",
    source_node_id: asset.source_node_id || null,
    status: asset.status || "fixed",
    asset_id: asset.asset_id,
    visual_asset_id: asset.asset_id,
    asset_type: asset.asset_type || null,
    image_asset_refs: Array.isArray(asset.image_asset_refs) ? asset.image_asset_refs : [],
    preview_url: visualAssetPreviewUrl(asset, runtime, imagePreviewById),
  };
}

function imageAssetProjection(asset) {
  return {
    id: `image_${asset.asset_id}`,
    kind: "image_reference",
    title: asset.filename || asset.asset_id,
    safe_summary: asset.role || "image asset",
    thumbnail_ref: "keyframe",
    source_node_id: asset.source_node_id || null,
    status: "ready",
    asset_id: asset.asset_id,
    preview_url: asset.preview_url || "",
  };
}

function assetStableKey(asset) {
  const visualId = String(asset?.visual_asset_id || (isVisualAssetKind(asset?.kind) ? asset?.asset_id : "") || "").trim();
  if (visualId) return `visual:${visualId}`;
  const imageId = String(asset?.asset_id || "").trim();
  if (imageId) return `image:${imageId}`;
  return "";
}

function isVisualAssetKind(kind) {
  return ["visual_asset", "character_asset", "scene_asset"].includes(String(kind || ""));
}

function mergeAsset(existing, generated) {
  if (!existing) return generated;
  return {
    ...generated,
    ...existing,
    id: generated.id,
    kind: generated.kind,
    title: generated.title || existing.title,
    safe_summary: generated.safe_summary || existing.safe_summary,
    thumbnail_ref: generated.thumbnail_ref || existing.thumbnail_ref,
    source_node_id: generated.source_node_id || existing.source_node_id || null,
    status: generated.status || existing.status,
    asset_id: generated.asset_id || existing.asset_id,
    visual_asset_id: generated.visual_asset_id || existing.visual_asset_id,
    preview_url: generated.preview_url || existing.preview_url,
    asset_type: generated.asset_type || existing.asset_type,
    image_asset_refs: generated.image_asset_refs || existing.image_asset_refs,
  };
}

function visualAssetPreviewUrl(asset, runtime, imagePreviewById) {
  const refs = Array.isArray(asset?.image_asset_refs) ? asset.image_asset_refs : [];
  const firstRef = String(refs[0] || "").trim();
  if (!firstRef) return "";
  const fromImageList = imagePreviewById.get(firstRef);
  if (fromImageList) return fromImageList;
  return `/projects/${encodeURIComponent(runtime.projectId)}/image-assets/${encodeURIComponent(firstRef)}/preview`;
}
