const NEXT_CONTEXT_HANDOFF_TYPE = "agentflow_production_memory_next_context_handoff";

export function buildProductionMemoryNextContextHandoffView(workspace, fallback) {
  const artifact = workspace?.productionMemoryNextContextHandoff;
  if (!isNextContextHandoffArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const included = arrayValue(payload.next_context_refs);
  const blocked = arrayValue(payload.blocked_refs);
  const nonClaims = arrayValue(payload.non_claims);
  const ready = payload.handoff_status === "ready" && payload.provider_calls_started === false;
  return {
    ...fallback,
    state: ready ? "next context ready" : "blocked",
    project: {
      title: payload.project_id || payload.handoff_id || artifact.fileName,
      brief: `Next context handoff: ${payload.handoff_status || "unknown"}`,
      format: NEXT_CONTEXT_HANDOFF_TYPE,
      route: "selected local JSON only; read-only no-provider next-context handoff",
    },
    workflow_actions: [
      action("inspect_handoff", "Inspect handoff", "review ready", "project"),
      action("inspect_next_context", "Inspect context", included.length ? "ready" : "missing", "memory-loaded"),
      action("inspect_blocked_refs", "Inspect blocked", blocked.length ? "blocked" : "review ready", "review"),
      action("prepare_next_ai_task", "Prepare next task", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [...included, ...blocked].map((item) => ({
      id: item.ref_id,
      label: item.ref_id,
      detail: item.summary || item.reason || item.status || "handoff ref",
      status: item.reason ? "blocked" : item.status || "review ready",
    })),
    bundle_summary: [
      card("next_context_refs", "Next context refs", included.length ? "review ready" : "missing", `${included.length} refs available for the next AI task`),
      card("blocked_refs", "Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs excluded from the next AI task`),
      card("non_claims", "Non-claims", nonClaims.length ? "blocked" : "review ready", `${nonClaims.length} boundaries retained`),
    ],
    memory_loaded: included.map((item) => ({
      id: item.ref_id,
      title: item.title || item.ref_id,
      why_eligible: item.promotion_decision ? `explicit decision ${item.decision_id}` : "included by context bundle",
      source_evidence_refs: item.source_feedback_ids || [item.status || "included"],
      promotion_status: item.promotion_decision || item.status || "included",
      request_projection: item.summary || "available for next AI task context",
      feedback_effect: "visible in next_context_refs only; no durable memory or Company KB write",
      status: item.promotion_decision ? "promotion decision ready" : "review ready",
    })),
    lanes: [
      lane("next-context-handoff", "Next context handoff", ready ? "ready" : "blocked", payload.task_id || "next task", payload.handoff_status || "unknown"),
      lane("included-refs", "Included refs", included.length ? "review ready" : "missing", `${included.length} refs`, "eligible for next AI task"),
      lane("blocked-refs", "Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`, "excluded from next AI task"),
    ],
    protocol_summary: {
      title: "Production memory next context handoff",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("blocked refs excluded", blockedRefsExcluded(included, blocked)),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `${included.length} next context refs`,
      visual_consistency: `${blocked.length} blocked refs`,
      boundary: "next task handoff only / no provider call / no Company KB write",
    },
    feedback: {
      status: "review ready",
      summary: "Use as task context handoff only; do not treat as acceptance or durable memory.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "use_handoff_for_next_ai_task" : "resolve_handoff_blockers",
    },
    timeline: [
      step("Handoff", ready ? "ready" : "blocked", payload.handoff_id),
      step("Included refs", included.length ? "review ready" : "missing", `${included.length} refs`),
      step("Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`),
      step("Next task", ready ? "ready" : "blocked", payload.task_id),
    ],
  };
}

function blockedRefsExcluded(included, blocked) {
  const includedIds = new Set(included.map((item) => String(item.ref_id)));
  return !blocked.some((item) => includedIds.has(String(item.ref_id)));
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
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by handoff" : "not confirmed" };
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

function isNextContextHandoffArtifact(artifact) {
  return artifact?.artifactType === NEXT_CONTEXT_HANDOFF_TYPE && artifact?.payload?.kind === NEXT_CONTEXT_HANDOFF_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
