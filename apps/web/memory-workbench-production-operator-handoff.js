const OPERATOR_HANDOFF_TYPE = "agentflow_production_memory_operator_handoff_packet";

export function buildProductionMemoryOperatorHandoffView(workspace, fallback) {
  const artifact = workspace?.productionMemoryOperatorHandoffPacket;
  if (!isOperatorHandoffArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const artifactRefs = arrayValue(payload.artifact_refs);
  const blockedItems = arrayValue(payload.blocked_items);
  const controls = arrayValue(payload.controls);
  const nonClaims = arrayValue(payload.non_claims);
  const action = objectValue(payload.next_operator_action);
  const ready = payload.handoff_status === "ready" && blockedItems.length === 0;

  return {
    ...fallback,
    state: ready ? "operator handoff ready" : "operator handoff blocked",
    project: {
      title: payload.handoff_id || artifact.fileName,
      brief: `Operator handoff: ${payload.handoff_status || "unknown"}`,
      format: OPERATOR_HANDOFF_TYPE,
      route: "selected local JSON only; read-only operator handoff packet",
    },
    workflow_actions: [
      actionItem("inspect_handoff", "Inspect handoff", ready ? "review ready" : "blocked", "project"),
      actionItem("inspect_artifact_refs", "Inspect refs", artifactRefs.length ? "review ready" : "missing", "assets"),
      actionItem("inspect_blockers", "Inspect blockers", blockedItems.length ? "blocked" : "review ready", "review"),
      actionItem("prepare_next_operator_action", "Prepare action", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      ...artifactRefs.map((item) => ({
        id: item.path,
        label: item.artifact_type || "handoff artifact ref",
        detail: item.path || "artifact ref",
        status: "review ready",
      })),
      ...blockedItems.map((item) => ({
        id: item.ref,
        label: item.ref || "blocked item",
        detail: item.reason || "blocked",
        status: "blocked",
      })),
    ],
    bundle_summary: [
      card("handoff_status", "Handoff status", ready ? "review ready" : "blocked", payload.handoff_status || "unknown"),
      card("manifest_check", "Manifest check", payload.manifest_check_status === "passed" ? "review ready" : "blocked", payload.manifest_check_status || "unknown"),
      card("artifact_refs", "Artifact refs", artifactRefs.length ? "review ready" : "missing", `${artifactRefs.length} refs in handoff`),
      card("blocked_items", "Blocked items", blockedItems.length ? "blocked" : "review ready", `${blockedItems.length} blockers`),
      card("non_claims", "Non-claims", nonClaims.length ? "blocked" : "review ready", `${nonClaims.length} boundaries retained`),
    ],
    memory_loaded: [
      {
        id: "operator_handoff_packet",
        title: "Operator handoff packet",
        why_eligible: "ready only after explicit manifest-check evidence",
        source_evidence_refs: [payload.source_operator_loop_id || "operator loop manifest"],
        promotion_status: payload.handoff_status || "unknown",
        request_projection: action.detail || action.action || "next operator action recorded",
        feedback_effect: "handoff evidence only; no durable memory or Company KB write",
        status: ready ? "review ready" : "blocked",
      },
    ],
    lanes: [
      lane("operator-handoff", "Operator handoff", ready ? "ready" : "blocked", payload.source_operator_loop_id || "operator loop", payload.handoff_status || "unknown"),
      lane("artifact-refs", "Artifact refs", artifactRefs.length ? "review ready" : "missing", `${artifactRefs.length} refs`, "available for inspection"),
      lane("blocked-items", "Blocked items", blockedItems.length ? "blocked" : "review ready", `${blockedItems.length} blockers`, "must stay out of next context"),
      lane("next-action", "Next operator action", ready ? "ready" : "blocked", action.action || "unknown", action.status || "unknown"),
    ],
    protocol_summary: {
      title: "Production memory operator handoff packet",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("manifest check passed", payload.manifest_check_status === "passed"),
        control("blocked items absent", blockedItems.length === 0),
        ...controls.map((item) => ({
          label: item.control_id || "control",
          status: item.status === "passed" ? "review ready" : "blocked",
          detail: item.status || "unknown",
        })),
      ],
      boundaries: boundaryItems(payload.claim_boundaries),
    },
    review: {
      storyboard_adherence: `${artifactRefs.length} handoff refs`,
      visual_consistency: `${blockedItems.length} blockers`,
      boundary: "operator handoff only / no provider call / no Company KB write",
    },
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: ready ? "Handoff packet is ready for the recorded next operator action." : "Resolve blocked_items before next operator action.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: action.action || "resolve_operator_handoff_blockers",
    },
    timeline: [
      step("Handoff", ready ? "ready" : "blocked", payload.handoff_id),
      step("Manifest check", payload.manifest_check_status || "unknown", `${payload.checked_ref_count ?? 0} refs checked`),
      step("Artifact refs", artifactRefs.length ? "review ready" : "missing", `${artifactRefs.length} refs`),
      step("Blocked items", blockedItems.length ? "blocked" : "review ready", `${blockedItems.length} blockers`),
      step("Next operator action", action.status || "unknown", action.action || "unknown"),
    ],
  };
}

function actionItem(id, label, status, focusTarget) {
  return { id, label, status, focusTarget, focus_target: focusTarget };
}

function card(id, title, status, detail) {
  return { id, title, status, detail };
}

function lane(id, title, status, input, output) {
  return { id, title, status, input, output };
}

function control(label, passed) {
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by handoff packet" : "not confirmed" };
}

function boundaryItems(boundaries = {}) {
  return [
    { label: "structure verification", status: "review ready", detail: boundaries.structure_verification || "not recorded" },
    { label: "runtime verification", status: "review ready", detail: boundaries.runtime_verification || "not recorded" },
    { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_claimed" },
    { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_claimed" },
    { label: "durable memory", status: "blocked", detail: boundaries.durable_memory || "not_written" },
    { label: "Company KB write", status: "blocked", detail: boundaries.company_kb_write || "not_written" },
  ];
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isOperatorHandoffArtifact(artifact) {
  return artifact?.artifactType === OPERATOR_HANDOFF_TYPE && artifact?.payload?.kind === OPERATOR_HANDOFF_TYPE;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
