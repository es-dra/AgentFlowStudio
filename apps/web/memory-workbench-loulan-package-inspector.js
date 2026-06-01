export function loulanPackageFacts(payload) {
  const b01Gate = objectValue(payload.feedback_loop_gates?.b01);
  const b01Operator = objectValue(payload.feedback_loop_gates?.b01_operator_entrypoint);
  const audits = objectValue(payload.project_audits);
  const manifestAudit = objectValue(audits.manifest_reference);
  const textAudit = objectValue(audits.text_encoding);
  const phaseGate = objectValue(audits.phase_gate);
  const manifestSummary = objectValue(manifestAudit.summary);
  const textSummary = objectValue(textAudit.summary);
  const phaseSummary = objectValue(phaseGate.summary);
  const nextContext = objectValue(payload.next_context_bundle_draft);
  return [
    fact("shots", payload.shot_summary?.total_shots ?? "unknown"),
    fact("eligible_refs", arrayValue(nextContext.eligible_memory_refs).length),
    fact("blocked_refs", arrayValue(nextContext.blocked_memory_refs).length),
    fact("promotion_gate", payload.promotion_gates?.overall_status || "unknown"),
    fact("next_context_status", nextContext.status || "unknown"),
    fact("context_rule", nextContext.context_rule || "unknown"),
    fact("manifest_reference_audit", manifestAudit.status || "not_provided"),
    fact("manifest_audit_errors", manifestSummary.errors ?? "unknown"),
    fact("invalid_asset_types", manifestSummary.invalid_asset_types ?? "unknown"),
    fact("invalid_statuses", manifestSummary.invalid_statuses ?? "unknown"),
    fact("text_encoding_audit", textAudit.status || "not_provided"),
    fact("text_encoding_errors", textSummary.errors ?? "unknown"),
    fact("phase_gate_audit", phaseGate.status || "not_provided"),
    fact("phase_gate_failures", phaseSummary.failures ?? "unknown"),
    fact("feedback_gate_b01", b01Gate.status || "not_supplied"),
    fact("b01_operator_entrypoint", b01Operator.status || "not_supplied"),
    fact("b01_pending_decisions", b01Gate.pending_decisions ?? "unknown"),
    fact("b01_validation_status", b01Gate.validation_status || "unknown"),
    fact("b01_apply_status", b01Gate.apply_status || "unknown"),
    fact("b01_context_projection_ready", yesNo(b01Gate.context_projection_ready)),
    fact("b01_human_acceptance_recorded", yesNo(b01Gate.human_acceptance_recorded)),
    fact("b01_media_generation_started", yesNo(b01Gate.media_generation_started)),
    fact("b01_operator_apply_status", b01Operator.apply_status || "unknown"),
    fact("b01_operator_next_context", b01Operator.next_context_status || "unknown"),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function loulanApiWorkbenchFacts(payload) {
  const intakeGate = objectValue(payload.context_projection?.decision_intake_gate);
  return [
    fact("adapter", payload.provider_adapter?.adapter_id || "unknown"),
    fact("context_projection", payload.context_projection?.status || "not_provided"),
    fact("context_intake_gate", intakeGate.status || "not_recorded"),
    fact("requests", arrayValue(payload.request_manifest?.requests).length),
    fact("response_ledger", payload.response_ledger?.status || "unknown"),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function loulanHumanReviewFacts(payload) {
  return [
    fact("block", payload.review_scope?.block_id || "unknown"),
    fact("shots", payload.review_scope?.shot_count ?? "unknown"),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
    fact("next_pass", payload.next_pass_readiness?.status || "unknown"),
  ];
}

export function loulanDecisionFacts(payload) {
  const facts = [
    fact("template_status", payload.template_status || "unknown"),
    fact("decisions", arrayValue(payload.decisions).length),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
  const summary = objectValue(payload.import_summary);
  if (Object.keys(summary).length) {
    facts.splice(1, 0, fact("source_block_id", payload.source_block_id || "unknown"), fact("imported_ready", summary.imported_ready_decisions ?? "unknown"), fact("pending", summary.pending_decisions ?? "unknown"), fact("skipped_local_items", summary.skipped_local_items ?? "unknown"));
  }
  return facts;
}

export function loulanDecisionReviewFacts(payload) {
  const summary = objectValue(payload.decision_summary);
  return [
    fact("review_status", payload.review_status || "unknown"),
    fact("pending", summary.pending_count ?? "unknown"),
    fact("ready", summary.ready_count ?? "unknown"),
    fact("missing", summary.missing_slot_count ?? "unknown"),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function loulanDecisionWorksheetFacts(payload) {
  return [
    fact("worksheet_status", payload.worksheet_status || "unknown"),
    fact("rows", arrayValue(payload.decision_rows).length),
    fact("manual_template_decisions", arrayValue(payload.manual_transfer_template?.decisions).length),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function loulanDecisionIntakeFacts(payload) {
  const summary = objectValue(payload.intake_summary);
  return [
    fact("intake_status", payload.intake_status || "unknown"),
    fact("context_bundle_ready", yesNo(payload.context_bundle_command_ready)),
    fact("ready", summary.ready_count ?? "unknown"),
    fact("pending", summary.pending_count ?? "unknown"),
    fact("invalid", summary.invalid_count ?? "unknown"),
    fact("human_acceptance_recorded", yesNo(payload.human_acceptance_recorded)),
  ];
}

export function loulanContextBundleFacts(payload) {
  const bundle = objectValue(payload.context_bundle);
  const intakeGate = objectValue(payload.decision_intake_gate);
  return [
    fact("decision_intake_gate", intakeGate.status || "not_supplied"),
    fact("context_bundle_ready", yesNo(intakeGate.context_bundle_command_ready)),
    fact("decision_audit", payload.decision_audit?.status || "unknown"),
    fact("context_bundle", bundle.status || "unknown"),
    fact("memory_refs", arrayValue(bundle.memory_refs).length),
    fact("blocked_refs", arrayValue(bundle.blocked_refs).length),
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
