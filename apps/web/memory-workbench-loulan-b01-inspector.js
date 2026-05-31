const LOULAN_B01_LABELS = {
  loulan_afs_b01_feedback_loop_gate: "Loulan B01 feedback loop gate",
  loulan_afs_b01_decision_crosswalk: "Loulan B01 decision crosswalk",
  loulan_b01_human_review_decision_template: "Loulan B01 human decision template",
  loulan_b01_decision_apply_plan_draft: "Loulan B01 decision apply plan draft",
  loulan_b01_decision_validation_report: "Loulan B01 decision validation report",
  loulan_b01_decision_apply_result: "Loulan B01 decision apply result",
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
  if (type === "loulan_b01_human_review_decision_template") return localDecisionTemplateFacts(payload);
  if (type === "loulan_b01_decision_apply_plan_draft") return decisionApplyPlanFacts(payload);
  if (type === "loulan_b01_decision_validation_report") return decisionValidationFacts(payload);
  if (type === "loulan_b01_decision_apply_result") return decisionApplyFacts(payload);
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

function localDecisionTemplateFacts(payload) {
  const items = arrayValue(payload.decision_items);
  const pendingCount = items.filter((item) => objectValue(item).decision === "pending_human_review").length;
  const targetShots = items.map((item) => objectValue(item).target_shot_id).filter(Boolean);
  return [
    fact("status", payload.status || "unknown"),
    fact("decision_items", items.length),
    fact("pending_decisions", pendingCount),
    fact("allowed_decisions", listText(payload.allowed_decisions)),
    fact("target_shots", listText(targetShots)),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function decisionApplyPlanFacts(payload) {
  const boundary = objectValue(payload.claim_boundary);
  const mutations = arrayValue(payload.planned_mutations);
  const blockedMutations = mutations.filter((item) => objectValue(item).mutation_status !== "ready_to_apply").length;
  return [
    fact("status", payload.status || "unknown"),
    fact("block_id", payload.block_id || "unknown"),
    fact("preconditions", arrayValue(payload.preconditions).length),
    fact("planned_mutations", mutations.length),
    fact("blocked_mutations", blockedMutations),
    fact("dry_run_plan_only", yesNo(boundary.dry_run_plan_only)),
    fact("applies_status_changes", yesNo(boundary.applies_status_changes)),
    fact("provider_calls_started", yesNo(boundary.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(boundary.writes_long_term_memory)),
  ];
}

function decisionValidationFacts(payload) {
  const summary = objectValue(payload.summary);
  return [
    fact("status", payload.status || "unknown"),
    fact("decision_items", summary.decision_items ?? "unknown"),
    fact("pending_decisions", summary.pending ?? "unknown"),
    fact("approved_decisions", summary.approved ?? "unknown"),
    fact("repair_requested", summary.request_repair ?? "unknown"),
    fact("rejected_decisions", summary.rejected ?? "unknown"),
    fact("errors", summary.errors ?? arrayValue(payload.errors).length),
    fact("warnings", summary.warnings ?? arrayValue(payload.warnings).length),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function decisionApplyFacts(payload) {
  return [
    fact("status", payload.status || "unknown"),
    fact("apply_requested", yesNo(payload.apply_requested)),
    fact("applied", yesNo(payload.applied)),
    fact("validation_status", payload.validation_status || "unknown"),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
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

function listText(value) {
  const values = arrayValue(value).filter(Boolean);
  return values.length > 0 ? values.join(", ") : "unknown";
}
