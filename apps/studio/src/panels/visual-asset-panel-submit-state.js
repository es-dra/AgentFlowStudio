export function collectFieldValues(root) {
  const card = {};
  for (const input of root.querySelectorAll("[data-card]")) {
    const value = String(input.value || "").trim();
    if (value) card[input.dataset.card] = value;
  }
  return {
    label: field(root, "label"),
    signature: field(root, "signature"),
    locks: String(root.querySelector('[data-field="negative_locks"]')?.value || ""),
    card,
    reuseIntent: String(root.querySelector('input[name="visual-asset-reuse-intent"]:checked')?.value || ""),
    existingAssetId: String(root.querySelector('input[name="visual-asset-reuse-intent"]:checked')?.dataset?.existingAssetId || ""),
  };
}

export function compactCard(card) {
  const result = {};
  for (const [key, value] of Object.entries(card || {})) {
    if (String(value || "").trim()) result[key] = String(value).trim();
  }
  return result;
}

export function mergeVisualAssets(existing, asset, supersedesAssetId = "") {
  const assetId = String(asset?.asset_id || "").trim();
  if (!assetId) return existing;
  return [
    ...existing.filter((item) => {
      const current = String(item?.asset_id || "").trim();
      return current !== assetId && current !== supersedesAssetId;
    }),
    asset,
  ].slice(-8);
}

function field(root, name, attr = "data-field") {
  return String(root.querySelector(`[${attr}="${name}"]`)?.value || "").trim();
}
