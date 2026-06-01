const DECISION_TYPE = "agentflow_production_memory_next_pass_promotion_decision";
const OVERLAY_TYPE = "agentflow_production_memory_next_pass_promotion_overlay";

export function buildProductionMemoryNextPassPromotionView(workspace, fallback) {
  const decisionArtifact = workspace?.productionMemoryNextPassPromotionDecision;
  const overlayArtifact = workspace?.productionMemoryNextPassPromotionOverlay;
  if (!isDecisionArtifact(decisionArtifact) && !isOverlayArtifact(overlayArtifact)) return fallback;

  const decision = objectValue(decisionArtifact?.payload);
  const overlay = objectValue(overlayArtifact?.payload);
  const candidateId = overlay.candidate_id || decision.candidate_id || "unknown";
  const decisionValue = overlay.decision || decision.decision || "unknown";
  const effect = overlay.decision_effect || effectFromDecision(decisionValue);
  const ready = boundaryOk(decision) && boundaryOk(overlay) && decisionValue !== "pending";
  const artifactType = overlayArtifact ? OVERLAY_TYPE : DECISION_TYPE;

  return {
    ...fallback,
    state: ready ? "next pass promotion ready" : "blocked",
    project: {
      title: candidateId,
      brief: `Next pass promotion decision: ${decisionValue}`,
      format: artifactType,
      route: "selected local JSON only; read-only no-provider promotion overlay",
    },
    workflow_actions: [
      action("inspect_next_pass_promotion", "Inspect decision", ready ? "review ready" : "blocked", "project"),
      action("inspect_decision_effect", "Inspect effect", effectStatus(effect), "review"),
      action("inspect_followup_context", "Inspect follow-up", effectStatus(effect), "next-pass"),
      action("inspect_boundaries", "Inspect boundaries", ready ? "review ready" : "blocked", "memory-loaded"),
    ],
    assets: [
      {
        id: candidateId,
        label: candidateId,
        detail: `decision=${decisionValue}; effect=${effect}`,
        status: effectStatus(effect),
      },
    ],
    bundle_summary: [
      card("explicit_decision", "Explicit decision", ready ? "review ready" : "blocked", decisionValue),
      card("decision_effect", "Decision effect", effectStatus(effect), effect),
      card("context_bundle", "Context bundle", overlay.context_bundle_id ? "review ready" : "missing", overlay.context_bundle_id || "not selected"),
      card("claim_boundaries", "Non-claim boundaries", "blocked", "not durable memory / not Company KB promotion"),
    ],
    memory_loaded: [
      {
        id: candidateId,
        title: candidateId,
        why_eligible: "explicit next-pass promotion decision controls reuse",
        source_evidence_refs: arrayValue(decision.source_feedback_ids),
        promotion_status: decisionValue,
        request_projection: effect,
        feedback_effect: "candidate feedback remains source evidence unless explicitly included in context",
        status: effectStatus(effect),
      },
    ],
    lanes: [
      lane("next-pass-promotion", "Next pass promotion", ready ? "ready" : "blocked", candidateId, decisionValue),
      lane("decision-effect", "Decision effect", effectStatus(effect), decisionValue, effect),
      lane("follow-up-context", "Follow-up context", effectStatus(effect), overlay.context_bundle_id || "context bundle", effect),
      lane("non-claims", "Non-claims", "blocked", "no durable memory", "no Company KB promotion"),
    ],
    protocol_summary: {
      title: "Production memory next pass promotion",
      status: ready ? "review ready" : "blocked",
      controls: controlsFor(decision, overlay, decisionValue, effect),
      boundaries: boundaryItems(decision, overlay),
    },
    review: {
      storyboard_adherence: `decision=${decisionValue}`,
      visual_consistency: `effect=${effect}`,
      boundary: "next-pass promotion overlay only / no provider call / no Company KB write",
    },
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: "Explicit operator decision controls whether next-pass feedback can be reused.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: effect === "included_in_context"
        ? "build_followup_context_from_explicit_decision"
        : "keep_next_pass_candidate_blocked",
    },
    timeline: [
      step("Decision", ready ? "ready" : "blocked", decisionValue),
      step("Effect", effectStatus(effect), effect),
      step("Context bundle", overlay.context_bundle_id ? "review ready" : "missing", overlay.context_bundle_id),
      step("Boundaries", "blocked", "not durable memory / not Company KB promotion"),
    ],
  };
}

function controlsFor(decision, overlay, decisionValue, effect) {
  return [
    control("provider calls not started", decision.provider_calls_started === false && overlay.provider_calls_started === false),
    control("long term memory write disabled", decision.writes_long_term_memory === false && overlay.writes_long_term_memory === false),
    control("Company KB write disabled", decision.writes_company_kb === false && overlay.writes_company_kb === false),
    control("explicit operator decision", decisionValue !== "pending"),
    control("decision effect recorded", Boolean(effect)),
  ];
}

function boundaryItems(decision, overlay) {
  const claims = [...arrayValue(decision.non_claims), ...arrayValue(overlay.non_claims)];
  const items = claims.length ? claims : ["not durable memory", "not Company KB promotion", "not provider success"];
  return items.map((item) => ({ label: item, status: "blocked", detail: "non-claim boundary" }));
}

function boundaryOk(payload) {
  if (!Object.keys(payload).length) return true;
  return payload.provider_calls_started === false && payload.writes_long_term_memory === false && payload.writes_company_kb === false;
}

function effectFromDecision(decision) {
  return ["promoted", "merged"].includes(decision) ? "included_in_context" : "blocked_from_context";
}

function effectStatus(effect) {
  return effect === "included_in_context" ? "review ready" : "blocked";
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

function control(label, passed) {
  return {
    label,
    status: passed ? "review ready" : "blocked",
    detail: passed ? "confirmed by promotion artifact" : "requires operator attention",
  };
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isDecisionArtifact(artifact) {
  return artifact?.artifactType === DECISION_TYPE && artifact?.payload?.kind === DECISION_TYPE;
}

function isOverlayArtifact(artifact) {
  return artifact?.artifactType === OVERLAY_TYPE && artifact?.payload?.kind === OVERLAY_TYPE;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
