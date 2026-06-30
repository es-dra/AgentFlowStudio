import { assetLabel, assetTypeLabel } from "./asset-reference-summary.js";

const MAX_SOURCE_EVIDENCE_ITEMS = 3;

export function preflightSourceEvidenceSummaryText(preflight) {
  const refs = sourceEvidenceRefs(preflight);
  if (!refs.length) return "";
  const shown = refs.slice(0, MAX_SOURCE_EVIDENCE_ITEMS).map(sourceEvidenceRefLabel);
  const more = refs.length > shown.length ? `；另 ${refs.length - shown.length} 项` : "";
  return `来源证据：${shown.join("；")}${more}`;
}

export function sourceEvidenceRefs(preflight) {
  const explicit = Array.isArray(preflight?.included_asset_source_evidence_refs)
    ? preflight.included_asset_source_evidence_refs
    : [];
  const fallback = explicit.length
    ? explicit
    : safeArray(preflight?.included_assets)
      .map((asset) => fallbackRefFromAsset(asset))
      .filter(Boolean);
  return fallback.map(normalizeRef).filter((ref) => ref.asset_id || ref.source_human_gate_id || ref.source_asset_card_candidate_id);
}

function fallbackRefFromAsset(asset) {
  const evidence = asset?.source_evidence;
  if (!evidence || typeof evidence !== "object") return null;
  return {
    asset_id: asset?.asset_id,
    asset_type: asset?.asset_type,
    label: asset?.label || asset?.title || asset?.signature,
    status: asset?.status,
    source_human_gate_id: evidence.source_human_gate_id,
    source_asset_card_candidate_id: evidence.source_asset_card_candidate_id,
    source_stage: evidence.source_stage,
    provider_calls_started: evidence.provider_calls_started === true,
    human_creative_acceptance_claimed: evidence.human_creative_acceptance_claimed === true,
  };
}

function normalizeRef(ref) {
  return {
    asset_id: safeText(ref?.asset_id, 80),
    asset_type: safeText(ref?.asset_type, 40),
    label: safeText(ref?.label, 80),
    status: safeText(ref?.status, 40),
    source_human_gate_id: safeText(ref?.source_human_gate_id, 120),
    source_asset_card_candidate_id: safeText(ref?.source_asset_card_candidate_id, 120),
    source_stage: safeText(ref?.source_stage, 80),
    provider_calls_started: ref?.provider_calls_started === true,
    human_creative_acceptance_claimed: ref?.human_creative_acceptance_claimed === true,
  };
}

function sourceEvidenceRefLabel(ref) {
  const source = ref.source_asset_card_candidate_id || ref.source_human_gate_id || ref.source_stage || "manual";
  return `${assetTypeLabel(ref)} · ${assetLabel(ref)} ← ${source}`;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function safeText(value, limit) {
  return String(value || "").trim().slice(0, limit);
}
