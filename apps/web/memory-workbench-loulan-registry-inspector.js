const REGISTRY_LABELS = {
  loulan_unified_asset_registry: "Loulan unified asset registry",
  loulan_asset_registry_health_report: "Loulan asset registry health report",
};

export function isLoulanRegistryArtifact(type) {
  return Object.prototype.hasOwnProperty.call(REGISTRY_LABELS, type);
}

export function loulanRegistryTypeLabel(type) {
  return REGISTRY_LABELS[type] || "";
}

export function loulanRegistryFocusTargets() {
  return ["project", "assets", "memory-loaded", "next-pass"];
}

export function loulanRegistryStatus(payload) {
  if (payload.status) return payload.status;
  const blockedCounts = objectValue(payload.summary?.status_counts);
  const blocked = ["candidate", "needs_repair", "rejected", "route_failed", "source_reference", "superseded"].some(
    (status) => Number(blockedCounts[status] || 0) > 0,
  );
  return blocked ? "blocked" : "review ready";
}

export function loulanRegistryFacts(payload) {
  const summary = objectValue(payload.summary);
  const boundary = objectValue(payload.claim_boundary);
  return [
    fact("project_id", payload.project_id || "unknown"),
    fact("total_assets", summary.total_assets ?? arrayValue(payload.assets).length),
    fact("type_counts", countText(summary.type_counts)),
    fact("status_counts", countText(summary.status_counts)),
    fact("eligible_refs", summary.eligible_reusable_refs ?? "unknown"),
    fact("blocked_refs", summary.blocked_refs ?? "unknown"),
    fact("missing_sha256", summary.missing_sha256_count ?? "unknown"),
    fact("missing_refs", summary.missing_ref_count ?? "unknown"),
    fact("source_quality_issues", summary.source_quality_issue_count ?? "unknown"),
    fact("provider_calls_started", yesNo(boundary.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(boundary.writes_long_term_memory)),
  ];
}

function countText(value) {
  return Object.entries(objectValue(value))
    .map(([key, count]) => `${key}: ${String(count)}`)
    .join(", ") || "none";
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
