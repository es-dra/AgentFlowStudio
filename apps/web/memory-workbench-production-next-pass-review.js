const NEXT_PASS_REVIEW_TYPE = "agentflow_production_memory_next_pass_review";

export function buildProductionMemoryNextPassReviewView(workspace, fallback) {
  const artifact = workspace?.productionMemoryNextPassReview;
  if (!isNextPassReviewArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const used = arrayValue(payload.used_allowed_refs);
  const blocked = arrayValue(payload.blocked_or_unknown_refs);
  const candidates = arrayValue(payload.feedback_candidates);
  const templates = arrayValue(payload.promotion_decision_templates);
  const nonClaims = arrayValue(payload.non_claims);
  const ready = payload.review_status === "ready_for_operator_review" && payload.provider_calls_started === false && blocked.length === 0;
  return {
    ...fallback,
    state: ready ? "next pass review ready" : "blocked",
    project: {
      title: payload.source_task_packet_id || payload.review_id || artifact.fileName,
      brief: `Next pass review: ${payload.review_status || "unknown"}`,
      format: NEXT_PASS_REVIEW_TYPE,
      route: "selected local JSON only; read-only no-provider next-pass review",
    },
    workflow_actions: [
      action("inspect_next_pass_review", "Inspect review", "review ready", "project"),
      action("inspect_used_refs", "Inspect used refs", used.length ? "ready" : "missing", "memory-loaded"),
      action("inspect_ref_blockers", "Inspect blockers", blocked.length ? "blocked" : "review ready", "review"),
      action("inspect_feedback_candidates", "Inspect candidates", candidates.length ? "review ready" : "missing", "feedback"),
      action("review_candidate_feedback", "Review promotion", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      ...used.map((item) => ({
        id: item.ref_id,
        label: item.ref_id,
        detail: item.summary || `usage_count=${item.usage_count || 0}`,
        status: "review ready",
      })),
      ...blocked.map((item) => ({
        id: item.ref_id,
        label: item.ref_id,
        detail: item.reason || "blocked or unknown context ref",
        status: "blocked",
      })),
      ...candidates.map((item) => ({
        id: item.candidate_id,
        label: item.candidate_id,
        detail: item.summary || item.decision || "candidate feedback",
        status: "candidate only",
      })),
    ],
    bundle_summary: [
      card("used_allowed_refs", "Used allowed refs", used.length ? "review ready" : "missing", `${used.length} allowed refs used by result outputs`),
      card("blocked_or_unknown_refs", "Blocked or unknown refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs require operator attention`),
      card("feedback_candidates", "Feedback candidates", candidates.length ? "review ready" : "missing", `${candidates.length} candidate-only feedback items`),
      card("promotion_templates", "Pending promotion templates", templates.length ? "planned" : "missing", `${templates.length} explicit decisions required`),
    ],
    memory_loaded: candidates.map((item) => ({
      id: item.candidate_id,
      title: item.target_ref || item.candidate_id,
      why_eligible: "candidate feedback only; explicit promotion decision required",
      source_evidence_refs: item.source_feedback_id ? [item.source_feedback_id] : [],
      promotion_status: "pending explicit decision",
      request_projection: item.summary || "candidate requires operator review before reuse",
      feedback_effect: "candidate-only next-pass feedback; no durable memory or Company KB write",
      status: "candidate only",
    })),
    lanes: [
      lane("next-pass-review", "Next pass review", ready ? "ready" : "blocked", payload.source_task_packet_id || "task packet", payload.review_status || "unknown"),
      lane("used-allowed-refs", "Used allowed refs", used.length ? "review ready" : "missing", `${used.length} refs`, "allowed context used"),
      lane("blocked-or-unknown-refs", "Blocked or unknown refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`, "excluded from reuse"),
      lane("candidate-feedback", "Candidate feedback", candidates.length ? "review ready" : "missing", `${candidates.length} candidates`, "pending promotion decisions"),
    ],
    protocol_summary: {
      title: "Production memory next pass review",
      status: ready ? "review ready" : "blocked",
      controls: arrayValue(payload.controls).map(controlFromPayload),
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `${used.length} allowed refs used`,
      visual_consistency: `${blocked.length} blocked or unknown refs`,
      boundary: "next-pass review only / no provider call / no Company KB write",
    },
    feedback: {
      status: candidates.length ? "review ready" : "missing",
      summary: "Candidate feedback requires explicit promotion decision before any reuse.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "review_candidate_feedback_for_explicit_promotion" : "resolve_next_pass_review_blockers",
    },
    timeline: [
      step("Review", ready ? "ready" : "blocked", payload.review_id),
      step("Used allowed refs", used.length ? "review ready" : "missing", `${used.length} refs`),
      step("Blocked or unknown refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`),
      step("Feedback candidates", candidates.length ? "review ready" : "missing", `${candidates.length} candidates`),
    ],
  };
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

function controlFromPayload(control) {
  const controlId = String(control?.control_id || "unknown_control");
  const passed = control?.status === "passed";
  return {
    label: controlLabel(controlId),
    status: passed ? "review ready" : "blocked",
    detail: passed ? "confirmed by review artifact" : "requires operator attention",
  };
}

function controlLabel(controlId) {
  if (controlId === "company_kb_write_disabled") return "Company KB write disabled";
  return controlId.replaceAll("_", " ");
}

function boundaryItems(payload) {
  return arrayValue(payload.non_claims).map((item) => ({
    label: item,
    status: "blocked",
    detail: "non-claim boundary",
  }));
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isNextPassReviewArtifact(artifact) {
  return artifact?.artifactType === NEXT_PASS_REVIEW_TYPE && artifact?.payload?.kind === NEXT_PASS_REVIEW_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
