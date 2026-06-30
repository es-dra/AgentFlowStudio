import { assetLabel, assetTypeLabel } from "./asset-reference-summary.js";
import { sourceEvidenceRefs } from "./generation-preflight-source-evidence.js";

export function keyframeLayerSourceEvidenceRefs(node) {
  const refs = node?.params?.keyframeLayer?.fixed_asset_source_evidence_refs;
  return sourceEvidenceRefs({ included_asset_source_evidence_refs: Array.isArray(refs) ? refs : [] });
}

export function keyframeSourceEvidenceTrace(node) {
  const refs = keyframeLayerSourceEvidenceRefs(node);
  if (!refs.length) return null;
  return {
    trace_type: "studio_keyframe_layer_source_evidence",
    source: "studio_keyframe_layer",
    provider_prompt_inclusion_policy: "excluded_by_default",
    fixed_asset_source_evidence_count: refs.length,
    fixed_asset_source_evidence_refs: refs,
  };
}

export function keyframeSourceEvidenceSummaryText(node) {
  const refs = keyframeLayerSourceEvidenceRefs(node);
  if (!refs.length) return "";
  return `关键帧来源证据：${refs.slice(0, 3).map(keyframeEvidenceLabel).join("、")}`;
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
