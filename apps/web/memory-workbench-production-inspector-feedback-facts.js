import { arrayValue, fact, objectValue, usedContextRefCount, yesNo } from "./memory-workbench-production-fact-utils.js";

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
