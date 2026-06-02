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
    fact("source_check_status", payload.source_check_status || "unknown"),
    fact("source_ready_for_handoff", yesNo(payload.source_ready_for_handoff)),
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
  return [
    fact("handoff_status", payload.handoff_status || "unknown"),
    fact("manifest_check_status", payload.manifest_check_status || "unknown"),
    fact("artifact_refs", String(arrayValue(payload.artifact_refs).length)),
    fact("blocked_items", String(arrayValue(payload.blocked_items).length)),
    fact("next_operator_action", payload.next_operator_action?.action || "unknown"),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionOperatorRunPackageFacts(payload) {
  return [
    fact("package_status", payload.package_status || "unknown"),
    fact("manifest_check_status", payload.manifest_check_status || "unknown"),
    fact("handoff_status", payload.handoff_status || "unknown"),
    fact("package_items", String(arrayValue(payload.package_items).length)),
    fact("blocked_items", String(arrayValue(payload.blocked_items).length)),
    fact("next_operator_action", payload.next_operator_action?.action || "unknown"),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionOperatorRunPackageCheckFacts(payload) {
  return [
    fact("check_status", payload.check_status || "unknown"),
    fact("package_status", payload.package_status || "unknown"),
    fact("ready_for_handoff", yesNo(payload.ready_for_handoff)),
    fact("checked_items", String(payload.checked_item_count ?? arrayValue(payload.checked_items).length)),
    fact("missing_refs", String(arrayValue(payload.missing_refs).length)),
    fact("mismatched_refs", String(arrayValue(payload.mismatched_refs).length)),
    fact("unsafe_refs", String(arrayValue(payload.unsafe_refs).length)),
    fact("failed_controls", String(arrayValue(payload.failed_controls).length)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
  ];
}

export function productionOperatorLoopFacts(payload) {
  const resultScaffold = objectValue(payload.next_pass_result);
  const promotion = objectValue(payload.next_pass_promotion);
  const feedbackCandidatePromotion = objectValue(payload.operator_feedback_candidate_promotion);
  const acceptanceCandidatePromotion = objectValue(payload.acceptance_feedback_candidate_promotion);
  return [
    fact("chain_status", payload.chain_status || "unknown"),
    fact("operator_nodes", String(arrayValue(payload.operator_loop_nodes).length)),
    fact("output_artifacts", String(arrayValue(payload.output_artifacts).length)),
    ...(resultScaffold.result_status ? [fact("next_pass_result_status", resultScaffold.result_status)] : []),
    ...(resultScaffold.output_artifact_count !== undefined ? [
      fact("next_pass_result_output_artifacts", String(resultScaffold.output_artifact_count)),
    ] : []),
    ...(promotion.decision ? [fact("next_pass_promotion_decision", promotion.decision)] : []),
    ...(promotion.decision_effect ? [fact("next_pass_promotion_effect", promotion.decision_effect)] : []),
    ...(feedbackCandidatePromotion.decision ? [
      fact("operator_feedback_candidate_promotion_decision", feedbackCandidatePromotion.decision),
    ] : []),
    ...(feedbackCandidatePromotion.decision_effect ? [
      fact("operator_feedback_candidate_promotion_effect", feedbackCandidatePromotion.decision_effect),
    ] : []),
    ...(acceptanceCandidatePromotion.decision ? [
      fact("acceptance_feedback_candidate_promotion_decision", acceptanceCandidatePromotion.decision),
    ] : []),
    ...(acceptanceCandidatePromotion.decision_effect ? [
      fact("acceptance_feedback_candidate_promotion_effect", acceptanceCandidatePromotion.decision_effect),
    ] : []),
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
