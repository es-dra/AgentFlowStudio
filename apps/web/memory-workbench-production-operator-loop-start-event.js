import { action, card, control, lane, step } from "./memory-workbench-production-operator-loop-utils.js";

export function isStartEventReady(startEvent) {
  return startEvent?.event_status === "operator_started" && startEvent.start_decision === "started";
}

export function startEventActions(startEvent, ready) {
  if (!startEvent) return [];
  return [action("inspect_next_operator_start_event", "Inspect start event", ready ? "review ready" : "blocked", "next-pass")];
}

export function startEventCards(startEvent) {
  if (!startEvent) return [];
  return [
    card(
      "next_operator_start_event",
      "Next operator start event",
      startEvent.event_status || "unknown",
      startEvent.start_decision || "unknown",
    ),
  ];
}

export function startEventMemoryRows(startEvent, ready) {
  if (!startEvent) return [];
  return [
    {
      id: "next_operator_start_event",
      title: "Next operator start event",
      why_eligible: "post-check start receipt evidence only",
      source_evidence_refs: [startEvent.path || "next_operator_start_event/next_operator_start_event.json"],
      promotion_status: "not_promoted",
      request_projection: startEvent.summary || startEvent.event_status || "start event recorded",
      feedback_effect: "no acceptance, execution, durable memory, or Company KB claim",
      status: ready ? "review ready" : "blocked",
    },
  ];
}

export function startEventLanes(startEvent, ready) {
  if (!startEvent) return [];
  return [
    lane(
      "next-operator-start-event",
      "Next operator start event",
      ready ? "ready" : "blocked",
      startEvent.start_decision || "unknown",
      startEvent.event_status || "unknown",
    ),
  ];
}

export function startEventControls(startEvent, ready) {
  if (!startEvent) return [];
  return [
    control("next operator start event recorded", ready),
    control("next operator start event provider calls not started", startEvent.provider_calls_started === false),
    control("next operator start event memory write disabled", startEvent.writes_long_term_memory === false),
    control("next operator start event Company KB write disabled", startEvent.writes_company_kb === false),
    control("next operator start event not acceptance", startEvent.start_event_is_acceptance === false),
    control("next operator start event not execution", startEvent.start_event_is_execution === false),
    control("next operator start event not memory", startEvent.start_event_is_memory === false),
  ];
}

export function startEventTimeline(startEvent, ready) {
  if (!startEvent) return [];
  return [step("Next operator start event", ready ? "ready" : "blocked", startEvent.path || "not recorded")];
}

export function nextPassStatusFor(
  ready,
  startPacket,
  startPacketReady,
  startEvent,
  startEventReady,
  actionResult = null,
  actionResultReady = false,
) {
  if (actionResult) return actionResultReady ? "ready" : "blocked";
  if (startEvent) return startEventReady ? "ready" : "blocked";
  if (startPacket) return startPacketReady ? "ready" : "blocked";
  return ready ? "ready" : "blocked";
}

export function nextPassActionFor(
  ready,
  resultScaffold,
  promotion,
  feedbackCandidatePromotion,
  acceptanceCandidatePromotion,
  startPacket,
  startPacketReady,
  startEvent,
  startEventReady,
  actionResult = null,
  actionResultReady = false,
) {
  if (!ready) return "resolve_operator_loop_blockers";
  if (actionResult) return actionResultReady ? "inspect_next_operator_action_result_before_next_loop" : "resolve_next_operator_action_result_blockers";
  if (startEvent) return startEventReady ? "continue_recorded_next_operator_action" : "resolve_next_operator_start_event_blockers";
  if (startPacket) return startPacketReady ? "start_next_operator_action" : "resolve_next_operator_start_packet_blockers";
  if (acceptanceCandidatePromotion) return "inspect_acceptance_feedback_candidate_overlay_before_next_pass";
  if (feedbackCandidatePromotion) return "inspect_operator_feedback_candidate_overlay_before_next_pass";
  if (promotion) return "inspect_next_pass_promotion_overlay_before_followup_context";
  if (resultScaffold) return "inspect_next_pass_result_scaffold_before_review";
  return "inspect_generated_artifacts_before_next_pass";
}
