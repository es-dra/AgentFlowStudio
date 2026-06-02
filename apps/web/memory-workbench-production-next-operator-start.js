import { buildNextOperatorBrief } from "./memory-workbench-production-next-operator-brief.js";

const NEXT_OPERATOR_START_PACKET_TYPE = "agentflow_production_memory_next_operator_start_packet";

export function buildProductionMemoryNextOperatorStartPacketView(workspace, fallback) {
  const artifact = workspace?.productionMemoryNextOperatorStartPacket;
  if (!isNextOperatorStartPacketArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const checked = arrayValue(payload.checked_package_items);
  const blocked = arrayValue(payload.blocked_items);
  const failedControls = arrayValue(payload.failed_controls);
  const nonClaims = arrayValue(payload.non_claims);
  const action = objectValue(payload.next_operator_action);
  const ready = payload.start_packet_status === "ready" && payload.ready_for_next_operator === true;
  const nextOperatorBrief = buildNextOperatorBrief(payload);

  return {
    ...fallback,
    state: ready ? "next operator start packet ready" : "next operator start packet blocked",
    project: {
      title: payload.start_packet_id || artifact.fileName,
      brief: `Next operator start packet: ${payload.start_packet_status || "unknown"}`,
      format: NEXT_OPERATOR_START_PACKET_TYPE,
      route: "selected local JSON only; read-only next-operator start packet",
    },
    workflow_actions: [
      actionItem("inspect_start_packet", "Inspect start", ready ? "review ready" : "blocked", "project"),
      actionItem("inspect_checked_package_items", "Inspect items", checked.length ? "review ready" : "missing", "assets"),
      actionItem("inspect_start_boundaries", "Inspect boundaries", nonClaims.length ? "blocked" : "review ready", "review"),
      actionItem("prepare_next_operator", "Prepare next", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      ...checked.map((item) => ({
        id: item.path,
        label: item.artifact_type || "checked package item",
        detail: `${item.role || "item"} | ${item.path || "not recorded"}`,
        status: "review ready",
      })),
      ...blocked.map((item) => ({
        id: item.ref || item.path || "blocked_item",
        label: item.ref || item.path || "blocked item",
        detail: item.reason || "blocked",
        status: "blocked",
      })),
    ],
    bundle_summary: [
      card("start_packet", "Start packet", ready ? "review ready" : "blocked", payload.start_packet_status || "unknown"),
      card("checked_package_items", "Checked package items", checked.length ? "review ready" : "missing", `${checkedCount(payload, checked)} items checked`),
      card("blocked_items", "Blocked items", blocked.length ? "blocked" : "review ready", `${blocked.length} start blockers`),
      card("failed_controls", "Failed controls", failedControls.length ? "blocked" : "review ready", `${failedControls.length} controls failed`),
      card("non_claims", "Non-claims", nonClaims.length ? "blocked" : "review ready", `${nonClaims.length} boundaries retained`),
    ],
    memory_loaded: [
      {
        id: "next_operator_start_packet",
        title: "Next operator start packet",
        why_eligible: "ready only after final checked run package, handoff packet, and disabled write/provider controls",
        source_evidence_refs: [payload.source_run_package_check_path || "operator run package check"],
        promotion_status: payload.start_packet_status || "unknown",
        request_projection: action.action || "next operator action recorded",
        feedback_effect: "startup packet only; no durable memory or Company KB write",
        status: ready ? "review ready" : "blocked",
      },
    ],
    lanes: [
      lane("start-packet", "Start packet", ready ? "ready" : "blocked", payload.source_operator_loop_id || "operator loop", payload.start_packet_status || "unknown"),
      lane("checked-package-items", "Checked package items", checked.length ? "review ready" : "missing", `${checkedCount(payload, checked)} items`, "available for next operator"),
      lane("blocked-items", "Blocked items", blocked.length ? "blocked" : "review ready", `${blocked.length} blockers`, "excluded from startup"),
      lane("boundaries", "Boundaries", nonClaims.length ? "blocked" : "review ready", `${nonClaims.length} non-claims`, "claims remain limited"),
      lane("next-operator", "Next operator", ready ? "ready" : "blocked", action.action || "unknown", action.status || "unknown"),
    ],
    protocol_summary: {
      title: "Production memory next operator start packet",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("ready for next operator", ready),
        control("blocked items absent", blocked.length === 0),
        control("failed controls absent", failedControls.length === 0),
      ],
      boundaries: boundaryItems(payload.claim_boundaries),
    },
    review: {
      storyboard_adherence: `${checkedCount(payload, checked)} checked package items`,
      visual_consistency: `${blocked.length} start blockers`,
      boundary: "next-operator start packet only / no provider call / no Company KB write",
    },
    next_operator_brief: nextOperatorBrief,
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: nextOperatorBrief.prompt_excerpt || (ready ? "Start packet is ready for the recorded next operator action." : "Resolve start packet blockers before use."),
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? action.action || "start_next_operator_action" : "resolve_next_operator_start_packet_blockers",
    },
    timeline: [
      step("Start packet", ready ? "ready" : "blocked", payload.start_packet_id),
      step("Package check", payload.package_check_status || "unknown", payload.source_run_package_check_path),
      step("Checked items", checked.length ? "review ready" : "missing", `${checkedCount(payload, checked)} items`),
      step("Boundaries", nonClaims.length ? "blocked" : "review ready", `${nonClaims.length} non-claims`),
      step("Next operator", ready ? "ready" : "blocked", action.action || "unknown"),
    ],
  };
}

function checkedCount(payload, checked) {
  return payload.checked_package_item_count ?? checked.length;
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
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by start packet" : "not confirmed" };
}

function boundaryItems(boundaries = {}) {
  return [
    { label: "structure verification", status: "review ready", detail: boundaries.structure_verification || "not recorded" },
    { label: "runtime verification", status: "review ready", detail: boundaries.runtime_verification || "not recorded" },
    { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_claimed" },
    { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_claimed" },
    { label: "durable memory", status: "blocked", detail: boundaries.durable_memory || "not_written" },
    { label: "Company KB write", status: "blocked", detail: boundaries.company_kb_write || "not_written" },
    { label: "provider success", status: "blocked", detail: boundaries.provider_success || "not_claimed" },
  ];
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

function isNextOperatorStartPacketArtifact(artifact) {
  return artifact?.artifactType === NEXT_OPERATOR_START_PACKET_TYPE && artifact?.payload?.kind === NEXT_OPERATOR_START_PACKET_TYPE;
}
