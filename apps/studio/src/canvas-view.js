import { NODE_TYPES, effectiveHeight, relationSets } from "./nodes.js";
import { bezier } from "./geometry.js";
import { icon } from "./icons.js";
import { directorSummary, normalizeDirectorSetup } from "./director-data.js";

const EDGE_OFFSET = 20000;

export function renderCanvas(state) {
  const world = document.getElementById("world");
  world.style.transform = `translate(${state.viewport.x}px, ${state.viewport.y}px) scale(${state.viewport.scale})`;
  const relations = relationSets(state);
  renderNodes(state, relations);
  renderEdges(state, relations);
  renderEmptyState(state);
  const zoomLabel = document.querySelector("#corner-controls .zoom-label");
  if (zoomLabel) zoomLabel.textContent = `${Math.round(state.viewport.scale * 100)}%`;
}

function renderEmptyState(state) {
  const empty = state.order.length === 0;
  document.getElementById("canvas-empty-hint").hidden = !empty;
  document.getElementById("starter-row").hidden = !empty;
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
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  const elNode = document.createElement("div");
  elNode.className = `node type-${node.type}`;
  elNode.dataset.nodeId = node.id;

  const title = document.createElement("div");
  title.className = "node-title";
  title.dataset.role = "title";
  elNode.appendChild(title);

  // hover 操作条：生成 / 复制 / 折叠 / 更多
  const actions = document.createElement("div");
  actions.className = "node-actions";
  actions.dataset.role = "actions";
  actions.innerHTML = [
    `<button class="na-btn" data-action="run" title="生成">${icon("play", 13)}</button>`,
    `<button class="na-btn" data-action="duplicate" title="复制节点">${icon("copy", 13)}</button>`,
    `<button class="na-btn" data-action="toggle-collapse" title="折叠/展开">${icon("chevronUp", 13)}</button>`,
    `<button class="na-btn" data-action="node-menu" title="更多">${icon("more", 13)}</button>`,
  ].join("");
  elNode.appendChild(actions);

  if (def.upload) {
    const upload = document.createElement("button");
    upload.className = "node-float-action";
    upload.dataset.action = "upload";
    upload.innerHTML = `${icon("upload", 13)}<span>上传</span>`;
    elNode.appendChild(upload);
  }

  const body = document.createElement("div");
  body.className = "node-body";
  body.dataset.role = "body";
  elNode.appendChild(body);

  const portIn = document.createElement("button");
  portIn.className = "node-port in";
  portIn.dataset.port = "in";
  portIn.innerHTML = icon("plus", 12);
  const portOut = document.createElement("button");
  portOut.className = "node-port out";
  portOut.dataset.port = "out";
  portOut.innerHTML = icon("plus", 12);
  elNode.appendChild(portIn);
  elNode.appendChild(portOut);
  return elNode;
}

function syncNodeElement(elNode, node, state, relations) {
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  elNode.style.transform = `translate(${node.x}px, ${node.y}px)`;
  elNode.style.width = `${node.w}px`;
  elNode.style.minHeight = `${effectiveHeight(node)}px`;
  elNode.style.height = node.collapsed ? `${effectiveHeight(node)}px` : "";
  elNode.classList.toggle("selected", state.selection.nodeIds.includes(node.id));
  elNode.classList.toggle("collapsed", Boolean(node.collapsed));
  elNode.classList.toggle("director", node.type === "director");
  elNode.classList.toggle("text-content", Boolean(node.content));
  elNode.classList.toggle("is-reference", Boolean(node.params?.isReference));

  elNode.classList.remove("rel-upstream", "rel-downstream", "rel-dimmed");
  if (relations && node.id !== relations.focus) {
    if (relations.upstream.has(node.id)) elNode.classList.add("rel-upstream");
    else if (relations.downstream.has(node.id)) elNode.classList.add("rel-downstream");
    else elNode.classList.add("rel-dimmed");
  }

  const title = elNode.querySelector('[data-role="title"]');
  const refBadge = node.params?.isReference ? `<span class="ref-badge">${icon("bookmark", 11)}参考</span>` : "";
  title.innerHTML = `${icon(def.icon, 13)}<span>${escapeHtml(node.title)}</span>${refBadge}`;

  const collapseBtn = elNode.querySelector('[data-action="toggle-collapse"]');
  if (collapseBtn) collapseBtn.innerHTML = icon(node.collapsed ? "chevronDown" : "chevronUp", 13);

  const body = elNode.querySelector('[data-role="body"]');
  body.hidden = Boolean(node.collapsed);
  const directorSig = node.params?.directorSetup ? directorSummary(normalizeDirectorSetup(node.params.directorSetup)) : "";
  const signature = [
    node.status,
    node.content ? node.content.length : 0,
    node.result ? node.result.length : 0,
    node.type,
    node.collapsed ? 1 : 0,
    directorSig,
    node.params?.appliedDownstreamCount || 0,
  ].join("|");
  if (body.dataset.signature !== signature) {
    body.dataset.signature = signature;
    body.replaceChildren(...buildNodeBody(node, def));
  }
}

function buildNodeBody(node, def) {
  const out = [];
  if (node.collapsed) return out;
  if (node.content) {
    const view = document.createElement("div");
    view.className = "text-content-view";
    view.textContent = node.content;
    out.push(view);
    return out;
  }
  if (node.type === "director") {
    const summary = directorSummary(normalizeDirectorSetup(node.params?.directorSetup));
    const applied = node.params?.appliedDownstreamCount
      ? ` / 已应用到 ${node.params.appliedDownstreamCount} 个相连节点`
      : "";
    const glyph = document.createElement("div");
    glyph.className = "node-glyph";
    glyph.innerHTML = icon(def.icon, 38);
    const desc = document.createElement("div");
    desc.className = "node-empty-label";
    desc.textContent = "二维顶视图布置机位、人物、灯光和道具";
    const badge = document.createElement("div");
    badge.className = "director-node-summary";
    badge.textContent = `${summary}${applied}`;
    const open = document.createElement("button");
    open.className = "director-open-btn";
    open.dataset.action = "open-director";
    open.textContent = "打开二维导演台";
    out.push(glyph, desc, badge, open);
    if (node.result) out.push(resultView(node));
    return out;
  }
  if (node.status === "generating") {
    const status = document.createElement("div");
    status.className = "node-status";
    status.innerHTML = '<span class="spinner"></span><span>生成中…</span>';
    out.push(status);
    return out;
  }
  if (node.status === "complete" && node.result) {
    const ok = document.createElement("div");
    ok.className = "node-status success";
    ok.innerHTML = `${icon("check", 13)}<span>已完成（本地预览）</span>`;
    out.push(ok, resultView(node));
    return out;
  }
  if (node.status === "error") {
    const err = document.createElement("div");
    err.className = "node-status error";
    err.innerHTML = `${icon("x", 13)}<span>生成失败，可在节点菜单重试</span>`;
    out.push(err);
    return out;
  }
  const glyph = document.createElement("div");
  glyph.className = "node-glyph";
  glyph.innerHTML = icon(def.icon, 38);
  out.push(glyph);
  if (def.intents.length) {
    const label = document.createElement("div");
    label.className = "node-empty-label";
    label.textContent = "尝试:";
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
    out.push(label, list);
  }
  return out;
}

function resultView(node) {
  const result = document.createElement("div");
  result.className = "node-result";
  result.textContent = node.result;
  return result;
}

function renderEdges(state, relations) {
  const svg = document.getElementById("edge-layer");
  let group = svg.querySelector("g[data-role='edges']");
  if (!group) {
    group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.dataset.role = "edges";
    group.setAttribute("transform", `translate(${EDGE_OFFSET}, ${EDGE_OFFSET})`);
    svg.appendChild(group);
  }
  const seen = new Set();
  for (const edge of Object.values(state.edges)) {
    const from = state.nodes[edge.from];
    const to = state.nodes[edge.to];
    if (!from || !to) continue;
    seen.add(edge.id);
    let item = group.querySelector(`[data-edge-id="${edge.id}"]`);
    if (!item) {
      item = document.createElementNS("http://www.w3.org/2000/svg", "g");
      item.dataset.edgeId = edge.id;
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.classList.add("edge-label");
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.classList.add("edge-flow");
      item.append(path, label);
      group.appendChild(item);
    }
    const path = item.querySelector("path");
    const label = item.querySelector(".edge-label");
    const x1 = from.x + from.w;
    const y1 = from.y + effectiveHeight(from) / 2;
    const x2 = to.x;
    const y2 = to.y + effectiveHeight(to) / 2;
    path.setAttribute("d", bezier(x1, y1, x2, y2));
    const relation = edge.relation_type || edge.relationType || "generation";
    path.classList.toggle("director-edge", relation === "director");
    path.classList.toggle("reference-edge", relation === "reference");
    path.classList.toggle("selected-edge", state.selection.edgeId === edge.id);
    path.classList.toggle("just-connected", state.ui.lastConnectedEdgeId === edge.id);
    path.classList.remove("rel-up-edge", "rel-down-edge", "rel-dim-edge");
    label.textContent = relation === "director" ? "导演台" : relation === "reference" ? "参考" : "";
    label.setAttribute("x", String((x1 + x2) / 2));
    label.setAttribute("y", String((y1 + y2) / 2 - 8));
    label.classList.toggle("visible", Boolean(label.textContent));
    if (relations) {
      const upSide = (relations.upstream.has(edge.from) || edge.from === relations.focus)
        && (relations.upstream.has(edge.to) || edge.to === relations.focus);
      const downSide = (relations.downstream.has(edge.to) || edge.to === relations.focus)
        && (relations.downstream.has(edge.from) || edge.from === relations.focus);
      if (edge.to === relations.focus || (upSide && relations.upstream.has(edge.from))) path.classList.add("rel-up-edge");
      else if (edge.from === relations.focus || (downSide && relations.downstream.has(edge.to))) path.classList.add("rel-down-edge");
      else path.classList.add("rel-dim-edge");
    }
  }
  for (const item of [...group.children]) {
    if (!seen.has(item.dataset.edgeId)) item.remove();
  }
}

export function getPendingEdgeGroup() {
  const svg = document.getElementById("edge-layer");
  let group = svg.querySelector("g[data-role='pending']");
  if (!group) {
    group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.dataset.role = "pending";
    group.setAttribute("transform", `translate(${EDGE_OFFSET}, ${EDGE_OFFSET})`);
    svg.appendChild(group);
  }
  return group;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}
