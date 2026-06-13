import { NODE_TYPES, NODE_MENU_ORDER, RESOURCE_ENTRIES, createNode, connect, downstreamTypesFor, effectiveHeight } from "../nodes.js";
import { screenToWorld, rectsIntersect } from "../geometry.js";
import { showPopover, el } from "../overlay.js";
import { icon } from "../icons.js";

export function openAddNodeMenu(store, runtime, screenPoint, anchorEl = null) {
  let closeRef = () => {};
  const pop = buildMenu(store, (type) => {
    const world = screenToWorld(store.get().viewport, screenPoint.x, screenPoint.y);
    const position = openPositionNear(store, type, world.x - 140, world.y - 40);
    spawn(store, type, position.x, position.y);
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
      const node = spawn(store, type, fromNode.x + fromNode.w + 160, fromNode.y);
      connect(store, fromNode.id, node.id);
      close();
    });
    pop.appendChild(item);
  }
  const refItem = menuItem("link", "参考节点");
  refItem.addEventListener("click", () => {
    const node = spawn(store, "text", fromNode.x + fromNode.w + 160, fromNode.y);
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

function buildMenu(store, onPick, onDone) {
  const pop = el("div");
  pop.style.minWidth = "210px";
  pop.appendChild(el("div", "menu-title", "添加节点"));
  for (const type of NODE_MENU_ORDER) {
    const def = NODE_TYPES[type];
    const item = menuItem(def.icon, def.label, def.tag);
    item.addEventListener("click", () => {
      onPick(type);
      onDone();
    });
    pop.appendChild(item);
  }
  pop.appendChild(el("div", "menu-title", "添加资源"));
  for (const entry of RESOURCE_ENTRIES) {
    const item = menuItem(entry.icon, entry.label);
    item.addEventListener("click", () => {
      onPick("image");
      onDone();
    });
    pop.appendChild(item);
  }
  return pop;
}

function spawn(store, type, wx, wy) {
  if (type === "library") {
    const node = createNode(store, "text", wx, wy);
    store.set((s) => {
      const n = s.nodes[node.id];
      n.title = "素材库";
      n.content = "素材库节点：从风格库 / 特效库选择素材后挂载到此节点。";
      n.h = 160;
    });
    return node;
  }
  return createNode(store, type, wx, wy);
}

function openPositionNear(store, type, wx, wy) {
  const nodeType = type === "library" ? "text" : type;
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

function menuItem(iconName, label, tag) {
  const item = el("button", "menu-item");
  item.innerHTML = `<span class="mi-icon">${icon(iconName, 14)}</span><span>${label}</span>${tag ? `<span class="mi-tag${tag === "NEW" ? " new" : ""}">${tag}</span>` : ""}`;
  return item;
}
