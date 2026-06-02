import { acceptanceFeedbackCandidatePromotionParts } from "./memory-workbench-production-acceptance-feedback-handoff.js";

const OPERATOR_RUN_PACKAGE_TYPE = "agentflow_production_memory_operator_run_package";

export function buildProductionMemoryOperatorRunPackageView(workspace, fallback) {
  const artifact = workspace?.productionMemoryOperatorRunPackage;
  if (!isOperatorRunPackageArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const packageItems = arrayValue(payload.package_items);
  const blockedItems = arrayValue(payload.blocked_items);
  const controls = arrayValue(payload.controls);
  const nonClaims = arrayValue(payload.non_claims);
  const action = objectValue(payload.next_operator_action);
  const ready = payload.package_status === "ready" && blockedItems.length === 0;
  const acceptancePromotion = acceptanceFeedbackCandidatePromotionParts(payload);

  return {
    ...fallback,
    state: ready ? "operator run package ready" : "operator run package blocked",
    project: {
      title: payload.package_id || artifact.fileName,
      brief: `Operator run package: ${payload.package_status || "unknown"}`,
      format: OPERATOR_RUN_PACKAGE_TYPE,
      route: "selected local JSON only; read-only operator run package",
    },
    workflow_actions: [
      actionItem("inspect_run_package", "Inspect package", ready ? "review ready" : "blocked", "project"),
      actionItem("inspect_package_items", "Inspect items", packageItems.length ? "review ready" : "missing", "assets"),
      actionItem("inspect_blockers", "Inspect blockers", blockedItems.length ? "blocked" : "review ready", "review"),
      ...acceptancePromotion.actions,
      actionItem("prepare_next_operator_action", "Prepare action", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      ...packageItems.map((item) => ({
        id: item.path,
        label: item.artifact_type || "run package item",
        detail: `${item.role || "item"} | ${item.path || "not recorded"}`,
        status: item.status === "expected" ? "review ready" : item.status || "review ready",
      })),
      ...blockedItems.map((item) => ({
        id: item.ref,
        label: item.ref || "blocked item",
        detail: item.reason || "blocked",
        status: "blocked",
      })),
    ],
    bundle_summary: [
      card("package_status", "Package status", ready ? "review ready" : "blocked", payload.package_status || "unknown"),
      card("manifest_check", "Manifest check", payload.manifest_check_status === "passed" ? "review ready" : "blocked", payload.manifest_check_status || "unknown"),
      card("handoff_packet", "Handoff packet", payload.handoff_status === "ready" ? "review ready" : "blocked", payload.handoff_status || "unknown"),
      card("package_items", "Package items", packageItems.length ? "review ready" : "missing", `${packageItems.length} items indexed`),
      card("blocked_items", "Blocked items", blockedItems.length ? "blocked" : "review ready", `${blockedItems.length} blockers`),
      ...acceptancePromotion.cards,
      card("non_claims", "Non-claims", nonClaims.length ? "blocked" : "review ready", `${nonClaims.length} boundaries retained`),
    ],
    memory_loaded: [
      {
        id: "operator_run_package",
        title: "Operator run package",
        why_eligible: "indexes manifest, manifest check, handoff packet, and output refs",
        source_evidence_refs: [payload.source_operator_loop_id || "operator loop manifest"],
        promotion_status: payload.package_status || "unknown",
        request_projection: action.detail || action.action || "next operator action recorded",
        feedback_effect: "run package evidence only; no durable memory or Company KB write",
        status: ready ? "review ready" : "blocked",
      },
      ...acceptancePromotion.memory,
    ],
    lanes: [
      lane("operator-run-package", "Operator run package", ready ? "ready" : "blocked", payload.source_operator_loop_id || "operator loop", payload.package_status || "unknown"),
      lane("package-items", "Package items", packageItems.length ? "review ready" : "missing", `${packageItems.length} items`, "indexed for inspection"),
      lane("blocked-items", "Blocked items", blockedItems.length ? "blocked" : "review ready", `${blockedItems.length} blockers`, "must be resolved first"),
      ...acceptancePromotion.lanes,
      lane("next-action", "Next operator action", ready ? "ready" : "blocked", action.action || "unknown", action.status || "unknown"),
    ],
    protocol_summary: {
      title: "Production memory operator run package",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("manifest check passed", payload.manifest_check_status === "passed"),
        control("handoff ready", payload.handoff_status === "ready"),
        control("blocked items absent", blockedItems.length === 0),
        ...acceptancePromotion.controls,
        ...controls.map((item) => ({
          label: item.control_id || "control",
          status: item.status === "passed" ? "review ready" : "blocked",
          detail: item.status || "unknown",
        })),
      ],
      boundaries: boundaryItems(payload.claim_boundaries),
    },
    review: {
      storyboard_adherence: `${packageItems.length} package items indexed`,
      visual_consistency: `${blockedItems.length} blockers`,
      boundary: "operator run package only / no provider call / no Company KB write",
    },
    feedback: {
      status: ready ? "review ready" : "blocked",
      summary: ready ? "Run package is ready for the recorded next operator action." : "Resolve blocked_items before using this run package.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: action.action || "resolve_operator_run_package_blockers",
    },
    timeline: [
      step("Run package", ready ? "ready" : "blocked", payload.package_id),
      step("Manifest check", payload.manifest_check_status || "unknown", `${payload.checked_ref_count ?? 0} refs checked`),
      step("Handoff", payload.handoff_status || "unknown", payload.source_operator_loop_id),
      step("Package items", packageItems.length ? "review ready" : "missing", `${packageItems.length} items`),
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
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by run package" : "not confirmed" };
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

function isOperatorRunPackageArtifact(artifact) {
  return artifact?.artifactType === OPERATOR_RUN_PACKAGE_TYPE && artifact?.payload?.kind === OPERATOR_RUN_PACKAGE_TYPE;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
