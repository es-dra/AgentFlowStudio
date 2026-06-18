import { NODE_TYPES } from "../nodes.js";
import { icon } from "../icons.js";
import { el } from "../overlay.js";
import { assetsFromNode } from "../asset-reference-summary.js";
import { algorithmConsoleSection, projectPipelineSection } from "./algorithm-context-panel.js";

export function renderInspectorPanel(state, store) {
  const panel = document.getElementById("inspector");
  if (!panel) return;
  const nodeId = state.selection.nodeIds.length === 1 ? state.selection.nodeIds[0] : "";
  const node = nodeId ? state.nodes[nodeId] : null;
  const signature = inspectorSignature(state, node);
  if (panel.dataset.signature === signature) return;
  panel.dataset.signature = signature;
  panel.className = `inspector-panel${node ? "" : " empty"}`;
  panel.replaceChildren();
  if (!node) {
    renderEmptyInspector(state, store, panel);
    return;
  }
  renderNodeInspector(panel, node, store);
}

function renderEmptyInspector(state, store, panel) {
  panel.appendChild(panelHead("panel", "创作助手", "下一步"));
  panel.appendChild(emptyGuide(state));
  panel.appendChild(decisionGuide(state));
  panel.appendChild(projectReferenceSummary(state));
  panel.appendChild(drawerLinks(store));
  panel.appendChild(projectPipelineSection(state));
}

function renderNodeInspector(panel, node, store) {
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  panel.appendChild(panelHead(def.icon, node.title, def.label));
  panel.appendChild(nodeFocus(node));
  panel.appendChild(section("下一步行动", nextStepText(node), "primary"));
  panel.appendChild(inspectorActions(nodeActions(node, store)));
  panel.appendChild(section("本次参考摘要", contextSummary(node)));
  panel.appendChild(drawerLinks(store));
  panel.appendChild(detailsSection("节点草稿", node.prompt || node.content || "还没有填写创作内容。", "内容"));
  panel.appendChild(algorithmConsoleSection(node));
  panel.appendChild(detailsSection("输出记录", recordSummary(node), "记录"));
}

function panelHead(iconName, title, meta) {
  const head = el("div", "inspector-head");
  head.innerHTML = `<span>${icon(iconName, 14)}</span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(meta)}</small>`;
  return head;
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

function decisionGuide(state) {
  const hasNodes = state.order.length > 0;
  const assetCount = state.assets.length;
  const message = hasNodes
    ? "选择画布节点后，优先处理继续生成、固定资产、查看参考或发起修订。算法 trace 默认折叠在下方，不会抢占主任务。"
    : "从底部工具栏新建文本、图片或视频节点；固定资产会在后续调用中自动参与调度。";
  const suffix = assetCount ? `当前已有 ${assetCount} 个可用素材。` : "当前还没有确认素材。";
  return section("下一步行动", `${message}\n${suffix}`, "primary");
}

function nodeFocus(node) {
  const wrap = el("section", `inspector-section inspector-focus ${node.status || "draft"}`);
  wrap.appendChild(el("h3", "", statusText(node.status)));
  const detail = el("div", "inspector-quiet-line");
  detail.appendChild(metaPill("模型", node.params?.model || "未选择"));
  detail.appendChild(metaPill("素材", assetsFromNode(node).length));
  detail.appendChild(metaPill("类型", NODE_TYPES[node.type]?.label || node.type || "节点"));
  wrap.appendChild(detail);
  return wrap;
}

function metaPill(label, value) {
  const item = el("span", "inspector-meta-pill");
  item.innerHTML = `<small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong>`;
  return item;
}

function inspectorActions(actions) {
  const row = el("div", "inspector-actions");
  for (const [label, iconName, onClick, tone = ""] of actions) {
    const button = el("button", `inspector-action${tone ? ` ${tone}` : ""}`);
    button.type = "button";
    button.innerHTML = `${icon(iconName, 13)}<span>${escapeHtml(label)}</span>`;
    button.addEventListener("click", onClick);
    row.appendChild(button);
  }
  return row;
}

function nodeActions(node, store) {
  const base = [
    ["继续创作", "play", () => dispatchNodeEvent("afs:studio-open-generation-panel", node), "primary"],
    ["保存素材", "bookmark", () => dispatchNodeEvent("afs:studio-fix-visual-asset", node)],
    ["看过程", "layers", () => dispatchNodeEvent("afs:studio-open-creation-process", node)],
  ];
  if (node.type === "video") {
    base.push(["整理卡片", "frames", () => dispatchNodeEvent("afs:video-asset-card-draft", node)]);
  }
  return base;
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
  const readyAssets = (state.assets || []).filter((asset) => String(asset.status || "").toLowerCase() !== "retired").length;
  const edgeCount = Object.keys(state.edges || {}).length;
  const nodeCount = state.order.length;
  const text = nodeCount
    ? `画布节点：${nodeCount}\n固定素材：${readyAssets}\n连线关系：${edgeCount}\n选择节点后会显示本次调用携带的参考。`
    : "还没有项目参考。创建节点并确认素材后，系统会在生成前整理本次参考摘要。";
  return section("本次参考摘要", text);
}

function nextStepText(node) {
  if (node.status === "generating") return "等待生成完成；如果是视频节点，可以继续刷新进度。";
  if (node.status === "error") return "检查失败原因后重试，或先打开生成面板调整描述。";
  if (node.previewUrl || node.result) return "结果已经出现，可以继续生成、保存为素材，或打开过程查看引用与输出。";
  if (node.type === "script") return "补充故事设定后继续生成分镜和关键帧。";
  if (node.type === "director") return "打开二维导演台，先把人物、机位、灯光和道具摆清楚。";
  if (node.type === "image") return "填写画面描述或接入参考图，然后生成首帧。";
  if (node.type === "video") return "确认首帧和动作描述后生成视频；完成后再整理成视频素材卡。";
  return "补充内容后继续连接下游节点。";
}

function contextSummary(node) {
  const bundle = node.params?.lastContextBundle || {};
  const assets = Array.isArray(bundle.included_assets) ? bundle.included_assets.length : 0;
  const nodes = Array.isArray(bundle.included_nodes) ? bundle.included_nodes.length : 0;
  if (!assets && !nodes) return "还没有引用内容。优化或生成后会显示本次携带的节点与素材。";
  return `引用节点：${nodes}\n引用素材：${assets}`;
}

function recordSummary(node) {
  const parts = [manifestSummary(node), jobSummary(node), assetSummary(node)].filter(Boolean);
  return parts.length ? parts.join("\n\n") : "还没有生成记录。";
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
  return {
    complete: "已完成",
    generated: "已完成",
    succeeded: "已完成",
    success: "已完成",
    ready: "待生成",
    generating: "生成中",
    running: "生成中",
    pending: "排队中",
    blocked: "已阻塞",
    error: "失败",
    failed: "失败",
    cancelled: "已取消",
    empty: "草稿",
  }[status] || "草稿";
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
    JSON.stringify(node?.params?.lastSafeManifest || node?.params?.lastGenerationManifest || {}),
    JSON.stringify(node?.params?.jobProgress || {}),
    node?.params?.lastOptimizedPromptPlain || "",
    node?.params?.lastVideoAssetCardDraftStatus || "",
  ].join("|");
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
