import { NODE_TYPES } from "../nodes.js";
import { icon } from "../icons.js";
import { el } from "../overlay.js";
import { assetsFromNode } from "../asset-reference-summary.js";

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
  const head = el("div", "inspector-head");
  head.innerHTML = `<span>${icon("panel", 14)}</span><strong>项目概览</strong>`;
  panel.appendChild(head);
  const stats = el("div", "inspector-grid");
  stats.appendChild(metric("节点", state.order.length));
  stats.appendChild(metric("素材", state.assets.length));
  stats.appendChild(metric("连线", Object.keys(state.edges || {}).length));
  panel.appendChild(stats);
  panel.appendChild(inspectorActions([
    ["素材库", "folder", () => openDrawerTab(store, "assets")],
    ["生成进度", "clock", () => openDrawerTab(store, "jobs")],
    ["作品库", "frames", () => openDrawerTab(store, "history")],
  ]));
  panel.appendChild(section("下一步", state.order.length
    ? "选择一个节点后，可以继续生成、保存素材或查看创作过程。"
    : "先从画布模板开始，或双击画布创建第一个节点。"));
}

function renderNodeInspector(panel, node, store) {
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  const head = el("div", "inspector-head");
  head.innerHTML = `<span>${icon(def.icon, 14)}</span><strong>${escapeHtml(node.title)}</strong><small>${escapeHtml(def.label)}</small>`;
  panel.appendChild(head);
  panel.appendChild(statusStrip(node));
  panel.appendChild(inspectorActions(nodeActions(node, store)));
  panel.appendChild(section("下一步", nextStepText(node)));
  panel.appendChild(section("创作内容", node.prompt || node.content || "还没有填写创作内容。"));
  panel.appendChild(section("关联参考", contextSummary(node)));
  panel.appendChild(section("生成状态", manifestSummary(node)));
  panel.appendChild(section("产物记录", jobSummary(node)));
  const assets = assetsFromNode(node);
  panel.appendChild(section("已保存素材", assets.length ? assets.map((asset) => asset.label || asset.asset_id).join("\n") : "还没有保存为角色或场景素材。"));
}

function statusStrip(node) {
  const strip = el("div", `inspector-status ${node.status || "draft"}`);
  strip.appendChild(metric("状态", statusText(node.status)));
  strip.appendChild(metric("模型", node.params?.model || "未选择"));
  strip.appendChild(metric("素材", assetsFromNode(node).length));
  return strip;
}

function metric(label, value) {
  const item = el("span", "inspector-metric");
  item.innerHTML = `<strong>${escapeHtml(value)}</strong><small>${escapeHtml(label)}</small>`;
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
  if (store) {
    base.push(["素材库", "folder", () => openDrawerTab(store, "assets")]);
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

function section(title, text) {
  const wrap = el("section", "inspector-section");
  wrap.appendChild(el("h3", "", title));
  const value = el("pre", "", String(text || "暂无内容"));
  wrap.appendChild(value);
  return wrap;
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

function manifestSummary(node) {
  const manifest = node.params?.lastSafeManifest || node.params?.lastGenerationManifest || {};
  const status = manifest.status || node.params?.lastVideoAssetCardDraftStatus || "";
  if (!status && !Object.keys(manifest).length) return "还没有生成摘要。";
  return [
    status ? `状态：${statusText(status)}` : "",
    manifest.provider_service_id ? `能力：${providerLabel(manifest.provider_service_id)}` : "",
    manifest.artifact_id ? `输出编号：${manifest.artifact_id}` : "",
  ].filter(Boolean).join("\n") || "已有生成摘要。";
}

function jobSummary(node) {
  const data = [
    node.params?.lastKeyframeJobId ? `关键帧任务：${node.params.lastKeyframeJobId}` : "",
    node.params?.lastVideoJobId ? `视频任务：${node.params.lastVideoJobId}` : "",
    node.params?.lastVideoArtifactId ? `输出编号：${node.params.lastVideoArtifactId}` : "",
  ].filter(Boolean);
  return data.length ? data.join("\n") : "还没有生成记录。";
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
    blocked: "已拦截",
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
    node?.id || "",
    node?.title || "",
    node?.status || "",
    node?.prompt || "",
    node?.result || "",
    JSON.stringify(node?.params?.lastContextBundle || {}),
    JSON.stringify(node?.params?.lastSafeManifest || node?.params?.lastGenerationManifest || {}),
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
