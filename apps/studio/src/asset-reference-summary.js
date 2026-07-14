export const MAX_CARRY_CHAIN_ITEMS = 4;

export function assetIdFromRef(ref) {
  return String(ref?.asset_id || ref?.assetId || ref?.visual_asset_id || ref || "").trim();
}

export function assetLabel(ref) {
  return String(ref?.label || ref?.title || ref?.signature || "未命名素材").trim();
}

export function assetTypeLabel(ref) {
  const type = String(ref?.asset_type || ref?.type || "").toLowerCase();
  if (type === "scene") return "场景";
  if (type === "character") return "角色";
  if (type === "prop") return "道具";
  return "资产";
}

export function assetCarryState(ref) {
  const runtime = String(ref?.runtime_status || "").toLowerCase();
  const status = String(ref?.status || "").toLowerCase();
  const reason = String(ref?.excluded_reason || ref?.reason || "").toLowerCase();
  if (runtime === "included" || ref?.connected || ref?.injected) return "included";
  if (runtime === "excluded" || status === "retired" || reason.includes("retired")) return "excluded";
  if (reason.includes("superseded")) return "superseded";
  if (reason.includes("degraded")) return "degraded";
  return "candidate";
}

export function assetCarryLabel(ref) {
  const state = assetCarryState(ref);
  if (state === "included") return "本次携带";
  if (state === "excluded") return "本次未携带";
  if (state === "superseded") return "已被新版本替代";
  if (state === "degraded") return "仅签名参与";
  return "候选资产";
}

export function assetsFromNode(node) {
  return Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : [];
}

export function assetsFromBundle(bundle) {
  if (!bundle) return [];
  const included = Array.isArray(bundle.included_assets) ? bundle.included_assets : [];
  const excluded = Array.isArray(bundle.excluded_assets) ? bundle.excluded_assets : [];
  return [
    ...included.map((item) => ({ ...item, runtime_status: "included" })),
    ...excluded.map((item) => ({ ...item, runtime_status: "excluded" })),
  ];
}

export function carryChainItems(node) {
  const fromBundle = assetsFromBundle(node?.params?.lastContextBundle);
  const items = fromBundle.length ? fromBundle : assetsFromNode(node);
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const id = assetIdFromRef(item);
    if (!id || seen.has(id)) continue;
    seen.add(id);
    result.push(item);
    if (result.length >= MAX_CARRY_CHAIN_ITEMS) break;
  }
  return result;
}

export function subjectSuffix(item, bundle) {
  return bundle?.subject_reference_asset_id && assetIdFromRef(item) === String(bundle.subject_reference_asset_id)
    ? "（含参考图）"
    : "";
}
