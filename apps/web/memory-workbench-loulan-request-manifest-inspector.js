const REQUEST_LABELS = {
  loulan_image2_request_manifest: "Loulan Image2 request manifest",
  loulan_kling_i2v_request_manifest: "Loulan Kling I2V request manifest",
};

export function isLoulanRequestManifest(type) {
  return Object.prototype.hasOwnProperty.call(REQUEST_LABELS, type);
}

export function loulanRequestManifestTypeLabel(type) {
  return REQUEST_LABELS[type] || "";
}

export function loulanRequestManifestFocusTargets() {
  return ["baseline-run", "memory-backed-run", "review", "next-pass"];
}

export function loulanRequestManifestStatus(payload) {
  const hasBlockedRequest = arrayValue(payload.requests).some((request) => String(objectValue(request).status || "").startsWith("blocked_"));
  return hasBlockedRequest ? "blocked" : "review ready";
}

export function loulanRequestManifestFacts(payload) {
  const requests = arrayValue(payload.requests).map(objectValue);
  return [
    fact("requests", requests.length),
    fact("models", listText(uniqueValues(requests, "model"))),
    fact("blocks", listText(uniqueBlocks(requests))),
    fact("status_counts", countText(requests, "status")),
    fact("aspect_ratios", listText(uniqueValues(requests, "aspect_ratio"))),
    fact("durations", listText(uniqueValues(requests, "duration"))),
    fact("provider_calls_started", "false"),
  ];
}

function uniqueValues(items, key) {
  return [...new Set(items.map((item) => item[key]).filter(Boolean))];
}

function uniqueBlocks(items) {
  return [...new Set(items.map((item) => String(item.shot_id || "").split("-")[0]).filter(Boolean))];
}

function countText(items, key) {
  const counts = {};
  for (const item of items) counts[item[key] || "unknown"] = (counts[item[key] || "unknown"] || 0) + 1;
  return Object.entries(counts)
    .map(([name, count]) => `${name}: ${String(count)}`)
    .join(", ") || "none";
}

function listText(values) {
  return values.length > 0 ? values.join(", ") : "none";
}

function fact(label, value) {
  return { label, value: String(value) };
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
