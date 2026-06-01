const AUDIT_LABELS = {
  loulan_manifest_reference_audit: "Loulan manifest reference audit",
  loulan_text_encoding_audit: "Loulan text encoding audit",
};

export function isLoulanGovernanceAuditArtifact(type) {
  return Object.prototype.hasOwnProperty.call(AUDIT_LABELS, type);
}

export function loulanGovernanceAuditTypeLabel(type) {
  return AUDIT_LABELS[type] || "";
}

export function loulanGovernanceAuditFocusTargets() {
  return ["project", "review", "next-pass"];
}

export function loulanGovernanceAuditStatus(payload) {
  return payload.status || "review ready";
}

export function loulanGovernanceAuditFacts(type, payload) {
  const summary = objectValue(payload.summary);
  const facts = type === "loulan_manifest_reference_audit"
    ? manifestReferenceFacts(summary)
    : textEncodingFacts(summary);
  return [
    ...facts,
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("new_media_generated", yesNo(payload.new_media_generated)),
  ];
}

function manifestReferenceFacts(summary) {
  return [
    fact("json_files_checked", summary.json_files_checked ?? "unknown"),
    fact("registry_assets", summary.registry_assets ?? "unknown"),
    fact("errors", summary.errors ?? "unknown"),
    fact("missing_sha256", summary.missing_sha256 ?? "unknown"),
    fact("missing_files", summary.missing_files ?? "unknown"),
    fact("absolute_refs", summary.absolute_refs ?? "unknown"),
    fact("secret_like_refs", summary.secret_like_refs ?? "unknown"),
    fact("invalid_asset_types", summary.invalid_asset_types ?? "unknown"),
    fact("invalid_statuses", summary.invalid_statuses ?? "unknown"),
  ];
}

function textEncodingFacts(summary) {
  return [
    fact("text_files_checked", summary.text_files_checked ?? "unknown"),
    fact("decode_errors", summary.decode_errors ?? "unknown"),
    fact("marker_hits", summary.marker_hits ?? "unknown"),
    fact("errors", summary.errors ?? "unknown"),
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
