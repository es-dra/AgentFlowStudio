import { containsUnsafeText } from "./safe-text-redaction.js";

export const KEYFRAME_CONSTRAINTS_SCHEMA_VERSION = "afs_keyframe_constraints.v0.1";
export const KEYFRAME_CONSTRAINT_EXCLUSION_REASON = "keyframe_constraint_fixed_asset_exclusion";

export const KEYFRAME_CONSTRAINT_SECTIONS = [
  "character", "scene", "object", "camera", "lighting", "motion", "negative", "fixed_asset", "local_reference",
];

export const KEYFRAME_PROVIDER_SECTIONS = ["character", "scene", "object", "camera", "lighting", "motion", "negative"];

const PROVIDER_SECTION_SET = new Set(KEYFRAME_PROVIDER_SECTIONS);
const VALID_SECTION_SET = new Set(KEYFRAME_CONSTRAINT_SECTIONS);
const SECTION_LABELS = {
  character: "Character",
  scene: "Scene",
  object: "Object",
  camera: "Camera",
  lighting: "Lighting",
  motion: "Motion",
  negative: "Negative",
  fixed_asset: "Fixed asset",
  local_reference: "Local reference",
};

export function isKeyframeConstraintNode(node) {
  return node?.type === "image" && node?.params?.nodeRole === "keyframe_generation";
}

export function sectionLabel(section) {
  return SECTION_LABELS[section] || "Local reference";
}

export function normalizeKeyframeConstraints(value, options = {}) {
  const source = value && typeof value === "object" ? value : {};
  const rows = Array.isArray(source.rows) ? source.rows : [];
  return {
    schema_version: KEYFRAME_CONSTRAINTS_SCHEMA_VERSION,
    updated_at: String(source.updated_at || timestamp(options)),
    rows: rows
      .map((row, index) => normalizeRow(row, index))
      .filter(Boolean)
      .sort(compareRowOrder)
      .map((row, index) => ({ ...row, order: index })),
  };
}

export function addKeyframeConstraintRow(value, row = {}, options = {}) {
  const constraints = normalizeKeyframeConstraints(value, options);
  const next = normalizeRow({ ...row, order: constraints.rows.length }, constraints.rows.length);
  if (!next) return touchConstraints(constraints, options);
  return touchConstraints({ ...constraints, rows: [...constraints.rows, next] }, options);
}

export function updateKeyframeConstraintRow(value, rowId, patch = {}, options = {}) {
  const constraints = normalizeKeyframeConstraints(value, options);
  const rows = constraints.rows.map((row) => (
    row.id === rowId ? normalizeRow({ ...row, ...patch, id: row.id, order: row.order }, row.order) : row
  )).filter(Boolean);
  return touchConstraints({ ...constraints, rows }, options);
}

export function toggleKeyframeConstraintRow(value, rowId, enabled, options = {}) {
  return updateKeyframeConstraintRow(value, rowId, { enabled: Boolean(enabled) }, options);
}

export function removeKeyframeConstraintRow(value, rowId, options = {}) {
  const constraints = normalizeKeyframeConstraints(value, options);
  return touchConstraints({
    ...constraints,
    rows: constraints.rows.filter((row) => row.id !== rowId).map((row, index) => ({ ...row, order: index })),
  }, options);
}

export function moveKeyframeConstraintRow(value, rowId, direction, options = {}) {
  const constraints = normalizeKeyframeConstraints(value, options);
  const rows = [...constraints.rows];
  const from = rows.findIndex((row) => row.id === rowId);
  const to = from + Math.sign(Number(direction) || 0);
  if (from < 0 || to < 0 || to >= rows.length) return constraints;
  [rows[from], rows[to]] = [rows[to], rows[from]];
  return touchConstraints({
    ...constraints,
    rows: rows.map((row, index) => ({ ...row, order: index })),
  }, options);
}

export function applyKeyframeConstraintRowAction(value, action = {}, options = {}) {
  if (action.type === "add") return addKeyframeConstraintRow(value, action.row || {}, options);
  if (action.type === "update") return updateKeyframeConstraintRow(value, action.id, action.patch || {}, options);
  if (action.type === "toggle") return toggleKeyframeConstraintRow(value, action.id, action.enabled, options);
  if (action.type === "remove") return removeKeyframeConstraintRow(value, action.id, options);
  if (action.type === "move") {
    const direction = action.direction === "up" ? -1 : action.direction === "down" ? 1 : Number(action.direction || 0);
    return moveKeyframeConstraintRow(value, action.id, direction, options);
  }
  return normalizeKeyframeConstraints(value, options);
}

export function newKeyframeConstraintRow(section = "character", patch = {}) {
  return normalizeRow({
    id: `kc_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`,
    section,
    text: "",
    enabled: true,
    projection: PROVIDER_SECTION_SET.has(section) ? "provider" : "audit_only",
    ...patch,
  }, 0);
}

export function projectKeyframeConstraintsForProvider(value) {
  const rows = providerConstraintRows(value);
  const blocks = [];
  for (const section of KEYFRAME_PROVIDER_SECTIONS) {
    const sectionRows = rows.filter((row) => row.section === section);
    if (!sectionRows.length) continue;
    blocks.push({
      section,
      label: sectionLabel(section),
      text: `${sectionLabel(section)}: ${sectionRows.map((row) => row.text).join("; ")}`,
    });
  }
  return {
    schema_version: KEYFRAME_CONSTRAINTS_SCHEMA_VERSION,
    rows,
    prompt_text: blocks.map((block) => block.text).join("\n"),
    sections: blocks,
  };
}

export const projectKeyframeConstraints = projectKeyframeConstraintsForProvider;

export function appendKeyframeConstraintPrompt(basePrompt, value) {
  const prompt = String(basePrompt || "").trim();
  const projected = projectKeyframeConstraintsForProvider(value);
  if (!projected.prompt_text) return prompt;
  const suffix = `Keyframe constraints:\n${projected.prompt_text}`;
  return prompt ? `${prompt}\n\n${suffix}` : suffix;
}

export const keyframePromptWithConstraints = appendKeyframeConstraintPrompt;

export function keyframeConstraintsProviderSnapshot(value) {
  const projected = projectKeyframeConstraintsForProvider(value);
  if (!projected.rows.length) return null;
  return {
    schema_version: KEYFRAME_CONSTRAINTS_SCHEMA_VERSION,
    rows: projected.rows.map((row) => ({ id: row.id, section: row.section, text: row.text })),
    prompt_text: projected.prompt_text,
  };
}

export function temporaryAssetExclusionsForKeyframeConstraints(value, existing = []) {
  return mergeFixedAssetConstraintRows(value, normalizeAssetExclusions(existing));
}

export function syncTemporaryAssetExclusionsFromKeyframeConstraints(node) {
  if (!node) return [];
  node.params = node.params || {};
  const next = temporaryAssetExclusionsForKeyframeConstraints(
    node.params.keyframeConstraints,
    node.params.temporaryAssetExclusions,
  );
  node.params.temporaryAssetExclusions = mergeFixedAssetConstraintRows(node.params.keyframeConstraints, next);
  return node.params.temporaryAssetExclusions;
}

export function setFixedAssetExclusion(values, assetId, excluded) {
  const normalized = normalizeAssetExclusions(values);
  const id = safeToken(assetId, 120);
  if (!id) return normalized;
  if (!excluded) {
    return normalized.filter((item) => !(item.asset_id === id && item.reason === KEYFRAME_CONSTRAINT_EXCLUSION_REASON));
  }
  if (normalized.some((item) => item.asset_id === id)) return normalized;
  return [...normalized, { asset_id: id, reason: KEYFRAME_CONSTRAINT_EXCLUSION_REASON }];
}

export function isTemporaryAssetExcluded(values, assetId) {
  const id = safeToken(assetId, 120);
  return Boolean(id && normalizeAssetExclusions(values).some((item) => item.asset_id === id));
}

export function fixedAssetExclusionRows(value) {
  return normalizeKeyframeConstraints(value).rows.filter((row) => (
    row.section === "fixed_asset"
    && row.enabled
    && row.asset_id
    && !containsUnsafeText(row.asset_id)
  ));
}

function providerConstraintRows(value) {
  return normalizeKeyframeConstraints(value).rows
    .filter((row) => (
      row.enabled
      && row.projection === "provider"
      && PROVIDER_SECTION_SET.has(row.section)
      && row.text
      && !containsUnsafeText(row.text)
    ))
    .sort((left, right) => {
      const sectionDelta = KEYFRAME_PROVIDER_SECTIONS.indexOf(left.section) - KEYFRAME_PROVIDER_SECTIONS.indexOf(right.section);
      if (sectionDelta) return sectionDelta;
      return left.order - right.order;
    })
    .map((row) => ({ id: row.id, section: row.section, text: row.text }));
}

function mergeFixedAssetConstraintRows(value, existing) {
  let result = normalizeAssetExclusions(existing);
  const fixedRows = fixedAssetExclusionRows(value);
  for (const row of fixedRows) {
    result = setFixedAssetExclusion(result, row.asset_id, true);
  }
  const activeIds = new Set(fixedRows.map((row) => row.asset_id));
  return result.filter((item) => item.reason !== KEYFRAME_CONSTRAINT_EXCLUSION_REASON || activeIds.has(item.asset_id));
}

function normalizeRow(row, index) {
  if (!row || typeof row !== "object") return null;
  const section = normalizeSection(row.section);
  const projection = normalizeProjection(row.projection, section);
  const assetId = safeToken(row.asset_id || row.assetId, 120);
  const normalized = {
    id: safeToken(row.id, 80) || `kc_${index + 1}`,
    section,
    text: compactText(row.text, 700),
    enabled: row.enabled !== false,
    order: normalizeOrder(row.order, index),
    projection,
  };
  if (assetId) normalized.asset_id = assetId;
  const label = compactText(row.label, 120);
  const note = compactText(row.note, 240);
  if (label) normalized.label = label;
  if (note) normalized.note = note;
  return normalized;
}

function normalizeSection(value) {
  const section = String(value || "").trim();
  return VALID_SECTION_SET.has(section) ? section : "local_reference";
}

function normalizeProjection(value, section) {
  if (!PROVIDER_SECTION_SET.has(section)) return "audit_only";
  return value === "audit_only" ? "audit_only" : "provider";
}

function normalizeOrder(value, fallback) {
  const order = Number(value);
  return Number.isFinite(order) ? Math.max(0, Math.min(9999, Math.round(order))) : fallback;
}

function compactText(value, limit) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function safeToken(value, limit) {
  const text = String(value || "").trim();
  if (!text || containsUnsafeText(text)) return "";
  return text.replace(/[^0-9A-Za-z_.:-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, limit);
}

function compareRowOrder(left, right) {
  return left.order - right.order || left.id.localeCompare(right.id);
}

function touchConstraints(constraints, options) {
  return normalizeKeyframeConstraints({
    ...constraints,
    updated_at: timestamp(options),
    rows: constraints.rows,
  }, options);
}

function timestamp(options = {}) {
  if (typeof options.now === "function") return String(options.now());
  return new Date().toISOString();
}

function normalizeAssetExclusions(values) {
  const result = [];
  const seen = new Set();
  for (const item of Array.isArray(values) ? values : []) {
    const assetId = safeToken(item?.asset_id || item?.assetId || item, 120);
    if (!assetId || seen.has(assetId)) continue;
    seen.add(assetId);
    result.push({
      asset_id: assetId,
      reason: compactText(item?.reason || "one_run_asset_exclusion", 120) || "one_run_asset_exclusion",
    });
  }
  return result;
}
