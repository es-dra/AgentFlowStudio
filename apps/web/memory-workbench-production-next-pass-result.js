const NEXT_PASS_RESULT_TYPE = "agentflow_production_memory_next_pass_result";

export function buildProductionMemoryNextPassResultView(workspace, fallback) {
  const artifact = workspace?.productionMemoryNextPassResult;
  if (!isNextPassResultArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const outputs = arrayValue(payload.output_artifacts);
  const usedRefs = uniqueUsedRefs(outputs);
  const feedbackEvents = arrayValue(payload.feedback_events);
  const nonClaims = arrayValue(payload.non_claims);
  const ready = payload.result_status === "scaffolded_for_operator_completion"
    && payload.provider_calls_started === false
    && outputs.length > 0;
  return {
    ...fallback,
    state: ready ? "next pass result scaffold ready" : "blocked",
    project: {
      title: payload.result_id || payload.task_packet_id || artifact.fileName,
      brief: `Next pass result: ${payload.result_status || "unknown"}`,
      format: NEXT_PASS_RESULT_TYPE,
      route: "selected local JSON only; read-only no-provider next-pass result scaffold",
    },
    workflow_actions: [
      action("inspect_next_pass_result", "Inspect result", "review ready", "project"),
      action("inspect_output_artifacts", "Inspect outputs", outputs.length ? "review ready" : "missing", "assets"),
      action("inspect_used_context_refs", "Inspect used refs", usedRefs.length ? "review ready" : "missing", "memory-loaded"),
      action("inspect_feedback_events", "Inspect feedback", feedbackEvents.length ? "review ready" : "missing", "feedback"),
      action("review_next_pass_result", "Review result", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: outputs.map((item) => ({
      id: item.ref_id || "next-pass:artifact:unknown",
      label: item.title || item.ref_id || "next-pass output",
      detail: item.summary || `${arrayValue(item.used_context_refs).length} used refs`,
      status: item.status || "scaffolded",
    })),
    bundle_summary: [
      card("output_artifacts", "Output artifacts", outputs.length ? "review ready" : "missing", `${outputs.length} scaffolded outputs`),
      card("used_context_refs", "Used context refs", usedRefs.length ? "review ready" : "missing", `${usedRefs.length} allowed refs used`),
      card("feedback_events", "Feedback events", feedbackEvents.length ? "review ready" : "missing", `${feedbackEvents.length} explicit feedback events`),
      card("non_claims", "Non-claims", nonClaims.length ? "blocked" : "review ready", `${nonClaims.length} boundaries retained`),
    ],
    memory_loaded: outputs.map((item) => ({
      id: item.ref_id || "next-pass:artifact:unknown",
      title: item.title || item.ref_id || "next-pass output",
      why_eligible: "scaffolded result output; review before feedback or promotion",
      source_evidence_refs: arrayValue(item.used_context_refs),
      promotion_status: "not memory",
      request_projection: item.summary || "operator-supplied result scaffold awaits review",
      feedback_effect: "no feedback auto-created; no durable memory or Company KB write",
      status: item.status || "scaffolded",
    })),
    lanes: [
      lane("next-pass-result", "Next pass result", ready ? "ready" : "blocked", payload.task_packet_id || "task packet", payload.result_status || "unknown"),
      lane("output-artifacts", "Output artifacts", outputs.length ? "review ready" : "missing", `${outputs.length} outputs`, "scaffolded result envelope"),
      lane("used-context-refs", "Used context refs", usedRefs.length ? "review ready" : "missing", `${usedRefs.length} refs`, "allowed refs only"),
      lane("feedback-events", "Feedback events", feedbackEvents.length ? "review ready" : "missing", `${feedbackEvents.length} events`, "explicit capture required"),
    ],
    protocol_summary: {
      title: "Production memory next pass result scaffold",
      status: ready ? "review ready" : "blocked",
      controls: arrayValue(payload.controls).map(controlFromPayload),
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `${outputs.length} scaffolded outputs`,
      visual_consistency: `${usedRefs.length} used context refs`,
      boundary: "next-pass result scaffold only / no provider call / no Company KB write",
    },
    feedback: {
      status: feedbackEvents.length ? "review ready" : "missing",
      summary: "Feedback is not auto-created; capture feedback explicitly after review.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "review_next_pass_result_against_task_packet" : "resolve_next_pass_result_blockers",
    },
    timeline: [
      step("Result scaffold", ready ? "ready" : "blocked", payload.result_id),
      step("Output artifacts", outputs.length ? "review ready" : "missing", `${outputs.length} outputs`),
      step("Used context refs", usedRefs.length ? "review ready" : "missing", `${usedRefs.length} refs`),
      step("Feedback events", feedbackEvents.length ? "review ready" : "missing", `${feedbackEvents.length} events`),
    ],
  };
}

function uniqueUsedRefs(outputs) {
  return [...new Set(outputs.flatMap((item) => arrayValue(item.used_context_refs).map(String)))];
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
    detail: passed ? "confirmed by result scaffold" : "requires operator attention",
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

function isNextPassResultArtifact(artifact) {
  return artifact?.artifactType === NEXT_PASS_RESULT_TYPE && artifact?.payload?.kind === NEXT_PASS_RESULT_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
