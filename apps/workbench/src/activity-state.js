function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeActivityTimeline(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Activity timeline"),
    summary: String(source.summary || ""),
    counts: normalizeActivityCounts(source.counts),
    items: asArray(source.items).map(normalizeActivityItem),
    non_claims: asArray(source.non_claims).map(String),
  };
}

function normalizeActivityCounts(value) {
  const source = asObject(value);
  return {
    total: Number(source.total || 0),
    running: Number(source.running || 0),
    blocked: Number(source.blocked || 0),
    failed: Number(source.failed || 0),
    succeeded: Number(source.succeeded || 0),
  };
}

function normalizeActivityItem(value) {
  const source = asObject(value);
  return {
    event_id: String(source.event_id || ""),
    title: String(source.title || "Runtime event"),
    action: String(source.action || ""),
    status: String(source.status || "not_started"),
    job_id: String(source.job_id || ""),
    primary_artifact_id: String(source.primary_artifact_id || ""),
    artifact_ids: asArray(source.artifact_ids).map(String),
    artifact_count: Number(source.artifact_count || 0),
  };
}
