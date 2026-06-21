import {
  assetCardDraftFromRef,
  assetCardText,
  assetCardTypeLabel,
  assetImagePrompt,
} from "./asset-card-drafts.js";
import { createNode, connect } from "./nodes.js";
import { structuredShotFromSegment } from "./structured-shot.js";

const MAX_ASSET_PREP_NODES_PER_SHOT = 4;

export function createShotAssetPrepNodes(store, scriptNodeId, structuredShot, x, y) {
  const refs = Array.isArray(structuredShot?.asset_refs) ? structuredShot.asset_refs : [];
  const created = [];
  refs.slice(0, MAX_ASSET_PREP_NODES_PER_SHOT).forEach((asset, index) => {
    const draft = assetCardDraftFromRef(asset, structuredShot, { sourceScriptNodeId: scriptNodeId });
    const assetNode = createNode(store, "image", x, y + index * 150);
    store.set((s) => {
      const node = s.nodes[assetNode.id];
      if (!node) return;
      node.title = `${assetCardTypeLabel(draft.asset_type)} · @${draft.label}`;
      node.prompt = assetImagePrompt(draft);
      node.content = assetCardText(draft);
      node.status = "complete";
      node.h = Math.max(300, Math.min(460, 210 + Object.keys(draft.feature_card || {}).length * 22));
      node.params.nodeRole = "asset_card_draft";
      node.params.assetCardDraft = draft;
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
    connect(store, scriptNodeId, assetNode.id);
    created.push(assetNode.id);
  });
  return created;
}

export function ensureShotAssetPrepNodesForScriptNode(store, scriptNode) {
  const fresh = store.get().nodes[scriptNode.id] || scriptNode;
  if (!fresh) return [];
  const existing = existingShotAssetCardNodeIds(store.get(), fresh.id);
  if (existing.length) return existing;
  const structuredShot = structuredShotFromSegment(fresh.content || fresh.prompt || "", Number(fresh.params?.scriptSegmentIndex || 1));
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

export function existingShotAssetCardNodeIds(state, scriptNodeId) {
  return Object.values(state.nodes || {})
    .filter((node) => node?.params?.assetCardDraft?.source_script_node_id === scriptNodeId)
    .map((node) => node.id);
}
