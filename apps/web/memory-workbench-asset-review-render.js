import { metaLine, row, statusPill } from "./render-helpers.js";

export function renderAssetReviewScreen(container, screen, copy) {
  if (!container || !screen) return;

  container.append(
    row(screen.title || "Asset Profile Review Screen", statusPill(screen.status || "review ready", copy)),
    metaLine(`Current character: ${screen.target?.character || "not recorded"}`),
    metaLine(`Current scene: ${screen.target?.scene || "not recorded"}`),
    metaLine(`Profile versions: ${joinList(screen.profile_versions)}`),
    metaLine(`Included refs: ${joinIncludedRefs(screen.included_refs)}`),
    metaLine(`Blocked refs: ${joinBlockedRefs(screen.blocked_refs)}`),
    metaLine(`Confirmed: ${joinFeedback(screen.tester_feedback?.confirmed_features)}`),
    metaLine(`Partial: ${joinFeedback(screen.tester_feedback?.partial_features)}`),
    metaLine(`Failed: ${joinFeedback(screen.tester_feedback?.failed_features)}`),
    metaLine(`Unknown: ${joinFeedback(screen.tester_feedback?.unknown_features)}`),
    metaLine(`Allowed changes: ${joinList(screen.allowed_changes)}`),
    metaLine(`Blocked changes: ${joinList(screen.blocked_changes)}`),
    metaLine(`Next recommendations: ${joinRecommendations(screen.next_recommendations)}`),
    metaLine(`Non-claims: ${joinList(screen.non_claims)}`),
  );
}

function joinIncludedRefs(items) {
  const refs = arrayValue(items).map((item) => item.ref_id || "unknown");
  return joinList(refs);
}

function joinBlockedRefs(items) {
  const refs = arrayValue(items).map((item) => `${item.ref_id || "unknown"} ${item.reason || "blocked"}`);
  return joinList(refs);
}

function joinFeedback(items) {
  const rows = arrayValue(items).map((item) => `${item.dimension || "unknown"} ${item.result || "unknown"}`);
  return joinList(rows);
}

function joinRecommendations(items) {
  const rows = arrayValue(items).map((item) => `${item.state || "unknown"}: ${item.count || 0}`);
  return joinList(rows);
}

function joinList(items) {
  const values = arrayValue(items)
    .map((item) => String(item).trim())
    .filter(Boolean);
  return values.length ? values.join(" / ") : "none";
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
