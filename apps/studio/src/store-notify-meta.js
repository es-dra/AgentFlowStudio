export function emptyNotifyMeta() {
  return { full: false, renderScopes: [] };
}

export function mergeNotifyMeta(current, options = {}) {
  const next = {
    full: Boolean(current?.full),
    renderScopes: Array.isArray(current?.renderScopes) ? [...current.renderScopes] : [],
  };
  const scope = typeof options.renderScope === "string" ? options.renderScope : "";
  if (scope) {
    if (!next.renderScopes.includes(scope)) next.renderScopes.push(scope);
  } else {
    next.full = true;
  }
  return next;
}
