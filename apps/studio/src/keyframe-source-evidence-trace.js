import { assetLabel, assetTypeLabel } from "./asset-reference-summary.js";
import { sourceEvidenceRefs } from "./generation-preflight-source-evidence.js";

export function keyframeLayerSourceEvidenceRefs(node) {
  const refs = node?.params?.keyframeLayer?.fixed_asset_source_evidence_refs;
  return sourceEvidenceRefs({ included_asset_source_evidence_refs: Array.isArray(refs) ? refs : [] });
}

export function keyframeSourceEvidenceTrace(node) {
  const refs = keyframeLayerSourceEvidenceRefs(node);
  const productionGraphReview = keyframeLayerProductionGraphReview(node);
  if (!refs.length && !productionGraphReview) return null;
  return {
    trace_type: "studio_keyframe_layer_source_evidence",
    source: "studio_keyframe_layer",
    provider_prompt_inclusion_policy: "excluded_by_default",
    fixed_asset_source_evidence_count: refs.length,
    fixed_asset_source_evidence_refs: refs,
    production_graph_review: productionGraphReview,
  };
}

export function keyframeSourceEvidenceSummaryText(node) {
  const refs = keyframeLayerSourceEvidenceRefs(node);
  if (!refs.length) return "";
  return `关键帧来源证据：${refs.slice(0, 3).map(keyframeEvidenceLabel).join("、")}`;
}

export function keyframeSourceEvidenceTraceSummaryText(trace) {
  const refs = sourceEvidenceRefs({ included_asset_source_evidence_refs: safeTraceRefs(trace) });
  const productionGraphReview = safeProductionGraphReview(trace?.production_graph_review);
  if (!refs.length && !productionGraphReview) return "";
  const policy = String(trace?.provider_prompt_inclusion_policy || "excluded_by_default").trim();
  return [
    refs.length ? `关键帧来源证据：${refs.length} 项` : "",
    refs.length ? refs.slice(0, 2).map(keyframeEvidenceLabel).join("、") : "",
    productionGraphReview ? productionGraphReviewLabel(productionGraphReview) : "",
    `提示词策略：${policy}`,
  ].filter(Boolean).join("；");
}

function safeTraceRefs(trace) {
  return Array.isArray(trace?.fixed_asset_source_evidence_refs) ? trace.fixed_asset_source_evidence_refs : [];
}

function keyframeLayerProductionGraphReview(node) {
  return safeProductionGraphReview(node?.params?.keyframeLayer?.production_graph_review);
}

function safeProductionGraphReview(review) {
  if (!review || typeof review !== "object") return null;
  const artifactId = safeToken(review.artifact_id);
  const fixedAssetReuseCount = Math.min(Math.max(Number(review.fixed_asset_reuse_count) || 0, 0), 99);
  const fixedVisualAssetIds = Array.isArray(review.fixed_visual_asset_ids)
    ? review.fixed_visual_asset_ids.map(safeToken).filter(Boolean).slice(0, 24)
    : [];
  if (!artifactId && !fixedAssetReuseCount && !fixedVisualAssetIds.length) return null;
  return {
    artifact_id: artifactId,
    fixed_asset_reuse_count: fixedAssetReuseCount,
    fixed_visual_asset_ids: fixedVisualAssetIds,
  };
}

function productionGraphReviewLabel(review) {
  const artifact = review.artifact_id ? `artifact=${review.artifact_id}` : "";
  return [`production_graph fixed_reuse=${review.fixed_asset_reuse_count}`, artifact].filter(Boolean).join(" ");
}

function keyframeEvidenceLabel(item) {
  const label = compactText(assetLabel(item), 32);
  const source = compactText(item.source_asset_card_candidate_id || item.source_human_gate_id || item.source_stage || "manual", 48);
  return `${assetTypeLabel(item)} ${label} -> ${source}`;
}

function compactText(value, maxLength) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

function safeToken(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, 160);
}
