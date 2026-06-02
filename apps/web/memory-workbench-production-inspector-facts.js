export { productionOperatorLoopFacts } from "./memory-workbench-production-operator-loop-facts.js";

export function companyKbFeedbackFacts(payload) {
  return [
    fact("promotion_status", payload.promotion_status || "unknown"),
    fact("candidate_items", String(arrayValue(payload.candidate_items).length)),
    fact("source_kb_status", payload.source_kb_status || "unknown"),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("requires_human_review", yesNo(payload.requires_human_review)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionNextContextHandoffFacts(payload) {
  return [
    fact("handoff_status", payload.handoff_status || "unknown"),
    fact("next_context_refs", String(arrayValue(payload.next_context_refs).length)),
    fact("blocked_refs", String(arrayValue(payload.blocked_refs).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionNextTaskPacketFacts(payload) {
  return [
    fact("packet_status", payload.packet_status || "unknown"),
    fact("allowed_context_refs", String(arrayValue(payload.allowed_context_refs).length)),
    fact("blocked_refs", String(arrayValue(payload.blocked_refs).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionNextPassReviewFacts(payload) {
  return [
    fact("review_status", payload.review_status || "unknown"),
    fact("used_allowed_refs", String(arrayValue(payload.used_allowed_refs).length)),
    fact("blocked_or_unknown_refs", String(arrayValue(payload.blocked_or_unknown_refs).length)),
    fact("feedback_candidates", String(arrayValue(payload.feedback_candidates).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionNextPassResultFacts(payload) {
  return [
    fact("result_status", payload.result_status || "unknown"),
    fact("output_artifacts", String(arrayValue(payload.output_artifacts).length)),
    fact("used_context_refs", String(usedContextRefCount(payload.output_artifacts))),
    fact("feedback_events", String(arrayValue(payload.feedback_events).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionNextPassPromotionFacts(payload) {
  return [
    fact("decision", payload.decision || "unknown"),
    ...(payload.decision_effect ? [fact("decision_effect", payload.decision_effect)] : []),
    fact("candidate_id", payload.candidate_id || "unknown"),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionOperatorFeedbackFacts(payload) {
  return [
    fact("status", payload.status || "unknown"),
    fact("decision", payload.decision || "unknown"),
    fact("target_node", payload.target_node_id || "unknown"),
    fact("human_acceptance", payload.claim_boundaries?.human_acceptance || "unknown"),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAcceptanceFeedbackFacts(payload) {
  return [
    fact("status", payload.status || "unknown"),
    fact("acceptance_decision", payload.acceptance_decision || "unknown"),
    fact("feedback_scope", payload.feedback_scope || "unknown"),
    ...(payload.source_artifact_status ? [
      fact("source_artifact_status", payload.source_artifact_status),
    ] : []),
    fact("source_check_status", payload.source_check_status || "unknown"),
    fact("source_ready_for_handoff", yesNo(payload.source_ready_for_handoff)),
    ...(payload.source_action_result_status ? [
      fact("source_action_result_status", payload.source_action_result_status),
    ] : []),
    ...(payload.source_action_decision ? [
      fact("source_action_decision", payload.source_action_decision),
    ] : []),
    ...(payload.source_result_refs ? [
      fact("source_result_refs", String(arrayValue(payload.source_result_refs).length)),
    ] : []),
    fact("business_validation", payload.business_validation || "not_validated"),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAcceptanceFeedbackCandidateFacts(payload) {
  return [
    fact("candidate_generation_status", payload.candidate_generation_status || "unknown"),
    fact("source_acceptance_decision", payload.source_acceptance_decision || "unknown"),
    fact("memory_candidate_status", payload.memory_candidate?.status || "unknown"),
    fact("promotion_decision", payload.promotion_decision_template?.decision || "unknown"),
    fact("candidate_is_promoted_memory", yesNo(payload.candidate_is_promoted_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionAcceptanceFeedbackCandidatePromotionFacts(payload) {
  return [
    fact("decision", payload.decision || "unknown"),
    fact("decision_effect", payload.decision_effect || "unknown"),
    fact("candidate_id", payload.candidate_id || "unknown"),
    ...(payload.source_artifact_type ? [
      fact("source_artifact_type", payload.source_artifact_type),
    ] : []),
    ...(payload.source_artifact_status ? [
      fact("source_artifact_status", payload.source_artifact_status),
    ] : []),
    ...(payload.source_target_ref ? [
      fact("source_target_ref", payload.source_target_ref),
    ] : []),
    fact("source_acceptance_decision", payload.source_acceptance_decision || "unknown"),
    fact("candidate_reuse_allowed", yesNo(payload.candidate_reuse_allowed)),
    fact("candidate_is_durable_memory", yesNo(payload.candidate_is_durable_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionOperatorFeedbackCandidateFacts(payload) {
  return [
    fact("candidate_generation_status", payload.candidate_generation_status || "unknown"),
    fact("memory_candidate_status", payload.memory_candidate?.status || "unknown"),
    fact("promotion_decision", payload.promotion_decision_template?.decision || "unknown"),
    fact("candidate_is_promoted_memory", yesNo(payload.candidate_is_promoted_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

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

export function productionOperatorManifestCheckFacts(payload) {
  return [
    fact("check_status", payload.check_status || "unknown"),
    fact("checked_refs", String(payload.checked_ref_count ?? arrayValue(payload.checked_refs).length)),
    fact("missing_refs", String(arrayValue(payload.missing_refs).length)),
    fact("mismatched_refs", String(arrayValue(payload.mismatched_refs).length)),
    fact("unsafe_refs", String(arrayValue(payload.unsafe_refs).length)),
    fact("failed_nodes", String(arrayValue(payload.failed_nodes).length)),
    fact("failed_controls", String(arrayValue(payload.failed_controls).length)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionOperatorHandoffFacts(payload) {
  const acceptanceCandidatePromotion = objectValue(payload.acceptance_feedback_candidate_promotion);
  return [
    fact("handoff_status", payload.handoff_status || "unknown"),
    fact("manifest_check_status", payload.manifest_check_status || "unknown"),
    fact("artifact_refs", String(arrayValue(payload.artifact_refs).length)),
    fact("blocked_items", String(arrayValue(payload.blocked_items).length)),
    fact("next_operator_action", payload.next_operator_action?.action || "unknown"),
    ...(acceptanceCandidatePromotion.decision ? [
      fact("acceptance_feedback_candidate_promotion_decision", acceptanceCandidatePromotion.decision),
    ] : []),
    ...(acceptanceCandidatePromotion.decision_effect ? [
      fact("acceptance_feedback_candidate_promotion_effect", acceptanceCandidatePromotion.decision_effect),
    ] : []),
    ...(acceptanceCandidatePromotion.candidate_included_in_context !== undefined ? [
      fact("acceptance_feedback_candidate_included", yesNo(acceptanceCandidatePromotion.candidate_included_in_context)),
    ] : []),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionOperatorRunPackageFacts(payload) {
  const acceptanceCandidatePromotion = objectValue(payload.acceptance_feedback_candidate_promotion);
  return [
    fact("package_status", payload.package_status || "unknown"),
    fact("manifest_check_status", payload.manifest_check_status || "unknown"),
    fact("handoff_status", payload.handoff_status || "unknown"),
    fact("package_items", String(arrayValue(payload.package_items).length)),
    fact("blocked_items", String(arrayValue(payload.blocked_items).length)),
    fact("next_operator_action", payload.next_operator_action?.action || "unknown"),
    ...(acceptanceCandidatePromotion.decision ? [
      fact("acceptance_feedback_candidate_promotion_decision", acceptanceCandidatePromotion.decision),
    ] : []),
    ...(acceptanceCandidatePromotion.decision_effect ? [
      fact("acceptance_feedback_candidate_promotion_effect", acceptanceCandidatePromotion.decision_effect),
    ] : []),
    ...(acceptanceCandidatePromotion.candidate_included_in_context !== undefined ? [
      fact("acceptance_feedback_candidate_included", yesNo(acceptanceCandidatePromotion.candidate_included_in_context)),
    ] : []),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionOperatorRunPackageCheckFacts(payload) {
  const acceptanceCandidatePromotionCheck = objectValue(payload.acceptance_feedback_candidate_promotion_check);
  return [
    fact("check_status", payload.check_status || "unknown"),
    fact("package_status", payload.package_status || "unknown"),
    fact("ready_for_handoff", yesNo(payload.ready_for_handoff)),
    fact("checked_items", String(payload.checked_item_count ?? arrayValue(payload.checked_items).length)),
    fact("missing_refs", String(arrayValue(payload.missing_refs).length)),
    fact("mismatched_refs", String(arrayValue(payload.mismatched_refs).length)),
    fact("unsafe_refs", String(arrayValue(payload.unsafe_refs).length)),
    fact("failed_controls", String(arrayValue(payload.failed_controls).length)),
    ...(acceptanceCandidatePromotionCheck.status ? [
      fact("acceptance_feedback_candidate_promotion_check", acceptanceCandidatePromotionCheck.status),
    ] : []),
    ...(acceptanceCandidatePromotionCheck.decision_effect ? [
      fact("acceptance_feedback_candidate_promotion_effect", acceptanceCandidatePromotionCheck.decision_effect),
    ] : []),
    ...(acceptanceCandidatePromotionCheck.candidate_included_in_context !== undefined ? [
      fact("acceptance_feedback_candidate_included", yesNo(acceptanceCandidatePromotionCheck.candidate_included_in_context)),
    ] : []),
    ...(acceptanceCandidatePromotionCheck.handoff_matches_package !== undefined ? [
      fact("acceptance_feedback_candidate_handoff_matches_package", yesNo(acceptanceCandidatePromotionCheck.handoff_matches_package)),
    ] : []),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionNextOperatorStartPacketFacts(payload) {
  return [
    fact("start_packet_status", payload.start_packet_status || "unknown"),
    fact("ready_for_next_operator", yesNo(payload.ready_for_next_operator)),
    fact("checked_package_items", String(payload.checked_package_item_count ?? arrayValue(payload.checked_package_items).length)),
    fact("next_operator_action", payload.next_operator_action?.action || "unknown"),
    fact("package_check_status", payload.package_check_status || "unknown"),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionNextOperatorStartEventFacts(payload) {
  return [
    fact("event_status", payload.event_status || "unknown"),
    fact("start_decision", payload.start_decision || "unknown"),
    fact("source_start_packet_status", payload.source_start_packet_status || "unknown"),
    fact("source_ready_for_next_operator", yesNo(payload.source_ready_for_next_operator)),
    fact("source_next_operator_action", payload.source_next_operator_action || "unknown"),
    fact("human_acceptance", payload.claim_boundaries?.human_acceptance || "unknown"),
    fact("next_pass_execution", payload.claim_boundaries?.next_pass_execution || "unknown"),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionNextOperatorActionResultFacts(payload) {
  return [
    fact("result_status", payload.result_status || "unknown"),
    fact("action_decision", payload.action_decision || "unknown"),
    fact("source_start_event_status", payload.source_start_event_status || "unknown"),
    fact("source_next_operator_action", payload.source_next_operator_action || "unknown"),
    fact("result_refs", String(arrayValue(payload.result_refs).length)),
    fact("action_result_acceptance", yesNo(payload.action_result_is_acceptance)),
    fact("action_result_execution", yesNo(payload.action_result_is_execution)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

export function productionSessionFacts(payload) {
  return [
    fact("session_status", payload.session_status || "unknown"),
    fact("included_refs", String(payload.context_summary?.included_ref_count ?? 0)),
    fact("blocked_refs", String(payload.context_summary?.blocked_ref_count ?? 0)),
    fact("next_action", payload.next_operator_action?.action || "unknown"),
    fact("provider_mode", payload.provider_mode || "unknown"),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
  ];
}

export function productionLoopFacts(payload) {
  return [
    fact("artifacts", String(arrayValue(payload.artifact_ledger).length)),
    fact("feedback_events", String(arrayValue(payload.feedback_events).length)),
    fact("memory_candidates", String(arrayValue(payload.memory_candidates).length)),
    fact("promotion_decisions", String(arrayValue(payload.promotion_decisions).length)),
    fact("provider_mode", payload.provider_mode || "unknown"),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
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

function usedContextRefCount(outputArtifacts) {
  const refs = arrayValue(outputArtifacts).flatMap((item) => arrayValue(item?.used_context_refs).map(String));
  return new Set(refs).size;
}
