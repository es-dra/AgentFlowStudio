import { NODE_TYPES, NODE_MENU_ORDER, createNode, connect, downstreamTypesFor, effectiveHeight } from "../nodes.js";
import { screenToWorld, rectsIntersect } from "../geometry.js";
import { showPopover, el } from "../overlay.js";
import { icon } from "../icons.js";
import { ACTION_GROUPS, createActionNode } from "../action-registry.js";

const QUICK_ACTION_IDS = ["node_text", "node_image", "node_video", "node_script", "node_director"];

export function openAddNodeMenu(store, runtime, screenPoint, anchorEl = null) {
  let closeRef = () => {};
  const pop = buildMenu((action) => {
    const world = screenToWorld(store.get().viewport, screenPoint.x, screenPoint.y);
    const position = openPositionNear(store, action, world.x - 140, world.y - 40);
    spawn(store, action, position.x, position.y);
  }, () => closeRef());
  if (anchorEl) {
    closeRef = showPopover(anchorEl, pop, { place: "top" });
    return closeRef;
  }
  const anchor = el("div");
  anchor.style.cssText = `position:fixed;left:${screenPoint.x}px;top:${screenPoint.y}px;width:1px;height:1px;pointer-events:none;`;
  document.body.appendChild(anchor);
  closeRef = showPopover(anchor, pop, { place: "bottom", onClose: () => anchor.remove() });
  return closeRef;
}

export function openReferenceMenu(store, runtime, fromNode, anchorEl) {
  const allowed = new Set(downstreamTypesFor(fromNode.type));
  const pop = el("div");
  pop.appendChild(el("div", "menu-title", "引用该节点生成"));
  for (const type of NODE_MENU_ORDER) {
    if (type === "library") continue;
    const def = NODE_TYPES[type];
    const item = menuItem(def.icon, def.label, def.tag);
    item.disabled = !allowed.has(type);
    item.addEventListener("click", () => {
      if (item.disabled) return;
      const node = spawn(store, { id: `node_${type}`, type, label: def.label }, fromNode.x + fromNode.w + 160, fromNode.y);
      connect(store, fromNode.id, node.id);
      close();
    });
    pop.appendChild(item);
  }
  const refItem = menuItem("link", "参考节点");
  refItem.addEventListener("click", () => {
    const node = spawn(store, { id: "node_reference", type: "text", label: "参考节点" }, fromNode.x + fromNode.w + 160, fromNode.y);
    store.set((s) => {
      const n = s.nodes[node.id];
      n.title = "参考节点";
      n.content = `引用：${fromNode.title}`;
      n.h = 160;
      n.params.isReference = true;
    });
    connect(store, fromNode.id, node.id);
    close();
  });
  pop.appendChild(refItem);
  const close = showPopover(anchorEl, pop, { place: "right" });
}

function buildMenu(onPick, onDone) {
  const pop = el("div");
  pop.classList.add("action-registry-menu");
  pop.style.minWidth = "420px";
  pop.appendChild(quickCreatePanel(onPick, onDone));
  pop.appendChild(el("div", "menu-title secondary", "全部类型"));
  for (const group of ACTION_GROUPS) {
    pop.appendChild(el("div", "menu-title", group.label));
    for (const action of group.actions) {
      const item = menuItem(action.icon, action.label, action.tag, action.requires_gate);
      item.addEventListener("click", () => {
        onPick(action);
        onDone();
      });
      pop.appendChild(item);
    }
  }
  return pop;
}

function quickCreatePanel(onPick, onDone) {
  const panel = el("div", "quick-create-panel");
  panel.appendChild(el("div", "quick-create-title", "双击创建"));
  panel.appendChild(el("div", "quick-create-hint", "先放一个常用节点，再继续连接生成流程。"));
  const grid = el("div", "quick-create-grid");
  for (const action of quickActions()) {
    const item = el("button", "quick-create-card");
    item.dataset.tone = quickTone(action);
    item.innerHTML = [
      `<span class="quick-create-icon">${icon(action.icon, 15)}</span>`,
      `<span><strong>${action.label}</strong><small>${quickHint(action)}</small></span>`,
    ].join("");
    item.addEventListener("click", () => {
      onPick(action);
      onDone();
    });
    grid.appendChild(item);
  }
  panel.appendChild(grid);
  return panel;
}

function quickActions() {
  const actions = ACTION_GROUPS.flatMap((group) => group.actions);
  return QUICK_ACTION_IDS.map((id) => actions.find((action) => action.id === id)).filter(Boolean);
}

function quickTone(action) {
  return {
    node_text: "story",
    node_image: "scene",
    node_video: "video",
    node_script: "story",
    node_director: "revision",
  }[action.id] || "story";
}

function quickHint(action) {
  return {
    node_text: "写想法",
    node_image: "放参考图",
    node_video: "做片段",
    node_script: "拆脚本",
    node_director: "控镜头",
  }[action.id] || "新节点";
}

function spawn(store, action, wx, wy) {
  if (action?.type === "library") {
    const node = createNode(store, "text", wx, wy);
    store.set((s) => {
      const n = s.nodes[node.id];
      n.params.actionId = action.id;
      n.params.actionLabel = action.label;
      n.title = action.label || "素材库";
      n.content = `${action.label || "素材库"}：从项目素材、生成历史或固定资产中选择引用。`;
      n.h = 160;
      n.status = "complete";
    });
    return node;
  }
  return createActionNode(store, action, wx, wy);
}

function openPositionNear(store, action, wx, wy) {
  const nodeType = action?.type === "library" ? "text" : action?.type || "text";
  const def = NODE_TYPES[nodeType] || NODE_TYPES.text;
  const base = { x: Math.round(wx), y: Math.round(wy), w: def.size.w, h: def.size.h };
  const existing = Object.values(store.get().nodes || {}).map((node) => ({
    x: node.x - 28,
    y: node.y - 28,
    w: node.w + 56,
    h: effectiveHeight(node) + 56,
  }));
  const stepX = Math.max(base.w + 80, 360);
  const stepY = Math.max(base.h + 80, 330);
  const offsets = [
    [0, 0],
    [stepX, 0],
    [0, stepY],
    [stepX, stepY],
    [-stepX, 0],
    [0, -stepY],
    [stepX * 2, 0],
    [-stepX, stepY],
    [stepX, -stepY],
    [0, stepY * 2],
  ];
  for (const [dx, dy] of offsets) {
    const candidate = { ...base, x: base.x + dx, y: base.y + dy };
    if (!existing.some((rect) => rectsIntersect(candidate, rect))) return candidate;
  }
  return { ...base, x: base.x + stepX * (existing.length + 1), y: base.y };
}

function menuItem(iconName, label, tag, gate) {
  const item = el("button", "menu-item");
  item.innerHTML = [
    `<span class="mi-icon">${icon(iconName, 14)}</span>`,
    `<span><span>${label}</span>${gate ? `<span class="mi-sub">需要 ${gate}</span>` : ""}</span>`,
    tag ? `<span class="mi-tag${tag === "NEW" ? " new" : ""}">${tag}</span>` : "",
  ].join("");
  return item;
}
