export const ASSET_LIFECYCLE_FILTERS = [
  { id: "all", label: "全部" },
  { id: "fixed", label: "已确认" },
  { id: "draft", label: "候选" },
  { id: "retired", label: "停用" },
];

export function assetLifecycleState(asset) {
  const status = String(asset?.status || asset?.asset_status || "").toLowerCase();
  const runtime = String(asset?.runtime_status || "").toLowerCase();
  const kind = String(asset?.kind || "").toLowerCase();
  const type = String(asset?.asset_type || asset?.type || "").toLowerCase();

  if (status === "retired" || runtime === "excluded") return "retired";
  if (status === "rejected") return "rejected";
  if (status === "draft" || runtime === "candidate" || kind.endsWith("_candidate")) return "draft";
  if (
    kind === "visual_asset"
    || kind === "character_asset"
    || kind === "scene_asset"
    || kind === "prop_asset"
    || type === "character"
    || type === "scene"
    || type === "prop"
  ) return "fixed";
  return "draft";
}

export function assetLifecycleLabel(asset) {
  return {
    fixed: "已确认",
    draft: "候选",
    retired: "已停用",
    rejected: "已拒绝",
  }[assetLifecycleState(asset)] || "候选";
}

export function assetLifecycleSummary(assets = []) {
  const counts = { fixed: 0, draft: 0, rejected: 0, retired: 0 };
  for (const asset of assets || []) counts[assetLifecycleState(asset)] += 1;
  return {
    ...counts,
    active: counts.fixed,
    total: (assets || []).length,
  };
}

export function matchesAssetLifecycleFilter(asset, filter) {
  const value = String(filter || "all");
  if (value === "all") return true;
  if (value === "draft") return ["draft", "rejected"].includes(assetLifecycleState(asset));
  return assetLifecycleState(asset) === value;
}
