export function resultView(node) {
  const result = document.createElement("div");
  result.className = `node-result${node.previewUrl ? " has-preview" : ""}`;
  if (node.previewUrl) {
    const img = document.createElement("img");
    img.className = "node-preview-img";
    img.src = node.previewUrl;
    img.alt = "MiniMax generated keyframe";
    img.loading = "lazy";
    img.style.aspectRatio = previewAspectRatio(node);
    result.appendChild(img);
  }
  const text = document.createElement("div");
  text.className = "node-result-text";
  text.textContent = node.result;
  result.appendChild(text);
  return result;
}

export function bundleSummary(node) {
  const bundle = node.params?.lastContextBundle;
  if (!bundle) return null;
  const included = Array.isArray(bundle.included_assets) ? bundle.included_assets : [];
  const warnings = Array.isArray(bundle.warnings) ? bundle.warnings : [];
  const box = document.createElement("details");
  box.className = "context-bundle-summary";
  const summary = document.createElement("summary");
  summary.textContent = `本次携带 ${included.length} assets`;
  const detail = document.createElement("div");
  detail.textContent = [
    included.map((item) => `${item.label || item.asset_id} (${item.channel || "text"})`).join("; "),
    warnings.length ? `warnings: ${warnings.map((item) => item.warning_id).join(", ")}` : "",
  ].filter(Boolean).join("\n");
  box.append(summary, detail);
  return box;
}

function previewAspectRatio(node) {
  const value = String(node.params?.previewAspectRatio || node.params?.spec?.ratio || "9:16");
  return /^\d+:\d+$/.test(value) ? value.replace(":", " / ") : "9 / 16";
}
