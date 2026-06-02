export function acceptanceFeedbackCandidatePromotionParts(payload) {
  const summary = objectValue(payload?.acceptance_feedback_candidate_promotion);
  if (!summary.decision && !summary.decision_effect) {
    return { actions: [], cards: [], memory: [], lanes: [], controls: [] };
  }
  const status = statusFor(summary);
  return {
    actions: [
      actionItem(
        "inspect_acceptance_feedback_candidate_promotion",
        "Inspect acceptance feedback candidate",
        status,
        "memory-loaded",
      ),
    ],
    cards: [
      card(
        "acceptance_feedback_candidate_promotion",
        "Acceptance feedback candidate",
        status,
        summary.decision_effect || summary.decision || "present",
      ),
    ],
    memory: [
      {
        id: "acceptance_feedback_candidate_promotion",
        title: "Acceptance feedback candidate promotion",
        why_eligible: "explicit promotion decision surfaced from the selected operator artifact",
        source_evidence_refs: [
          summary.decision_id || "acceptance feedback candidate promotion decision",
          summary.source_acceptance_feedback_event_id || "acceptance feedback event",
        ],
        promotion_status: summary.decision || "unknown",
        request_projection: summary.decision_effect || "operator-visible acceptance feedback context",
        feedback_effect: summary.candidate_included_in_context === true
          ? "included in next context; still not durable memory or Company KB"
          : "blocked from next context unless explicitly reviewed again",
        status,
      },
    ],
    lanes: [
      lane(
        "acceptance-feedback-candidate-promotion",
        "Acceptance feedback candidate",
        status,
        summary.decision || "unknown",
        summary.decision_effect || "unknown",
      ),
    ],
    controls: [
      {
        label: "acceptance feedback candidate included",
        status,
        detail: summary.candidate_included_in_context === true ? "included in context" : "not included",
      },
    ],
  };
}

function statusFor(summary) {
  if (summary.candidate_blocked_from_context === true) return "blocked";
  return "review ready";
}

function actionItem(id, label, status, focusTarget) {
  return { id, label, status, focusTarget, focus_target: focusTarget };
}

function card(id, title, status, detail) {
  return { id, title, status, detail };
}

function lane(id, title, status, input, output) {
  return { id, title, status, input, output };
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
