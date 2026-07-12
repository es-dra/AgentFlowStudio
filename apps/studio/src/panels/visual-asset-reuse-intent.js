import { graphBoundVisualAssetsForShot } from "../asset-auto-binding-refs.js";

export const VISUAL_ASSET_REUSE_INTENTS = Object.freeze(["link_existing", "replace", "create_new"]);

export function visualAssetPromotionReuseChoices(state, node, { assetType, label } = {}) {
  const candidates = matchingFixedAssets(state, node, { assetType, label });
  return {
    requires_intent: candidates.length > 0,
    candidate_count: candidates.length,
    candidates,
    intents: [...VISUAL_ASSET_REUSE_INTENTS],
  };
}

export function matchingFixedAssets(state, node, { assetType, label } = {}) {
  const type = safeAssetType(assetType);
  const labelKey = normalizedLabel(label);
  if (!labelKey) return [];
  const result = [];
  const seen = new Set();
  const add = (asset, source, options = {}) => {
    const assetId = assetIdFromRef(asset);
    if (!assetId || seen.has(assetId)) return;
    if (!isFixed(asset)) return;
    if (safeAssetType(asset.asset_type) !== type) return;
    if (options.requireLabelMatch !== false && normalizedLabel(asset.label || asset.title) !== labelKey) return;
    seen.add(assetId);
    result.push({
      asset_id: assetId,
      asset_type: type,
      label: cleanText(asset.label || asset.title, 80),
      status: cleanText(asset.status || asset.asset_status || "fixed", 40),
      source,
      graph_bound: Boolean(asset.graph_bound),
    });
  };

  for (const asset of graphBoundAssetsForNode(node)) add(asset, "graph_bound", { requireLabelMatch: false });
  for (const asset of Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : []) add(asset, "node_visual_asset");
  for (const asset of Object.values(state?.nodes || {}).flatMap((item) => item?.params?.visualAssets || [])) add(asset, "canvas_node");
  for (const asset of Array.isArray(state?.assets) ? state.assets : []) add(asset, "asset_library");
  return result.slice(0, 8);
}

export function primaryReuseCandidate(choices) {
  return Array.isArray(choices?.candidates) ? choices.candidates[0] || null : null;
}

export function assetIdFromRef(asset) {
  return String(asset?.asset_id || asset?.visual_asset_id || asset?.assetId || "").trim();
}

function graphBoundAssetsForNode(node) {
  const params = node?.params || {};
  const graph = params.assetAutoBindingGraph
    || params.asset_auto_binding_graph
    || params.storyboardBreakdown?.assetAutoBindingGraph
    || params.storyboardBreakdown?.asset_auto_binding_graph
    || null;
  const shot = params.structuredShot || { asset_refs: params.shotAssetRefs || [] };
  return graphBoundVisualAssetsForShot(graph, shot);
}

function isFixed(asset) {
  return ["fixed", "ready"].includes(String(asset?.status || asset?.asset_status || "fixed"));
}

function safeAssetType(value) {
  const text = String(value || "").trim();
  return ["character", "scene", "prop"].includes(text) ? text : "character";
}

function cleanText(value, limit) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function normalizedLabel(value) {
  return String(value || "").replace(/^@+/, "").replace(/[^0-9A-Za-z\u4e00-\u9fff]+/g, "").toLowerCase();
}
