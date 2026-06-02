const ACCEPTANCE_FEEDBACK_TYPE = "agentflow_production_memory_acceptance_feedback_event";

export function buildProductionMemoryAcceptanceFeedbackView(workspace, fallback) {
  const artifact = workspace?.productionMemoryAcceptanceFeedbackEvent;
  if (!isAcceptanceFeedbackArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const boundaries = payload.claim_boundaries || {};
  const source = sourceInfo(payload);
  const ready = payload.status === "human_recorded"
    && payload.provider_calls_started === false
    && payload.writes_long_term_memory === false
    && payload.writes_company_kb === false
    && payload.business_validation === "not_validated";
  const reusableForNextPass = ready && source.ready;

  return {
    ...fallback,
    state: ready ? "acceptance feedback recorded" : "blocked",
    project: {
      title: payload.feedback_id || artifact.fileName,
      brief: `Acceptance feedback: ${payload.acceptance_decision || "unknown"}`,
      format: ACCEPTANCE_FEEDBACK_TYPE,
      route: "selected local JSON only; read-only human acceptance feedback event",
    },
    workflow_actions: [
      action("inspect_acceptance_feedback", "Inspect feedback", ready ? "review ready" : "blocked", "feedback"),
      action("inspect_source_artifact", `Inspect ${source.shortLabel}`, source.status !== "unknown" ? "review ready" : "missing", "review"),
      action("inspect_boundaries", "Inspect boundaries", "blocked", "memory-loaded"),
      action("start_business_validation", "Business validation", "blocked", "next-pass"),
    ],
    assets: [
      {
        id: payload.feedback_id || artifact.fileName,
        label: "acceptance feedback event",
        detail: source.path,
        status: ready ? "review ready" : "blocked",
      },
    ],
    bundle_summary: [
      card("acceptance_decision", "Acceptance decision", ready ? "review ready" : "blocked", payload.acceptance_decision || "unknown"),
      card("source_artifact", source.title, source.ready ? "review ready" : "blocked", source.status),
      card("ready_for_source_use", source.readyTitle, source.ready ? "review ready" : "blocked", boolText(source.ready)),
      card("business_validation", "Business validation", "blocked", payload.business_validation || "not_validated"),
      card("memory_boundary", "Memory boundary", payload.feedback_is_memory === false ? "review ready" : "blocked", "feedback is not memory"),
    ],
    memory_loaded: [
      {
        id: payload.feedback_id || "acceptance-feedback",
        title: payload.acceptance_scope || "operator run package",
        why_eligible: "human-supplied acceptance feedback is selected evidence only",
        source_evidence_refs: [source.path],
        promotion_status: "not_promoted",
        request_projection: payload.summary || "not recorded",
        feedback_effect: "records human acceptance decision without business validation or memory promotion",
        status: payload.status || "unknown",
      },
    ],
    lanes: [
      lane("acceptance-feedback", "Acceptance feedback", ready ? "review ready" : "blocked", source.status, payload.acceptance_decision || "unknown"),
      lane(source.id, source.title, source.ready ? "ready" : "blocked", source.path, source.status),
      lane("business-boundary", "Business boundary", "blocked", "human feedback", payload.business_validation || "not_validated"),
      lane("memory-boundary", "Memory boundary", payload.feedback_is_memory === false ? "review ready" : "blocked", "feedback", "not memory"),
    ],
    protocol_summary: {
      title: "Production memory acceptance feedback",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("human acceptance recorded", payload.human_acceptance_recorded === true),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("feedback is not memory", payload.feedback_is_memory === false),
        control("business validation not claimed", payload.business_validation === "not_validated", "blocked"),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `${source.factLabel}=${source.status}`,
      visual_consistency: `decision=${payload.acceptance_decision || "unknown"}`,
      boundary: "human acceptance feedback only / no business validation / no memory promotion",
    },
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: payload.summary || "acceptance feedback recorded without promotion side effects",
    },
    next_pass: {
      status: payload.acceptance_decision === "accepted" && reusableForNextPass ? "ready" : "blocked",
      action: nextPassAction(payload, source, reusableForNextPass),
    },
    timeline: [
      step(source.title, source.status, source.path),
      step("Human feedback", payload.status || "unknown", payload.acceptance_decision),
      step("Business validation", "blocked", payload.business_validation || "not_validated"),
      step("Memory promotion", "blocked", boundaries.memory_promotion || "not_performed"),
    ],
  };
}

function sourceInfo(payload) {
  if (isActionResultSource(payload)) {
    const status = payload.source_artifact_status || payload.source_action_result_status || "unknown";
    return {
      id: "source-action-result",
      title: "Source action result",
      shortLabel: "source action result",
      readyTitle: "Ready for acceptance",
      factLabel: "source_action_result",
      status,
      ready: payload.source_ready_for_acceptance === true,
      path: payload.source_artifact_path || "next operator action result not recorded",
    };
  }
  return {
    id: "source-package-check",
    title: "Source package check",
    shortLabel: "source package check",
    readyTitle: "Ready for handoff",
    factLabel: "source_check",
    status: payload.source_check_status || payload.source_artifact_status || "unknown",
    ready: payload.source_ready_for_handoff === true,
    path: payload.source_package_path || payload.source_artifact_path || "operator run package check not recorded",
  };
}

function isActionResultSource(payload) {
  return payload.feedback_scope === "next_operator_action_result"
    || payload.source_artifact_type === "agentflow_production_memory_next_operator_action_result";
}

function nextPassAction(payload, source, ready) {
  if (payload.acceptance_decision !== "accepted" || !ready) {
    return "resolve_acceptance_feedback_blockers";
  }
  if (source.id === "source-action-result") {
    return "draft_acceptance_feedback_candidate_from_action_result";
  }
  return "continue_operator_iteration";
}

function boundaryItems(payload) {
  const boundaries = payload.claim_boundaries || {};
  return [
    { label: "human acceptance", status: "review ready", detail: boundaries.human_acceptance || "unknown" },
    { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
    { label: "provider success", status: "blocked", detail: boundaries.provider_success || "not_claimed" },
    { label: "durable memory", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    { label: "Company KB promotion", status: "blocked", detail: boundaries.company_kb_promotion || "not_performed" },
    { label: "memory promotion", status: "blocked", detail: boundaries.memory_promotion || "not_performed" },
  ];
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

function boolText(value) {
  return value === true ? "true" : "false";
}

function isAcceptanceFeedbackArtifact(artifact) {
  return artifact?.artifactType === ACCEPTANCE_FEEDBACK_TYPE && artifact?.payload?.kind === ACCEPTANCE_FEEDBACK_TYPE;
}
