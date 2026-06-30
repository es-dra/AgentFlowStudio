export function promotionGateProvenance(node) {
  const decision = latestAcceptedAssetCardGate(node);
  if (!decision?.human_gate_id || !decision?.target_id) return {};
  return {
    source_human_gate_id: safeToken(decision.human_gate_id),
    source_asset_card_candidate_id: safeToken(decision.target_id),
  };
}

export function promotionGateReviewSummary(node) {
  const decision = latestAcceptedAssetCardGate(node);
  if (!decision?.human_gate_id || !decision?.target_id) return null;
  const reuse = parseReuseSummary(decision.note);
  return {
    source_human_gate_id: safeToken(decision.human_gate_id),
    source_asset_card_candidate_id: safeToken(decision.target_id),
    reuse_scope: reuse.reuse_scope,
    shot_ref_count: reuse.shot_ref_count,
    label: reuse.label,
    writes_fixed_asset: false,
  };
}

function latestAcceptedAssetCardGate(node) {
  const decisions = Array.isArray(node?.params?.humanGateDecisions) ? node.params.humanGateDecisions : [];
  for (let index = decisions.length - 1; index >= 0; index -= 1) {
    const decision = decisions[index] || {};
    if (decision.target_type === "asset_card_candidate" && decision.decision === "accepted_for_next_step") {
      return decision;
    }
  }
  return null;
}

function parseReuseSummary(note) {
  const text = String(note || "");
  const scope = safeReuseScope((text.match(/reuse_scope=([a-z_]+)/) || [])[1]);
  const count = Math.max(0, Math.min(Number((text.match(/shot_ref_count=(\d+)/) || [])[1]) || 0, 99));
  return {
    reuse_scope: scope,
    shot_ref_count: count,
    label: scope ? reuseLabel(scope, count) : "Accepted asset-card gate",
  };
}

function safeReuseScope(value) {
  if (value === "project_reuse_candidate") return "project_reuse_candidate";
  if (value === "shot_local_candidate") return "shot_local_candidate";
  return "";
}

function reuseLabel(scope, shotRefCount) {
  const scopeLabel = scope === "project_reuse_candidate" ? "Project reuse" : "Shot local";
  return `${scopeLabel} / ${shotRefCount} shots`;
}

function safeToken(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, 160);
}
