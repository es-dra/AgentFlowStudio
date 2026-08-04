import { NODE_TYPES } from "../nodes.js";
import { icon } from "../icons.js";
import { el } from "../overlay.js";
import { assetsFromNode } from "../asset-reference-summary.js";
import { blockedReasonForNode, nextActionForNode, statusLineForNode } from "../generation-status-view.js";
import { keyframeSourceEvidenceTraceSummaryText } from "../keyframe-source-evidence-trace.js";
import { studioStatusLabel } from "../studio-entity-status-vocabulary.js";
import { SCRIPT_CANDIDATE_EXTRACTION_EVENT, SCRIPT_CANDIDATE_REVIEW_EVENT } from "../script-candidate-review.js";
import { algorithmConsoleSection, projectPipelineSection } from "./algorithm-context-panel.js";
import {
  nodeAssetDecisionText,
  nodeContextSummaryText,
  projectAssetDecisionText,
  projectReferenceSummaryText,
} from "./inspector-context-summary.js";

export function renderInspectorPanel(state, store) {
  const panel = document.getElementById("inspector");
  if (!panel) return;
  const nodeId = state.selection.nodeIds.length === 1 ? state.selection.nodeIds[0] : "";
  const node = nodeId ? state.nodes[nodeId] : null;
  const signature = inspectorSignature(state, node);
  if (panel.dataset.signature === signature) return;
  panel.dataset.signature = signature;
  panel.className = inspectorPanelClass(state, node);
  panel.replaceChildren();
  panel.appendChild(inspectorCollapseToggle(state, store));
  if (state.ui.inspectorOpen === false) return;
  if (!node) {
    renderEmptyInspector(state, store, panel);
    return;
  }
  renderNodeInspector(panel, node, store);
}

function renderEmptyInspector(state, store, panel) {
  panel.appendChild(panelHead("panel", "创作助手", "下一步"));
  panel.appendChild(emptyGuide(state));
  panel.appendChild(projectReferenceSummary(state));
  panel.appendChild(drawerLinks(store));
  panel.appendChild(detailsSection("资产确认状态", projectAssetDecisionText(state), "资产"));
  panel.appendChild(projectPipelineSection(state));
}

function renderNodeInspector(panel, node, store) {
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  panel.appendChild(panelHead(def.icon, node.title, def.label));
  panel.appendChild(section("下一步行动", nodeActionBrief(node), "primary"));
  panel.appendChild(inspectorActions(nodeActions(node, store)));
  if (node.params?.coreAssetTruth) panel.appendChild(analysisAssetReviewPanel(node));
  panel.appendChild(section("本次参考摘要", nodeContextSummaryText(node)));
  panel.appendChild(drawerLinks(store));
  panel.appendChild(detailsSection("资产确认状态", nodeAssetDecisionText(node), "资产"));
  panel.appendChild(detailsSection("节点草稿", node.prompt || node.content || "还没有填写创作内容。", "内容"));
  panel.appendChild(algorithmConsoleSection(node));
  panel.appendChild(detailsSection("输出记录", recordSummary(node), "记录"));
}

function panelHead(iconName, title, meta) {
  const head = el("div", "inspector-head");
  head.innerHTML = `<span>${icon(iconName, 14)}</span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(meta)}</small>`;
  return head;
}

function inspectorCollapseToggle(state, store) {
  const button = el("button", "inspector-collapse-toggle");
  button.type = "button";
  const isOpen = state.ui.inspectorOpen !== false;
  button.title = isOpen ? "收起右侧状态栏" : "展开右侧状态栏";
  button.innerHTML = `${icon(isOpen ? "shrink" : "panel", 13)}<span>${isOpen ? "收起" : "状态"}</span>`;
  button.addEventListener("click", () => store.set((s) => {
    s.ui.inspectorOpen = s.ui.inspectorOpen === false;
  }, { history: false, persist: false }));
  return button;
}

function emptyGuide(state) {
  const wrap = el("section", "inspector-section inspector-focus");
  const hasNodes = state.order.length > 0;
  wrap.appendChild(el("h3", "", hasNodes ? "选择一个节点继续" : "从画布开始"));
  wrap.appendChild(el("p", "", hasNodes
    ? "点击画布中的节点，优先决定是继续创作、保存素材，还是查看本次参考。"
    : "选择一个创作起点，先写清本轮意图；系统会在生成前整理上下文和已确认素材。"));
  const line = el("div", "inspector-quiet-line");
  line.appendChild(metaPill("节点", state.order.length));
  line.appendChild(metaPill("素材", state.assets.length));
  line.appendChild(metaPill("连线", Object.keys(state.edges || {}).length));
  wrap.appendChild(line);
  return wrap;
}

function nodeActionBrief(node) {
  const truth = node.params?.coreAssetTruth;
  if (truth) {
    const evidenceCount = Array.isArray(truth.evidence_spans) ? truth.evidence_spans.length : 0;
    return [
      `候选状态：${coreAssetStatusLabel(truth.status)}`,
      `证据性质：${evidenceStatusLabel(truth.evidence_status)}`,
      `来源证据：${evidenceCount} 处`,
      ["candidate", "modified"].includes(truth.status)
        ? "核对名称和来源后确认或拒绝；只有确认结果会进入 Production Graph。"
        : truth.status === "expired"
          ? "源剧本已更新，此候选不能继续审阅。"
          : "该候选的审阅决定已保存。",
    ].join("\n");
  }
  if (node.params?.scriptRevision && node.params?.scriptCoreProjection) {
    const extraction = node.params?.scriptCandidateExtraction || {};
    return extraction.error
      ? `候选提取未完成：${extraction.error}\n原始剧本未改变，可以重试。`
      : extraction.message || "从当前剧本提取有原文依据的人物和场景，再逐项人工确认。";
  }
  const model = node.params?.model || "未选择模型";
  const assetCount = assetsFromNode(node).length;
  const blockedReason = blockedReasonForNode(node);
  return [
    `${statusLineForNode(node)} · ${model} · ${assetCount} 个素材`,
    blockedReason ? `Blocked reason: ${blockedReason}` : "",
    nextActionForNode(node),
    nextStepText(node),
  ].filter(Boolean).join("\n");
}

function metaPill(label, value) {
  const item = el("span", "inspector-meta-pill");
  item.innerHTML = `<small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong>`;
  return item;
}

function inspectorActions(actions) {
  const row = el("div", "inspector-actions");
  for (const [label, iconName, onClick, tone = "", disabled = false] of actions) {
    const button = el("button", `inspector-action${tone ? ` ${tone}` : ""}`);
    button.type = "button";
    button.innerHTML = `${icon(iconName, 13)}<span>${escapeHtml(label)}</span>`;
    button.disabled = disabled;
    button.addEventListener("click", onClick);
    row.appendChild(button);
  }
  return row;
}

function nodeActions(node, store) {
  const truth = node.params?.coreAssetTruth;
  if (truth) {
    if (!["candidate", "modified"].includes(truth.status)) return [];
    const busy = Boolean(node.params?.coreAssetReview?.busy);
    return [
      ["确认", "check", () => dispatchScriptReview(node, "confirm"), "primary", busy],
      ["拒绝", "x", () => dispatchScriptReview(node, "reject"), "", busy],
    ];
  }
  if (node.params?.scriptRevision && node.params?.scriptCoreProjection) {
    const busy = Boolean(node.params?.scriptCandidateExtraction?.busy);
    return [["提取候选", "sparkles", () => dispatchScriptExtraction(node), "primary", busy]];
  }
  const retry = ["error", "partial"].includes(node.status)
    ? [["Retry failed items", "retry", () => dispatchNodeEvent("afs:studio-open-generation-panel", node), "primary"]]
    : [];
  const base = [
    ...retry,
    ["继续创作", "play", () => dispatchNodeEvent("afs:studio-open-generation-panel", node), retry.length ? "" : "primary"],
    ["保存素材", "bookmark", () => dispatchNodeEvent("afs:studio-fix-visual-asset", node)],
    ["看过程", "layers", () => dispatchNodeEvent("afs:studio-open-creation-process", node)],
  ];
  if (node.type === "video") {
    base.push(["整理卡片", "frames", () => dispatchNodeEvent("afs:video-asset-card-draft", node)]);
  }
  return base;
}

function analysisAssetReviewPanel(node) {
  const truth = node.params.coreAssetTruth;
  const review = node.params?.coreAssetReview || {};
  const wrap = el("section", "inspector-section analysis-asset-review");
  wrap.appendChild(el("h3", "", "候选审阅"));
  const evidence = (Array.isArray(truth.evidence_spans) ? truth.evidence_spans : [])
    .map((item) => String(item?.quote || "").trim())
    .filter(Boolean);
  wrap.appendChild(el("p", "analysis-asset-evidence", evidence.length ? `来源：${evidence.join(" / ")}` : "没有可核对的来源证据。"));
  wrap.appendChild(el("p", "analysis-asset-evidence-kind", `证据性质：${evidenceStatusLabel(truth.evidence_status)}`));
  const editable = ["candidate", "modified"].includes(truth.status);
  const label = el("label", "analysis-asset-label", "名称");
  const input = el("input", "analysis-asset-input");
  input.type = "text";
  input.maxLength = 120;
  input.value = String(truth.display_name || node.title || "");
  input.disabled = !editable || Boolean(review.busy);
  label.appendChild(input);
  wrap.appendChild(label);
  if (editable) {
    const save = el("button", "inspector-action analysis-asset-save");
    save.type = "button";
    save.disabled = Boolean(review.busy);
    save.innerHTML = `${icon("pencil", 13)}<span>保存修改</span>`;
    save.addEventListener("click", () => dispatchScriptReview(node, "edit", input.value));
    wrap.appendChild(save);
  }
  const status = el("p", "analysis-asset-review-status", review.error || review.message || coreAssetStatusLabel(truth.status));
  status.setAttribute("aria-live", "polite");
  if (review.error) status.dataset.state = "error";
  wrap.appendChild(status);
  return wrap;
}

function dispatchScriptReview(node, action, label = "") {
  window.dispatchEvent(new CustomEvent(SCRIPT_CANDIDATE_REVIEW_EVENT, {
    detail: { action, label, node_id: node.id, node },
  }));
}

function dispatchScriptExtraction(node) {
  window.dispatchEvent(new CustomEvent(SCRIPT_CANDIDATE_EXTRACTION_EVENT, {
    detail: { node_id: node.id, node },
  }));
}

function coreAssetStatusLabel(value) {
  return {
    candidate: "待审阅",
    modified: "已修改，待审阅",
    confirmed: "已确认",
    rejected: "已拒绝",
    expired: "已过期",
  }[String(value || "")] || "待审阅";
}

function evidenceStatusLabel(value) {
  return {
    extracted_from_text: "原文直接提取",
    model_inferred: "模型推断，需人工核对",
    conflicting: "证据冲突，需人工处理",
  }[String(value || "")] || "来源待核对";
}

function dispatchNodeEvent(eventName, node) {
  window.dispatchEvent(new CustomEvent(eventName, { detail: { node_id: node.id, node } }));
}

function openDrawerTab(store, tab) {
  if (!store) return;
  store.set((s) => {
    s.ui.drawerOpen = true;
    s.ui.drawerTab = tab;
  }, { history: false, persist: false });
}

function section(title, text, tone = "") {
  const wrap = el("section", `inspector-section${tone ? ` ${tone}` : ""}`);
  wrap.appendChild(el("h3", "", title));
  const value = el("pre", "", String(text || "暂无内容"));
  wrap.appendChild(value);
  return wrap;
}

function detailsSection(title, text, tag = "详情") {
  const details = el("details", "inspector-section inspector-disclosure");
  const summary = el("summary", "inspector-disclosure-summary");
  summary.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(tag)}</span>`;
  details.appendChild(summary);
  const value = el("pre", "", String(text || "暂无内容"));
  details.appendChild(value);
  return details;
}

function drawerLinks(store) {
  const wrap = el("section", "inspector-drawer-links");
  wrap.appendChild(el("h3", "", "更多面板"));
  wrap.appendChild(inspectorActions([
    ["素材库", "folder", () => openDrawerTab(store, "assets")],
    ["生成进度", "clock", () => openDrawerTab(store, "jobs")],
    ["作品库", "frames", () => openDrawerTab(store, "history")],
  ]));
  return wrap;
}

function projectReferenceSummary(state) {
  return section("本次参考摘要", projectReferenceSummaryText(state));
}

function nextStepText(node) {
  if (node.status === "generating") return "等待生成完成；如果是视频节点，可以继续刷新进度。";
  if (node.status === "partial") return "partial result 已保留；默认只重试失败项，成功输出继续保留。";
  if (node.status === "error") return "检查 blocked reason 后重试失败项，或先打开生成面板调整描述。";
  if (node.previewUrl || node.result) return "结果已经出现，可以继续生成、保存为素材，或打开过程查看引用与输出。";
  if (node.type === "script") return "补充故事设定后继续生成分镜和关键帧。";
  if (node.type === "director") return "打开导演台，先把角色、机位、灯光、道具和镜头生产包摆清楚。";
  if (node.type === "image") return "填写画面描述或接入参考图，然后生成首帧。";
  if (node.type === "video") return "确认首帧和动作描述后生成视频；完成后再整理成视频素材卡。";
  return "补充内容后继续连接下游节点。";
}

function recordSummary(node) {
  const parts = [manifestSummary(node), jobSummary(node), statusRefSummary(node), keyframeEvidenceTraceSummary(node), assetSummary(node)].filter(Boolean);
  return parts.length ? parts.join("\n\n") : "还没有生成记录。";
}

function statusRefSummary(node) {
  const refs = node.params?.generationSafeRefs;
  if (!Array.isArray(refs) || !refs.length) return "";
  return `安全引用：${refs.map((ref) => `${ref.label}:${ref.value}`).join(" / ")}`;
}

function keyframeEvidenceTraceSummary(node) {
  return keyframeSourceEvidenceTraceSummaryText(node.params?.lastKeyframeSourceEvidenceTrace);
}

function manifestSummary(node) {
  const manifest = node.params?.lastSafeManifest || node.params?.lastGenerationManifest || {};
  const status = manifest.status || node.params?.lastVideoAssetCardDraftStatus || "";
  if (!status && !Object.keys(manifest).length) return "";
  return [
    status ? `状态：${statusText(status)}` : "",
    manifest.provider_service_id ? `能力：${providerLabel(manifest.provider_service_id)}` : "",
    manifest.artifact_id ? `输出编号：${manifest.artifact_id}` : "",
  ].filter(Boolean).join("\n") || "已有生成摘要。";
}

function jobSummary(node) {
  return [
    node.params?.lastKeyframeJobId ? `关键帧任务：${node.params.lastKeyframeJobId}` : "",
    node.params?.lastVideoJobId ? `视频任务：${node.params.lastVideoJobId}` : "",
    node.params?.lastVideoArtifactId ? `输出编号：${node.params.lastVideoArtifactId}` : "",
  ].filter(Boolean).join("\n");
}

function assetSummary(node) {
  const assets = assetsFromNode(node);
  if (!assets.length) return "还没有保存为角色或场景素材。";
  return `已保存素材：${assets.map((asset) => asset.label || asset.asset_id).join("、")}`;
}

function statusText(status) {
  return studioStatusLabel(status, "草稿");
}

function providerLabel(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("image")) return "图片生成";
  if (text.includes("video") || text.includes("i2v")) return "视频生成";
  if (text.includes("llm") || text.includes("prompt")) return "文案优化";
  if (text.includes("vision")) return "视觉识别";
  return "生成服务";
}

function inspectorSignature(state, node) {
  return [
    state.ui.inspectorOpen,
    state.selection.nodeIds.join(","),
    state.order.length,
    state.assets.length,
    Object.keys(state.edges || {}).length,
    node?.id || "",
    node?.title || "",
    node?.status || "",
    node?.prompt || "",
    node?.result || "",
    JSON.stringify(node?.params?.lastContextBundle || {}),
    JSON.stringify(node?.params?.keyframeLayer || {}),
    JSON.stringify(node?.params?.lastSafeManifest || node?.params?.lastGenerationManifest || {}),
    JSON.stringify(node?.params?.jobProgress || {}),
    JSON.stringify(node?.params?.coreAssetTruth || {}),
    JSON.stringify(node?.params?.coreAssetReview || {}),
    JSON.stringify(node?.params?.scriptCandidateExtraction || {}),
    node?.params?.lastOptimizedPromptPlain || "",
    node?.params?.lastVideoAssetCardDraftStatus || "",
  ].join("|");
}

function inspectorPanelClass(state, node) {
  return [
    "inspector-panel",
    node ? "" : "empty",
    state.ui.inspectorOpen === false ? "is-collapsed" : "",
  ].filter(Boolean).join(" ");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
