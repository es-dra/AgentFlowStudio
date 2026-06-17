export function reconcileVisualAssetBadges(node, bundle) {
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
