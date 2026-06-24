import { assetIdFromRef } from "./asset-reference-summary.js";

export function assetReferenceCandidates(state, nodeId = "", query = "") {
  const tree = connectedNodeIds(state, nodeId);
  const normalizedQuery = normalize(query);
  const candidates = [
    ...fixedProjectAssets(state),
    ...treeCandidateAssets(state, tree),
  ];
  const seen = new Set();
  return candidates
    .filter((asset) => !normalizedQuery || normalize(asset.label).includes(normalizedQuery))
    .filter((asset) => {
      const key = `${asset.scope}:${asset.asset_type}:${asset.label}:${asset.asset_id || ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 12);
}

function fixedProjectAssets(state) {
  const fromLibrary = (state.assets || [])
    .filter(isFixedVisualAsset)
    .map((asset) => candidateFromVisualAsset(asset, "project_fixed"));
  const fromNodes = Object.values(state.nodes || {})
    .flatMap((node) => (Array.isArray(node.params?.visualAssets) ? node.params.visualAssets : []))
    .filter(isFixedVisualAsset)
    .map((asset) => candidateFromVisualAsset(asset, "project_fixed"));
  return [...fromLibrary, ...fromNodes].filter(Boolean);
}

function treeCandidateAssets(state, tree) {
  if (!tree.size) return [];
  return Object.values(state.nodes || {})
    .filter((node) => tree.has(node.id))
    .map((node) => candidateFromAssetCardNode(node))
    .filter(Boolean);
}

function candidateFromVisualAsset(asset, scope) {
  const assetId = assetIdFromRef(asset);
  const label = String(asset.label || asset.title || assetId || "").trim();
  if (!label || !assetId || isRetired(asset)) return null;
  return {
    asset_id: assetId,
    label,
    asset_type: normalizeAssetType(asset.asset_type || asset.kind),
    scope,
    status: asset.status || asset.asset_status || "fixed",
    source_node_id: asset.source_node_id || "",
  };
}

function candidateFromAssetCardNode(node) {
  const draft = node.params?.assetCardDraft;
  if (!draft || isRetired(draft)) return null;
  return {
    asset_id: draft.card_id || node.id,
    label: String(draft.label || node.title || "候选资产").replace(/^@+/, "").trim(),
    asset_type: normalizeAssetType(draft.asset_type),
    scope: "shot_tree_candidate",
    status: draft.status || "draft",
    source_node_id: node.id,
  };
}

export function connectedNodeIds(state, nodeId) {
  const start = String(nodeId || "").trim();
  if (!start || !state.nodes?.[start]) return new Set();
  const result = new Set([start]);
  const queue = [start];
  while (queue.length) {
    const current = queue.shift();
    for (const edge of Object.values(state.edges || {})) {
      const next = edge.from === current ? edge.to : edge.to === current ? edge.from : "";
      if (next && state.nodes?.[next] && !result.has(next)) {
        result.add(next);
        queue.push(next);
      }
    }
  }
  return result;
}

function isFixedVisualAsset(asset) {
  if (isRetired(asset)) return false;
  const kind = String(asset?.kind || "").trim();
  const status = String(asset?.status || asset?.asset_status || "fixed").trim();
  const assetType = normalizeAssetType(asset?.asset_type || asset?.type);
  const hasAssetCardShape = Boolean(asset?.label || asset?.signature || asset?.feature_card) && ["character", "scene", "prop"].includes(assetType);
  return ["visual_asset", "character_asset", "scene_asset", "prop_asset"].includes(kind)
    || Boolean(asset?.visual_asset_id)
    || (hasAssetCardShape && ["fixed", "ready"].includes(status));
}

function isRetired(asset) {
  const status = String(asset?.status || asset?.asset_status || asset?.runtime_status || "").toLowerCase();
  return status === "retired" || status === "excluded";
}

function normalizeAssetType(value) {
  const raw = String(value || "").toLowerCase();
  if (raw.includes("scene")) return "scene";
  if (raw.includes("prop")) return "prop";
  return "character";
}

function normalize(value) {
  return String(value || "").replace(/^@+/, "").trim().toLowerCase();
}
