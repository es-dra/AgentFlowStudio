import { assetsFromNode } from "./asset-reference-summary.js";
import { starterRailState } from "./canvas-starter-rail.js";
import { buildNodeBody, candidatePreviews, escapeHtml, generationProgress, nodeBodySignature, statusLabel } from "./canvas-node-body.js";
import { renderEdges } from "./canvas-edges.js";
import { icon } from "./icons.js";
import { NODE_TYPES, effectiveHeight, relationSets } from "./nodes.js";

export function renderCanvas(state, store) {
  const world = document.getElementById("world");
  world.style.transform = `translate(${state.viewport.x}px, ${state.viewport.y}px) scale(${state.viewport.scale})`;
  const relations = relationSets(state);
  renderNodes(state, relations);
  renderEdges(state, relations, store);
  renderEmptyState(state);
  const zoomLabel = document.querySelector("#corner-controls .zoom-label");
  if (zoomLabel) zoomLabel.textContent = `${Math.round(state.viewport.scale * 100)}%`;
}

function renderEmptyState(state) {
  const rail = starterRailState(state);
  const starterRow = document.getElementById("starter-row");
  document.getElementById("canvas-empty-hint").hidden = !rail.empty;
  starterRow.hidden = !rail.show;
  starterRow.dataset.mode = rail.mode;
}

function renderNodes(state, relations) {
  const layer = document.getElementById("node-layer");
  const seen = new Set();
  for (const id of state.order) {
    const node = state.nodes[id];
    if (!node) continue;
    seen.add(id);
    let elNode = layer.querySelector(`[data-node-id="${id}"]`);
    if (!elNode) {
      elNode = buildNodeElement(node);
      layer.appendChild(elNode);
    }
    syncNodeElement(elNode, node, state, relations);
  }
  for (const child of [...layer.children]) {
    if (!seen.has(child.dataset.nodeId)) child.remove();
  }
}

function buildNodeElement(node) {
  const elNode = document.createElement("div");
  elNode.className = `node type-${node.type}`;
  elNode.dataset.nodeId = node.id;
  elNode.appendChild(nodeTitle());
  elNode.appendChild(nodeStateStrip());
  elNode.appendChild(nodeActions());
  elNode.appendChild(uploadButton());
  elNode.appendChild(contextToolbar());
  elNode.appendChild(nodeBody());
  elNode.appendChild(portButton("in"));
  elNode.appendChild(portButton("out"));
  return elNode;
}

function nodeTitle() {
  const title = document.createElement("div");
  title.className = "node-title";
  title.dataset.role = "title";
  return title;
}

function nodeStateStrip() {
  const strip = document.createElement("div");
  strip.className = "node-state-strip";
  strip.dataset.role = "state-strip";
  return strip;
}

function nodeActions() {
  const actions = document.createElement("div");
  actions.className = "node-actions";
  actions.dataset.role = "actions";
  actions.innerHTML = [
    `<button class="na-btn" data-action="fix-visual-asset" title="保存为素材">${icon("bookmark", 13)}</button>`,
    `<button class="na-btn" data-action="run" title="生成">${icon("play", 13)}</button>`,
    `<button class="na-btn" data-action="duplicate" title="复制节点">${icon("copy", 13)}</button>`,
    `<button class="na-btn" data-action="toggle-collapse" title="折叠/展开">${icon("chevronUp", 13)}</button>`,
    `<button class="na-btn" data-action="node-menu" title="更多">${icon("more", 13)}</button>`,
  ].join("");
  return actions;
}

function uploadButton() {
  const upload = document.createElement("button");
  upload.className = "node-float-action";
  upload.dataset.action = "upload";
  upload.innerHTML = `${icon("upload", 13)}<span>上传</span>`;
  return upload;
}

function contextToolbar() {
  const workflow = document.createElement("div");
  workflow.className = "node-context-toolbar";
  workflow.dataset.role = "context-toolbar";
  workflow.innerHTML = [
    `<button data-action="continue-generate" title="继续生成">${icon("play", 13)}<span>继续生成</span></button>`,
    `<button data-action="fix-visual-asset" title="保存为素材">${icon("bookmark", 13)}<span>保存素材</span></button>`,
    `<button data-action="content-card" title="整理卡片">${icon("frames", 13)}<span>整理卡片</span></button>`,
    `<button data-action="open-creation-process" title="查看创作过程">${icon("layers", 13)}<span>看过程</span></button>`,
  ].join("");
  return workflow;
}

function nodeBody() {
  const body = document.createElement("div");
  body.className = "node-body";
  body.dataset.role = "body";
  return body;
}

function portButton(port) {
  const button = document.createElement("button");
  button.className = `node-port ${port}`;
  button.dataset.port = port;
  button.innerHTML = icon("plus", 12);
  return button;
}

function syncNodeElement(elNode, node, state, relations) {
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  syncNodeFrame(elNode, node, state);
  syncNodeRelations(elNode, node, relations);
  syncNodeTitle(elNode, node, def);
  syncNodeStateStrip(elNode, node, def);
  syncRunAction(elNode, node);
  syncNodeBody(elNode, node, def);
}

function syncNodeFrame(elNode, node, state) {
  elNode.style.transform = `translate(${node.x}px, ${node.y}px)`;
  elNode.style.width = `${node.w}px`;
  elNode.style.minHeight = `${effectiveHeight(node)}px`;
  elNode.style.height = node.collapsed ? `${effectiveHeight(node)}px` : "";
  elNode.classList.toggle("selected", state.selection.nodeIds.includes(node.id));
  elNode.classList.toggle("collapsed", Boolean(node.collapsed));
  elNode.classList.toggle("director", node.type === "director");
  elNode.classList.toggle("text-content", Boolean(node.content));
  elNode.classList.toggle("is-reference", Boolean(node.params?.isReference));
  elNode.classList.toggle("has-image-preview", Boolean(node.previewUrl));
  elNode.classList.toggle("has-media-result", Boolean(node.previewUrl || candidatePreviews(node).length));
  elNode.classList.toggle("is-generating", node.status === "generating");
  elNode.classList.toggle("script-expanding", node.params?.scriptExpansionState?.status === "running");
  elNode.classList.toggle("hide-context-toolbar", node.type === "text");
  elNode.classList.toggle("has-candidates", candidatePreviews(node).length > 1);
}

function syncNodeRelations(elNode, node, relations) {
  elNode.classList.remove("rel-upstream", "rel-downstream", "rel-dimmed");
  if (!relations || node.id === relations.focus) return;
  if (relations.upstream.has(node.id)) elNode.classList.add("rel-upstream");
  else if (relations.downstream.has(node.id)) elNode.classList.add("rel-downstream");
  else elNode.classList.add("rel-dimmed");
}

function syncNodeTitle(elNode, node, def) {
  const title = elNode.querySelector('[data-role="title"]');
  const refBadge = node.params?.isReference ? `<span class="ref-badge">${icon("bookmark", 11)}参考</span>` : "";
  const visualAssets = assetsFromNode(node);
  const hasInvalidAsset = visualAssets.some((asset) => asset?.runtime_status === "excluded" || asset?.status === "retired");
  const fixedBadge = visualAssets.length
    ? `<button class="ref-badge asset-badge${hasInvalidAsset ? " invalid" : ""}" data-action="asset-detail" title="${hasInvalidAsset ? "已失效，本次未携带" : "查看固定资产"}">${icon("lock", 11)}${visualAssets.length}资产</button>`
    : "";
  title.innerHTML = `${icon(def.icon, 13)}<span>${escapeHtml(node.title)}</span>${refBadge}${fixedBadge}`;
}

function syncNodeStateStrip(elNode, node, def) {
  const stateStrip = elNode.querySelector('[data-role="state-strip"]');
  if (!stateStrip) return;
  const nodeStatus = node.status || "empty";
  stateStrip.className = `node-state-strip ${nodeStatus}`;
  stateStrip.innerHTML = `<span class="dot"></span><span>${escapeHtml(statusLabel(nodeStatus))}</span><span>${escapeHtml(def.label)}</span>`;
}

function syncNodeBody(elNode, node, def) {
  const body = elNode.querySelector('[data-role="body"]');
  body.hidden = Boolean(node.collapsed);
  body.classList.toggle("full-bleed-media", node.type === "image" && node.status === "complete" && Boolean(node.previewUrl));
  const signature = nodeBodySignature(node);
  if (body.dataset.signature !== signature) {
    body.dataset.signature = signature;
    body.replaceChildren(...buildNodeBody(node, def));
  }
}

function syncRunAction(elNode, node) {
  const runBtn = elNode.querySelector('[data-action="run"], [data-action="video-poll"]');
  if (!runBtn) return;
  runBtn.disabled = false;
  if (node.type === "video" && node.status === "generating") {
    if (node.params?.lastVideoJobId) {
      runBtn.dataset.action = "video-poll";
      runBtn.title = "继续轮询视频任务";
      runBtn.innerHTML = icon("retry", 13);
    } else {
      runBtn.dataset.action = "run";
      runBtn.title = "视频任务提交中";
      runBtn.disabled = true;
      runBtn.innerHTML = icon("clock", 13);
    }
    return;
  }
  runBtn.dataset.action = "run";
  runBtn.title = "生成";
  runBtn.innerHTML = icon("play", 13);
}
