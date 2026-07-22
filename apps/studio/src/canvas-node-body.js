import { assetsFromNode, carryChainItems, assetCarryLabel, assetCarryState, assetLabel, assetTypeLabel } from "./asset-reference-summary.js";
import { directorSummary, normalizeDirectorSetup } from "./director-data.js";
import { icon } from "./icons.js";
import { bindAssetMentionSuggestions } from "./mention-suggestions.js";
import { canRunNodeGeneration } from "./node-actions.js";
import { generationStatusCard } from "./generation-status-view.js";
import { candidatePreviewsFromNode } from "./node-candidate-previews.js";
import { bundleSummary, resultView } from "./node-result-view.js";
import { studioStatusLabel } from "./studio-entity-status-vocabulary.js";
import { bindStableTextInputLifecycle } from "./stable-text-input.js";

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
  if (isEditableContentNode(node) && store) {
    out.push(editableContentBlock(node, store, false));
    const embedded = embeddedCreativeActionPanel(node);
    if (embedded) out.push(embedded);
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
    (node.params?.revisions || []).map((revision) => `${revision.revision_id || ""}:${(revision.after_text || "").length}`).join(","),
    node.params?.currentRevisionId || "",
    node.params?.scriptExpansionState?.status || "",
    embeddedActionSignature(node.params?.embeddedCreativeAction),
    node.params?.productionGraphProjection || "",
    node.params?.productionGraphLegacyProjection || "",
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
  ok.innerHTML = `${icon("check", 13)}<span>已就绪，可审阅；尚未代表人工确认</span>`;
  const bundle = bundleSummary(node);
  const revisionPanel = revisionHistoryPanel(node);
  const items = bundle ? [ok, bundle, resultView(node)] : [ok, resultView(node)];
  if (revisionPanel) items.push(revisionPanel);
  return items;
}

function imageCompleteBody(node) {
  return [resultView(node)];
}

function embeddedActionSignature(action) {
  if (!action) return "";
  const preview = action.preview || {};
  const shotPlan = preview.shot_plan || {};
  return [
    action.action_id || "",
    action.action_type || "",
    action.mode || "",
    action.status || "",
    action.message || "",
    preview.preview_id || "",
    (preview.revised_text || "").length,
    (preview.change_summary || []).join(","),
    shotPlan.total_shots || "",
    action.applied_revision_id || "",
  ].join(":");
}

function embeddedCreativeActionPanel(node) {
  const action = node.params?.embeddedCreativeAction;
  if (!action || action.status === "cancelled") return null;
  const panel = document.createElement("section");
  panel.className = `embedded-creative-action ${action.status || "idle"}`;
  panel.dataset.creativeAction = action.action_type || "script_revision";
  const title = action.action_type === "shot_breakdown" ? "节点内分镜预览" : "节点内优化预览";
  const head = document.createElement("header");
  head.className = "embedded-creative-head";
  head.innerHTML = [
    `<span>${icon(action.status === "running" ? "clock" : "sparkles", 12)}</span>`,
    `<strong>${escapeHtml(title)}</strong>`,
    `<small>${escapeHtml(creativeModeLabel(action.mode))} · 确认前不改动画布</small>`,
  ].join("");
  panel.appendChild(head);
  const message = document.createElement("p");
  message.className = "embedded-creative-message";
  message.textContent = action.message || "等待 AI 预览。";
  panel.appendChild(message);
  if (action.status === "running") panel.appendChild(progressStrip("正在生成可审查预览"));
  if (action.status === "needs_input") panel.appendChild(actionButtons(action, { clear: true }));
  if (action.status === "unavailable") panel.appendChild(actionButtons(action, { retry: true, clear: true }));
  if (action.status === "preview") {
    panel.appendChild(creativePreview(action));
    panel.appendChild(actionButtons(action, { apply: true, cancel: true, retry: true }));
  }
  if (action.status === "applied") panel.appendChild(actionButtons(action, { clear: true, undoHint: true }));
  return panel;
}

function progressStrip(label) {
  const strip = document.createElement("div");
  strip.className = "embedded-creative-progress";
  strip.innerHTML = `<span class="spinner"></span><span>${escapeHtml(label)}</span>`;
  return strip;
}

function creativePreview(action) {
  const preview = action.preview || {};
  const wrap = document.createElement("div");
  wrap.className = "embedded-creative-preview";
  const diff = document.createElement("div");
  diff.className = "embedded-creative-diff";
  diff.innerHTML = [
    `<div><strong>原文</strong><p>${escapeHtml(revisionExcerpt(action.source_text))}</p></div>`,
    `<div><strong>AI 预览</strong><textarea class="embedded-creative-preview-editor" aria-label="编辑 AI 预览">${escapeHtml(preview.revised_text || "")}</textarea></div>`,
  ].join("");
  wrap.appendChild(diff);
  if (Array.isArray(preview.change_summary) && preview.change_summary.length) {
    const list = document.createElement("ul");
    list.className = "embedded-creative-summary";
    preview.change_summary.slice(0, 5).forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    });
    wrap.appendChild(list);
  }
  if (preview.shot_plan) wrap.appendChild(shotPlanPreview(preview.shot_plan));
  if (preview.rationale) {
    const rationale = document.createElement("p");
    rationale.className = "embedded-creative-rationale";
    rationale.textContent = preview.rationale;
    wrap.appendChild(rationale);
  }
  const evidence = creativeEvidence(action);
  if (evidence) wrap.appendChild(evidence);
  return wrap;
}

function shotPlanPreview(plan) {
  const box = document.createElement("details");
  box.className = "embedded-shot-plan";
  box.open = true;
  const summary = document.createElement("summary");
  summary.textContent = `分镜草案：${Number(plan.total_shots || 0)} 镜头 · 约 ${Math.round(Number(plan.estimated_duration_sec || 0))} 秒`;
  box.appendChild(summary);
  const scenes = document.createElement("div");
  scenes.className = "embedded-shot-plan-scenes";
  (plan.scenes || []).slice(0, 4).forEach((scene) => {
    const section = document.createElement("section");
    section.innerHTML = `<strong>${escapeHtml(scene.title || "场景")}</strong><p>${escapeHtml(scene.purpose || "")}</p>`;
    const list = document.createElement("ol");
    (scene.shots || []).slice(0, 6).forEach((shot) => {
      const item = document.createElement("li");
      item.textContent = `${shot.title || "镜头"} · ${shot.shot_size || "景别待定"} · ${shot.camera_angle || "机位待定"} · ${shot.movement || "运动待定"} · ${shot.sound || "声音待定"}`;
      list.appendChild(item);
    });
    section.appendChild(list);
    scenes.appendChild(section);
  });
  box.appendChild(scenes);
  return box;
}

function creativeEvidence(action) {
  const lineage = action.provider_lineage || {};
  if (!lineage.provider_calls_started && !action.latency_ms) return null;
  const details = document.createElement("details");
  details.className = "embedded-creative-evidence";
  const summary = document.createElement("summary");
  summary.textContent = "高级证据";
  details.appendChild(summary);
  const dl = document.createElement("dl");
  for (const [label, value] of [
    ["能力", lineage.provider_calls_started ? "真实 LLM 预览" : "未调用"],
    ["模型面", lineage.model_surface || ""],
    ["请求", lineage.request_id || ""],
    ["耗时", action.latency_ms ? `${Math.round(Number(action.latency_ms))} ms` : ""],
    ["费用", `$${Number(action.cost_usd || 0).toFixed(4)}`],
    ["图变化", action.graph_mutation?.mutated ? "有变化" : "无变化"],
  ]) {
    if (!value) continue;
    dl.append(labelEl(label), valueEl(value));
  }
  details.appendChild(dl);
  return details;
}

function actionButtons(action, flags = {}) {
  const row = document.createElement("div");
  row.className = "embedded-creative-actions";
  if (flags.apply) row.appendChild(actionButton("embedded-creative-apply", "应用到当前节点", "studio-primary-button"));
  if (flags.cancel) row.appendChild(actionButton("embedded-creative-cancel", "取消", "studio-secondary-button"));
  if (flags.retry) {
    const retry = actionButton("embedded-creative-retry", "重新预览", "studio-secondary-button");
    retry.dataset.creativeAction = action.action_type || "script_revision";
    retry.dataset.creativeMode = action.mode || "";
    row.appendChild(retry);
  }
  if (flags.clear) row.appendChild(actionButton("embedded-creative-clear", "收起", "studio-text-button"));
  if (flags.undoHint) {
    const hint = document.createElement("small");
    hint.textContent = "本次应用已进入画布历史，可用撤销恢复。";
    row.appendChild(hint);
  }
  return row;
}

function actionButton(action, label, className) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.dataset.action = action;
  button.textContent = label;
  return button;
}

function labelEl(text) {
  const dt = document.createElement("dt");
  dt.textContent = text;
  return dt;
}

function valueEl(text) {
  const dd = document.createElement("dd");
  dd.textContent = String(text || "");
  return dd;
}

function creativeModeLabel(mode) {
  return {
    concise_polish: "简洁润色",
    professional_expansion: "专业扩写",
    structure_pace: "结构节奏",
    character_relationship: "人物关系",
    dialogue_action: "对白动作",
    visual_production: "视觉制作",
    dynamic_shot_breakdown: "动态拆分分镜",
  }[String(mode || "")] || "创作预览";
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
  if (isEditableContentNode(node) && store) {
    const out = document.createElement("div");
    out.className = "node-editable-stack";
    out.appendChild(editableContentBlock(node, store, expanding));
    const embedded = embeddedCreativeActionPanel(node);
    if (embedded) out.appendChild(embedded);
    const revisions = revisionHistoryPanel(node);
    if (revisions) out.appendChild(revisions);
    return out;
  }
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
  textarea.placeholder = node.type === "script" ? "输入剧本、分镜或制作说明" : "输入想法、剧本文字或参考说明";
  textarea.spellcheck = false;
  textarea.dataset.nodeId = node.id;
  textarea.addEventListener("focus", () => {
    store.set((s) => {
      if (!s.nodes[node.id]) return;
      s.selection = { nodeIds: [node.id], edgeId: null };
    }, { history: false, persist: false, renderScope: "canvas-local-edit" });
  });
  bindStableTextInputLifecycle(textarea, () => persistEditorValue(textarea, node, store));
  bindAssetMentionSuggestions(textarea, store, node.id);
  return textarea;
}

function isEditableContentNode(node) {
  if (node.params?.scriptCoreProjection) return false;
  if (node.params?.productionPlanProjection) return false;
  if (node.params?.productionGraphProjection || node.params?.productionGraphLegacyProjection) return false;
  return node.type === "text" || node.type === "script" || Boolean(node.params?.assetCardDraft);
}

function persistEditorValue(textarea, node, store) {
  store.set((s) => {
    const target = s.nodes[node.id];
    if (!target) return;
    const text = textarea.value;
    target.content = text;
    target.prompt = text;
    target.status = text.trim() ? "draft" : "empty";
    if (target.params?.assetCardDraft) {
      target.params.assetCardDraft.user_edited_text = text;
      target.params.assetCardDraft.updated_by_user = true;
    }
  }, { history: false, renderScope: "canvas-local-edit" });
}

function revisionHistoryPanel(node) {
  const revisions = Array.isArray(node.params?.revisions) ? node.params.revisions : [];
  if (!revisions.length) return null;
  const latest = revisions[revisions.length - 1] || {};
  const panel = document.createElement("details");
  panel.className = "node-revision-history";
  panel.open = false;
  const summary = document.createElement("summary");
  summary.innerHTML = [
    `${icon("retry", 12)}`,
    `<span>节点内修订 ${revisions.length} 次</span>`,
    `<small>同一节点身份，可撤销</small>`,
  ].join("");
  panel.appendChild(summary);

  const before = revisionExcerpt(latest.before_text);
  const after = revisionExcerpt(latest.after_text);
  const body = document.createElement("div");
  body.className = "node-revision-body";
  body.innerHTML = [
    `<div><strong>修订前</strong><p>${escapeHtml(before || "无可显示内容")}</p></div>`,
    `<div><strong>修订后</strong><p>${escapeHtml(after || "无可显示内容")}</p></div>`,
  ].join("");
  panel.appendChild(body);
  return panel;
}

function revisionExcerpt(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 180);
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
  if (node.type === "text" || node.type === "script") out.push(textBlock("node-empty-label", "输入故事、剧本或制作说明后，可从节点工具条默认优化。"));
  else out.push(textBlock("node-empty-label", def.upload ? "上传或连接参考后继续。" : "选择该节点后查看可用动作。"));
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
