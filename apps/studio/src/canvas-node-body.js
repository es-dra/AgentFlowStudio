import { assetsFromNode, carryChainItems, assetCarryLabel, assetCarryState, assetLabel, assetTypeLabel } from "./asset-reference-summary.js";
import { directorSummary, normalizeDirectorSetup } from "./director-data.js";
import { icon } from "./icons.js";
import { bindAssetMentionSuggestions } from "./mention-suggestions.js";
import { canRunNodeGeneration } from "./node-actions.js";
import { generationStatusCard } from "./generation-status-view.js";
import { candidatePreviewsFromNode } from "./node-candidate-previews.js";
import { bundleSummary, resultView } from "./node-result-view.js";
import { studioStatusLabel } from "./studio-entity-status-vocabulary.js";

export function buildNodeBody(node, def, store = null) {
  const out = [];
  if (node.collapsed) return out;
  const carry = carryChainView(node);
  if (carry) out.push(carry);
  if (node.type === "director") return withCreativeRuntimeContract(node, directorBody(node, def));
  if (node.status === "generating") return withCreativeRuntimeContract(node, generationBody(node));
  if (node.status === "cancelled") return withCreativeRuntimeContract(node, cancelledBody(node));
  if (node.status === "partial") return withCreativeRuntimeContract(node, partialBody(node));
  if (node.type === "image" && node.status === "complete" && node.previewUrl) {
    return withCreativeRuntimeContract(node, completeBody(node));
  }
  if (node.status === "complete" && node.result) return withCreativeRuntimeContract(node, completeBody(node));
  if (node.status === "error") return withCreativeRuntimeContract(node, errorBody(node));
  if (node.content) {
    out.push(contentBlock(node, store));
    return withCreativeRuntimeContract(node, out);
  }
  return withCreativeRuntimeContract(node, emptyBody(node, def));
}

export function candidatePreviews(node) {
  return candidatePreviewsFromNode(node);
}

export function generationProgress(node) {
  const value = node.params?.progressPercent ?? node.params?.jobProgress?.percent ?? node.params?.terminalProgress?.percent;
  const mode = String(node.params?.jobProgress?.mode || "");
  const percent = Number(value);
  if (!Number.isFinite(percent)) {
    return {
      percent: null,
      mode,
      status: node.params?.jobProgress?.status || "",
      label: node.params?.jobProgress?.label || "正在生成",
      hint: node.params?.jobProgress?.hint || "请保持页面打开，完成后会显示预览",
    };
  }
  return {
    percent: Math.max(0, Math.min(100, Math.round(percent))),
    mode,
    status: node.params?.jobProgress?.status || "",
    label: node.params?.jobProgress?.label || "正在生成",
    hint: node.params?.jobProgress?.hint || "请保持页面打开，完成后会显示预览",
  };
}

export function statusLabel(status) {
  return studioStatusLabel(status, "草稿");
}

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

export function nodeBodySignature(node) {
  const directorSig = node.params?.directorSetup ? directorSummary(normalizeDirectorSetup(node.params.directorSetup)) : "";
  return [
    node.status,
    node.content || "",
    node.result ? node.result.length : 0,
    node.previewUrl || "",
    node.params?.previewAspectRatio || "",
    candidatePreviews(node).map((item) => [
      item.candidate_id || "",
      item.status || item.state || "",
      item.url || item.preview_url || "",
    ].join(":")).join(","),
    generationProgress(node)?.percent ?? "",
    node.params?.visualAssets?.length || 0,
    node.params?.lastContextBundle?.included_assets?.length || 0,
    node.params?.lastCreativeRuntimeContractSummary?.contract_id || "",
    carryChainItems(node).map((asset) => `${asset.asset_id || asset.assetId || ""}:${assetCarryState(asset)}`).join(","),
    node.type,
    node.collapsed ? 1 : 0,
    directorSig,
    node.params?.appliedDownstreamCount || 0,
    node.params?.scriptExpansionState?.status || "",
  ].join("|");
}

function directorBody(node, def) {
  const out = [];
  const summary = directorSummary(normalizeDirectorSetup(node.params?.directorSetup));
  const applied = node.params?.appliedDownstreamCount
    ? ` / 已应用到 ${node.params.appliedDownstreamCount} 个相连节点`
    : "";
  out.push(iconBlock(def.icon));
  out.push(textBlock("node-empty-label", "布置机位、角色、灯光和道具，输出镜头生产包"));
  out.push(textBlock("director-node-summary", `${summary}${applied}`));
  const open = document.createElement("button");
  open.className = "director-open-btn";
  open.dataset.action = "open-director";
  open.textContent = "打开导演台";
  out.push(open);
  if (node.result) out.push(resultView(node));
  return out;
}

function generationBody(node) {
  const out = [generationProgressView(node)];
  out.push(generationStatusCard(node, { compact: true, refs: false }));
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
  if (node.type === "image" && node.previewUrl) return imageCompleteBody(node);
  const ok = document.createElement("div");
  ok.className = "node-status success";
  ok.innerHTML = `${icon("check", 13)}<span>complete · ready for review · not yet accepted</span>`;
  const bundle = bundleSummary(node);
  return bundle ? [ok, bundle, resultView(node)] : [ok, resultView(node)];
}

function imageCompleteBody(node) {
  return [resultView(node)];
}

function partialBody(node) {
  const out = [generationStatusCard(node)];
  const bundle = bundleSummary(node);
  if (bundle) out.push(bundle);
  if (node.result || node.previewUrl) out.push(resultView(node));
  return out;
}

function contentBlock(node, store) {
  const expanding = node.params?.scriptExpansionState?.status === "running";
  if (isEditableContentNode(node) && store) return editableContentBlock(node, store, expanding);
  const view = document.createElement("div");
  view.className = `text-content-view${expanding ? " content-shimmer" : ""}`;
  view.textContent = node.content;
  return view;
}

function withCreativeRuntimeContract(node, items) {
  const contract = creativeRuntimeContractSummary(node);
  return contract ? [...items, contract] : items;
}

function creativeRuntimeContractSummary(node) {
  const summary = node.params?.lastCreativeRuntimeContractSummary
    || node.params?.promptOptimizationState?.creative_runtime_contract_summary;
  if (!summary?.contract_id) return null;
  const provider = safeSummaryObject(summary.provider_context);
  const knowledge = safeSummaryObject(summary.knowledge_context);
  const assets = safeSummaryObject(summary.asset_context);
  const artifact = safeSummaryObject(summary.artifact);
  const box = document.createElement("details");
  box.className = "creative-runtime-contract-summary";

  const header = document.createElement("summary");
  const generationStarted = provider.provider_calls_started === true;
  header.innerHTML = [
    `<span>${icon("sparkles", 12)}</span>`,
    `<strong>本次制作依据</strong>`,
    `<small>${generationStarted ? "生成已开始" : "尚未开始生成"} · ${safeCount(knowledge.rule_count)} 条规则</small>`,
  ].join("");
  box.appendChild(header);

  const detail = document.createElement("div");
  detail.className = "creative-runtime-contract-detail";
  appendContractChip(detail, "生成状态", generationStarted ? "已开始" : "尚未开始");
  appendContractChip(detail, "制作规则", `${safeCount(knowledge.rule_count)} 条`);
  appendContractChip(detail, "参考素材", `${safeCount(assets.fixed_asset_count)} 个固定 / ${safeCount(assets.draft_asset_count)} 个草稿`);
  appendContractChip(detail, "待确认素材", `${safeCount(assets.unresolved_asset_count)} 个`);
  appendContractChip(detail, "产物记录", artifact.filename ? "已记录" : "尚未生成");
  appendContractChip(detail, "需人工确认", `${safeArray(summary.non_claims).length} 项`);
  box.appendChild(detail);

  return box;
}

function appendContractChip(parent, label, value) {
  const chip = document.createElement("span");
  chip.className = "creative-runtime-contract-chip";
  chip.textContent = `${label}：${value === 0 ? "0" : String(value || "未记录")}`;
  parent.appendChild(chip);
}

function safeSummaryObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function safeCount(value) {
  const count = Number(value);
  return Number.isFinite(count) ? Math.max(0, Math.round(count)) : 0;
}

function editableContentBlock(node, store, expanding) {
  const textarea = document.createElement("textarea");
  const assetCardEditor = node.params?.assetCardDraft ? " asset-card-content-editor" : "";
  textarea.className = `text-content-view node-content-editor${assetCardEditor}${expanding ? " content-shimmer" : ""}`;
  textarea.value = node.content || "";
  textarea.spellcheck = false;
  textarea.dataset.nodeId = node.id;
  textarea.addEventListener("input", () => {
    store.set((s) => {
      const target = s.nodes[node.id];
      if (!target) return;
      target.content = textarea.value;
      target.prompt = textarea.value;
      target.status = target.status === "empty" ? "complete" : target.status;
      if (target.params?.assetCardDraft) {
        target.params.assetCardDraft.user_edited_text = textarea.value;
        target.params.assetCardDraft.updated_by_user = true;
      }
    }, { history: false });
  });
  bindAssetMentionSuggestions(textarea, store, node.id);
  textarea.addEventListener("pointerdown", (event) => event.stopPropagation());
  textarea.addEventListener("wheel", (event) => event.stopPropagation(), { passive: true });
  return textarea;
}

function isEditableContentNode(node) {
  return node.type === "text" || node.type === "script" || Boolean(node.params?.assetCardDraft);
}

function errorBody(node) {
  const out = [generationStatusCard(node)];
  const err = document.createElement("div");
  err.className = "node-status error";
  const message = canRunNodeGeneration(node)
    ? "failed · retry failed items"
    : "处理失败，请检查该节点的专用操作或错误详情";
  err.innerHTML = `${icon("x", 13)}<span>${escapeHtml(message)}</span>`;
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
  const isIndeterminate = !progress || progress?.percent == null;
  status.className = `node-status generation-progress-layer${isIndeterminate ? " indeterminate" : ""}`;
  const percentLabel = isIndeterminate ? (progress?.mode === "queued" ? "排队中" : "生成中") : `${progress.percent}%`;
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
    chip.innerHTML = `<span class="carry-chain-icon">${icon(carryAssetIcon(item), 11)}</span><span>${escapeHtml(assetLabel(item))}</span>`;
    strip.appendChild(chip);
  }
  return strip;
}

function carryAssetIcon(item) {
  if (item.asset_type === "scene") return "image";
  if (item.asset_type === "character") return "user";
  return "bookmark";
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
