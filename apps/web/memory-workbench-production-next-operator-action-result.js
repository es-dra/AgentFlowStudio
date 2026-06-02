const NEXT_OPERATOR_ACTION_RESULT_TYPE = "agentflow_production_memory_next_operator_action_result";

export function buildProductionMemoryNextOperatorActionResultView(workspace, fallback) {
  const artifact = workspace?.productionMemoryNextOperatorActionResult;
  if (!isNextOperatorActionResultArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const boundaries = objectValue(payload.claim_boundaries);
  const nonClaims = arrayValue(payload.non_claims);
  const controls = arrayValue(payload.controls);
  const completed = payload.result_status === "action_completed" && payload.action_decision === "completed";
  const ready = baseControlsReady(payload);
  const resultRefs = arrayValue(payload.result_refs);

  return {
    ...fallback,
    state: ready ? "next operator action result recorded" : "blocked",
    project: {
      title: payload.action_result_id || artifact.fileName,
      brief: `Next operator action result: ${payload.result_status || "unknown"}`,
      format: NEXT_OPERATOR_ACTION_RESULT_TYPE,
      route: "selected local JSON only; read-only next-operator action result",
    },
    workflow_actions: [
      action("inspect_action_result", "Inspect result", ready ? "review ready" : "blocked", "project"),
      action("review_result_refs", "Review refs", resultRefs.length ? "ready" : "blocked", "assets"),
      action("inspect_action_result_boundaries", "Inspect boundaries", "blocked", "review"),
      action("prepare_followup_review", "Prepare review", completed ? "ready" : "blocked", "next-pass"),
    ],
    assets: resultRefs.map((ref) => ({
      id: ref,
      label: "result ref",
      detail: payload.source_next_operator_action || "recorded action",
      status: completed ? "review ready" : "blocked",
    })),
    bundle_summary: [
      card("action_result", "Action result", ready ? "review ready" : "blocked", payload.result_status || "unknown"),
      card("source_start_event", "Source start event", "review ready", payload.source_start_event_status || "unknown"),
      card("result_refs", "Result refs", resultRefs.length ? "review ready" : "blocked", `${resultRefs.length} refs`),
      card("execution_boundary", "Execution boundary", "blocked", boundaries.next_pass_execution || "not_claimed"),
      card("memory_boundary", "Memory boundary", payload.action_result_is_memory === false ? "review ready" : "blocked", "action result is not memory"),
    ],
    memory_loaded: [
      {
        id: "next_operator_action_result",
        title: "Next operator action result",
        why_eligible: "action outcome evidence only; it does not create memory or promotion decisions",
        source_evidence_refs: [payload.source_start_event_id || "next_operator_start_event"],
        promotion_status: "not_promoted",
        request_projection: payload.summary || "action result recorded",
        feedback_effect: "does not claim human acceptance, execution success, or memory promotion",
        status: ready ? "review ready" : "blocked",
      },
    ],
    lanes: [
      lane("action-result", "Action result", ready ? "ready" : "blocked", payload.action_decision || "unknown", payload.result_status || "unknown"),
      lane("source-start-event", "Source start event", "review ready", payload.source_start_event_status || "unknown", payload.source_start_event_id || "unknown"),
      lane("result-refs", "Result refs", resultRefs.length ? "review ready" : "blocked", `${resultRefs.length} refs`, payload.source_next_operator_action || "unknown"),
      lane("boundaries", "Boundaries", "blocked", `${nonClaims.length} non-claims`, "no acceptance or execution claim"),
    ],
    protocol_summary: {
      title: "Production memory next operator action result",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("source start event recorded", controlPassed(controls, "source_start_event_recorded")),
        control("completed action has result refs", controlPassed(controls, "completed_requires_result_refs")),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("action result not acceptance", payload.action_result_is_acceptance === false),
        control("action result not execution", payload.action_result_is_execution === false),
        control("action result not memory", payload.action_result_is_memory === false),
      ],
      boundaries: boundaryItems(boundaries, nonClaims),
    },
    review: {
      storyboard_adherence: `action_decision=${payload.action_decision || "unknown"}`,
      visual_consistency: `source_start_event=${payload.source_start_event_status || "unknown"}`,
      boundary: "next-operator action result only / no provider call / no Company KB write",
    },
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: payload.summary || "action result recorded without acceptance or memory promotion",
    },
    next_pass: {
      status: completed ? "ready" : "blocked",
      action: completed ? "review_recorded_action_result_refs" : "resolve_next_operator_action_result_blockers",
    },
    timeline: [
      step("Source start event", payload.source_start_event_status || "unknown", payload.source_start_event_id),
      step("Action result", payload.result_status || "unknown", payload.action_decision),
      step("Result refs", resultRefs.length ? "review ready" : "blocked", `${resultRefs.length} refs`),
      step("Boundaries", "blocked", "not acceptance / not execution / not memory"),
    ],
  };
}

function baseControlsReady(payload) {
  return payload.provider_calls_started === false
    && payload.writes_long_term_memory === false
    && payload.writes_company_kb === false
    && payload.action_result_is_acceptance === false
    && payload.action_result_is_execution === false
    && payload.action_result_is_memory === false;
}

function boundaryItems(boundaries, nonClaims) {
  const claims = nonClaims.length ? nonClaims : ["not human acceptance", "not next-pass execution result"];
  return claims.map((item) => ({
    label: item,
    status: "blocked",
    detail: boundaries.human_acceptance || boundaries.next_pass_execution || "non-claim boundary",
  }));
}

function control(label, passed) {
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by action result" : "not confirmed" };
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

function isNextOperatorActionResultArtifact(artifact) {
  return artifact?.artifactType === NEXT_OPERATOR_ACTION_RESULT_TYPE
    && artifact?.payload?.kind === NEXT_OPERATOR_ACTION_RESULT_TYPE;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
