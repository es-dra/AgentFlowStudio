import { promotionGateProvenance } from "../human-gate-provenance.js";

export function buildVisualAssetPromotionPayload({
  node,
  imageAsset,
  decision,
  label,
  assetType,
  signature,
  featureCard,
  negativeLocks,
  supersedesAssetId = "",
  reviewedAt = new Date().toISOString(),
}) {
  return {
    source_image_asset_refs: [imageAsset.asset_id],
    asset_type: assetType,
    label,
    signature,
    feature_card: featureCard,
    negative_locks: negativeLocks,
    source_node_id: node.id,
    ...promotionGateProvenance(node),
    supersedes_asset_id: supersedesAssetId || null,
    review_decision: decision,
    reviewed_at: reviewedAt,
  };
}
