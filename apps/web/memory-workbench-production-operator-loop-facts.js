export function productionOperatorLoopFacts(payload) {
  const resultScaffold = objectValue(payload.next_pass_result);
  const promotion = objectValue(payload.next_pass_promotion);
  const feedbackCandidatePromotion = objectValue(payload.operator_feedback_candidate_promotion);
  const acceptanceCandidatePromotion = objectValue(payload.acceptance_feedback_candidate_promotion);
  const startPacket = objectValue(payload.next_operator_start_packet);
  const startEvent = objectValue(payload.next_operator_start_event);
  const actionResult = objectValue(payload.next_operator_action_result);
  return [
    fact("chain_status", payload.chain_status || "unknown"),
    fact("operator_nodes", String(arrayValue(payload.operator_loop_nodes).length)),
    fact("output_artifacts", String(arrayValue(payload.output_artifacts).length)),
    fact("post_check_artifacts", String(arrayValue(payload.post_check_artifacts).length)),
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
    ...(startPacket.start_packet_status ? [
      fact("next_operator_start_packet_status", startPacket.start_packet_status),
    ] : []),
    ...(startPacket.ready_for_next_operator !== undefined ? [
      fact("ready_for_next_operator", yesNo(startPacket.ready_for_next_operator)),
    ] : []),
    ...(startEvent.event_status ? [
      fact("next_operator_start_event_status", startEvent.event_status),
    ] : []),
    ...(startEvent.start_decision ? [
      fact("next_operator_start_decision", startEvent.start_decision),
    ] : []),
    ...(startEvent.start_event_is_acceptance !== undefined ? [
      fact("next_operator_start_event_acceptance", yesNo(startEvent.start_event_is_acceptance)),
    ] : []),
    ...(startEvent.start_event_is_execution !== undefined ? [
      fact("next_operator_start_event_execution", yesNo(startEvent.start_event_is_execution)),
    ] : []),
    ...(actionResult.result_status ? [
      fact("next_operator_action_result_status", actionResult.result_status),
    ] : []),
    ...(actionResult.action_decision ? [
      fact("next_operator_action_decision", actionResult.action_decision),
    ] : []),
    ...(actionResult.action_result_is_acceptance !== undefined ? [
      fact("next_operator_action_result_acceptance", yesNo(actionResult.action_result_is_acceptance)),
    ] : []),
    ...(actionResult.action_result_is_execution !== undefined ? [
      fact("next_operator_action_result_execution", yesNo(actionResult.action_result_is_execution)),
    ] : []),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
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
