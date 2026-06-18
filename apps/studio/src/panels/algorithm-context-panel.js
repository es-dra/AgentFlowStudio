import { assetsFromNode, assetCarryState } from "../asset-reference-summary.js";
import { icon } from "../icons.js";
import { el } from "../overlay.js";

const CORE_ALGORITHMS = [
  { id: "context", label: "上下文调度", icon: "layers" },
  { id: "prompt", label: "提示词优化", icon: "wand" },
  { id: "projection", label: "请求投影", icon: "bolt" },
  { id: "vision", label: "视觉识别", icon: "camera" },
  { id: "memory", label: "资产记忆", icon: "bookmark" },
  { id: "drift", label: "漂移控制", icon: "retry" },
];

export function projectPipelineSection(state) {
  return algorithmSection({
    title: "系统过程",
    tag: "项目链路",
    summary: projectSummary(state),
    steps: CORE_ALGORITHMS.map((item) => [item, projectAlgorithmStatus(state, item.id)]),
    stats: [
      ["上下文", projectContextLabel(state), "context"],
      ["素材状态", projectAssetLabel(state), "memory"],
      ["证据", projectEvidenceLabel(state), "evidence"],
      ["反馈", projectFeedbackLabel(state), "drift"],
    ],
  });
}

export function algorithmConsoleSection(node) {
  const bundle = node.params?.lastContextBundle || {};
  const manifest = safeManifest(node);
  return algorithmSection({
    title: "系统过程",
    tag: operationLabel(node),
    summary: nodeSummary(node, bundle),
    steps: CORE_ALGORITHMS.map((item) => [item, nodeAlgorithmStatus(node, item.id)]),
    stats: [
      ["意图", operationLabel(node), "intent"],
      ["目标", generationTargetLabel(node), "target"],
      ["纳入", includedLabel(node, bundle), "context"],
      ["排除", excludedLabel(bundle), "warning"],
    ],
    warnings: traceWarnings(node, bundle, manifest),
  });
}

function algorithmSection({ title, tag, summary, steps, stats, warnings = [] }) {
  const details = el("details", "inspector-section algorithm-console algorithm-disclosure");
  const head = el("summary", "algorithm-summary");
  head.innerHTML = [
    `<span class="algorithm-summary-icon">${icon("layers", 13)}</span>`,
    `<span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(summary)}</small></span>`,
    `<em>${escapeHtml(tag)}</em>`,
  ].join("");
  details.appendChild(head);

  const stages = el("div", "algorithm-step-track");
  for (const [item, status] of steps) stages.appendChild(stepRow(item, status));
  details.appendChild(stages);

  const statWrap = el("div", "algorithm-call-summary");
  for (const [label, value, tone] of stats) statWrap.appendChild(statChip(label, value, tone));
  details.appendChild(statWrap);

  if (warnings.length) details.appendChild(traceList(warnings));
  return details;
}

function stepRow(item, status) {
  const row = el("div", `algorithm-step ${status.tone}`);
  row.innerHTML = [
    `<span class="algorithm-step-icon">${icon(item.icon, 12)}</span>`,
    `<strong>${escapeHtml(item.label)}</strong>`,
    `<small>${escapeHtml(status.label)}</small>`,
  ].join("");
  return row;
}

function statChip(label, value, tone = "") {
  const item = el("div", `algorithm-stat${tone ? ` ${tone}` : ""}`);
  item.appendChild(el("small", "", label));
  item.appendChild(el("strong", "", value));
  return item;
}

function traceList(items) {
  const wrap = el("div", "algorithm-trace-list");
  for (const item of items.slice(0, 3)) {
    const row = el("div", "algorithm-trace-item");
    row.innerHTML = `${icon("check", 11)}<span>${escapeHtml(item)}</span>`;
    wrap.appendChild(row);
  }
  return wrap;
}

function projectAlgorithmStatus(state, id) {
  if (id === "context") return anyNode(state, (node) => node.params?.lastContextBundle) ? done("已调度") : ready("待调用");
  if (id === "prompt") return anyNode(state, (node) => node.params?.lastOptimizedPromptPlain) ? done("已优化") : ready("可触发");
  if (id === "projection") return anyNode(state, hasRequestEvidence) ? done("已投影") : ready("待请求");
  if (id === "vision") return anyNode(state, (node) => node.params?.lastVideoAssetCardDraft || node.params?.lastAssetCardDraft) ? done("有草稿") : muted("待证据");
  if (id === "memory") return (state.assets || []).length ? done(`${state.assets.length} 项`) : ready("待确认");
  if (id === "drift") return anyNode(state, hasFeedbackSignal) ? done("有反馈") : muted("待输出");
  return muted("待触发");
}

function nodeAlgorithmStatus(node, id) {
  const bundle = node.params?.lastContextBundle;
  const manifest = safeManifest(node);
  if (id === "context") return bundle ? done("已调度") : ready("待调度");
  if (id === "prompt") return node.params?.lastOptimizedPromptPlain ? done("已优化") : promptReady(node);
  if (id === "projection") return hasRequestEvidence(node) ? done("已投影") : requestReady(node);
  if (id === "vision") return node.params?.lastVideoAssetCardDraft || node.params?.lastAssetCardDraft ? done("草稿") : visionReady(node);
  if (id === "memory") return assetMemoryStatus(node, bundle);
  if (id === "drift") return hasFeedbackSignal(node) ? done("已记录") : driftReady(node, manifest);
  return muted("待触发");
}

function promptReady(node) {
  return node.prompt || node.content ? ready("可优化") : muted("待输入");
}

function requestReady(node) {
  if (node.status === "generating") return ready("进行中");
  return node.prompt || node.previewUrl || node.content ? ready("可提交") : muted("待输入");
}

function visionReady(node) {
  return node.previewUrl || node.result || safeManifest(node)?.artifact_id ? ready("可整理") : muted("待证据");
}

function driftReady(node, manifest) {
  return node.previewUrl || node.result || manifest?.artifact_id ? ready("可反馈") : muted("待输出");
}

function assetMemoryStatus(node, bundle) {
  const assets = assetsFromNode(node);
  const included = Array.isArray(bundle?.included_assets) ? bundle.included_assets : [];
  if (included.length) return done(`${included.length} 已纳入`);
  if (assets.some((asset) => assetCarryState(asset) === "included")) return done("已携带");
  if (assets.length) return ready(`${assets.length} 候选`);
  return muted("待确认");
}

function projectSummary(state) {
  const readyCount = CORE_ALGORITHMS.filter((item) => projectAlgorithmStatus(state, item.id).tone === "complete").length;
  return readyCount ? `${readyCount} 个算法已有证据` : "生成前会自动调度上下文";
}

function nodeSummary(node, bundle) {
  const assets = Array.isArray(bundle?.included_assets) ? bundle.included_assets.length : 0;
  const nodes = Array.isArray(bundle?.included_nodes) ? bundle.included_nodes.length : 0;
  if (assets || nodes) return `已参考 ${nodes} 个节点 / ${assets} 个素材`;
  if (hasRequestEvidence(node)) return "已有请求与安全摘要";
  return "触发生成时再展开";
}

function projectContextLabel(state) {
  const count = countNodes(state, (node) => node.params?.lastContextBundle);
  return count ? `${count} 节点已调度` : "等待首次调用";
}

function projectAssetLabel(state) {
  const assets = state.assets || [];
  if (!assets.length) return "待确认";
  const retired = assets.filter((asset) => String(asset.status || "").toLowerCase() === "retired").length;
  return retired ? `${assets.length - retired} 可用 / ${retired} 停用` : `${assets.length} 可用`;
}

function projectEvidenceLabel(state) {
  const count = countNodes(state, (node) => safeManifest(node)?.artifact_id || node.params?.lastKeyframeJobId || node.params?.lastVideoJobId);
  return count ? `${count} 条` : "暂无";
}

function projectFeedbackLabel(state) {
  const count = countNodes(state, hasFeedbackSignal);
  return count ? `${count} 条` : "待生成后记录";
}

function operationLabel(node) {
  if (node.params?.videoRevision || node.params?.lastRevisionJobId) return "视频修订";
  if (node.type === "video") return "视频生成";
  if (node.type === "image") return "图片生成";
  if (node.type === "director") return "导演上下文";
  if (node.type === "script") return "脚本到分镜";
  return "提示词优化";
}

function generationTargetLabel(node) {
  if (node.params?.videoRevision) return "修订片段";
  if (node.type === "video") return "视频片段";
  if (node.type === "image") return "关键帧";
  if (node.type === "director") return "导演参数";
  if (node.type === "script") return "分镜 brief";
  return "创作 brief";
}

function includedLabel(node, bundle) {
  const assets = Array.isArray(bundle?.included_assets) ? bundle.included_assets.length : 0;
  const nodes = Array.isArray(bundle?.included_nodes) ? bundle.included_nodes.length : 0;
  if (assets || nodes) return `${nodes} 节点 / ${assets} 素材`;
  const localAssets = assetsFromNode(node).length;
  return localAssets ? `${localAssets} 候选素材` : "待调度";
}

function excludedLabel(bundle) {
  const excluded = Array.isArray(bundle?.excluded_assets) ? bundle.excluded_assets.length : 0;
  const conflicts = Array.isArray(bundle?.asset_conflicts) ? bundle.asset_conflicts.length : 0;
  return excluded || conflicts ? `${excluded + conflicts} 项` : "无";
}

function traceWarnings(node, bundle, manifest) {
  const out = [];
  if (Array.isArray(bundle?.warnings)) out.push(...bundle.warnings.map(shortText));
  if (Array.isArray(bundle?.asset_conflicts)) out.push(...bundle.asset_conflicts.map((item) => shortText(item?.reason || item)));
  if (Array.isArray(manifest?.blocks)) out.push(...manifest.blocks.map((item) => shortText(item?.reason || item)));
  if (node.params?.lastVideoAssetCardDraftStatus) out.push(`资产卡草稿：${node.params.lastVideoAssetCardDraftStatus}`);
  return out.filter(Boolean);
}

function safeManifest(node) {
  return node.params?.lastSafeManifest || node.params?.lastGenerationManifest || null;
}

function hasRequestEvidence(node) {
  return Boolean(
    safeManifest(node)?.artifact_id
    || node.params?.lastKeyframeJobId
    || node.params?.lastVideoJobId
    || node.params?.lastVideoArtifactId
    || node.params?.jobProgress
  );
}

function hasFeedbackSignal(node) {
  return Boolean(
    node.params?.lastQualityFeedbackId
    || node.params?.feedbackEventId
    || node.params?.videoRevision?.lastRevisionJobId
    || node.params?.lastRevisionJobId
  );
}

function anyNode(state, predicate) {
  return countNodes(state, predicate) > 0;
}

function countNodes(state, predicate) {
  return (state.order || []).reduce((count, id) => {
    const node = state.nodes?.[id];
    return node && predicate(node) ? count + 1 : count;
  }, 0);
}

function done(label) {
  return { label, tone: "complete" };
}

function ready(label) {
  return { label, tone: "ready" };
}

function muted(label) {
  return { label, tone: "muted" };
}

function shortText(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 80);
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
