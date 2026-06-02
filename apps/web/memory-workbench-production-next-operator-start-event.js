const NEXT_OPERATOR_START_EVENT_TYPE = "agentflow_production_memory_next_operator_start_event";

export function buildProductionMemoryNextOperatorStartEventView(workspace, fallback) {
  const artifact = workspace?.productionMemoryNextOperatorStartEvent;
  if (!isNextOperatorStartEventArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const boundaries = objectValue(payload.claim_boundaries);
  const nonClaims = arrayValue(payload.non_claims);
  const controls = arrayValue(payload.controls);
  const started = payload.event_status === "operator_started" && payload.start_decision === "started";
  const ready = baseControlsReady(payload);

  return {
    ...fallback,
    state: ready ? "next operator start event recorded" : "blocked",
    project: {
      title: payload.start_event_id || artifact.fileName,
      brief: `Next operator start event: ${payload.event_status || "unknown"}`,
      format: NEXT_OPERATOR_START_EVENT_TYPE,
      route: "selected local JSON only; read-only next-operator start event",
    },
    workflow_actions: [
      action("inspect_start_event", "Inspect start", ready ? "review ready" : "blocked", "project"),
      action("inspect_source_start_packet", "Inspect packet", payload.source_start_packet_id ? "review ready" : "missing", "assets"),
      action("inspect_start_event_boundaries", "Inspect boundaries", "blocked", "review"),
      action("continue_next_operator", "Continue next", started ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      {
        id: payload.source_start_packet_id || "source_start_packet",
        label: "source start packet",
        detail: payload.source_start_packet_path || "not recorded",
        status: payload.source_ready_for_next_operator === true ? "review ready" : "blocked",
      },
      ...arrayValue(payload.source_blocked_items).map((item) => ({
        id: item.ref || item.path || "blocked_item",
        label: item.ref || item.path || "blocked item",
        detail: item.reason || "blocked",
        status: "blocked",
      })),
    ],
    bundle_summary: [
      card("start_event", "Start event", ready ? "review ready" : "blocked", payload.event_status || "unknown"),
      card("source_start_packet", "Source start packet", payload.source_ready_for_next_operator === true ? "review ready" : "blocked", payload.source_start_packet_status || "unknown"),
      card("acceptance_boundary", "Acceptance boundary", "blocked", boundaries.human_acceptance || "not_claimed"),
      card("execution_boundary", "Execution boundary", "blocked", boundaries.next_pass_execution || "not_claimed"),
      card("memory_boundary", "Memory boundary", payload.start_event_is_memory === false ? "review ready" : "blocked", "start event is not memory"),
    ],
    memory_loaded: [
      {
        id: "next_operator_start_event",
        title: "Next operator start event",
        why_eligible: "start receipt evidence only; it does not create memory or promotion decisions",
        source_evidence_refs: [payload.source_start_packet_id || "next_operator_start_packet"],
        promotion_status: "not_promoted",
        request_projection: payload.summary || "start event recorded",
        feedback_effect: "does not claim human acceptance, execution success, or memory promotion",
        status: ready ? "review ready" : "blocked",
      },
    ],
    lanes: [
      lane("start-event", "Start event", ready ? "ready" : "blocked", payload.start_decision || "unknown", payload.event_status || "unknown"),
      lane("source-start-packet", "Source start packet", payload.source_ready_for_next_operator === true ? "review ready" : "blocked", payload.source_start_packet_status || "unknown", payload.source_start_packet_id || "unknown"),
      lane("boundaries", "Boundaries", "blocked", `${nonClaims.length} non-claims`, "no acceptance or execution claim"),
      lane("next-operator", "Next operator", started ? "ready" : "blocked", payload.operator_role || "unknown", payload.source_next_operator_action || "unknown"),
    ],
    protocol_summary: {
      title: "Production memory next operator start event",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("source start packet ready for started decision", controlPassed(controls, "source_start_packet_ready_for_started_decision")),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("start event not acceptance", payload.start_event_is_acceptance === false),
        control("start event not execution", payload.start_event_is_execution === false),
        control("start event not memory", payload.start_event_is_memory === false),
      ],
      boundaries: boundaryItems(boundaries, nonClaims),
    },
    review: {
      storyboard_adherence: `start_decision=${payload.start_decision || "unknown"}`,
      visual_consistency: `source_packet=${payload.source_start_packet_status || "unknown"}`,
      boundary: "next-operator start event only / no provider call / no Company KB write",
    },
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: payload.summary || "start event recorded without acceptance or memory promotion",
    },
    next_pass: {
      status: started ? "ready" : "blocked",
      action: started ? payload.source_next_operator_action || "continue_next_operator_action" : "resolve_next_operator_start_event_blockers",
    },
    timeline: [
      step("Source start packet", payload.source_start_packet_status || "unknown", payload.source_start_packet_id),
      step("Start event", payload.event_status || "unknown", payload.start_decision),
      step("Boundaries", "blocked", "not acceptance / not execution / not memory"),
      step("Next operator", started ? "ready" : "blocked", payload.source_next_operator_action),
    ],
  };
}

function baseControlsReady(payload) {
  return payload.provider_calls_started === false
    && payload.writes_long_term_memory === false
    && payload.writes_company_kb === false
    && payload.start_event_is_acceptance === false
    && payload.start_event_is_execution === false
    && payload.start_event_is_memory === false;
}

function boundaryItems(boundaries, nonClaims) {
  const claims = nonClaims.length ? nonClaims : ["not human acceptance", "not next-pass execution result", "not durable memory"];
  return claims.map((item) => ({
    label: item,
    status: "blocked",
    detail: boundaries.human_acceptance || boundaries.next_pass_execution || "non-claim boundary",
  }));
}

function control(label, passed) {
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by start event" : "not confirmed" };
}

function controlPassed(controls, id) {
  return controls.some((item) => item?.control_id === id && item?.status === "passed");
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

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isNextOperatorStartEventArtifact(artifact) {
  return artifact?.artifactType === NEXT_OPERATOR_START_EVENT_TYPE && artifact?.payload?.kind === NEXT_OPERATOR_START_EVENT_TYPE;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
