const LOULAN_B01_LABELS = {
  loulan_afs_b01_feedback_loop_gate: "Loulan B01 feedback loop gate",
  loulan_afs_b01_decision_crosswalk: "Loulan B01 decision crosswalk",
};

export function isLoulanB01Artifact(type) {
  return Object.prototype.hasOwnProperty.call(LOULAN_B01_LABELS, type);
}

export function loulanB01TypeLabel(type) {
  return LOULAN_B01_LABELS[type] || "";
}

export function loulanB01FocusTargets() {
  return ["review", "feedback", "next-pass"];
}

export function loulanB01Status(type, payload) {
  return isLoulanB01Artifact(type) ? payload.status || "review ready" : "";
}

export function loulanB01Facts(type, payload) {
  if (type === "loulan_afs_b01_feedback_loop_gate") return feedbackGateFacts(payload);
  if (type === "loulan_afs_b01_decision_crosswalk") return decisionCrosswalkFacts(payload);
  return [];
}

function feedbackGateFacts(payload) {
  const summary = objectValue(payload.current_gate_summary);
  return [
    fact("status", payload.status || "unknown"),
    fact("pending_decisions", summary.pending_decisions ?? "unknown"),
    fact("validation_status", summary.validation_status || "unknown"),
    fact("apply_status", summary.apply_status || "unknown"),
    fact("context_projection_ready", yesNo(summary.context_projection_ready)),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function decisionCrosswalkFacts(payload) {
  const layers = Object.fromEntries(arrayValue(payload.decision_layers).map((layer) => [layer?.layer_id || "", layer || {}]));
  const localGate = objectValue(layers.loulan_local_b01_shot_gate);
  const importGate = objectValue(layers.afs_b01_import_gate);
  const broaderGate = objectValue(layers.afs_broader_decision_review_gate);
  return [
    fact("status", payload.status || "unknown"),
    fact("local_shot_decisions", localGate.decision_count ?? "unknown"),
    fact("local_pending", localGate.pending_count ?? "unknown"),
    fact("afs_import_decisions", importGate.decision_count ?? "unknown"),
    fact("afs_import_pending", importGate.pending_count ?? "unknown"),
    fact("broader_review_decisions", broaderGate.decision_count ?? "unknown"),
    fact("broader_pending", broaderGate.pending_count ?? "unknown"),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function fact(label, value) {
  return { label, value: String(value) };
}

function yesNo(value) {
  return value === true ? "true" : "false";
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
