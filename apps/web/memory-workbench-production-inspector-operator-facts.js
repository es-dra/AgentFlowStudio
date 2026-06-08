import { arrayValue, fact, objectValue, usedContextRefCount, yesNo } from "./memory-workbench-production-fact-utils.js";

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
