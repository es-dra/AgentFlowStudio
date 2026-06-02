import { action, card, control, lane, step } from "./memory-workbench-production-operator-loop-utils.js";

export function isActionResultReady(actionResult) {
  return actionResult?.result_status === "action_completed" && actionResult.action_decision === "completed";
}

export function actionResultActions(actionResult, ready) {
  if (!actionResult) return [];
  return [
    action(
      "inspect_next_operator_action_result",
      "Inspect action result",
      ready ? "review ready" : "blocked",
      "next-pass",
    ),
  ];
}

export function actionResultCards(actionResult) {
  if (!actionResult) return [];
  return [
    card(
      "next_operator_action_result",
      "Next operator action result",
      actionResult.result_status || "unknown",
      actionResult.action_decision || "unknown",
    ),
  ];
}

export function actionResultMemoryRows(actionResult, ready) {
  if (!actionResult) return [];
  return [
    {
      id: "next_operator_action_result",
      title: "Next operator action result",
      why_eligible: "post-check action outcome evidence only",
      source_evidence_refs: [actionResult.path || "next_operator_action_result/next_operator_action_result.json"],
      promotion_status: "not_promoted",
      request_projection: actionResult.summary || actionResult.result_status || "action result recorded",
      feedback_effect: "no acceptance, execution, durable memory, Company KB, candidate, or promotion claim",
      status: ready ? "review ready" : "blocked",
    },
  ];
}

export function actionResultLanes(actionResult, ready) {
  if (!actionResult) return [];
  return [
    lane(
      "next-operator-action-result",
      "Next operator action result",
      ready ? "ready" : "blocked",
      actionResult.action_decision || "unknown",
      actionResult.result_status || "unknown",
    ),
  ];
}

export function actionResultControls(actionResult, ready) {
  if (!actionResult) return [];
  return [
    control("next operator action result completed", ready),
    control("next operator action result provider calls not started", actionResult.provider_calls_started === false),
    control("next operator action result memory write disabled", actionResult.writes_long_term_memory === false),
    control("next operator action result Company KB write disabled", actionResult.writes_company_kb === false),
    control("next operator action result not acceptance", actionResult.action_result_is_acceptance === false),
    control("next operator action result not execution", actionResult.action_result_is_execution === false),
    control("next operator action result not memory", actionResult.action_result_is_memory === false),
    control("next operator action result creates no candidate", actionResult.creates_memory_candidate === false),
    control("next operator action result creates no promotion decision", actionResult.creates_promotion_decision === false),
  ];
}

export function actionResultTimeline(actionResult, ready) {
  if (!actionResult) return [];
  return [step("Next operator action result", ready ? "ready" : "blocked", actionResult.path || "not recorded")];
}
