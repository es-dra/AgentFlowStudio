function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeProductionBoard(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Production board"),
    summary: String(source.summary || ""),
    current_action: String(source.current_action || ""),
    current_action_label: String(source.current_action_label || "Continue"),
    lanes: asArray(source.lanes).map(normalizeProductionLane),
    non_claims: asArray(source.non_claims).map(String),
  };
}

function normalizeProductionLane(value) {
  const source = asObject(value);
  return {
    lane_id: String(source.lane_id || ""),
    label: String(source.label || "Stage"),
    status: String(source.status || "not_started"),
    summary: String(source.summary || ""),
    action: String(source.action || ""),
    action_label: String(source.action_label || "Continue"),
    primary_artifact_id: String(source.primary_artifact_id || ""),
    artifact_count: Number(source.artifact_count || 0),
  };
}
