function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeProjectReadiness(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Project readiness"),
    summary: String(source.summary || ""),
    current_action: String(source.current_action || ""),
    current_action_label: String(source.current_action_label || "Next action"),
    steps: asArray(source.steps).map(normalizeReadinessStep),
    non_claims: asArray(source.non_claims).map(String),
  };
}

export function normalizeReadinessStep(value) {
  const source = asObject(value);
  return {
    step_id: String(source.step_id || ""),
    label: String(source.label || "Step"),
    status: String(source.status || "not_started"),
    action: String(source.action || ""),
    action_label: String(source.action_label || ""),
  };
}
