import {
  assetCardDraftFromRef,
  assetCardText,
  assetCardTypeLabel,
} from "./asset-card-drafts.js";
import { assetImageRatio } from "./asset-card-image-prompts.js";
import { createNode, connect } from "./nodes.js";
import { refineStructuredShotAssets, structuredShotFromSegment } from "./structured-shot.js";

const MAX_ASSET_PREP_NODES_PER_SHOT = 4;

export function createShotAssetPrepNodes(store, scriptNodeId, structuredShot, x, y) {
  const refs = Array.isArray(structuredShot?.asset_refs) ? structuredShot.asset_refs : [];
  const created = [];
  refs.slice(0, MAX_ASSET_PREP_NODES_PER_SHOT).forEach((asset, index) => {
    const draft = assetCardDraftFromRef(asset, structuredShot, { sourceScriptNodeId: scriptNodeId });
    const assetNode = createNode(store, "image", x, y + index * 150);
    applyAssetDraftToNode(store, assetNode.id, draft, structuredShot, scriptNodeId, asset);
    connect(store, scriptNodeId, assetNode.id);
    created.push(assetNode.id);
  });
  return created;
}

export function ensureShotAssetPrepNodesForScriptNode(store, scriptNode, options = {}) {
  const fresh = store.get().nodes[scriptNode.id] || scriptNode;
  if (!fresh) return [];
  const existing = existingShotAssetCardNodeIds(store.get(), fresh.id);
  if (existing.length && !options.replaceExisting) return existing;
  if (existing.length && options.replaceExisting) {
    removeShotAssetCardNodes(store, existing);
  }
  const context = fresh.content || fresh.prompt || "";
  const structuredShot = options.structuredShot
    ? refineStructuredShotAssets(options.structuredShot, context)
    : fresh.params?.structuredShot
    ? refineStructuredShotAssets(fresh.params.structuredShot, context)
    : structuredShotFromSegment(context, Number(fresh.params?.scriptSegmentIndex || 1));
  const created = createShotAssetPrepNodes(store, fresh.id, structuredShot, fresh.x + fresh.w + 160, fresh.y);
  store.set((s) => {
    const node = s.nodes[fresh.id];
    if (!node) return;
    node.params.structuredShot = structuredShot;
    node.params.shotAssetRefs = structuredShot.asset_refs;
    node.params.assetPrepState = {
      status: created.length ? "card_ready" : "no_assets_detected",
      downstream_node_ids: created,
      updated_at: new Date().toISOString(),
    };
  });
  return created;
}

export function createManualShotAssetNode(store, scriptNode, assetType, label = "") {
  const fresh = store.get().nodes[scriptNode.id] || scriptNode;
  if (!fresh) return null;
  const safeType = ["character", "scene", "prop"].includes(assetType) ? assetType : "character";
  const fallback = safeType === "scene" ? "新增场景" : safeType === "prop" ? "新增道具" : "新增角色";
  const context = fresh.content || fresh.prompt || "";
  const structuredShot = fresh.params?.structuredShot
    ? refineStructuredShotAssets(fresh.params.structuredShot, context)
    : structuredShotFromSegment(context, Number(fresh.params?.scriptSegmentIndex || 1));
  const asset = {
    label: label || fallback,
    asset_type: safeType,
    asset_id: `manual:${safeType}:${Date.now()}`,
    status: "candidate",
    source: "manual",
  };
  const draft = assetCardDraftFromRef(asset, structuredShot, { sourceScriptNodeId: fresh.id });
  const yOffset = existingShotAssetCardNodeIds(store.get(), fresh.id).length * 150;
  const assetNode = createNode(store, "image", fresh.x + fresh.w + 160, fresh.y + yOffset);
  applyAssetDraftToNode(store, assetNode.id, draft, structuredShot, fresh.id, asset);
  connect(store, fresh.id, assetNode.id);
  store.set((s) => {
    const node = s.nodes[fresh.id];
    if (!node) return;
    const refs = Array.isArray(node.params.shotAssetRefs) ? node.params.shotAssetRefs : [];
    node.params.shotAssetRefs = [...refs, asset];
    node.params.assetPrepState = {
      status: "card_ready",
      downstream_node_ids: existingShotAssetCardNodeIds(s, fresh.id),
      updated_at: new Date().toISOString(),
    };
  });
  return assetNode.id;
}

export function existingShotAssetCardNodeIds(state, scriptNodeId) {
  return Object.values(state.nodes || {})
    .filter((node) => node?.params?.assetCardDraft?.source_script_node_id === scriptNodeId)
    .map((node) => node.id);
}

function removeShotAssetCardNodes(store, nodeIds) {
  const removal = new Set(nodeIds);
  store.set((s) => {
    for (const id of removal) delete s.nodes[id];
    s.order = s.order.filter((id) => !removal.has(id));
    for (const [edgeId, edge] of Object.entries(s.edges || {})) {
      if (removal.has(edge.from) || removal.has(edge.to)) delete s.edges[edgeId];
    }
    for (const group of Object.values(s.groups || {})) {
      group.nodeIds = group.nodeIds.filter((id) => !removal.has(id));
    }
    for (const groupId of Object.keys(s.groups || {})) {
      if (!s.groups[groupId].nodeIds.length) delete s.groups[groupId];
    }
  });
}

function applyAssetDraftToNode(store, nodeId, draft, structuredShot, scriptNodeId, asset) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.title = `${assetCardTypeLabel(draft.asset_type)} · @${draft.label}`;
    node.prompt = "";
    node.content = assetCardText(draft);
    node.status = "complete";
    node.h = Math.max(300, Math.min(460, 210 + Object.keys(draft.feature_card || {}).length * 22));
    node.params.nodeRole = "asset_card_draft";
    node.params.assetCardDraft = draft;
    node.params.spec = {
      ...(node.params.spec || {}),
      ratio: assetImageRatio(draft.asset_type),
      count: 1,
    };
    node.params.asset_prep = {
      status: "card_ready",
      source_script_node_id: scriptNodeId,
      source_shot_id: structuredShot.shot_id,
      asset_ref: asset,
      asset_card_id: draft.card_id,
    };
    node.params.assetPrepState = {
      status: "card_ready",
      source_script_node_id: scriptNodeId,
      source_shot_id: structuredShot.shot_id,
    };
  });
}
