const SESSION_REPORT_TYPE = "agentflow_production_memory_session_report";

export function buildProductionMemorySessionReportView(workspace, fallback) {
  const artifact = workspace?.productionMemorySessionReport;
  if (!isSessionReportArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const summary = payload.context_summary || {};
  const included = arrayValue(summary.included_refs);
  const blocked = arrayValue(summary.blocked_refs);
  const action = payload.next_operator_action || {};
  const ready = payload.session_status === "ready" && payload.provider_calls_started === false;
  return {
    ...fallback,
    state: ready ? "pass ready" : "blocked",
    project: {
      title: payload.project_id || payload.session_id || artifact.fileName,
      brief: `Operator session report: ${payload.session_status || "unknown"}`,
      format: SESSION_REPORT_TYPE,
      route: "selected local JSON only; read-only no-provider session report",
    },
    workflow_actions: [
      stepAction("inspect_session", "Inspect session", "review ready", "review"),
      stepAction("inspect_included", "Inspect included refs", included.length ? "ready" : "missing", "memory-loaded"),
      stepAction("inspect_blocked", "Inspect blocked refs", blocked.length ? "blocked" : "review ready", "assets"),
      stepAction("prepare_next_pass", "Prepare next pass", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [...included, ...blocked].map((item) => ({
      id: item.ref_id,
      label: item.ref_id,
      detail: item.summary || item.reason || item.source_record_type || "session ref",
      status: item.reason ? "blocked" : item.status || "review ready",
    })),
    bundle_summary: [
      summaryCard("included_refs", "Included refs", included.length ? "review ready" : "missing", `${included.length} refs in next context`),
      summaryCard("blocked_refs", "Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs excluded from next context`),
      summaryCard("next_operator_action", "Next operator action", ready ? "ready" : "blocked", action.action || "unknown"),
    ],
    memory_loaded: included.map((item) => ({
      id: item.ref_id,
      title: item.title || item.ref_id,
      why_eligible: item.promotion_decision ? `explicit decision ${item.decision_id}` : "included in session report",
      source_evidence_refs: item.source_feedback_ids || [item.status || "included"],
      promotion_status: item.promotion_decision || item.status || "included",
      request_projection: item.summary || "eligible for next context bundle",
      feedback_effect: "listed in session next_context_refs only; no durable memory write",
      status: item.promotion_decision ? "promotion decision ready" : "review ready",
    })),
    lanes: [
      lane("session-report", "Session report", ready ? "ready" : "blocked", payload.session_status || "unknown", action.action || "unknown"),
      lane("included-refs", "Included refs", included.length ? "review ready" : "missing", `${included.length} refs`, "eligible for next context"),
      lane("blocked-refs", "Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`, "excluded from next context"),
    ],
    protocol_summary: {
      title: "Production memory session report",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable write disabled", payload.writes_long_term_memory === false),
        control("human acceptance separate", payload.claim_boundaries?.human_acceptance === "not_reviewed"),
      ],
      boundaries: boundaryItems(payload.claim_boundaries),
    },
    review: {
      storyboard_adherence: `${included.length} included refs`,
      visual_consistency: `${blocked.length} blocked refs`,
      boundary: "operator report only / no provider call / no human acceptance claim",
    },
    feedback: feedbackSummary(payload.feedback_capture, payload.promotion_decision),
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: action.action || "unknown",
    },
    timeline: [
      timelineStep("Session", ready ? "ready" : "blocked", payload.session_id),
      timelineStep("Included refs", included.length ? "review ready" : "missing", `${included.length} refs`),
      timelineStep("Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`),
      timelineStep("Next action", ready ? "ready" : "blocked", action.reason || action.action),
    ],
  };
}

function feedbackSummary(feedback, promotion) {
  return {
    status: promotion?.decision || feedback?.status || "not_provided",
    summary: `feedback ${feedback?.status || "not provided"} / promotion ${promotion?.decision || "not provided"}`,
  };
}

function summaryCard(id, title, status, detail) {
  return { id, title, status, detail };
}

function lane(id, title, status, input, output) {
  return { id, title, status, input, output };
}

function stepAction(id, label, status, focusTarget) {
  return { id, label, status, focusTarget, focus_target: focusTarget };
}

function control(label, passed) {
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by session report" : "not confirmed" };
}

function boundaryItems(boundaries = {}) {
  return [
    { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_reviewed" },
    { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
    { label: "durable memory runtime", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    { label: "provider success", status: "blocked", detail: boundaries.provider_success || "not_attempted" },
  ];
}

function timelineStep(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isSessionReportArtifact(artifact) {
  return artifact?.artifactType === SESSION_REPORT_TYPE && artifact?.payload?.kind === SESSION_REPORT_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
