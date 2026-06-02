const DECISION_TYPE = "agentflow_production_memory_acceptance_feedback_candidate_promotion_decision";

export function buildProductionMemoryAcceptanceFeedbackCandidatePromotionView(workspace, fallback) {
  const artifact = workspace?.productionMemoryAcceptanceFeedbackCandidatePromotionDecision;
  if (!isAcceptanceFeedbackCandidatePromotionArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const decision = payload.decision || "unknown";
  const effect = payload.decision_effect || effectFromDecision(decision);
  const candidateId = payload.candidate_id || "unknown";
  const reuseAllowed = payload.candidate_reuse_allowed === true;
  const ready = boundaryOk(payload) && decision !== "pending";
  const source = sourceInfo(payload);

  return {
    ...fallback,
    state: ready ? "acceptance candidate promotion decided" : "blocked",
    project: {
      title: candidateId,
      brief: `Acceptance feedback candidate decision: ${decision}`,
      format: DECISION_TYPE,
      route: "selected local JSON only; read-only acceptance feedback candidate decision",
    },
    workflow_actions: [
      action("inspect_acceptance_candidate_decision", "Inspect decision", ready ? "review ready" : "blocked", "project"),
      action("inspect_candidate_reuse", "Inspect reuse", reuseAllowed ? "review ready" : "blocked", "memory-loaded"),
      action("inspect_decision_effect", "Inspect effect", effectStatus(effect), "review"),
      action("inspect_non_claims", "Inspect boundaries", "blocked", "next-pass"),
    ],
    assets: [
      {
        id: candidateId,
        label: payload.source_packet_id || "acceptance feedback candidate packet",
        detail: `decision=${decision}; effect=${effect}`,
        status: effectStatus(effect),
      },
    ],
    bundle_summary: [
      card("explicit_decision", "Explicit decision", ready ? "review ready" : "blocked", decision),
      card("decision_effect", "Decision effect", effectStatus(effect), effect),
      card("candidate_reuse", "Candidate reuse", reuseAllowed ? "review ready" : "blocked", reuseAllowed ? "allowed" : "blocked"),
      card("source_artifact", "Source artifact", source.status, source.type),
      card("source_acceptance", "Source acceptance", payload.source_human_acceptance_recorded ? "review ready" : "blocked", payload.source_acceptance_decision || "unknown"),
      card("claim_boundaries", "Non-claim boundaries", "blocked", "not durable memory / not Company KB promotion"),
    ],
    memory_loaded: [
      {
        id: candidateId,
        title: payload.source_packet_id || "acceptance feedback candidate",
        why_eligible: "explicit acceptance feedback promotion decision controls reuse",
        source_evidence_refs: evidenceRefs(payload, source),
        promotion_status: decision,
        request_projection: payload.rationale || effect,
        feedback_effect: "candidate can inform later context only through this explicit decision",
        status: effectStatus(effect),
      },
    ],
    lanes: [
      lane("acceptance-candidate-promotion", "Acceptance candidate promotion", ready ? "ready" : "blocked", candidateId, decision),
      lane("decision-effect", "Decision effect", effectStatus(effect), decision, effect),
      lane(source.id, source.title, source.status, source.path, source.detail),
      lane("source-acceptance", "Source acceptance", payload.source_human_acceptance_recorded ? "review ready" : "blocked", payload.source_acceptance_decision || "unknown", payload.source_acceptance_feedback_event_id || "feedback"),
      lane("non-claims", "Non-claims", "blocked", "no durable memory", "no Company KB promotion"),
    ],
    protocol_summary: {
      title: "Production memory acceptance feedback candidate promotion",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("provider calls not started", payload.provider_calls_started === false),
        control("long term memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("explicit operator decision", decision !== "pending"),
        control("candidate not durable memory", payload.candidate_is_durable_memory === false),
        control("business validation not claimed", objectValue(payload.claim_boundaries).business_validation === "not_validated", "blocked"),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `decision=${decision}`,
      visual_consistency: `source_acceptance=${payload.source_acceptance_decision || "unknown"}`,
      boundary: "explicit decision only / no durable memory write / no Company KB write",
    },
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: payload.rationale || "acceptance feedback candidate promotion decision recorded",
    },
    next_pass: {
      status: reuseAllowed ? "ready" : "blocked",
      action: reuseAllowed
        ? "build_next_context_overlay_from_acceptance_feedback_decision"
        : "keep_acceptance_feedback_candidate_blocked",
    },
    timeline: [
      step("Candidate", payload.source_candidate_status || "unknown", candidateId),
      step(source.title, source.status, source.detail),
      step("Decision", ready ? "ready" : "blocked", decision),
      step("Effect", effectStatus(effect), effect),
      step("Boundaries", "blocked", "not business validation / not durable memory"),
    ],
  };
}

function sourceInfo(payload) {
  const type = payload.source_artifact_type || payload.source_target_artifact_type || "agentflow_production_memory_operator_run_package";
  const isActionResult = type === "agentflow_production_memory_next_operator_action_result";
  return {
    id: isActionResult ? "source-action-result" : "source-package",
    title: isActionResult ? "Source action result" : "Source package",
    type,
    status: payload.source_artifact_status ? "review ready" : "blocked",
    detail: payload.source_artifact_status || payload.source_target_status || "unknown",
    path: payload.source_artifact_path || payload.source_target_ref || "unknown",
  };
}

function evidenceRefs(payload, source) {
  return [
    source.path,
    payload.source_acceptance_feedback_event_id,
    payload.source_promotion_decision_template_id,
  ].filter((item) => item && item !== "unknown");
}

function boundaryItems(payload) {
  const items = arrayValue(payload.non_claims);
  const labels = items.length ? items : ["not durable memory", "not Company KB promotion", "not provider success"];
  return labels.map((item) => ({ label: item, status: "blocked", detail: "non-claim boundary" }));
}

function boundaryOk(payload) {
  return payload.provider_calls_started === false && payload.writes_long_term_memory === false && payload.writes_company_kb === false;
}

function effectFromDecision(decision) {
  return ["promoted", "merged"].includes(decision) ? "eligible_for_next_context_overlay" : "blocked_by_explicit_operator_decision";
}

function effectStatus(effect) {
  return effect === "eligible_for_next_context_overlay" ? "review ready" : "blocked";
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
  return {
    label,
    status: forcedStatus || (passed ? "review ready" : "blocked"),
    detail: passed ? "confirmed by promotion decision" : "requires operator attention",
  };
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isAcceptanceFeedbackCandidatePromotionArtifact(artifact) {
  return artifact?.artifactType === DECISION_TYPE && artifact?.payload?.kind === DECISION_TYPE;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
