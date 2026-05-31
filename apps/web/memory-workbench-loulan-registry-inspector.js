const REGISTRY_TYPE = "loulan_unified_asset_registry";

export function isLoulanRegistryArtifact(type) {
  return type === REGISTRY_TYPE;
}

export function loulanRegistryTypeLabel(type) {
  return isLoulanRegistryArtifact(type) ? "Loulan unified asset registry" : "";
}

export function loulanRegistryFocusTargets() {
  return ["project", "assets", "memory-loaded", "next-pass"];
}

export function loulanRegistryStatus(payload) {
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
