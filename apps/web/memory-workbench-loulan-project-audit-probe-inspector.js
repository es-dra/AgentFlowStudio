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
  const audits = objectValue(packageProbe.project_audits);
  const manifestReference = objectValue(audits.manifest_reference);
  const textEncoding = objectValue(audits.text_encoding);
  const phaseGate = objectValue(audits.phase_gate);
  const facts = [
    fact("manifest_reference_audit", manifestReference.status || "unknown"),
    fact("text_encoding_audit", textEncoding.status || "unknown"),
    fact("phase_gate_audit", phaseGate.status || "unknown"),
    fact("promotion_gate", packageProbe.promotion_gate || "unknown"),
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
  return facts;
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
