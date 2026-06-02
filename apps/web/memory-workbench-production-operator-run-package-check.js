const OPERATOR_RUN_PACKAGE_CHECK_TYPE = "agentflow_production_memory_operator_run_package_check";

export function buildProductionMemoryOperatorRunPackageCheckView(workspace, fallback) {
  const artifact = findOperatorRunPackageCheckArtifact(workspace);
  if (!isOperatorRunPackageCheckArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const checked = arrayValue(payload.checked_items);
  const missing = arrayValue(payload.missing_refs);
  const mismatched = arrayValue(payload.mismatched_refs);
  const unsafe = arrayValue(payload.unsafe_refs);
  const blocked = arrayValue(payload.blocked_items);
  const failedControls = arrayValue(payload.failed_controls);
  const passed = payload.check_status === "passed";
  const ready = passed && payload.ready_for_handoff === true;

  return {
    ...fallback,
    state: passed ? "operator run package check passed" : "operator run package check blocked",
    project: {
      title: payload.package_path || artifact.fileName,
      brief: `Operator run package check: ${payload.check_status || "unknown"}`,
      format: OPERATOR_RUN_PACKAGE_CHECK_TYPE,
      route: "selected local JSON only; read-only operator run package check report",
    },
    workflow_actions: [
      action("inspect_run_package_check", "Inspect check", passed ? "review ready" : "blocked", "project"),
      action("inspect_checked_items", "Inspect checked items", checked.length ? "review ready" : "missing", "assets"),
      action("inspect_missing_items", "Inspect missing items", missing.length ? "blocked" : "review ready", "review"),
      action("inspect_failed_controls", "Inspect controls", failedControls.length ? "blocked" : "review ready", "memory-loaded"),
      action("prepare_handoff", "Prepare handoff", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      ...checked.map((item) => ({
        id: item.path,
        label: item.artifact_type || "checked item",
        detail: `${item.role || "item"} | ${item.path || "not recorded"}`,
        status: "review ready",
      })),
      ...missing.map((item) => blockedAsset(item, "missing item")),
      ...mismatched.map((item) => blockedAsset(item.path, "type mismatch")),
      ...unsafe.map((item) => blockedAsset(item, "unsafe item")),
      ...blocked.map((item) => blockedAsset(item.ref, item.reason || "blocked item")),
    ],
    bundle_summary: [
      card("check_status", "Package check", passed ? "review ready" : "blocked", payload.check_status || "unknown"),
      card("checked_items", "Checked items", checked.length ? "review ready" : "missing", `${checkedCount(payload, checked)} items checked`),
      card("missing_items", "Missing items", missing.length ? "blocked" : "review ready", `${missing.length} items missing`),
      card("mismatched_items", "Mismatched items", mismatched.length ? "blocked" : "review ready", `${mismatched.length} items mismatched`),
      card("unsafe_items", "Unsafe items", unsafe.length ? "blocked" : "review ready", `${unsafe.length} items unsafe`),
      card("blocked_items", "Blocked items", blocked.length ? "blocked" : "review ready", `${blocked.length} package blockers`),
      card("failed_controls", "Failed controls", failedControls.length ? "blocked" : "review ready", `${failedControls.length} controls failed`),
    ],
    memory_loaded: [
      {
        id: "operator_run_package_check",
        title: "Operator run package check",
        why_eligible: "machine check over explicit package item refs and handoff controls",
        source_evidence_refs: [payload.package_path || "operator run package"],
        promotion_status: payload.check_status || "unknown",
        request_projection: `${checkedCount(payload, checked)} checked; ${missing.length + mismatched.length + unsafe.length} ref blockers`,
        feedback_effect: "check report only; no durable memory or Company KB write",
        status: passed ? "review ready" : "blocked",
      },
    ],
    lanes: [
      lane("run-package-check", "Run package check", passed ? "review ready" : "blocked", payload.package_status || "unknown", payload.check_status || "unknown"),
      lane("checked-items", "Checked items", checked.length ? "review ready" : "missing", `${checkedCount(payload, checked)} items`, "artifact refs checked"),
      lane("missing-items", "Missing items", missing.length ? "blocked" : "review ready", `${missing.length} items`, "excluded until present"),
      lane("failed-controls", "Failed controls", failedControls.length ? "blocked" : "review ready", `${failedControls.length} controls`, "handoff controls checked"),
      lane("next-operator", "Next operator", ready ? "ready" : "blocked", payload.next_operator_action?.action || "unknown", ready ? "handoff ready" : "blockers unresolved"),
    ],
    protocol_summary: {
      title: "Production memory operator run package check",
      status: passed ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("ready for handoff", ready),
        control("missing refs absent", missing.length === 0),
        control("mismatched refs absent", mismatched.length === 0),
        control("unsafe refs absent", unsafe.length === 0),
        control("blocked items absent", blocked.length === 0),
        control("failed controls absent", failedControls.length === 0),
      ],
      boundaries: boundaryItems(payload.claim_boundaries),
    },
    review: {
      storyboard_adherence: `${checkedCount(payload, checked)} package items checked`,
      visual_consistency: `${missing.length + mismatched.length + unsafe.length} ref blockers`,
      boundary: "operator run package check only / no provider call / no Company KB write",
    },
    feedback: {
      status: passed ? "review ready" : "blocked",
      summary: passed ? "Run package refs and handoff controls are machine-checked." : "Resolve package check blockers before handoff.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "handoff_to_next_operator" : "resolve_operator_run_package_check_blockers",
    },
    timeline: [
      step("Run package", payload.package_status || "unknown", payload.package_path),
      step("Package check", payload.check_status || "unknown", `${checkedCount(payload, checked)} items checked`),
      step("Missing items", missing.length ? "blocked" : "review ready", `${missing.length} items`),
      step("Failed controls", failedControls.length ? "blocked" : "review ready", `${failedControls.length} controls`),
      step("Next operator", ready ? "ready" : "blocked", payload.next_operator_action?.action || "unknown"),
    ],
  };
}

function findOperatorRunPackageCheckArtifact(workspace) {
  const artifacts = Array.isArray(workspace?.memoryBundle) ? workspace.memoryBundle : [];
  return artifacts.find((artifact) => artifact?.artifactType === OPERATOR_RUN_PACKAGE_CHECK_TYPE);
}

function blockedAsset(path, detail) {
  return {
    id: String(path || detail),
    label: detail,
    detail: String(path || "not recorded"),
    status: "blocked",
  };
}

function checkedCount(payload, checked) {
  return payload.checked_item_count ?? checked.length;
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
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by check report" : "not confirmed" };
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

function isOperatorRunPackageCheckArtifact(artifact) {
  return artifact?.artifactType === OPERATOR_RUN_PACKAGE_CHECK_TYPE && artifact?.payload?.kind === OPERATOR_RUN_PACKAGE_CHECK_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
