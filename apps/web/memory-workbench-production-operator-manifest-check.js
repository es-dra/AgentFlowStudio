const OPERATOR_MANIFEST_CHECK_TYPE = "agentflow_production_memory_operator_manifest_check";

export function buildProductionMemoryOperatorManifestCheckView(workspace, fallback) {
  const artifact = workspace?.productionMemoryOperatorManifestCheck;
  if (!isOperatorManifestCheckArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const checked = arrayValue(payload.checked_refs);
  const missing = arrayValue(payload.missing_refs);
  const mismatched = arrayValue(payload.mismatched_refs);
  const unsafe = arrayValue(payload.unsafe_refs);
  const failedNodes = arrayValue(payload.failed_nodes);
  const failedControls = arrayValue(payload.failed_controls);
  const passed = payload.check_status === "passed";
  const ready = passed && payload.ready_for_next_pass === true;

  return {
    ...fallback,
    state: passed ? "operator manifest check passed" : "operator manifest check blocked",
    project: {
      title: payload.manifest_path || artifact.fileName,
      brief: `Operator manifest check: ${payload.check_status || "unknown"}`,
      format: OPERATOR_MANIFEST_CHECK_TYPE,
      route: "selected local JSON only; read-only operator manifest check report",
    },
    workflow_actions: [
      action("inspect_manifest_check", "Inspect check", passed ? "review ready" : "blocked", "project"),
      action("inspect_checked_refs", "Inspect checked refs", checked.length ? "review ready" : "missing", "assets"),
      action("inspect_missing_refs", "Inspect missing refs", missing.length ? "blocked" : "review ready", "review"),
      action("inspect_failed_nodes", "Inspect failed nodes", failedNodes.length ? "blocked" : "review ready", "memory-loaded"),
      action("prepare_next_pass", "Prepare next pass", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      ...checked.map((item) => ({
        id: item.path,
        label: item.artifact_type || "checked ref",
        detail: item.path || "checked artifact ref",
        status: "review ready",
      })),
      ...missing.map((item) => blockedAsset(item, "missing ref")),
      ...mismatched.map((item) => blockedAsset(item.path, "type mismatch")),
      ...unsafe.map((item) => blockedAsset(item, "unsafe ref")),
    ],
    bundle_summary: [
      card("check_status", "Manifest check", passed ? "review ready" : "blocked", payload.check_status || "unknown"),
      card("checked_refs", "Checked refs", checked.length ? "review ready" : "missing", `${checkedCount(payload, checked)} refs checked`),
      card("missing_refs", "Missing refs", missing.length ? "blocked" : "review ready", `${missing.length} refs missing`),
      card("mismatched_refs", "Mismatched refs", mismatched.length ? "blocked" : "review ready", `${mismatched.length} refs mismatched`),
      card("failed_nodes", "Failed nodes", failedNodes.length ? "blocked" : "review ready", `${failedNodes.length} nodes failed`),
      card("failed_controls", "Failed controls", failedControls.length ? "blocked" : "review ready", `${failedControls.length} controls failed`),
    ],
    memory_loaded: [
      {
        id: "operator_manifest_check",
        title: "Operator manifest check",
        why_eligible: "machine check over explicit operator-loop artifact refs",
        source_evidence_refs: [payload.manifest_path || "operator manifest"],
        promotion_status: payload.check_status || "unknown",
        request_projection: `${checkedCount(payload, checked)} refs checked; ${missing.length + mismatched.length + unsafe.length} ref blockers`,
        feedback_effect: "audit report only; no durable memory or Company KB write",
        status: passed ? "review ready" : "blocked",
      },
    ],
    lanes: [
      lane("manifest-check", "Manifest check", passed ? "review ready" : "blocked", payload.manifest_kind || "manifest", payload.check_status || "unknown"),
      lane("checked-refs", "Checked refs", checked.length ? "review ready" : "missing", `${checkedCount(payload, checked)} refs`, "artifact refs checked"),
      lane("missing-refs", "Missing refs", missing.length ? "blocked" : "review ready", `${missing.length} refs`, "excluded until present"),
      lane("failed-nodes", "Failed nodes", failedNodes.length ? "blocked" : "review ready", `${failedNodes.length} nodes`, "operator nodes checked"),
      lane("failed-controls", "Failed controls", failedControls.length ? "blocked" : "review ready", `${failedControls.length} controls`, "operator controls checked"),
    ],
    protocol_summary: {
      title: "Production memory operator manifest check",
      status: passed ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        control("checked refs available", checked.length > 0),
        control("missing refs absent", missing.length === 0),
        control("mismatched refs absent", mismatched.length === 0),
        control("failed nodes absent", failedNodes.length === 0),
        control("failed controls absent", failedControls.length === 0),
      ],
      boundaries: boundaryItems(payload.claim_boundaries),
    },
    review: {
      storyboard_adherence: `${checkedCount(payload, checked)} artifact refs checked`,
      visual_consistency: `${missing.length + mismatched.length + unsafe.length} ref blockers`,
      boundary: "operator manifest check only / no provider call / no Company KB write",
    },
    feedback: {
      status: passed ? "review ready" : "blocked",
      summary: passed ? "Manifest artifact refs are machine-checked." : "Resolve manifest check blockers before next pass.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "inspect_operator_manifest_check_before_next_pass" : "resolve_operator_manifest_check_blockers",
    },
    timeline: [
      step("Manifest", payload.chain_status || "unknown", payload.manifest_path),
      step("Checked refs", checked.length ? "review ready" : "missing", `${checkedCount(payload, checked)} refs`),
      step("Missing refs", missing.length ? "blocked" : "review ready", `${missing.length} refs`),
      step("Failed nodes", failedNodes.length ? "blocked" : "review ready", `${failedNodes.length} nodes`),
      step("Failed controls", failedControls.length ? "blocked" : "review ready", `${failedControls.length} controls`),
    ],
  };
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
  return payload.checked_ref_count ?? checked.length;
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
  ];
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isOperatorManifestCheckArtifact(artifact) {
  return artifact?.artifactType === OPERATOR_MANIFEST_CHECK_TYPE && artifact?.payload?.kind === OPERATOR_MANIFEST_CHECK_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
