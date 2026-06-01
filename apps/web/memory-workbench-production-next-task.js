const NEXT_TASK_PACKET_TYPE = "agentflow_production_memory_next_task_packet";

export function buildProductionMemoryNextTaskPacketView(workspace, fallback) {
  const artifact = workspace?.productionMemoryNextTaskPacket;
  if (!isNextTaskPacketArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const allowed = arrayValue(payload.allowed_context_refs);
  const blocked = arrayValue(payload.blocked_refs);
  const nonClaims = arrayValue(payload.non_claims);
  const ready = payload.packet_status === "ready" && payload.provider_calls_started === false;
  return {
    ...fallback,
    state: ready ? "next task ready" : "blocked",
    project: {
      title: payload.project_id || payload.task_packet_id || artifact.fileName,
      brief: `Next task packet: ${payload.packet_status || "unknown"}`,
      format: NEXT_TASK_PACKET_TYPE,
      route: "selected local JSON only; read-only no-provider next-task packet",
    },
    workflow_actions: [
      action("inspect_packet", "Inspect packet", "review ready", "project"),
      action("inspect_allowed_context", "Inspect allowed", allowed.length ? "ready" : "missing", "memory-loaded"),
      action("inspect_blocked_refs", "Inspect blocked", blocked.length ? "blocked" : "review ready", "review"),
      action("prepare_next_ai_task", "Prepare next task", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [...allowed, ...blocked].map((item) => ({
      id: item.ref_id,
      label: item.ref_id,
      detail: item.summary || item.reason || item.status || "next-task ref",
      status: item.reason ? "blocked" : item.status || "review ready",
    })),
    bundle_summary: [
      card("allowed_context_refs", "Allowed context refs", allowed.length ? "review ready" : "missing", `${allowed.length} refs available for the next AI task`),
      card("blocked_refs", "Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs excluded from the next AI task`),
      card("non_claims", "Non-claims", nonClaims.length ? "blocked" : "review ready", `${nonClaims.length} boundaries retained`),
    ],
    memory_loaded: allowed.map((item) => ({
      id: item.ref_id,
      title: item.title || item.ref_id,
      why_eligible: item.promotion_decision ? `explicit decision ${item.decision_id}` : "allowed by next task packet",
      source_evidence_refs: item.source_feedback_ids || [item.status || "allowed"],
      promotion_status: item.promotion_decision || item.status || "allowed",
      request_projection: item.summary || "available for next AI task context",
      feedback_effect: "visible in allowed_context_refs only; no durable memory or Company KB write",
      status: item.promotion_decision ? "promotion decision ready" : "review ready",
    })),
    lanes: [
      lane("next-task-packet", "Next task packet", ready ? "ready" : "blocked", payload.task_id || "next task", payload.packet_status || "unknown"),
      lane("allowed-context-refs", "Allowed context refs", allowed.length ? "review ready" : "missing", `${allowed.length} refs`, "eligible for next AI task"),
      lane("blocked-refs", "Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`, "excluded from next AI task"),
    ],
    protocol_summary: {
      title: "Production memory next task packet",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("blocked refs excluded", blockedRefsExcluded(allowed, blocked)),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `${allowed.length} allowed context refs`,
      visual_consistency: `${blocked.length} blocked refs`,
      boundary: "next task packet only / no provider call / no Company KB write",
    },
    feedback: {
      status: "review ready",
      summary: "Use as next-task input packet only; do not treat as acceptance or durable memory.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "use_next_task_packet_for_next_ai_task" : "resolve_next_task_packet_blockers",
    },
    timeline: [
      step("Packet", ready ? "ready" : "blocked", payload.task_packet_id),
      step("Allowed context refs", allowed.length ? "review ready" : "missing", `${allowed.length} refs`),
      step("Blocked refs", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`),
      step("Next task", ready ? "ready" : "blocked", payload.task_id),
    ],
  };
}

function blockedRefsExcluded(allowed, blocked) {
  const allowedIds = new Set(allowed.map((item) => String(item.ref_id)));
  return !blocked.some((item) => allowedIds.has(String(item.ref_id)));
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
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by packet" : "not confirmed" };
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

function isNextTaskPacketArtifact(artifact) {
  return artifact?.artifactType === NEXT_TASK_PACKET_TYPE && artifact?.payload?.kind === NEXT_TASK_PACKET_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
