const OPERATOR_FEEDBACK_CANDIDATE_TYPE = "agentflow_production_memory_operator_feedback_candidate_packet";

export function buildProductionMemoryOperatorFeedbackCandidateView(workspace, fallback) {
  const artifact = workspace?.productionMemoryOperatorFeedbackCandidatePacket;
  if (!isOperatorFeedbackCandidateArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const candidate = objectValue(payload.memory_candidate);
  const template = objectValue(payload.promotion_decision_template);
  const boundaries = objectValue(payload.claim_boundaries);
  const candidateOnly = payload.candidate_generation_status === "candidate_only";
  const candidateStatus = candidate.status || "unknown";
  const ready = candidateOnly && payload.provider_calls_started === false && payload.writes_company_kb === false;

  return {
    ...fallback,
    state: candidateOnly ? "candidate review" : "blocked",
    project: {
      title: candidate.candidate_id || payload.packet_id || artifact.fileName,
      brief: `Operator feedback candidate: ${candidateStatus}`,
      format: OPERATOR_FEEDBACK_CANDIDATE_TYPE,
      route: "selected local JSON only; read-only operator feedback candidate packet",
    },
    workflow_actions: [
      action("inspect_candidate_packet", "Inspect packet", ready ? "review ready" : "blocked", "project"),
      action("inspect_memory_candidate", "Inspect candidate", candidate.candidate_id ? "review ready" : "missing", "memory-loaded"),
      action("inspect_promotion_template", "Inspect template", "blocked", "review"),
      action("review_explicit_decision", "Review decision", "blocked", "next-pass"),
    ],
    assets: [
      {
        id: candidate.candidate_id || "memory-candidate",
        label: candidate.target_ref || "operator feedback candidate",
        detail: candidate.statement || "candidate-only packet",
        status: candidateStatus,
      },
    ],
    bundle_summary: [
      card("candidate_packet", "Candidate packet", ready ? "review ready" : "blocked", payload.candidate_generation_status || "unknown"),
      card("memory_candidate", "Memory candidate", candidateStatus, candidate.target_ref || "unknown"),
      card("promotion_decision", "Promotion decision", "blocked", template.decision || "pending"),
      card("acceptance_boundary", "Acceptance boundary", "blocked", boundaries.human_acceptance || "not_claimed"),
    ],
    memory_loaded: [
      {
        id: candidate.candidate_id || "operator-feedback-candidate",
        title: candidate.target_ref || "operator feedback candidate",
        why_eligible: "candidate-only packet; explicit promotion decision required before reuse",
        source_evidence_refs: arrayValue(candidate.source_feedback_ids),
        promotion_status: template.decision || "pending",
        request_projection: candidate.statement || "candidate requires operator review",
        feedback_effect: "visible as candidate feedback only; no durable memory or Company KB write",
        status: candidateStatus,
      },
    ],
    lanes: [
      lane("feedback-candidate-packet", "Feedback candidate packet", ready ? "review ready" : "blocked", payload.source_feedback_event_id || "feedback", payload.candidate_generation_status || "unknown"),
      lane("memory-candidate", "Memory candidate", candidateStatus, candidate.candidate_id || "candidate", candidate.target_ref || "target unknown"),
      lane("promotion-template", "Promotion template", "blocked", template.decision || "pending", "explicit decision required"),
    ],
    protocol_summary: {
      title: "Production memory operator feedback candidate",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("candidate only", candidateOnly),
        control("pending promotion template", template.decision === "pending", "blocked"),
        control("feedback is not memory", payload.feedback_is_memory === false),
        control("candidate not promoted memory", payload.candidate_is_promoted_memory === false),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("human acceptance not claimed", boundaries.human_acceptance === "not_claimed", "blocked"),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `source_target=${payload.source_target_node_id || "unknown"}`,
      visual_consistency: `candidate_status=${candidateStatus}`,
      boundary: "candidate-only packet / pending promotion template / no Company KB write",
    },
    feedback: {
      status: candidateStatus,
      summary: candidate.statement || "operator feedback candidate requires explicit promotion review",
    },
    next_pass: {
      status: "blocked",
      action: "requires_explicit_promotion_decision_before_next_context",
    },
    timeline: [
      step("Feedback event", "review ready", payload.source_feedback_event_id),
      step("Candidate", candidateStatus, candidate.candidate_id),
      step("Promotion template", "blocked", template.decision || "pending"),
      step("Boundaries", "blocked", "not human acceptance / not promoted memory"),
    ],
  };
}

function boundaryItems(payload) {
  return arrayValue(payload.non_claims).map((item) => ({
    label: item,
    status: "blocked",
    detail: "non-claim boundary",
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
  return { label, status: forcedStatus || (passed ? "review ready" : "blocked"), detail: passed ? "confirmed by candidate packet" : "not confirmed" };
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isOperatorFeedbackCandidateArtifact(artifact) {
  return artifact?.artifactType === OPERATOR_FEEDBACK_CANDIDATE_TYPE && artifact?.payload?.kind === OPERATOR_FEEDBACK_CANDIDATE_TYPE;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
