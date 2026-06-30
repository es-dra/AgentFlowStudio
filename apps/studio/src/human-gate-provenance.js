export function promotionGateProvenance(node) {
  const decision = latestAcceptedAssetCardGate(node);
  if (!decision?.human_gate_id || !decision?.target_id) return {};
  return {
    source_human_gate_id: safeToken(decision.human_gate_id),
    source_asset_card_candidate_id: safeToken(decision.target_id),
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

function safeToken(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, 160);
}
