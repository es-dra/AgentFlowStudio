export function buildAssetReviewScreen(payload) {
  const includedRefs = arrayValue(payload.included_profile_refs || payload.included_refs);
  const blockedRefs = arrayValue(payload.blocked_profile_refs || payload.blocked_refs);
  const findings = arrayValue(payload.consistency_findings);
  const firstFinding = findings[0] || {};
  const firstIncluded = includedRefs[0] || {};

  return {
    title: "Asset Profile Review Screen",
    status: payload.review_status || payload.projection_status || "review ready",
    target: {
      character: firstFinding.profile_ref || firstIncluded.ref_id || payload.profile_id || "not recorded",
      scene: payload.source_result_ref || payload.comparison_scope || "not recorded",
    },
    profile_versions: profileVersions(includedRefs, findings),
    confirmed_features: uniqueList(includedRefs.flatMap((item) => arrayValue(item.evidence_refs))),
    allowed_changes: uniqueList(includedRefs.flatMap((item) => arrayValue(item.allowed_variations))),
    blocked_changes: uniqueList([
      ...includedRefs.flatMap((item) => arrayValue(item.negative_constraints)),
      ...findings.flatMap((item) => arrayValue(item.violated_constraints)),
    ]),
    included_refs: includedRefs.map((item) => ({
      ref_id: item.ref_id || "unknown",
      summary: item.summary || item.profile_kind || "included asset profile",
      profile_version: item.profile_version || "unknown",
    })),
    blocked_refs: blockedRefs.map((item) => ({
      ref_id: item.ref_id || "unknown",
      reason: item.reason || "blocked",
    })),
    tester_feedback: testerFeedback(findings),
    next_recommendations: nextRecommendations(findings),
    non_claims: nonClaims(payload),
  };
}

function testerFeedback(findings) {
  return {
    confirmed_features: findingRows(findings, "kept"),
    partial_features: findingRows(findings, "partially_kept"),
    failed_features: findingRows(findings, "not_kept"),
    unknown_features: findingRows(findings, "cannot_judge"),
  };
}

function findingRows(findings, result) {
  return findings
    .filter((item) => item.review_result === result)
    .map((item) => ({
      dimension: item.review_dimension || "unknown",
      result: item.review_result || "unknown",
      next_state: item.suggested_next_state || "unknown",
      evidence_refs: arrayValue(item.evidence_refs),
      observations: arrayValue(item.drift_observations),
    }));
}

function nextRecommendations(findings) {
  const counts = new Map();
  for (const item of findings) {
    const state = item.suggested_next_state || "unknown";
    counts.set(state, (counts.get(state) || 0) + 1);
  }
  return [...counts.entries()].map(([state, count]) => ({ state, count }));
}

function profileVersions(includedRefs, findings) {
  const fromRefs = includedRefs.map((item) => `${item.ref_id || "unknown"}:${item.profile_version || "unknown"}`);
  const fromFindings = findings.map((item) => `${item.profile_ref || "unknown"}:${item.profile_version || "unknown"}`);
  return uniqueList([...fromRefs, ...fromFindings].filter((item) => !item.endsWith(":unknown")));
}

function nonClaims(payload) {
  const explicit = arrayValue(payload.non_claims);
  if (explicit.length) return explicit;
  const boundaries = payload.claim_boundaries && typeof payload.claim_boundaries === "object" ? payload.claim_boundaries : {};
  return [
    `human acceptance: ${boundaries.human_acceptance || "not_claimed"}`,
    `business validation: ${boundaries.business_validation || "not_validated"}`,
    `durable memory: ${boundaries.durable_memory_runtime || "not_implemented"}`,
  ];
}

function uniqueList(values) {
  return [...new Set(values.map((value) => String(value)).filter(Boolean))];
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
