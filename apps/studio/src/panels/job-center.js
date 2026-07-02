import { icon } from "../icons.js";
import { el } from "../overlay.js";
import { nodeStatusSummary } from "../generation-status-policy.js";
import { setRuntimeMediaSource } from "../runtime-media-source.js";
import { openCreationProcessPanel } from "./creation-process-panel.js";

export function renderJobCenter(state, store, body, mode = "jobs") {
  const center = el("div", `job-center ${mode}`);
  body.appendChild(center);
  if (mode === "history") {
    renderHistory(state, store, center);
    return;
  }
  center.appendChild(el("div", "drawer-toolbar-title", "生成进度"));
  const jobs = Object.values(state.nodes || {}).filter((node) => jobLike(node));
  if (!jobs.length) {
    center.appendChild(emptyPanel({
      iconName: "clock",
      title: "当前没有生成任务",
      copy: "开始生成后，排队、失败、等待确认和可继续刷新的记录会出现在这里。",
      actions: [["回到画布", () => openDrawerTab(store, "canvas")]],
    }));
    return;
  }
  for (const node of jobs) center.appendChild(jobCard(state, store, node));
}

function renderHistory(state, store, center) {
  center.appendChild(el("div", "drawer-toolbar-title", "作品库"));
  const items = Object.values(state.nodes || {}).filter((node) => node.result || node.previewUrl);
  if (!items.length) {
    center.appendChild(emptyPanel({
      iconName: "frames",
      title: "还没有作品",
      copy: "生成完成的图片、视频和可复用结果会形成作品卡，方便继续生成、保存素材或回看过程。",
      actions: [["查看生成进度", () => openDrawerTab(store, "jobs")]],
    }));
    return;
  }
  const grid = el("div", "work-card-grid");
  for (const node of items) grid.appendChild(workCard(state, store, node));
  center.appendChild(grid);
}

function jobLike(node) {
  return ["generating", "error", "partial", "cancelled"].includes(node.status)
    || node.params?.lastKeyframeJobId
    || node.params?.lastVideoJobId
    || node.params?.lastVideoArtifactId;
}

function jobCard(state, store, node, compact = false) {
  const summary = nodeStatusSummary(node);
  const card = el("button", `job-center-card ${node.status || "draft"} ${summary.tone}`);
  card.appendChild(jobThumb(node));
  const main = el("span", "job-main");
  main.innerHTML = [
    `<strong>${escapeHtml(node.title)}</strong>`,
    `<small>${escapeHtml(jobSummary(node, compact))}</small>`,
  ].join("");
  card.appendChild(main);
  card.appendChild(el("span", "job-state", summary.displayStatus));
  card.addEventListener("click", () => {
    store.set((s) => { s.selection = { nodeIds: [node.id], edgeId: null }; }, { history: false, persist: false });
    if (compact) openCreationProcessPanel(state, node);
  });
  return card;
}

function workCard(state, store, node) {
  const card = el("article", `work-card ${node.type || "text"}`);
  card.appendChild(jobThumb(node));
  const copy = el("div", "work-card-copy");
  copy.innerHTML = [
    `<span>${escapeHtml(workType(node))}</span>`,
    `<strong>${escapeHtml(node.title || "未命名输出")}</strong>`,
    `<small>${escapeHtml(jobSummary(node, true))}</small>`,
  ].join("");
  const actions = el("div", "work-card-actions");
  const inspect = el("button", "mini-btn", "看过程");
  inspect.addEventListener("click", () => {
    store.set((s) => { s.selection = { nodeIds: [node.id], edgeId: null }; }, { history: false, persist: false });
    openCreationProcessPanel(state, node);
  });
  const next = workAction("继续生成", "afs:studio-open-generation-panel", node, store);
  const asset = workAction("保存素材", "afs:studio-fix-visual-asset", node, store);
  const cardAction = workAction("整理卡片", "afs:video-asset-card-draft", node, store);
  actions.append(inspect, next, asset, cardAction);
  card.append(copy, actions);
  return card;
}

function emptyPanel({ iconName, title, copy, actions = [] }) {
  const panel = el("div", "drawer-empty rich-empty");
  panel.innerHTML = [
    `<span class="folder-glyph">${icon(iconName, 34)}</span>`,
    `<strong>${escapeHtml(title)}</strong>`,
    `<small>${escapeHtml(copy)}</small>`,
  ].join("");
  if (actions.length) {
    const row = el("div", "rich-empty-actions");
    for (const [label, onClick] of actions) {
      const button = el("button", "mini-btn", label);
      button.type = "button";
      button.addEventListener("click", onClick);
      row.appendChild(button);
    }
    panel.appendChild(row);
  }
  return panel;
}

function openDrawerTab(store, tab) {
  store.set((s) => {
    s.ui.drawerOpen = true;
    s.ui.drawerTab = tab;
  }, { history: false, persist: false });
}

function workAction(label, eventName, node, store) {
  const button = el("button", "mini-btn", label);
  button.type = "button";
  button.addEventListener("click", () => {
    store.set((s) => { s.selection = { nodeIds: [node.id], edgeId: null }; }, { history: false, persist: false });
    window.dispatchEvent(new CustomEvent(eventName, { detail: { node_id: node.id, node } }));
  });
  return button;
}

function jobThumb(node) {
  const thumb = el("span", `job-thumb ${node.type || "text"}`);
  if (node.previewUrl && node.type === "image") {
    const img = document.createElement("img");
    setRuntimeMediaSource(img, node.previewUrl);
    img.alt = "";
    img.loading = "lazy";
    thumb.appendChild(img);
    return thumb;
  }
  thumb.innerHTML = icon(iconForNode(node), 14);
  return thumb;
}

function jobSummary(node, compact) {
  const summary = nodeStatusSummary(node);
  const suffixParts = [];
  if (summary.blockedReason) suffixParts.push(`blocked reason: ${summary.blockedReason}`);
  if (summary.nextAction) suffixParts.push(`next action: ${summary.nextAction}`);
  const suffix = suffixParts.length ? ` · ${suffixParts.join(" · ")}` : "";
  if (node.params?.lastVideoJobId) return `视频任务 ${node.params.lastVideoJobId}${suffix}`;
  if (node.params?.lastKeyframeJobId) return `关键帧任务 ${node.params.lastKeyframeJobId}${suffix}`;
  if (node.params?.lastVideoArtifactId) return `输出 ${node.params.lastVideoArtifactId}${suffix}`;
  if (node.status === "partial") return `partial result preserved${suffix}`;
  if (compact && node.previewUrl) return "已有预览";
  return node.result ? String(node.result).slice(0, 80) : "本地草稿";
}

function iconForNode(node) {
  if (node.type === "video") return "video";
  if (node.type === "image") return "image";
  if (node.type === "script") return "script";
  return "clock";
}

function workType(node) {
  if (node.type === "video") return "视频作品";
  if (node.type === "image") return "关键帧";
  if (node.type === "script") return "脚本";
  return "创作记录";
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
