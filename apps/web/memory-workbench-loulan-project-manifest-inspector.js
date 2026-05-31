const PROJECT_MANIFEST_LABELS = {
  loulan_character_asset_manifest: "Loulan character asset manifest",
  loulan_character_asset_versions: "Loulan character asset versions",
  loulan_prop_asset_versions: "Loulan prop asset versions",
  loulan_shot_list_manifest: "Loulan shot list manifest",
};

export function isLoulanProjectManifest(type) {
  return Object.prototype.hasOwnProperty.call(PROJECT_MANIFEST_LABELS, type);
}

export function loulanProjectManifestTypeLabel(type) {
  return PROJECT_MANIFEST_LABELS[type] || "";
}

export function loulanProjectManifestFocusTargets() {
  return ["project", "assets", "review", "next-pass"];
}

export function loulanProjectManifestStatus(type, payload) {
  if (type === "loulan_shot_list_manifest") {
    return shotRows(payload).some((shot) => String(shot.quality_status || "").includes("pending")) ? "pending_human_review" : "review ready";
  }
  return payload.claim_level || payload.status || "review ready";
}

export function loulanProjectManifestFacts(type, payload) {
  if (type === "loulan_shot_list_manifest") return shotListFacts(payload);
  return assetManifestFacts(payload);
}

function assetManifestFacts(payload) {
  const assets = assetRows(payload);
  const facts = [
    fact("assets", assets.length),
    fact("characters", listText(uniqueValues(assets, "character"))),
    fact("props", listText(uniqueValues(assets, "prop"))),
    fact("status_counts", countText(assets, "status")),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
  ];
  if (payload.provider_route) facts.splice(4, 0, fact("provider_route", payload.provider_route));
  return facts.filter((item) => item.value !== "none" || item.label === "status_counts");
}

function shotListFacts(payload) {
  const shots = shotRows(payload);
  return [
    fact("shots", shots.length),
    fact("blocks", listText(uniqueValues(shots, "generation_block"))),
    fact("quality_status_counts", countText(shots, "quality_status")),
    fact("target_formats", listText(uniqueValues(shots, "target_format"))),
    fact("scenes", listText(uniqueValues(shots, "scene"))),
  ].filter((item) => item.value !== "none" || item.label === "quality_status_counts");
}

function assetRows(payload) {
  return arrayValue(payload.assets).map(objectValue);
}

function shotRows(payload) {
  return arrayValue(payload.shots).map(objectValue);
}

function uniqueValues(items, key) {
  return [...new Set(items.map((item) => item[key]).filter((value) => value !== undefined && value !== null && value !== ""))];
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

function yesNo(value) {
  return value === true ? "true" : "false";
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
