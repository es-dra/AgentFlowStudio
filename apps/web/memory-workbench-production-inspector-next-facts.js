import { arrayValue, fact, objectValue, usedContextRefCount, yesNo } from "./memory-workbench-production-fact-utils.js";

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
