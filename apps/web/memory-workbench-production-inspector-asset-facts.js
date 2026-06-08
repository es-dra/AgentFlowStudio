import { arrayValue, fact, objectValue, usedContextRefCount, yesNo } from "./memory-workbench-production-fact-utils.js";

export function productionAssetProfileSeedFacts(payload) {
  return [
    fact("profiles", String(arrayValue(payload.profiles).length)),
    fact("project_id", payload.project_id || "unknown"),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetProfileFacts(payload) {
  return [
    fact("profile_id", payload.profile_id || "unknown"),
    fact("profile_kind", payload.profile_kind || "unknown"),
    fact("profile_status", payload.profile_status || "unknown"),
    fact("profile_version", payload.profile_version || "unknown"),
    fact("allowed_variations", String(arrayValue(payload.allowed_variations).length)),
    fact("negative_constraints", String(arrayValue(payload.negative_constraints).length)),
    fact("context_eligibility", payload.context_eligibility || "unknown"),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionAssetProfileReadinessFacts(payload) {
  return [
    fact("readiness_status", payload.readiness_status || "unknown"),
    fact("profiles", String(arrayValue(payload.profiles).length)),
    fact("blocked_refs", String(arrayValue(payload.blocked_refs).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetTestPackageFacts(payload) {
  return [
    fact("package_status", payload.package_status || payload.test_package_status || "unknown"),
    fact("profiles", String(arrayValue(payload.asset_profiles || payload.profiles).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetProviderValidationFacts(payload) {
  return [
    fact("validation_status", payload.validation_status || payload.status || "unknown"),
    fact("blockers", String(arrayValue(payload.blockers).length)),
    fact("safe_refs", String(arrayValue(payload.safe_refs || payload.result_refs).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetFeedbackFacts(payload) {
  return [
    fact("parse_status", payload.parse_status || "unknown"),
    fact("profile_id", payload.profile_id || "unknown"),
    fact("profile_kind", payload.profile_kind || "unknown"),
    fact("review_dimension", payload.review_dimension || "unknown"),
    fact("review_result", payload.review_result || "unknown"),
    fact("review_result_effect", payload.review_result_effect || "unknown"),
    fact("feedback_is_memory", yesNo(payload.feedback_is_memory)),
    fact("creates_promotion_decision", yesNo(payload.creates_promotion_decision)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetProfileUpdateCandidateFacts(payload) {
  const patch = objectValue(payload.proposed_profile_patch);
  return [
    fact("candidate_generation_status", payload.candidate_generation_status || "unknown"),
    fact("profile_id", payload.profile_id || "unknown"),
    fact("profile_kind", payload.profile_kind || "unknown"),
    fact("review_result", payload.review_result || "unknown"),
    fact("patch_ops", String(arrayValue(patch.patch_ops).length)),
    fact("candidate_is_promoted_profile", yesNo(payload.candidate_is_promoted_profile)),
    fact("applies_profile_version", yesNo(payload.applies_profile_version)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetProfilePromotionFacts(payload) {
  return [
    fact("decision", payload.decision || "unknown"),
    fact("decision_effect", payload.decision_effect || "unknown"),
    fact("profile_id", payload.profile_id || "unknown"),
    fact("profile_kind", payload.profile_kind || "unknown"),
    fact("creates_profile_version", yesNo(payload.creates_profile_version)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetProfileVersionFacts(payload) {
  return [
    fact("version_id", payload.version_id || "unknown"),
    fact("profile_id", payload.profile_id || "unknown"),
    fact("profile_kind", payload.profile_kind || "unknown"),
    fact("profile_version", payload.profile_version || "unknown"),
    fact("source_patch_ops_count", String(payload.source_patch_ops_count ?? 0)),
    fact("usable_for_next_context", yesNo(payload.usable_for_next_context)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetProfileContextProjectionFacts(payload) {
  return [
    fact("projection_status", payload.projection_status || "unknown"),
    fact("included_refs", String(arrayValue(payload.included_refs).length)),
    fact("blocked_refs", String(arrayValue(payload.blocked_refs).length)),
    fact("context_projection_policy", payload.context_payload?.context_projection_policy || "unknown"),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAssetConsistencyReviewFacts(payload) {
  return [
    fact("review_status", payload.review_status || "unknown"),
    fact("overall_consistency_result", payload.overall_consistency_result || "unknown"),
    fact("comparison_scope", payload.comparison_scope || "unknown"),
    fact("consistency_findings", String(arrayValue(payload.consistency_findings).length)),
    fact("blocked_findings", String(arrayValue(payload.blocked_findings).length)),
    fact("creates_asset_feedback_event", yesNo(payload.creates_asset_feedback_event)),
    fact("creates_profile_update_candidate", yesNo(payload.creates_profile_update_candidate)),
    fact("creates_promotion_decision", yesNo(payload.creates_promotion_decision)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}
