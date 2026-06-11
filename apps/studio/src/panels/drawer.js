import { NODE_TYPES, deleteNodes } from "../nodes.js";
import { el } from "../overlay.js";
import { fitViewport } from "../geometry.js";
import { icon } from "../icons.js";

export function renderDrawer(state, store) {
  const drawer = document.getElementById("drawer");
  drawer.classList.toggle("collapsed", !state.ui.drawerOpen);
  const signature = drawerSignature(state);
  if (drawer.dataset.signature === signature) return;
  drawer.dataset.signature = signature;
  drawer.replaceChildren();

  const head = el("div", "drawer-head");
  const logo = el("div", "topbar-logo", "▣");
  head.appendChild(logo);
  drawer.appendChild(head);

  const proj = el("div", "drawer-project");
  proj.appendChild(el("span", "proj-name", state.meta.projectName));
  proj.appendChild(el("span", "", "|"));
  proj.appendChild(el("span", "", `${state.meta.canvasName} ▾`));
  drawer.appendChild(proj);

  const tabs = el("div", "drawer-tabs");
  for (const [id, label] of [["canvas", "画布"], ["assets", "资产"]]) {
    const tab = el("button", `drawer-tab${state.ui.drawerTab === id ? " active" : ""}`, label);
    tab.addEventListener("click", () => store.set((s) => { s.ui.drawerTab = id; }));
    tabs.appendChild(tab);
  }
  drawer.appendChild(tabs);

  const body = el("div", "drawer-body");
  if (state.ui.drawerTab === "canvas") {
    drawer.appendChild(canvasToolbar());
    renderCanvasTree(state, store, body);
  } else {
    const search = el("div", "drawer-search");
    search.innerHTML = icon("search", 13);
    const input = document.createElement("input");
    input.placeholder = "请输入搜索内容";
    search.appendChild(input);
    drawer.appendChild(search);
    renderAssets(state, body);
  }
  drawer.appendChild(body);

  const foot = el("div", "drawer-foot");
  const collapse = el("button", "icon-btn", "⇤");
  collapse.title = "收起节点侧栏";
  collapse.addEventListener("click", () => store.set((s) => { s.ui.drawerOpen = false; }));
  foot.appendChild(collapse);
  foot.appendChild(el("span", "", `共 ${state.order.length} 节点`));
  drawer.appendChild(foot);
}

function canvasToolbar() {
  const bar = el("div", "drawer-toolbar");
  bar.appendChild(el("span", "", "画布元素"));
  bar.appendChild(el("span", "", "全部 ▾"));
  return bar;
}

function renderCanvasTree(state, store, body) {
  if (!state.order.length) {
    body.appendChild(el("div", "drawer-empty", "当前画布没有内容"));
    return;
  }
  const grouped = new Set();
  for (const group of Object.values(state.groups)) {
    const wrap = el("div", "tree-group");
    const head = el("div", "tree-group-head");
    head.innerHTML = `<span>▾</span>${icon("folder", 13)}<span>${group.title}</span>`;
    wrap.appendChild(head);
    for (const id of group.nodeIds) {
      const node = state.nodes[id];
      if (!node) continue;
      grouped.add(id);
      wrap.appendChild(treeItem(state, store, node));
    }
    body.appendChild(wrap);
  }
  for (const id of [...state.order].reverse()) {
    if (grouped.has(id)) continue;
    const node = state.nodes[id];
    if (node) body.appendChild(treeItem(state, store, node));
  }
}

function treeItem(state, store, node) {
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  const item = el("button", `tree-item${state.selection.nodeIds.includes(node.id) ? " selected" : ""}`);
  item.innerHTML = `<span class="tree-icon">${icon(def.icon, 12)}</span><span class="tree-label">${node.title}</span>`;
  item.addEventListener("click", () => {
    store.set((s) => {
      s.selection = { nodeIds: [node.id], edgeId: null };
      const root = document.getElementById("canvas-root").getBoundingClientRect();
      const single = { [node.id]: node };
      const fitted = fitViewport(single, root.width, root.height, 200);
      s.viewport = fitted;
    });
  });
  const remove = el("button", "icon-btn");
  remove.innerHTML = icon("x", 11);
  remove.title = "删除节点";
  remove.addEventListener("click", (e) => {
    e.stopPropagation();
    deleteNodes(store, [node.id]);
  });
  item.appendChild(remove);
  return item;
}

function renderAssets(state, body) {
  if (!state.assets.length) {
    const empty = el("div", "drawer-empty");
    empty.innerHTML = `<span class="folder-glyph">${icon("folder", 34)}</span>暂无资产`;
    body.appendChild(empty);
    return;
  }
  for (const asset of state.assets) {
    const item = el("button", "tree-item");
    item.innerHTML = `<span class="tree-icon">${icon("archive", 12)}</span><span class="tree-label">${asset.title}</span>`;
    body.appendChild(item);
  }
}

function drawerSignature(state) {
  return [
    state.ui.drawerOpen, state.ui.drawerTab,
    state.order.join(","),
    state.selection.nodeIds.join(","),
    Object.keys(state.groups).join(","),
    state.assets.length,
    ...Object.values(state.nodes).map((n) => n.title),
  ].join("|");
}
