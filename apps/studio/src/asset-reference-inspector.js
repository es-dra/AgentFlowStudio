export function buildAssetReferenceActions(source) {
  const bundle = source?.context_bundle || source || {};
  const warnings = Array.isArray(bundle.warnings) ? bundle.warnings : [];
  const available = Array.isArray(bundle.available_project_assets) ? bundle.available_project_assets : [];
  const excluded = Array.isArray(source?.excluded_assets) ? source.excluded_assets : [];
  const excludedByUser = new Set(
    excluded
      .filter((item) => ["temporary_asset_excluded_by_user", "user_excluded_from_preflight_confirmation"].includes(item.reason))
      .map((item) => String(item.asset_id || "")),
  );
  const warningActions = warnings
    .filter((item) => item.warning_id === "named_asset_not_connected")
    .map((item) => ({
      kind: "connect_named_asset",
      asset_id: String(item.asset_id || ""),
      label: item.label || item.asset_id,
      blocking: false,
      warning: item,
    }))
    .filter((item) => item.asset_id);
  const failClosedActions = available
    .filter((asset) => (
      asset?.label_matched
      && !asset.connected
      && !asset.injected
      && !excludedByUser.has(String(asset.asset_id || ""))
    ))
    .map((asset) => ({
      kind: "connect_named_asset",
      asset_id: String(asset.asset_id || ""),
      label: asset.label || asset.asset_id,
      blocking: true,
      warning: { warning_id: "named_asset_not_connected", ...asset },
    }))
    .filter((item) => item.asset_id);
  return dedupeActions([...failClosedActions, ...warningActions]);
}

function dedupeActions(actions) {
  const seen = new Set();
  const result = [];
  for (const action of actions) {
    const key = `${action.kind}:${action.asset_id}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(action);
  }
  return result;
}
