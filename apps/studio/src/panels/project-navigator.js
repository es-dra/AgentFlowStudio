import { NODE_TYPES, deleteNodes } from "../nodes.js";
import { visibleCanvasCenter } from "../canvas-safe-area.js";
import { icon } from "../icons.js";
import { el } from "../overlay.js";
import { canonicalStudioStatusId, studioStatusLabel } from "../studio-entity-status-vocabulary.js";

export function renderProjectNavigator(state, store, body) {
  body.appendChild(summaryRow(state));
  const query = String(state.ui.navigatorSearch || "").trim().toLowerCase();
  const search = el("div", "drawer-search navigator-search");
  search.innerHTML = icon("search", 13);
  const input = document.createElement("input");
  input.placeholder = "搜索节点、状态或类型";
  input.value = state.ui.navigatorSearch || "";
  input.addEventListener("input", () => store.set((s) => { s.ui.navigatorSearch = input.value; }, { history: false, persist: false }));
  search.appendChild(input);
  body.appendChild(search);

  const nodes = [...state.order]
    .reverse()
    .map((id) => state.nodes[id])
    .filter(Boolean)
    .filter((node) => {
      if (!query) return true;
      const text = `${node.title} ${node.type} ${node.status} ${node.prompt || ""}`.toLowerCase();
      return text.includes(query);
    });

  if (!nodes.length) {
    body.appendChild(el("div", "drawer-empty", query ? "没有匹配的节点。" : "当前画布还没有节点。"));
    return;
  }
  for (const node of nodes) body.appendChild(navigatorItem(state, store, node));
}

function summaryRow(state) {
  const wrap = el("div", "drawer-summary-row");
  wrap.appendChild(countPill("节点", state.order.length));
  wrap.appendChild(countPill("素材", state.assets.length));
  wrap.appendChild(countPill("生成中", runningCount(state)));
  return wrap;
}

function countPill(label, value) {
  const pill = el("span", "drawer-section-count");
  pill.innerHTML = `<strong>${value}</strong><span>${escapeHtml(label)}</span>`;
  return pill;
}

function runningCount(state) {
  return Object.values(state.nodes || {}).filter((node) => node.status === "generating").length;
}

function navigatorItem(state, store, node) {
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  const item = el("button", `tree-item navigator-item${state.selection.nodeIds.includes(node.id) ? " selected" : ""}`);
  item.innerHTML = [
    `<span class="tree-icon">${icon(def.icon, 12)}</span>`,
    `<span class="tree-label">${escapeHtml(node.title)}</span>`,
    `<span class="node-mini-status ${statusClass(node.status)}">${escapeHtml(statusText(node.status))}</span>`,
  ].join("");
  item.addEventListener("click", () => focusNode(store, node));
  const remove = el("button", "icon-btn");
  remove.innerHTML = icon("x", 11);
  remove.title = "删除节点";
  remove.addEventListener("click", (event) => {
    event.stopPropagation();
    deleteNodes(store, [node.id]);
  });
  item.appendChild(remove);
  return item;
}

function focusNode(store, node) {
  store.set((s) => {
    s.selection = { nodeIds: [node.id], edgeId: null };
    s.viewport = panViewportToNode(s.viewport, node);
  }, { history: false, persist: false });
}

function panViewportToNode(viewport, node) {
  const scale = Number(viewport?.scale || 1);
  const center = visibleCanvasCenter();
  const nodeCenterX = Number(node.x || 0) + Number(node.w || 0) / 2;
  const nodeCenterY = Number(node.y || 0) + Number(node.h || 0) / 2;
  return {
    ...viewport,
    scale,
    x: center.x - nodeCenterX * scale,
    y: center.y - nodeCenterY * scale,
  };
}

function statusText(status) {
  return studioStatusLabel(status, "草稿");
}

function statusClass(status) {
  const canonical = canonicalStudioStatusId(status, "draft");
  if (canonical === "running" || canonical === "queued" || canonical === "submitted" || canonical === "retrying") return "running";
  if (canonical === "succeeded" || canonical === "accepted" || canonical === "fixed") return "done";
  if (canonical === "failed") return "failed";
  if (canonical === "partial" || canonical === "cancelled" || canonical === "blocked" || canonical === "needs_attention") return "attention";
  return "";
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
