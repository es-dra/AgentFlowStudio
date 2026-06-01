const PROJECT_AUDIT_PROBE_TYPE = "loulan_afs_project_audit_package_probe";

export function isLoulanProjectAuditProbe(type) {
  return type === PROJECT_AUDIT_PROBE_TYPE;
}

export function loulanProjectAuditProbeTypeLabel(type) {
  return isLoulanProjectAuditProbe(type) ? "Loulan AFS project audit package probe" : "";
}

export function loulanProjectAuditProbeFocusTargets() {
  return ["project", "review", "next-pass"];
}

export function loulanProjectAuditProbeStatus(payload) {
  return payload.status || "review ready";
}

export function loulanProjectAuditProbeFacts(payload) {
  const packageProbe = objectValue(payload.afs_package_probe);
  const summarySync = objectValue(payload.afs_package_audit_summary_sync);
  const cliProbe = objectValue(payload.afs_package_audit_summary_cli_probe);
  const packageGateFacts = objectValue(payload.afs_package_gate_facts_web_direct_probe);
  const rootGateFacts = objectValue(payload.afs_root_gate_facts_web_direct_probe);
  const audits = objectValue(packageProbe.project_audits);
  const manifestReference = objectValue(audits.manifest_reference);
  const textEncoding = objectValue(audits.text_encoding);
  const phaseGate = objectValue(audits.phase_gate);
  const facts = [
    fact("manifest_reference_audit", manifestReference.status || "unknown"),
    fact("text_encoding_audit", textEncoding.status || "unknown"),
    fact("phase_gate_audit", phaseGate.status || "unknown"),
    fact("promotion_gate", packageProbe.promotion_gate || "unknown"),
    fact("latest_gate_facts", latestGateFactsStatus(payload)),
    fact("b01_feedback_loop_gate", packageProbe.b01_feedback_loop_gate || "unknown"),
    fact("b01_pending_decisions", packageProbe.b01_pending_decisions ?? "unknown"),
    fact("b01_operator_entrypoint", packageProbe.b01_operator_entrypoint || "unknown"),
    fact("b01_operator_pending_decisions", packageProbe.b01_operator_pending_decisions ?? "unknown"),
    fact("b01_operator_steps", packageProbe.b01_operator_steps ?? "unknown"),
    fact("b01_operator_blocked_until_count", packageProbe.b01_operator_blocked_until_count ?? "unknown"),
    fact("b01_operator_recommendations", packageProbe.b01_operator_recommendations ?? "unknown"),
    fact("b01_operator_pending_operator_decisions", packageProbe.b01_operator_pending_operator_decisions ?? "unknown"),
    fact("eligible_refs", packageProbe.eligible_memory_refs ?? "unknown"),
    fact("blocked_refs", packageProbe.blocked_memory_refs ?? "unknown"),
    fact("provider_calls_started", yesNo(packageProbe.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(packageProbe.writes_long_term_memory)),
  ];
  if (Object.keys(summarySync).length) {
    const manifestSummary = objectValue(summarySync.manifest_reference_audit);
    const textSummary = objectValue(summarySync.text_encoding_audit);
    const phaseSummary = objectValue(summarySync.phase_gate_audit);
    facts.push(
      fact("package_audit_summary_sync", summarySync.status || "unknown"),
      fact("package_manifest_errors", manifestSummary.errors ?? "unknown"),
      fact("package_invalid_asset_types", manifestSummary.invalid_asset_types ?? "unknown"),
      fact("package_invalid_statuses", manifestSummary.invalid_statuses ?? "unknown"),
      fact("package_text_errors", textSummary.errors ?? "unknown"),
      fact("package_phase_failures", phaseSummary.failures ?? "unknown"),
      fact("package_phase_pending_b01", phaseSummary.pending_b01_decisions ?? "unknown"),
      fact("package_summary_eligible_refs", summarySync.eligible_memory_refs ?? "unknown"),
      fact("package_summary_blocked_refs", summarySync.blocked_memory_refs ?? "unknown"),
      fact("package_summary_provider_calls_started", yesNo(summarySync.provider_calls_started)),
      fact("package_summary_writes_long_term_memory", yesNo(summarySync.writes_long_term_memory)),
    );
  }
  if (Object.keys(cliProbe).length) {
    const stdoutLines = Array.isArray(cliProbe.stdout_lines) ? cliProbe.stdout_lines : [];
    facts.push(
      fact("package_audit_summary_cli", cliProbe.status || "unknown"),
      fact("package_cli_stdout_lines", stdoutLines.length),
      fact("package_cli_eligible_refs", cliProbe.eligible_memory_refs ?? "unknown"),
      fact("package_cli_blocked_refs", cliProbe.blocked_memory_refs ?? "unknown"),
      fact("package_cli_provider_calls_started", yesNo(cliProbe.provider_calls_started)),
      fact("package_cli_writes_long_term_memory", yesNo(cliProbe.writes_long_term_memory)),
    );
  }
  if (Object.keys(packageGateFacts).length) {
    const gateInspectorFacts = objectValue(packageGateFacts.inspector_facts);
    facts.push(
      fact("package_gate_facts", packageGateFacts.status || payload.status || "unknown"),
      fact("package_gate_next_context", gateInspectorFacts.next_context_status || "unknown"),
      fact("package_gate_b01_apply", gateInspectorFacts.b01_apply_status || "unknown"),
      fact("package_gate_b01_operator_next_context", gateInspectorFacts.b01_operator_next_context || "unknown"),
      fact("package_gate_provider_calls_started", yesNo(packageGateFacts.provider_calls_started)),
      fact("package_gate_writes_long_term_memory", yesNo(packageGateFacts.writes_long_term_memory)),
    );
  }
  if (Object.keys(rootGateFacts).length) {
    const rootInspectorFacts = objectValue(rootGateFacts.inspector_facts);
    facts.push(
      fact("root_gate_facts", rootGateFacts.status || rootInspectorFacts.package_gate_facts || "unknown"),
      fact("root_gate_b01_validation", rootInspectorFacts.b01_validation || "unknown"),
      fact("root_gate_next_context", rootInspectorFacts.next_context || "unknown"),
      fact("root_gate_provider_calls_started", yesNo(rootGateFacts.provider_calls_started)),
      fact("root_gate_writes_long_term_memory", yesNo(rootGateFacts.writes_long_term_memory)),
    );
  }
  return facts;
}

function latestGateFactsStatus(payload) {
  const projectAuditLatestGateFacts = objectValue(payload.afs_project_audit_latest_gate_facts_web_direct_probe);
  const rootLatestGateFacts = objectValue(payload.afs_latest_gate_facts_web_direct_probe);
  const rootProjectAuditGateFacts = objectValue(payload.afs_root_project_audit_gate_facts_web_direct_probe);
  const projectAuditGateFacts = objectValue(payload.afs_project_audit_gate_facts_web_direct_probe);
  const rootGateFacts = objectValue(payload.afs_root_gate_facts_web_direct_probe);
  const packageGateFacts = objectValue(payload.afs_package_gate_facts_web_direct_probe);

  return (
    objectStatus(projectAuditLatestGateFacts, "latest_gate_facts")
    || objectStatus(rootLatestGateFacts, "latest_gate_facts")
    || objectStatus(rootProjectAuditGateFacts, "latest_gate_facts")
    || objectStatus(projectAuditGateFacts, "latest_gate_facts")
    || objectStatus(rootGateFacts, "latest_gate_facts")
    || objectStatus(packageGateFacts, "latest_gate_facts")
    || "not_provided"
  );
}

function objectStatus(value, preferredFact) {
  const facts = objectValue(value.inspector_facts);
  return (
    facts[preferredFact]
    || value.status
    || facts.next_context
    || facts.next_context_status
    || facts.root_gate_next_context
    || facts.package_gate_b01_operator_next_context
    || value.inspector_status
    || ""
  );
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
