const OPERATOR_FEEDBACK_TYPE = "agentflow_production_memory_operator_feedback_event";

export function buildProductionMemoryOperatorFeedbackView(workspace, fallback) {
  const artifact = workspace?.productionMemoryOperatorFeedbackEvent;
  if (!isOperatorFeedbackArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const boundaries = payload.claim_boundaries || {};
  const ready = payload.status === "evidence_only"
    && payload.provider_calls_started === false
    && payload.writes_long_term_memory === false
    && payload.writes_company_kb === false
    && payload.feedback_is_memory === false;

  return {
    ...fallback,
    state: ready ? "operator feedback captured" : "blocked",
    project: {
      title: payload.target_node_id || payload.feedback_id || artifact.fileName,
      brief: `Operator feedback: ${payload.decision || "unknown"}`,
      format: OPERATOR_FEEDBACK_TYPE,
      route: "selected local JSON only; read-only operator feedback event",
    },
    workflow_actions: [
      action("inspect_operator_feedback", "Inspect feedback", ready ? "review ready" : "blocked", "feedback"),
      action("inspect_target_node", "Inspect target", payload.target_node_id ? "review ready" : "missing", "review"),
      action("inspect_boundaries", "Inspect boundaries", "blocked", "memory-loaded"),
      action("decide_candidate_path", "Decide candidate path", "blocked", "next-pass"),
    ],
    assets: [
      {
        id: payload.feedback_id || artifact.fileName,
        label: "operator feedback event",
        detail: payload.target_node_id || "target not recorded",
        status: ready ? "review ready" : "blocked",
      },
    ],
    bundle_summary: [
      card("operator_feedback", "Operator feedback", ready ? "review ready" : "blocked", payload.decision || "unknown"),
      card("target_node", "Target node", payload.target_node_status || "unknown", payload.target_node_id || "unknown"),
      card("memory_boundary", "Memory boundary", payload.feedback_is_memory === false ? "review ready" : "blocked", "feedback is not memory"),
      card("acceptance_boundary", "Acceptance boundary", "blocked", boundaries.human_acceptance || "not_claimed"),
    ],
    memory_loaded: [
      {
        id: payload.feedback_id || "operator-feedback",
        title: payload.target_node_id || "operator feedback",
        why_eligible: "operator feedback is review evidence only",
        source_evidence_refs: [payload.source_operator_loop_id || "operator loop"],
        promotion_status: "not_promoted",
        request_projection: payload.summary || "not recorded",
        feedback_effect: "does not create memory candidate or promotion decision",
        status: payload.status || "unknown",
      },
    ],
    lanes: [
      lane("operator-feedback", "Operator feedback", ready ? "ready" : "blocked", payload.feedback_id || "feedback", payload.decision || "unknown"),
      lane("target-node", "Target node", payload.target_node_status || "unknown", payload.target_node_id || "unknown", payload.target_detail || ""),
      lane("memory-boundary", "Memory boundary", payload.feedback_is_memory === false ? "review ready" : "blocked", "feedback", "not memory"),
      lane("non-claims", "Non-claims", "blocked", "no human acceptance", "no durable memory"),
    ],
    protocol_summary: {
      title: "Production memory operator feedback",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("evidence only", payload.status === "evidence_only"),
        control("feedback is not memory", payload.feedback_is_memory === false),
        control("memory candidate not created", payload.creates_memory_candidate === false),
        control("promotion decision not created", payload.creates_promotion_decision === false),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("human acceptance not claimed", boundaries.human_acceptance === "not_claimed", "blocked"),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `target=${payload.target_node_id || "unknown"}`,
      visual_consistency: `decision=${payload.decision || "unknown"}`,
      boundary: "operator feedback evidence only / no provider call / no Company KB write",
    },
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: payload.summary || "operator feedback recorded without memory promotion",
    },
    next_pass: {
      status: "blocked",
      action: "requires_explicit_candidate_promotion_path",
    },
    timeline: [
      step("Source manifest", payload.source_chain_status || "unknown", payload.source_operator_loop_id),
      step("Target node", payload.target_node_status || "unknown", payload.target_node_id),
      step("Feedback", payload.status || "unknown", payload.decision),
      step("Boundaries", "blocked", "not human acceptance / not durable memory"),
    ],
  };
}

function boundaryItems(payload) {
  const boundaries = payload.claim_boundaries || {};
  const claims = Array.isArray(payload.non_claims) ? payload.non_claims : [];
  const items = claims.length ? claims : ["not human acceptance", "not durable memory", "not provider success"];
  return items.map((item) => ({
    label: item,
    status: "blocked",
    detail: boundaries.human_acceptance || "non-claim boundary",
  }));
}

function action(id, label, status, focusTarget) {
  return { id, label, status, focusTarget, focus_target: focusTarget };
}

function card(id, title, status, detail) {
  return { id, title, status, detail };
}

function lane(id, title, status, input, output) {
  return { id, title, status, input, output };
}

function control(label, passed, forcedStatus = null) {
  return { label, status: forcedStatus || (passed ? "review ready" : "blocked"), detail: passed ? "confirmed by feedback event" : "not confirmed" };
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isOperatorFeedbackArtifact(artifact) {
  return artifact?.artifactType === OPERATOR_FEEDBACK_TYPE && artifact?.payload?.kind === OPERATOR_FEEDBACK_TYPE;
}
