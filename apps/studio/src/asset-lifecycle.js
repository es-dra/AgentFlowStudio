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

export function currentAssetLibraryAssets(assets = []) {
  const list = Array.isArray(assets) ? assets : [];
  const visualRefs = visualImageAssetRefs(list);
  const latestRenderable = latestRenderableAssetBySource(list, visualRefs);
  return list.filter((asset) => {
    if (isVisualAsset(asset)) return true;
    if (!isRenderableImageAsset(asset)) return true;
    const id = assetIdentity(asset);
    if (visualRefs.has(id)) return false;
    return latestRenderable.has(id);
  });
}

export function historicalAssetLibraryAssets(assets = [], tabId = "image") {
  const list = Array.isArray(assets) ? assets : [];
  const currentIds = new Set(currentAssetLibraryAssets(list).map(assetIdentity).filter(Boolean));
  return list
    .filter((asset) => matchesHistoryTab(asset, tabId))
    .filter((asset) => {
      if (isVisualAsset(asset)) return false;
      const id = assetIdentity(asset);
      return id && !currentIds.has(id);
    })
    .sort((a, b) => assetCreatedAtMs(b) - assetCreatedAtMs(a));
}

export function latestRenderableAssetBySource(assets = [], visualRefs = visualImageAssetRefs(assets)) {
  const latestBySource = new Map();
  (Array.isArray(assets) ? assets : []).forEach((asset, index) => {
    if (!isRenderableImageAsset(asset) || assetLifecycleState(asset) === "retired") return;
    const id = assetIdentity(asset);
    if (!id || visualRefs.has(id)) return;
    const key = renderableSourceKey(asset);
    const created = assetCreatedAtMs(asset);
    const previous = latestBySource.get(key);
    if (!previous || created > previous.created || (created === previous.created && index < previous.index)) {
      latestBySource.set(key, { id, created, index });
    }
  });
  return new Set([...latestBySource.values()].map((item) => item.id));
}

export function visualImageAssetRefs(assets = []) {
  const refs = new Set();
  for (const asset of Array.isArray(assets) ? assets : []) {
    if (!isVisualAsset(asset)) continue;
    for (const ref of asset.image_asset_refs || asset.source_image_asset_refs || []) {
      const id = String(ref || "").trim();
      if (id) refs.add(id);
    }
  }
  return refs;
}

function matchesHistoryTab(asset, tabId) {
  const kind = String(asset?.kind || "").toLowerCase();
  if (tabId === "video") return ["video_clip", "video_comp", "video"].includes(kind);
  if (tabId === "audio") return ["audio_clip", "audio"].includes(kind);
  return isRenderableImageAsset(asset);
}

function isVisualAsset(asset) {
  const kind = String(asset?.kind || "").toLowerCase();
  return kind === "visual_asset"
    || kind === "character_asset"
    || kind === "scene_asset"
    || kind === "prop_asset"
    || Boolean(asset?.visual_asset_id);
}

function isRenderableImageAsset(asset) {
  const kind = String(asset?.kind || "").toLowerCase();
  const role = String(asset?.role || asset?.safe_summary || "").toLowerCase();
  return Boolean(asset?.asset_id)
    && (
      kind === "image_reference"
      || kind === "keyframe"
      || kind === "character_turnaround"
      || kind === "scene_board"
      || kind === "character_asset_candidate"
      || kind === "scene_asset_candidate"
      || kind === "prop_asset_candidate"
      || role === "generated_keyframe_reference"
      || role.endsWith("_reference")
    );
}

function renderableSourceKey(asset) {
  const source = String(asset?.source_node_id || "").trim();
  if (source) return source;
  return assetIdentity(asset);
}

function assetIdentity(asset) {
  return String(asset?.asset_id || asset?.visual_asset_id || asset?.id || "").trim();
}

function assetCreatedAtMs(asset) {
  const parsed = Date.parse(String(asset?.created_at || asset?.updated_at || ""));
  return Number.isFinite(parsed) ? parsed : 0;
}
