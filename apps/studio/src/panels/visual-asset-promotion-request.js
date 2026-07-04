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
  reuseIntent = "",
  linkExistingAssetId = "",
  supersedesAssetId = "",
  reviewedAt = new Date().toISOString(),
}) {
  const intent = safeReuseIntent(reuseIntent);
  return {
    source_image_asset_refs: [imageAsset.asset_id],
    asset_type: assetType,
    label,
    signature,
    feature_card: featureCard,
    negative_locks: negativeLocks,
    source_node_id: node.id,
    ...promotionGateProvenance(node),
    ...(intent ? { reuse_intent: intent } : {}),
    ...(intent === "link_existing" && linkExistingAssetId ? { link_existing_asset_id: linkExistingAssetId } : {}),
    supersedes_asset_id: supersedesAssetId || null,
    review_decision: decision,
    reviewed_at: reviewedAt,
  };
}

function safeReuseIntent(value) {
  const text = String(value || "").trim();
  return ["link_existing", "replace", "create_new"].includes(text) ? text : "";
}
