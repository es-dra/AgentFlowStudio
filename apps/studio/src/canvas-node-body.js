import { assetsFromNode, carryChainItems, assetCarryLabel, assetCarryState, assetLabel, assetTypeLabel } from "./asset-reference-summary.js";
import { directorSummary, normalizeDirectorSetup } from "./director-data.js";
import { icon } from "./icons.js";
import { bundleSummary, resultView } from "./node-result-view.js";

export function buildNodeBody(node, def) {
  const out = [];
  if (node.collapsed) return out;
  const carry = carryChainView(node);
  if (carry) out.push(carry);
  if (node.content) {
    const view = document.createElement("div");
    view.className = "text-content-view";
    view.textContent = node.content;
    out.push(view);
    return out;
  }
  if (node.type === "director") return directorBody(node, def);
  if (node.status === "generating") return generationBody(node);
  if (node.status === "cancelled") return cancelledBody(node);
  if (node.status === "complete" && node.result) return completeBody(node);
  if (node.status === "error") return errorBody(node);
  return emptyBody(node, def);
}

export function candidatePreviews(node) {
  const raw = node.params?.candidatePreviewUrls || node.params?.candidate_previews || node.params?.candidates || [];
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => (typeof item === "string" ? { url: item } : item))
    .filter((item) => item?.url || item?.preview_url);
}

export function generationProgress(node) {
  const value = node.params?.progressPercent ?? node.params?.jobProgress?.percent ?? node.params?.terminalProgress?.percent;
  const mode = String(node.params?.jobProgress?.mode || "");
  if (mode === "indeterminate") {
    return {
      percent: null,
      mode,
      label: node.params?.jobProgress?.label || "正在生成",
      hint: node.params?.jobProgress?.hint || "请保持页面打开，完成后会显示预览",
    };
  }
  const percent = Number(value);
  if (!Number.isFinite(percent)) return null;
  return {
    percent: Math.max(0, Math.min(100, Math.round(percent))),
    mode,
    label: node.params?.jobProgress?.label || "正在生成",
    hint: node.params?.jobProgress?.hint || "请保持页面打开，完成后会显示预览",
  };
}

export function statusLabel(status) {
  return {
    empty: "待生成",
    idle: "待生成",
    running: "生成中",
    generating: "生成中",
    pending: "排队中",
    complete: "已完成",
    error: "需检查",
    cancelled: "已取消",
  }[status] || "待生成";
}

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

export function nodeBodySignature(node) {
  const directorSig = node.params?.directorSetup ? directorSummary(normalizeDirectorSetup(node.params.directorSetup)) : "";
  return [
    node.status,
    node.content ? node.content.length : 0,
    node.result ? node.result.length : 0,
    node.previewUrl || "",
    node.params?.previewAspectRatio || "",
    candidatePreviews(node).map((item) => item.url || item.preview_url || "").join(","),
    generationProgress(node)?.percent ?? "",
    node.params?.visualAssets?.length || 0,
    node.params?.lastContextBundle?.included_assets?.length || 0,
    carryChainItems(node).map((asset) => `${asset.asset_id || asset.assetId || ""}:${assetCarryState(asset)}`).join(","),
    node.type,
    node.collapsed ? 1 : 0,
    directorSig,
    node.params?.appliedDownstreamCount || 0,
  ].join("|");
}

function directorBody(node, def) {
  const out = [];
  const summary = directorSummary(normalizeDirectorSetup(node.params?.directorSetup));
  const applied = node.params?.appliedDownstreamCount
    ? ` / 已应用到 ${node.params.appliedDownstreamCount} 个相连节点`
    : "";
  out.push(iconBlock(def.icon));
  out.push(textBlock("node-empty-label", "二维顶视图布置机位、人物、灯光和道具"));
  out.push(textBlock("director-node-summary", `${summary}${applied}`));
  const open = document.createElement("button");
  open.className = "director-open-btn";
  open.dataset.action = "open-director";
  open.textContent = "打开二维导演台";
  out.push(open);
  if (node.result) out.push(resultView(node));
  return out;
}

function generationBody(node) {
  const out = [generationProgressView(node)];
  if (node.result) out.push(resultView(node));
  return out;
}

function cancelledBody(node) {
  const out = [];
  const cancelled = document.createElement("div");
  cancelled.className = "node-status cancelled";
  cancelled.innerHTML = `${icon("x", 13)}<span>本地已取消</span>`;
  out.push(cancelled);
  if (node.result) out.push(resultView(node));
  return out;
}

function completeBody(node) {
  const ok = document.createElement("div");
  ok.className = "node-status success";
  ok.innerHTML = `${icon("check", 13)}<span>已完成</span>`;
  const bundle = bundleSummary(node);
  return bundle ? [ok, bundle, resultView(node)] : [ok, resultView(node)];
}

function errorBody(node) {
  const err = document.createElement("div");
  err.className = "node-status error";
  err.innerHTML = `${icon("x", 13)}<span>生成失败，可在节点菜单重试</span>`;
  const out = [];
  const bundle = bundleSummary(node);
  if (bundle) out.push(err, bundle);
  else out.push(err);
  if (node.result) out.push(resultView(node));
  return out;
}

function emptyBody(node, def) {
  const out = [iconBlock(def.icon)];
  if (def.intents.length && !["image", "video"].includes(node.type)) {
    out.push(textBlock("node-empty-label", "尝试:"));
    const list = document.createElement("div");
    list.className = "node-intents";
    for (const intent of def.intents) {
      const btn = document.createElement("button");
      btn.className = "node-intent";
      btn.dataset.action = "intent";
      btn.dataset.intent = intent.label;
      btn.innerHTML = `<span class="intent-icon">${icon(intent.icon, 13)}</span><span>${intent.label}</span>`;
      list.appendChild(btn);
    }
    out.push(list);
  }
  return out;
}

function generationProgressView(node) {
  const progress = generationProgress(node);
  const status = document.createElement("div");
  const isIndeterminate = !progress || progress?.mode === "indeterminate" || progress?.percent == null;
  status.className = `node-status generation-progress-layer${isIndeterminate ? " indeterminate" : ""}`;
  const percentLabel = isIndeterminate ? "生成中" : `${progress.percent}%`;
  status.innerHTML = [
    '<span class="spinner"></span>',
    `<span class="generation-progress-copy"><strong>${escapeHtml(progress?.label || "正在生成")}</strong><small>${escapeHtml(progress?.hint || "结果完成后会自动回到节点中")}</small></span>`,
    `<span class="generation-progress-percent">${escapeHtml(percentLabel)}</span>`,
    `<span class="generation-progress-track"><span style="width:${isIndeterminate ? 46 : progress.percent}%"></span></span>`,
  ].join("");
  return status;
}

function carryChainView(node) {
  const items = carryChainItems(node);
  if (!items.length) return null;
  const strip = document.createElement("div");
  strip.className = "carry-chain-strip";
  for (const item of items) {
    const state = assetCarryState(item);
    const chip = document.createElement("button");
    chip.className = `carry-chain-chip${state === "excluded" || state === "superseded" ? " invalid" : ""}`;
    chip.dataset.action = "asset-detail";
    chip.dataset.assetId = item.asset_id || item.assetId || "";
    chip.title = `${assetTypeLabel(item)} · ${assetLabel(item)} · ${assetCarryLabel(item)}`;
    chip.innerHTML = `<span class="carry-chain-icon">${icon(item.asset_type === "scene" ? "image" : "bookmark", 11)}</span><span>${escapeHtml(assetLabel(item))}</span>`;
    strip.appendChild(chip);
  }
  return strip;
}

function iconBlock(iconName) {
  const glyph = document.createElement("div");
  glyph.className = "node-glyph";
  glyph.innerHTML = icon(iconName, 38);
  return glyph;
}

function textBlock(className, text) {
  const div = document.createElement("div");
  div.className = className;
  div.textContent = text;
  return div;
}

export function hasNodeVisualAssets(node) {
  return assetsFromNode(node).length > 0;
}
