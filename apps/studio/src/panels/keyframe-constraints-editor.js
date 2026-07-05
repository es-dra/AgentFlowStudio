import { icon } from "../icons.js";
import { el } from "../overlay.js";
import {
  addKeyframeConstraintRow,
  fixedAssetExclusionRows,
  KEYFRAME_CONSTRAINT_SECTIONS,
  moveKeyframeConstraintRow,
  normalizeKeyframeConstraints,
  removeKeyframeConstraintRow,
  sectionLabel,
  syncTemporaryAssetExclusionsFromKeyframeConstraints,
  toggleKeyframeConstraintRow,
  updateKeyframeConstraintRow,
} from "../keyframe-constraints.js";

export function createKeyframeConstraintsEditor(node) {
  let constraints = normalizeKeyframeConstraints(node?.params?.keyframeConstraints);
  const wrap = el("section", "keyframe-constraints-editor");

  function render() {
    wrap.replaceChildren();
    wrap.append(header(constraints));
    wrap.append(toolbar());
    const fixed = fixedAssetPicker(node, constraints, setConstraints);
    if (fixed) wrap.append(fixed);
    const list = el("div", "keyframe-constraints-list");
    if (!constraints.rows.length) {
      list.appendChild(el("div", "keyframe-constraints-empty", "No constraints yet."));
    } else {
      constraints.rows.forEach((row, index) => list.appendChild(rowEditor(row, index)));
    }
    wrap.appendChild(list);
  }

  function setConstraints(next) {
    constraints = normalizeKeyframeConstraints(next);
    render();
  }

  function mutateText(rowId, patch) {
    constraints = updateKeyframeConstraintRow(constraints, rowId, patch);
  }

  function rowEditor(row, index) {
    const item = el("div", `keyframe-constraint-row ${row.enabled ? "enabled" : "disabled"}`);
    const top = el("div", "keyframe-constraint-row-top");
    const enabled = document.createElement("input");
    enabled.type = "checkbox";
    enabled.checked = row.enabled;
    enabled.title = "Enable row";
    enabled.addEventListener("change", () => setConstraints(toggleKeyframeConstraintRow(constraints, row.id, enabled.checked)));

    const section = document.createElement("select");
    for (const value of KEYFRAME_CONSTRAINT_SECTIONS) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = sectionLabel(value);
      section.appendChild(option);
    }
    section.value = row.section;
    section.addEventListener("change", () => setConstraints(updateKeyframeConstraintRow(constraints, row.id, { section: section.value })));

    const projection = document.createElement("select");
    for (const value of ["provider", "audit_only"]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value === "provider" ? "Provider" : "Audit";
      projection.appendChild(option);
    }
    projection.value = row.projection;
    projection.disabled = ["fixed_asset", "local_reference"].includes(row.section);
    projection.addEventListener("change", () => setConstraints(updateKeyframeConstraintRow(constraints, row.id, { projection: projection.value })));

    const up = iconButton("chevronUp", "Move up");
    up.disabled = index === 0;
    up.addEventListener("click", () => setConstraints(moveKeyframeConstraintRow(constraints, row.id, -1)));
    const down = iconButton("chevronDown", "Move down");
    down.disabled = index === constraints.rows.length - 1;
    down.addEventListener("click", () => setConstraints(moveKeyframeConstraintRow(constraints, row.id, 1)));
    const remove = iconButton("trash", "Remove");
    remove.addEventListener("click", () => setConstraints(removeKeyframeConstraintRow(constraints, row.id)));

    top.append(enabled, section, projection, up, down, remove);
    item.appendChild(top);

    const text = document.createElement("textarea");
    text.rows = 2;
    text.value = row.text || "";
    text.placeholder = row.section === "fixed_asset" ? "One-run fixed asset exclusion note" : "Constraint text";
    text.addEventListener("input", () => mutateText(row.id, { text: text.value }));
    item.appendChild(text);

    if (row.section === "fixed_asset" || row.section === "local_reference") {
      const meta = el("div", "keyframe-constraint-meta");
      const assetId = document.createElement("input");
      assetId.value = row.asset_id || "";
      assetId.placeholder = "asset_id";
      assetId.addEventListener("input", () => mutateText(row.id, { asset_id: assetId.value }));
      const label = document.createElement("input");
      label.value = row.label || "";
      label.placeholder = "label";
      label.addEventListener("input", () => mutateText(row.id, { label: label.value }));
      meta.append(assetId, label);
      item.appendChild(meta);
    }

    return item;
  }

  function toolbar() {
    const bar = el("div", "keyframe-constraints-toolbar");
    const addProvider = el("button", "ghost-btn", "Add constraint");
    addProvider.innerHTML = `${icon("plus", 13)}<span>Add constraint</span>`;
    addProvider.addEventListener("click", () => setConstraints(addKeyframeConstraintRow(constraints, { section: "character" })));
    const addLocal = el("button", "ghost-btn", "Add local ref");
    addLocal.innerHTML = `${icon("plus", 13)}<span>Add local ref</span>`;
    addLocal.addEventListener("click", () => setConstraints(addKeyframeConstraintRow(constraints, {
      section: "local_reference",
      projection: "audit_only",
    })));
    bar.append(addProvider, addLocal);
    return bar;
  }

  render();
  return {
    wrap,
    value: () => normalizeKeyframeConstraints(constraints),
    applyToNode(target) {
      if (!target) return null;
      target.params = target.params || {};
      target.params.keyframeConstraints = normalizeKeyframeConstraints(constraints);
      target.params.temporaryAssetExclusions = syncTemporaryAssetExclusionsFromKeyframeConstraints(target);
      return target.params.keyframeConstraints;
    },
  };
}

function header(constraints) {
  const head = el("div", "keyframe-constraints-head");
  const activeRows = constraints.rows.filter((row) => row.enabled && row.projection === "provider").length;
  const fixedRows = fixedAssetExclusionRows(constraints).length;
  head.appendChild(el("strong", "", "Keyframe constraints"));
  head.appendChild(el("small", "", `${activeRows} provider rows / ${fixedRows} one-run exclusions`));
  return head;
}

function fixedAssetPicker(node, constraints, setConstraints) {
  const assets = fixedVisualAssets(node);
  if (!assets.length) return null;
  const active = new Set(fixedAssetExclusionRows(constraints).map((row) => row.asset_id));
  const wrap = el("div", "keyframe-fixed-assets");
  for (const asset of assets) {
    const row = el("label", "keyframe-fixed-asset-row");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = active.has(asset.asset_id);
    input.addEventListener("change", () => {
      setConstraints(upsertFixedAssetExclusion(constraints, asset, input.checked));
    });
    row.append(input, el("span", "", asset.label || asset.asset_id), el("small", "", asset.asset_id));
    wrap.appendChild(row);
  }
  return wrap;
}

function upsertFixedAssetExclusion(constraints, asset, enabled) {
  const current = normalizeKeyframeConstraints(constraints);
  const existing = current.rows.find((row) => row.section === "fixed_asset" && row.asset_id === asset.asset_id);
  if (existing) {
    return updateKeyframeConstraintRow(current, existing.id, { enabled });
  }
  return addKeyframeConstraintRow(current, {
    section: "fixed_asset",
    projection: "audit_only",
    enabled,
    asset_id: asset.asset_id,
    label: asset.label,
    text: `Exclude fixed asset ${asset.label || asset.asset_id} for the next run`,
  });
}

function fixedVisualAssets(node) {
  const values = Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : [];
  const result = [];
  const seen = new Set();
  for (const asset of values) {
    const assetId = String(asset?.asset_id || asset?.assetId || asset?.visual_asset_id || "").trim();
    if (!assetId || seen.has(assetId)) continue;
    const status = String(asset?.status || "").trim();
    if (status && !["fixed", "ready"].includes(status)) continue;
    seen.add(assetId);
    result.push({ asset_id: assetId, label: String(asset?.label || asset?.title || "").trim() });
  }
  return result;
}

function iconButton(name, title) {
  const button = el("button", "icon-btn");
  button.type = "button";
  button.title = title;
  button.innerHTML = icon(name, 13);
  return button;
}
