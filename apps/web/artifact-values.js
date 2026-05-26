export function normalizeStatus(value) {
  const status = asText(value, "unknown").toLowerCase();
  if (["pass", "passed", "success", "succeeded", "valid"].includes(status)) return "pass";
  if (["fail", "failed", "error", "invalid", "blocked"].includes(status)) return "fail";
  if (["warning", "warn", "unsupported", "needs_changes", "running", "pending", "not_started"].includes(status)) return "warning";
  if (status === "missing") return "missing";
  if (["optional", "not_applicable", "n/a"].includes(status)) return "unknown";
  return status || "unknown";
}

export function asText(value, fallback = "") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

export function asList(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => describeValue(item));
}

export function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function collectChecks(payload) {
  const checks = Array.isArray(payload?.checks) ? payload.checks : [];
  return checks.filter((check) => check && typeof check === "object");
}

export function describeValue(value) {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "object") {
    return asText(value.message || value.name || value.id || JSON.stringify(value), "");
  }
  return String(value);
}

export function firstText(payload, fieldNames, fallback = "") {
  for (const fieldName of fieldNames) {
    const value = payload?.[fieldName];
    if (value !== null && value !== undefined && value !== "") return String(value);
  }
  return fallback;
}
