const PHASE_AUDIT_TYPE = "loulan_asset_governance_phase_audit";

export function isLoulanPhaseAuditArtifact(type) {
  return type === PHASE_AUDIT_TYPE;
}

export function loulanPhaseAuditTypeLabel(type) {
  return isLoulanPhaseAuditArtifact(type) ? "Loulan asset governance phase audit" : "";
}

export function loulanPhaseAuditFocusTargets() {
  return ["project", "review", "next-pass"];
}

export function loulanPhaseAuditStatus(payload) {
  return payload.status || "review ready";
}

export function loulanPhaseAuditFacts(payload) {
  const summary = objectValue(payload.summary);
  return [
    fact("phases", summary.phases ?? "unknown"),
    fact("passed", summary.passed ?? "unknown"),
    fact("blocked_expected", summary.blocked_expected ?? "unknown"),
    fact("failures", summary.failures ?? "unknown"),
    fact("registry_assets", summary.registry_assets ?? "unknown"),
    fact("eligible_context_refs", summary.eligible_context_refs ?? "unknown"),
    fact("blocked_context_refs", summary.blocked_context_refs ?? "unknown"),
    fact("pending_b01_decisions", summary.pending_b01_decisions ?? "unknown"),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("new_media_generated", yesNo(payload.new_media_generated)),
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
