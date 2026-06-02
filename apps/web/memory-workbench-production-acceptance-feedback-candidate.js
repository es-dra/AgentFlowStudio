const ACCEPTANCE_FEEDBACK_CANDIDATE_TYPE = "agentflow_production_memory_acceptance_feedback_candidate_packet";

export function buildProductionMemoryAcceptanceFeedbackCandidateView(workspace, fallback) {
  const artifact = workspace?.productionMemoryAcceptanceFeedbackCandidatePacket;
  if (!isAcceptanceFeedbackCandidateArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const candidate = objectValue(payload.memory_candidate);
  const template = objectValue(payload.promotion_decision_template);
  const candidateOnly = payload.candidate_generation_status === "candidate_only";
  const candidateStatus = candidate.status || "unknown";
  const ready = candidateOnly && payload.provider_calls_started === false && payload.writes_company_kb === false;

  return {
    ...fallback,
    state: candidateOnly ? "acceptance candidate review" : "blocked",
    project: {
      title: candidate.candidate_id || payload.packet_id || artifact.fileName,
      brief: `Acceptance feedback candidate: ${candidateStatus}`,
      format: ACCEPTANCE_FEEDBACK_CANDIDATE_TYPE,
      route: "selected local JSON only; read-only acceptance feedback candidate packet",
    },
    workflow_actions: [
      action("inspect_acceptance_candidate_packet", "Inspect packet", ready ? "review ready" : "blocked", "project"),
      action("inspect_memory_candidate", "Inspect candidate", candidate.candidate_id ? "review ready" : "missing", "memory-loaded"),
      action("inspect_promotion_template", "Inspect template", "blocked", "review"),
      action("review_explicit_decision", "Review decision", "blocked", "next-pass"),
    ],
    assets: [
      {
        id: candidate.candidate_id || "memory-candidate",
        label: candidate.target_ref || "acceptance feedback candidate",
        detail: candidate.statement || "candidate-only packet",
        status: candidateStatus,
      },
    ],
    bundle_summary: [
      card("candidate_packet", "Candidate packet", ready ? "review ready" : "blocked", payload.candidate_generation_status || "unknown"),
      card("source_acceptance", "Source acceptance", payload.source_human_acceptance_recorded ? "review ready" : "blocked", payload.source_acceptance_decision || "unknown"),
      card("memory_candidate", "Memory candidate", candidateStatus, candidate.target_ref || "unknown"),
      card("promotion_decision", "Promotion decision", "blocked", template.decision || "pending"),
      card("business_validation", "Business validation", "blocked", payload.business_validation || "not_validated"),
    ],
    memory_loaded: [
      {
        id: candidate.candidate_id || "acceptance-feedback-candidate",
        title: candidate.target_ref || "acceptance feedback candidate",
        why_eligible: "candidate-only packet; explicit promotion decision required before reuse",
        source_evidence_refs: arrayValue(candidate.source_feedback_ids),
        promotion_status: template.decision || "pending",
        request_projection: candidate.statement || "candidate requires operator review",
        feedback_effect: "visible as candidate feedback only; no durable memory or Company KB write",
        status: candidateStatus,
      },
    ],
    lanes: [
      lane("acceptance-candidate-packet", "Acceptance candidate packet", ready ? "review ready" : "blocked", payload.source_acceptance_feedback_event_id || "feedback", payload.candidate_generation_status || "unknown"),
      lane("memory-candidate", "Memory candidate", candidateStatus, candidate.candidate_id || "candidate", candidate.target_ref || "target unknown"),
      lane("promotion-template", "Promotion template", "blocked", template.decision || "pending", "explicit decision required"),
      lane("business-boundary", "Business boundary", "blocked", "source acceptance", payload.business_validation || "not_validated"),
    ],
    protocol_summary: {
      title: "Production memory acceptance feedback candidate",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("candidate only", candidateOnly),
        control("source human acceptance recorded", payload.source_human_acceptance_recorded === true),
        control("pending promotion template", template.decision === "pending", "blocked"),
        control("feedback is not memory", payload.feedback_is_memory === false),
        control("candidate not promoted memory", payload.candidate_is_promoted_memory === false),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `source_acceptance=${payload.source_acceptance_decision || "unknown"}`,
      visual_consistency: `candidate_status=${candidateStatus}`,
      boundary: "candidate-only packet / pending promotion template / no business validation",
    },
    feedback: {
      status: candidateStatus,
      summary: candidate.statement || "acceptance feedback candidate requires explicit promotion review",
    },
    next_pass: {
      status: "blocked",
      action: "requires_explicit_promotion_decision_before_next_context",
    },
    timeline: [
      step("Acceptance feedback", "review ready", payload.source_acceptance_feedback_event_id),
      step("Candidate", candidateStatus, candidate.candidate_id),
      step("Promotion template", "blocked", template.decision || "pending"),
      step("Boundaries", "blocked", "not business validation / not promoted memory"),
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

function isAcceptanceFeedbackCandidateArtifact(artifact) {
  return artifact?.artifactType === ACCEPTANCE_FEEDBACK_CANDIDATE_TYPE && artifact?.payload?.kind === ACCEPTANCE_FEEDBACK_CANDIDATE_TYPE;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
