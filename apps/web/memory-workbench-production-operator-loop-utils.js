export function companyBoundary(company) {
  if (company.requires_human_review) return "candidate-only; human review required before Company KB promotion";
  return company.writes_company_kb === false ? "Company KB write disabled" : "unknown";
}

export function action(id, label, status, focusTarget) {
  return { id, label, status, focusTarget, focus_target: focusTarget };
}

export function card(id, title, status, detail) {
  return { id, title, status, detail };
}

export function lane(id, title, status, input, output) {
  return { id, title, status, input, output };
}

export function control(label, passed, forcedStatus = null) {
  return { label, status: forcedStatus || (passed ? "review ready" : "blocked"), detail: passed ? "confirmed by manifest" : "not confirmed" };
}

export function boundaryItems(boundaries = {}) {
  return [
    { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_reviewed" },
    { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
    { label: "durable memory runtime", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    { label: "provider success", status: "blocked", detail: boundaries.provider_success || "not_attempted" },
  ];
}

export function hasPassedControl(payload, controlId) {
  return arrayValue(payload.controls).some((item) => item?.control_id === controlId && item?.status === "passed");
}

export function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

export function isOperatorLoopArtifact(artifact) {
  return artifact?.artifactType === "agentflow_production_memory_operator_loop_run"
    && artifact?.payload?.kind === "agentflow_production_memory_operator_loop_run";
}

export function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

export function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : null;
}
